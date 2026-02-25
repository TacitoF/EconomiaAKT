import disnake
from disnake.ext import commands, tasks
import aiohttp
import os
import database as db
from datetime import datetime, timedelta
import asyncio


LIMITES_CARGO = {
    "Lêmure":      400,
    "Macaquinho":  1500,
    "Babuíno":     4500,
    "Chimpanzé":   12000,
    "Orangutango": 30000,
    "Gorila":      80000,
    "Ancestral":   250000,
    "Rei Símio":   1500000,
}

LIGAS_EMOJI = {
    "BSA": "🇧🇷",
    "PL":  "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "PD":  "🇪🇸",
    "CL":  "⭐",
    "SA":  "🇮🇹",
    "BL1": "🇩🇪",
    "PPL": "🇵🇹",
}

def get_limite(cargo):
    return LIMITES_CARGO.get(cargo, 400)

def hora_br(utc_str):
    """Converte string UTC ISO para horário de Brasília formatado."""
    dt = datetime.fromisoformat(utc_str.replace('Z', ''))
    return (dt - timedelta(hours=3)).strftime('%d/%m às %H:%M')

class Esportes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://api.football-data.org/v4"
        self.headers = {"X-Auth-Token": os.getenv("FOOTBALL_API_KEY") or ""}
        self.cache_jogos = None
        self.cache_time  = None
        self.checar_resultados.start()

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"⚽ {ctx.author.mention}, as apostas esportivas ficam no {mencao}!", delete_after=10)
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["jogos_hoje"])
    async def futebol(self, ctx):
        """Lista os próximos jogos mais importantes programados"""
        agora = datetime.now()
        if self.cache_jogos and self.cache_time and (agora - self.cache_time) < timedelta(minutes=30):
            return await ctx.send(embed=self.cache_jogos)

        await ctx.send("🔎 Consultando o calendário... Aguarde!", delete_after=5)

        try:
            async with aiohttp.ClientSession() as session:
                hoje_str   = agora.strftime("%Y-%m-%d")
                futuro_str = (agora + timedelta(days=3)).strftime("%Y-%m-%d")
                params = {
                    "competitions": "BSA,PL,PD,CL,SA,BL1,PPL",
                    "status":       "SCHEDULED",
                    "dateFrom":     hoje_str,
                    "dateTo":       futuro_str,
                }
                async with session.get(f"{self.api_url}/matches", headers=self.headers, params=params) as resp:
                    print(f"🔄 Chamadas API Futebol restantes: {resp.headers.get('X-Requests-Available-Minute')}")
                    data = await resp.json()

                    if 'errorCode' in data or resp.status != 200:
                        print(f"⚠️ Erro na API de Futebol: {data.get('message', resp.status)}")
                        return await ctx.send("❌ Não consegui acessar os jogos no momento. Verifique o console.")

                    if 'matches' not in data or not data['matches']:
                        return await ctx.send("⚽ Nenhum jogo das grandes ligas programado para os próximos 3 dias.")

                    embed = disnake.Embed(
                        title="⚽ BETS DA SELVA — PRÓXIMOS JOGOS",
                        description=(
                            "Use `!palpite <ID> <casa/empate/fora> <valor>` para apostar\n"
                            "💰 Odd fixa de **2.0x** · 📋 Veja seus bilhetes com `!pule`"
                        ),
                        color=disnake.Color.blue()
                    )

                    for match in data['matches'][:12]:
                        m_id      = match['id']
                        home      = match['homeTeam']['name']
                        away      = match['awayTeam']['name']
                        liga_code = match.get('competition', {}).get('code', '')
                        liga_nome = match.get('competition', {}).get('name', liga_code)
                        emoji     = LIGAS_EMOJI.get(liga_code, "🏆")
                        horario   = hora_br(match['utcDate'])

                        embed.add_field(
                            name=f"{emoji} {liga_nome}  •  ⏰ {horario}",
                            value=(
                                f"🏠 **{home}** vs **{away}** ✈️\n"
                                f"`!palpite {m_id} casa/empate/fora <valor>`"
                            ),
                            inline=False
                        )

                    embed.set_footer(text=f"Atualizado às {agora.strftime('%H:%M')} • Cache de 30 min")
                    self.cache_jogos = embed
                    self.cache_time  = agora
                    await ctx.send(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !futebol: {e}")
            await ctx.send("⚠️ Ocorreu um erro ao buscar os jogos. Tente novamente!")

    @commands.command()
    async def palpite(self, ctx, match_id: int = None, palpite_escolha: str = None, valor: float = None):
        """Faz uma aposta em um jogo real e salva no Google Sheets"""
        if match_id is None or palpite_escolha is None or valor is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!palpite <ID do Jogo> <casa/empate/fora> <valor>`")

        palpite_escolha = palpite_escolha.lower()
        if palpite_escolha not in ["casa", "empate", "fora"]:
            return await ctx.send("❌ Opção inválida! Escolha entre: `casa`, `empate` ou `fora`.")

        if valor <= 0:
            return await ctx.send("❌ O valor da aposta deve ser maior que zero!")
        valor = round(valor, 2)

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send(f"❌ {ctx.author.mention}, conta não encontrada!")

            saldo = db.parse_float(user['data'][2])
            cargo = user['data'][3] if len(user['data']) > 3 else "Lêmure"

            if saldo < valor:
                return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")
            if valor > get_limite(cargo):
                return await ctx.send(f"🚫 Limite de aposta para **{cargo}** é de **{get_limite(cargo)} MC**!")

            msg_buscando = await ctx.send(f"📊 {ctx.author.mention}, validando a partida...")

            jogo_valido  = False
            time_casa    = None
            time_fora    = None
            status_jogo  = None
            horario_jogo = None
            liga_jogo    = None

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/matches/{match_id}", headers=self.headers) as resp:
                    if resp.status == 404:
                        await msg_buscando.delete()
                        return await ctx.send(
                            f"❌ {ctx.author.mention}, o ID `{match_id}` não corresponde a nenhum jogo. "
                            f"Use `!futebol` para ver os IDs válidos."
                        )
                    if resp.status != 200:
                        await msg_buscando.delete()
                        return await ctx.send(
                            f"⚠️ {ctx.author.mention}, não foi possível validar a partida no momento "
                            f"(erro {resp.status}). Tente novamente mais tarde."
                        )

                    match_data = await resp.json()

                    if 'id' not in match_data:
                        await msg_buscando.delete()
                        return await ctx.send(
                            f"❌ {ctx.author.mention}, o ID `{match_id}` não é válido. "
                            f"Use `!futebol` para ver os jogos disponíveis."
                        )

                    status_jogo  = match_data.get('status', '')
                    time_casa    = match_data['homeTeam']['name']
                    time_fora    = match_data['awayTeam']['name']
                    horario_jogo = hora_br(match_data['utcDate'])
                    liga_jogo    = match_data.get('competition', {}).get('name', '')
                    jogo_valido  = True

            if status_jogo in ('FINISHED', 'IN_PLAY', 'PAUSED', 'SUSPENDED', 'CANCELLED', 'POSTPONED'):
                await msg_buscando.delete()
                status_pt = {
                    'FINISHED':  'já encerrado',
                    'IN_PLAY':   'em andamento',
                    'PAUSED':    'pausado',
                    'SUSPENDED': 'suspenso',
                    'CANCELLED': 'cancelado',
                    'POSTPONED': 'adiado',
                }.get(status_jogo, status_jogo)
                return await ctx.send(
                    f"⛔ {ctx.author.mention}, não é possível apostar nesta partida — ela está **{status_pt}**!\n"
                    f"Use `!futebol` para ver jogos disponíveis para aposta."
                )

            await msg_buscando.edit(content=f"🎟️ {ctx.author.mention}, gerando o seu bilhete...")

            EMOJI_PALPITE = {"casa": "🏠", "empate": "🤝", "fora": "✈️"}
            if palpite_escolha == "casa":
                nome_palpite = time_casa
            elif palpite_escolha == "fora":
                nome_palpite = time_fora
            else:
                nome_palpite = "Empate"

            odd_fixa        = 2.0
            ganho_potencial = round(valor * odd_fixa, 2)

            db.update_value(user['row'], 3, round(saldo - valor, 2))
            db.registrar_aposta_esportiva(ctx.author.id, match_id, palpite_escolha, valor, odd_fixa)

            await msg_buscando.delete()

            emoji_p = EMOJI_PALPITE[palpite_escolha]
            embed = disnake.Embed(title="🎟️ BILHETE REGISTRADO!", color=disnake.Color.gold())
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            embed.add_field(name="⚽ Partida",        value=f"**{time_casa}** vs **{time_fora}**", inline=False)
            embed.add_field(name="🏆 Liga",           value=liga_jogo or "—",                      inline=True)
            embed.add_field(name="⏰ Data/Hora",      value=horario_jogo or "—",                   inline=True)
            embed.add_field(name="🆔 Jogo ID",        value=f"`{match_id}`",                        inline=True)
            embed.add_field(name=f"{emoji_p} Palpite",value=f"**{nome_palpite}**",                  inline=True)
            embed.add_field(name="💸 Apostado",       value=f"`{valor:.2f} MC`",                    inline=True)
            embed.add_field(name="💰 Retorno",        value=f"`{ganho_potencial:.2f} MC`",           inline=True)
            embed.set_footer(text="Pagamento automático ao fim da partida • !pule para ver seus bilhetes")
            await ctx.send(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !palpite de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro ao registrar a aposta.")

    @commands.command(aliases=["palpites", "cupom", "cupoms", "cupons"])
    async def pule(self, ctx):
        """Mostra os bilhetes pendentes do usuário com todas as informações"""
        try:
            await ctx.message.delete()
        except:
            pass

        msg = await ctx.send(f"🔎 {ctx.author.mention}, buscando seus bilhetes...")

        try:
            pendentes = db.obter_apostas_pendentes()
            minhas    = [a for a in pendentes if str(a['user_id']) == str(ctx.author.id)]

            if not minhas:
                return await msg.edit(content=f"⚽ {ctx.author.mention}, você não tem nenhum bilhete pendente no momento!")

            agora       = datetime.now()
            data_inicio = (agora - timedelta(days=3)).strftime("%Y-%m-%d")
            data_fim    = (agora + timedelta(days=7)).strftime("%Y-%m-%d")

            info_jogos = {}
            async with aiohttp.ClientSession() as session:
                params = {"dateFrom": data_inicio, "dateTo": data_fim}
                async with session.get(f"{self.api_url}/matches", headers=self.headers, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for match in data.get('matches', []):
                            info_jogos[str(match['id'])] = {
                                "home":      match['homeTeam']['name'],
                                "away":      match['awayTeam']['name'],
                                "hora":      hora_br(match['utcDate']),
                                "liga":      match.get('competition', {}).get('name', ''),
                                "liga_code": match.get('competition', {}).get('code', ''),
                            }

            total_apostado = sum(a['valor'] for a in minhas)
            total_retorno  = sum(round(a['valor'] * a['odd'], 2) for a in minhas)

            embed = disnake.Embed(
                title="🎟️ SEUS BILHETES PENDENTES",
                description=(
                    f"**{len(minhas)} bilhete(s)** aguardando resultado\n"
                    f"💸 Total apostado: `{total_apostado:.2f} MC`  •  "
                    f"💰 Retorno potencial: `{total_retorno:.2f} MC`"
                ),
                color=disnake.Color.orange()
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)

            EMOJI_PALPITE = {"casa": "🏠", "fora": "✈️", "empate": "🤝"}

            for aposta in minhas[:15]:
                ganho_potencial = round(aposta['valor'] * aposta['odd'], 2)
                m_id  = str(aposta['match_id'])
                info  = info_jogos.get(m_id, {})

                time_casa = info.get("home", "Time da Casa")
                time_fora = info.get("away", "Time Visitante")
                horario   = info.get("hora", "—")
                liga      = info.get("liga", "—")
                emoji_l   = LIGAS_EMOJI.get(info.get("liga_code", ""), "🏆")

                palpite_bruto = aposta['palpite'].lower()
                emoji_p = EMOJI_PALPITE.get(palpite_bruto, "🎯")
                if palpite_bruto == "casa":
                    palpite_fmt = time_casa
                elif palpite_bruto == "fora":
                    palpite_fmt = time_fora
                else:
                    palpite_fmt = "Empate"

                embed.add_field(
                    name=f"⚽ {time_casa} vs {time_fora}",
                    value=(
                        f"{emoji_l} {liga}  •  ⏰ {horario}\n"
                        f"{emoji_p} **Palpite:** {palpite_fmt}\n"
                        f"💸 `{aposta['valor']:.2f} MC` → 💰 `{ganho_potencial:.2f} MC`\n"
                        f"🆔 ID: `{m_id}`"
                    ),
                    inline=False
                )

            embed.set_footer(text="Os prêmios são pagos automaticamente ao fim de cada partida")
            await msg.edit(content=None, embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !pule de {ctx.author}: {e}")
            await msg.edit(content=f"⚠️ {ctx.author.mention}, erro ao buscar bilhetes. Tente novamente!")

    @tasks.loop(minutes=60, reconnect=True)
    async def checar_resultados(self):
        print("🔄 checar_resultados: verificando apostas pendentes...")
        apostas_pendentes = db.obter_apostas_pendentes()
        if not apostas_pendentes:
            print("ℹ️ checar_resultados: nenhuma aposta pendente.")
            return
        print(f"📋 checar_resultados: {len(apostas_pendentes)} aposta(s) pendente(s) encontrada(s).")

        agora       = datetime.utcnow()
        data_inicio = (agora - timedelta(days=3)).strftime("%Y-%m-%d")
        data_fim    = (agora + timedelta(days=1)).strftime("%Y-%m-%d")

        try:
            async with aiohttp.ClientSession() as session:
                params = {"status": "FINISHED", "dateFrom": data_inicio, "dateTo": data_fim}
                async with session.get(f"{self.api_url}/matches", headers=self.headers, params=params) as resp:
                    if resp.status != 200:
                        print(f"⚠️ Erro ao buscar resultados na API (Status: {resp.status})")
                        return

                    data = await resp.json()
                    if 'matches' not in data:
                        return

                    canal_cassino = disnake.utils.get(self.bot.get_all_channels(), name='🎰・akbet')
                    if not canal_cassino:
                        print('⚠️ checar_resultados: canal #🎰・akbet não encontrado! Verifique se o bot está no servidor.')
                    else:
                        print(f'✅ checar_resultados: canal encontrado → {canal_cassino.guild.name}')

                    for aposta in apostas_pendentes:
                        aposta_id = str(aposta['match_id'])

                        jogo_encontrado = None
                        for match in data['matches']:
                            if str(match['id']) == aposta_id:
                                jogo_encontrado = match
                                break

                        if not jogo_encontrado:
                            continue

                        gols_casa = jogo_encontrado['score']['fullTime']['home']
                        gols_fora = jogo_encontrado['score']['fullTime']['away']
                        home_nome = jogo_encontrado['homeTeam']['name']
                        away_nome = jogo_encontrado['awayTeam']['name']
                        placar    = f"{gols_casa} x {gols_fora}"
                        liga_nome = jogo_encontrado.get('competition', {}).get('name', '')

                        if gols_casa > gols_fora:   resultado_real = "casa"
                        elif gols_fora > gols_casa: resultado_real = "fora"
                        else:                       resultado_real = "empate"

                        # get_user só funciona se o usuário está no cache.
                        # fetch_user faz uma chamada à API do Discord se necessário.
                        try:
                            jogador = self.bot.get_user(int(aposta['user_id'])) or await self.bot.fetch_user(int(aposta['user_id']))
                        except Exception as fetch_err:
                            print(f'⚠️ checar_resultados: não encontrei o usuário {aposta["user_id"]} → {fetch_err}')
                            jogador = None
                        se_venceu = (aposta['palpite'].lower() == resultado_real)

                        LABEL = {"casa": home_nome, "fora": away_nome, "empate": "Empate"}

                        if se_venceu:
                            db.atualizar_status_aposta(aposta['row'], 'Venceu')
                            user_db = db.get_user_data(str(aposta['user_id']))
                            if user_db:
                                saldo_atual = db.parse_float(user_db['data'][2])
                                premio      = round(aposta['valor'] * aposta['odd'], 2)
                                db.update_value(user_db['row'], 3, round(saldo_atual + premio, 2))

                                if canal_cassino and jogador:
                                    embed = disnake.Embed(title="🏆 APOSTA VENCEDORA!", color=disnake.Color.green())
                                    embed.add_field(name="⚽ Partida",    value=f"**{home_nome}** vs **{away_nome}**",              inline=False)
                                    embed.add_field(name="🏆 Liga",       value=liga_nome or "—",                                   inline=True)
                                    embed.add_field(name="📊 Placar",     value=f"**{placar}**",                                    inline=True)
                                    embed.add_field(name="\u200b",        value="\u200b",                                           inline=True)
                                    embed.add_field(name="🎯 Palpite",    value=LABEL.get(aposta['palpite'].lower(), "—"),          inline=True)
                                    embed.add_field(name="💸 Apostado",   value=f"`{aposta['valor']:.2f} MC`",                     inline=True)
                                    embed.add_field(name="💰 Prêmio",     value=f"**{premio:.2f} MC**",                            inline=True)
                                    embed.set_footer(text="O saldo já foi creditado na sua conta!")
                                    await canal_cassino.send(content=f"🎉 {jogador.mention}", embed=embed)
                        else:
                            db.atualizar_status_aposta(aposta['row'], 'Perdeu')
                            if canal_cassino and jogador:
                                embed = disnake.Embed(title="💀 APOSTA PERDIDA", color=disnake.Color.red())
                                embed.add_field(name="⚽ Partida",    value=f"**{home_nome}** vs **{away_nome}**",              inline=False)
                                embed.add_field(name="🏆 Liga",       value=liga_nome or "—",                                   inline=True)
                                embed.add_field(name="📊 Placar",     value=f"**{placar}**",                                    inline=True)
                                embed.add_field(name="\u200b",        value="\u200b",                                           inline=True)
                                embed.add_field(name="✅ Resultado",  value=LABEL.get(resultado_real, resultado_real),          inline=True)
                                embed.add_field(name="❌ Seu Palpite",value=LABEL.get(aposta['palpite'].lower(), "—"),          inline=True)
                                embed.add_field(name="💸 Perdido",    value=f"`{aposta['valor']:.2f} MC`",                     inline=True)
                                embed.set_footer(text="Tente novamente com !palpite • veja jogos com !futebol")
                                await canal_cassino.send(content=f"{jogador.mention}", embed=embed)

        except Exception as e:
            print(f"❌ Erro no checar_resultados: {e}")

    @checar_resultados.before_loop
    async def before_checar_resultados(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)  # aguarda o cache de canais e servidores ser populado
        print("✅ checar_resultados: bot pronto, iniciando loop de apostas esportivas.")

def setup(bot):
    bot.add_cog(Esportes(bot))