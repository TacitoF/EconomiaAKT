import disnake
from disnake.ext import commands, tasks
import aiohttp
import os
import database as db
from datetime import datetime, timedelta

# Limites de aposta sincronizados com o restante do projeto (shop.py, minas.py, etc.)
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

def get_limite(cargo):
    return LIMITES_CARGO.get(cargo, 400)

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

        await ctx.send("🔎 Consultando o calendário para os próximos dias... Aguarde!", delete_after=5)

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
                    print(f"🔄 Chamadas restantes: {resp.headers.get('X-Requests-Available-Minute')}")
                    data = await resp.json()

                    if 'errorCode' in data or resp.status != 200:
                        print(f"⚠️ Erro na API de Futebol: {data.get('message', resp.status)}")
                        return await ctx.send("❌ Não consegui acessar os jogos no momento. Verifique o console.")

                    if 'matches' not in data or not data['matches']:
                        return await ctx.send("⚽ Nenhum jogo das grandes ligas programado para os próximos 3 dias.")

                    embed = disnake.Embed(
                        title="⚽ BETS DA SELVA - PRÓXIMOS JOGOS ⚽",
                        description=(
                            "Para apostar use: `!palpite <ID> <casa/empate/fora> <valor>`\n"
                            "*Todos os jogos têm Odd fixa de 2.0x no sistema grátis.*"
                        ),
                        color=disnake.Color.blue()
                    )

                    for match in data['matches'][:10]:
                        match_id = match['id']
                        home     = match['homeTeam']['name']
                        away     = match['awayTeam']['name']

                        data_utc = datetime.fromisoformat(match['utcDate'].replace('Z', ''))
                        hora_br  = (data_utc - timedelta(hours=3)).strftime('%d/%m às %H:%M')

                        embed.add_field(
                            name=f"🆔 ID: {match_id} | ⏰ {hora_br}",
                            value=f"🏠 **{home}** (Casa) 🆚 **{away}** (Fora) ✈️",
                            inline=False
                        )

                    self.cache_jogos = embed
                    self.cache_time  = agora
                    await ctx.send(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !futebol: {e}")
            await ctx.send(f"⚠️ Ocorreu um erro ao buscar os jogos. Tente novamente!")

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
                return await ctx.send(f"🚫 Limite de aposta para **{cargo}** é de **{get_limite(cargo)} C**!")

            msg_buscando = await ctx.send(f"📊 {ctx.author.mention}, validando a partida e gerando o bilhete...")

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/matches/{match_id}", headers=self.headers) as resp:
                    print(f"🔄 Chamadas restantes: {resp.headers.get('X-Requests-Available-Minute')}")
                    match_data = await resp.json()

                    if 'id' not in match_data:
                        await msg_buscando.delete()
                        return await ctx.send(
                            f"❌ {ctx.author.mention}, partida não encontrada! "
                            f"Verifique se o ID `{match_id}` está correto."
                        )

                    time_casa = match_data['homeTeam']['name']
                    time_fora = match_data['awayTeam']['name']

            await msg_buscando.delete()

            if palpite_escolha == "casa":
                nome_palpite = f"{time_casa} (Casa)"
            elif palpite_escolha == "fora":
                nome_palpite = f"{time_fora} (Fora)"
            else:
                nome_palpite = "Empate"

            odd_fixa = 2.0

            db.update_value(user['row'], 3, round(saldo - valor, 2))
            db.registrar_aposta_esportiva(ctx.author.id, match_id, palpite_escolha, valor, odd_fixa)
            ganho_potencial = round(valor * odd_fixa, 2)

            embed = disnake.Embed(title="🎟️ BILHETE CADASTRADO!", color=disnake.Color.gold())
            embed.description = (
                f"**Apostador:** {ctx.author.mention}\n"
                f"**Jogo ID:** `{match_id}`\n"
                f"**Palpite:** `{nome_palpite}`\n"
                f"**Valor Apostado:** `{valor:.2f} C`\n"
                f"**Multiplicador:** `{odd_fixa}x`\n"
                f"**Retorno Potencial:** `{ganho_potencial:.2f} C`"
            )
            embed.set_footer(text="O pagamento será feito automaticamente quando a partida acabar!")
            await ctx.send(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !palpite de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro ao registrar a aposta.")

    @commands.command(aliases=["palpites", "cupom", "cupoms", "cupons"])
    async def pule(self, ctx):
        """Mostra os bilhetes pendentes do usuário com os nomes dos times"""
        try:
            await ctx.message.delete()
        except:
            pass

        msg = await ctx.send(f"🔎 {ctx.author.mention}, buscando seus bilhetes na gaveta...")

        try:
            pendentes = db.obter_apostas_pendentes()
            minhas    = [a for a in pendentes if str(a['user_id']) == str(ctx.author.id)]

            if not minhas:
                return await msg.edit(content=f"⚽ {ctx.author.mention}, você não tem nenhum bilhete pendente no momento!")

            agora        = datetime.now()
            data_inicio  = (agora - timedelta(days=3)).strftime("%Y-%m-%d")
            data_fim     = (agora + timedelta(days=7)).strftime("%Y-%m-%d")

            nomes_times = {}
            async with aiohttp.ClientSession() as session:
                params = {"dateFrom": data_inicio, "dateTo": data_fim}
                async with session.get(f"{self.api_url}/matches", headers=self.headers, params=params) as resp:
                    print(f"🔄 Chamadas restantes: {resp.headers.get('X-Requests-Available-Minute')}")
                    if resp.status == 200:
                        data = await resp.json()
                        for match in data.get('matches', []):
                            nomes_times[str(match['id'])] = {
                                "home": match['homeTeam']['name'],
                                "away": match['awayTeam']['name'],
                            }

            embed = disnake.Embed(
                title="🎟️ SEUS BILHETES PENDENTES",
                description=f"{ctx.author.mention}, aqui estão as suas apostas que aguardam o fim da partida:",
                color=disnake.Color.orange()
            )

            for aposta in minhas[:15]:
                ganho_potencial = round(aposta['valor'] * aposta['odd'], 2)
                m_id = str(aposta['match_id'])

                time_casa = nomes_times.get(m_id, {}).get("home", "Time da Casa")
                time_fora = nomes_times.get(m_id, {}).get("away", "Time Visitante")

                palpite_bruto = aposta['palpite']
                if palpite_bruto == "casa":
                    palpite_fmt = f"{time_casa} (Casa)"
                elif palpite_bruto == "fora":
                    palpite_fmt = f"{time_fora} (Fora)"
                else:
                    palpite_fmt = f"Empate ({time_casa} x {time_fora})"

                embed.add_field(
                    name=f"🆔 Jogo ID: {m_id}",
                    value=(
                        f"**Palpite:** `{palpite_fmt}`\n"
                        f"**Apostou:** `{aposta['valor']:.2f} C` ➔ **Retorno:** `{ganho_potencial:.2f} C`"
                    ),
                    inline=False
                )

            await msg.edit(content=None, embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !pule de {ctx.author}: {e}")
            await msg.edit(content=f"⚠️ {ctx.author.mention}, erro ao buscar bilhetes. Tente novamente!")

    @tasks.loop(minutes=60)
    async def checar_resultados(self):
        apostas_pendentes = db.obter_apostas_pendentes()
        if not apostas_pendentes:
            return

        agora        = datetime.now()
        data_inicio  = (agora - timedelta(days=3)).strftime("%Y-%m-%d")
        data_fim     = agora.strftime("%Y-%m-%d")

        try:
            async with aiohttp.ClientSession() as session:
                params = {"status": "FINISHED", "dateFrom": data_inicio, "dateTo": data_fim}
                async with session.get(f"{self.api_url}/matches", headers=self.headers, params=params) as resp:
                    print(f"🔄 Chamadas restantes: {resp.headers.get('X-Requests-Available-Minute')}")
                    data = await resp.json()

                    if 'matches' not in data:
                        return

                    canal_cassino = disnake.utils.get(self.bot.get_all_channels(), name='🎰・akbet')

                    for aposta in apostas_pendentes:
                        for match in data['matches']:
                            if str(match['id']) != str(aposta['match_id']):
                                continue

                            gols_casa = match['score']['fullTime']['home']
                            gols_fora = match['score']['fullTime']['away']

                            if gols_casa > gols_fora:   resultado_real = "casa"
                            elif gols_fora > gols_casa: resultado_real = "fora"
                            else:                       resultado_real = "empate"

                            jogador   = self.bot.get_user(int(aposta['user_id']))
                            se_venceu = aposta['palpite'] == resultado_real

                            if se_venceu:
                                db.atualizar_status_aposta(aposta['row'], 'Venceu')
                                user_db = db.get_user_data(str(aposta['user_id']))
                                if user_db:
                                    saldo_atual = db.parse_float(user_db['data'][2])
                                    premio      = round(aposta['valor'] * aposta['odd'], 2)
                                    db.update_value(user_db['row'], 3, round(saldo_atual + premio, 2))
                                    if canal_cassino and jogador:
                                        await canal_cassino.send(
                                            f"🏆 **APOSTA ESPORTIVA VENCEDORA!**\n"
                                            f"{jogador.mention} acertou que `{resultado_real.upper()}` venceria "
                                            f"no jogo `{match['id']}` e faturou **{premio:.2f} C**!"
                                        )
                            else:
                                db.atualizar_status_aposta(aposta['row'], 'Perdeu')
                                if canal_cassino and jogador:
                                    await canal_cassino.send(
                                        f"💀 **APOSTA PERDIDA!**\n"
                                        f"O jogo `{match['id']}` terminou com vitória de `{resultado_real.upper()}`. "
                                        f"{jogador.mention} perdeu o bilhete."
                                    )
        except Exception as e:
            print(f"❌ Erro no checar_resultados: {e}")

    @checar_resultados.before_loop
    async def before_checar_resultados(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(Esportes(bot))