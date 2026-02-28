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
    dt = datetime.fromisoformat(utc_str.replace('Z', ''))
    return (dt - timedelta(hours=3)).strftime('%d/%m às %H:%M')


# ──────────────────────────────────────────────
#  MODAL — pede o valor após escolher palpite
# ──────────────────────────────────────────────
class ModalValorAposta(disnake.ui.Modal):
    def __init__(self, match_id: int, palpite: str, time_casa: str, time_fora: str, liga: str, horario: str):
        self.match_id  = match_id
        self.palpite   = palpite
        self.time_casa = time_casa
        self.time_fora = time_fora
        self.liga      = liga
        self.horario   = horario

        EMOJI  = {"casa": "🏠", "empate": "🤝", "fora": "✈️"}
        LABELS = {"casa": time_casa, "empate": "Empate", "fora": time_fora}

        components = [
            disnake.ui.TextInput(
                label=f"{EMOJI.get(palpite,'🎯')} Apostando em: {LABELS.get(palpite, palpite)}",
                placeholder="Digite o valor em MC (ex: 100)",
                custom_id="valor_aposta",
                style=disnake.TextInputStyle.short,
                min_length=1,
                max_length=12,
            )
        ]
        super().__init__(title=f"💰 {time_casa} vs {time_fora}", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)

        valor_raw = inter.text_values.get("valor_aposta", "").strip().replace(",", ".")
        try:
            valor = round(float(valor_raw), 2)
        except ValueError:
            return await inter.edit_original_response(content="❌ Valor inválido! Digite apenas números (ex: `100` ou `50.50`).")

        if valor <= 0:
            return await inter.edit_original_response(content="❌ O valor deve ser maior que zero!")

        user = db.get_user_data(str(inter.author.id))
        if not user:
            return await inter.edit_original_response(content="❌ Conta não encontrada!")

        saldo  = db.parse_float(user['data'][2])
        cargo  = user['data'][3] if len(user['data']) > 3 else "Lêmure"
        limite = get_limite(cargo)

        if saldo < valor:
            return await inter.edit_original_response(
                content=f"❌ Saldo insuficiente! Você tem **{saldo:.2f} MC** e tentou apostar **{valor:.2f} MC**."
            )
        if valor > limite:
            return await inter.edit_original_response(
                content=f"🚫 Limite de aposta para **{cargo}** é de **{limite} MC**!"
            )

        odd_fixa        = 2.0
        ganho_potencial = round(valor * odd_fixa, 2)

        db.update_value(user['row'], 3, round(saldo - valor, 2))
        db.registrar_aposta_esportiva(
            inter.author.id, self.match_id, self.palpite, valor, odd_fixa,
            time_casa=self.time_casa, time_fora=self.time_fora,
            liga=self.liga, horario=self.horario,
        )

        EMOJI  = {"casa": "🏠", "empate": "🤝", "fora": "✈️"}
        LABELS = {"casa": self.time_casa, "empate": "Empate", "fora": self.time_fora}

        embed = disnake.Embed(title="🎟️ BILHETE REGISTRADO!", color=disnake.Color.gold())
        embed.set_author(name=inter.author.display_name, icon_url=inter.author.display_avatar.url)
        embed.add_field(name="⚽ Partida",                              value=f"**{self.time_casa}** vs **{self.time_fora}**", inline=False)
        embed.add_field(name="🏆 Liga",                                 value=self.liga or "—",                               inline=True)
        embed.add_field(name="⏰ Data/Hora",                            value=self.horario or "—",                            inline=True)
        embed.add_field(name="🆔 ID",                                   value=f"`{self.match_id}`",                           inline=True)
        embed.add_field(name=f"{EMOJI.get(self.palpite,'🎯')} Palpite", value=f"**{LABELS.get(self.palpite, self.palpite)}**",inline=True)
        embed.add_field(name="💸 Apostado",                             value=f"`{valor:.2f} MC`",                            inline=True)
        embed.add_field(name="💰 Retorno",                              value=f"`{ganho_potencial:.2f} MC`",                  inline=True)
        embed.set_footer(text="Pagamento automático ao fim da partida • !pule para ver seus bilhetes")
        await inter.edit_original_response(content=None, embed=embed)


# ──────────────────────────────────────────────
#  VIEW — botões Casa / Empate / Fora
# ──────────────────────────────────────────────
class ViewPalpiteJogo(disnake.ui.View):
    def __init__(self, match_id: int, time_casa: str, time_fora: str, liga: str, horario: str):
        super().__init__(timeout=120)
        self.match_id  = match_id
        self.time_casa = time_casa
        self.time_fora = time_fora
        self.liga      = liga
        self.horario   = horario

    async def _abrir_modal(self, inter: disnake.MessageInteraction, palpite: str):
        await inter.response.send_modal(ModalValorAposta(
            match_id  = self.match_id,
            palpite   = palpite,
            time_casa = self.time_casa,
            time_fora = self.time_fora,
            liga      = self.liga,
            horario   = self.horario,
        ))

    @disnake.ui.button(label="🏠 Casa",   style=disnake.ButtonStyle.primary)
    async def btn_casa(self, button, inter):   await self._abrir_modal(inter, "casa")

    @disnake.ui.button(label="🤝 Empate", style=disnake.ButtonStyle.secondary)
    async def btn_empate(self, button, inter): await self._abrir_modal(inter, "empate")

    @disnake.ui.button(label="✈️ Fora",   style=disnake.ButtonStyle.danger)
    async def btn_fora(self, button, inter):   await self._abrir_modal(inter, "fora")

    @disnake.ui.button(label="↩️ Voltar", style=disnake.ButtonStyle.secondary, row=1)
    async def btn_voltar(self, button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        await inter.delete_original_response()


# ──────────────────────────────────────────────
#  SELECT MENU — lista todos os jogos
# ──────────────────────────────────────────────
class SelectJogo(disnake.ui.StringSelect):
    def __init__(self, jogos: list):
        self.jogos_map = {str(j['id']): j for j in jogos}

        options = []
        for j in jogos:
            liga_code = j.get('competition', {}).get('code', '')
            emoji_str = LIGAS_EMOJI.get(liga_code, "🏆")
            label = f"{j['homeTeam']['name']} vs {j['awayTeam']['name']}"
            desc  = f"{j.get('competition',{}).get('name','')}  •  {hora_br(j['utcDate'])}"
            options.append(disnake.SelectOption(
                label       = label[:100],
                description = desc[:100],
                value       = str(j['id']),
                emoji       = emoji_str,
            ))

        super().__init__(
            placeholder = "⚽ Selecione um jogo para apostar...",
            options     = options,
            min_values  = 1,
            max_values  = 1,
        )

    async def callback(self, inter: disnake.MessageInteraction):
        match_id  = self.values[0]
        jogo      = self.jogos_map[match_id]
        time_casa = jogo['homeTeam']['name']
        time_fora = jogo['awayTeam']['name']
        liga_code = jogo.get('competition', {}).get('code', '')
        liga_nome = jogo.get('competition', {}).get('name', liga_code)
        horario   = hora_br(jogo['utcDate'])
        emoji_l   = LIGAS_EMOJI.get(liga_code, "🏆")

        embed = disnake.Embed(
            title       = f"⚽ {time_casa} vs {time_fora}",
            description = (
                f"{emoji_l} **{liga_nome}**  •  ⏰ {horario}\n\n"
                f"Escolha o seu palpite abaixo:"
            ),
            color = disnake.Color.blue()
        )
        embed.add_field(name="🏠 Casa",   value=time_casa,  inline=True)
        embed.add_field(name="🤝 Empate", value="Empate",   inline=True)
        embed.add_field(name="✈️ Fora",   value=time_fora,  inline=True)
        embed.add_field(name="💰 Odd fixa", value="**2.0x** para qualquer resultado", inline=False)
        embed.set_footer(text=f"ID: {match_id}")

        view = ViewPalpiteJogo(
            match_id  = int(match_id),
            time_casa = time_casa,
            time_fora = time_fora,
            liga      = liga_nome,
            horario   = horario,
        )
        await inter.response.send_message(embed=embed, view=view, ephemeral=True)


class ViewSelectJogos(disnake.ui.View):
    def __init__(self, jogos: list):
        super().__init__(timeout=None)
        self.add_item(SelectJogo(jogos))


# ──────────────────────────────────────────────
#  COG principal
# ──────────────────────────────────────────────
class Esportes(commands.Cog):
    def __init__(self, bot):
        self.bot      = bot
        self.api_url  = "https://api.football-data.org/v4"
        self.headers  = {"X-Auth-Token": os.getenv("FOOTBALL_API_KEY") or ""}
        self.cache_embed = None
        self.cache_jogos = None
        self.cache_time  = None
        self.checar_resultados.start()

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal  = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"⚽ {ctx.author.mention}, as apostas esportivas ficam no {mencao}!", delete_after=10)
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["jogos_hoje"])
    async def futebol(self, ctx):
        """Lista os próximos jogos num menu dropdown para apostas"""
        agora = datetime.now()

        if self.cache_embed and self.cache_jogos and self.cache_time and (agora - self.cache_time) < timedelta(minutes=30):
            view = ViewSelectJogos(self.cache_jogos)
            return await ctx.send(embed=self.cache_embed, view=view)

        aviso = await ctx.send("🔎 Consultando o calendário... Aguarde!", delete_after=5)

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
                    print(f"🔄 API Futebol restantes: {resp.headers.get('X-Requests-Available-Minute')}")
                    data = await resp.json()

                    if 'errorCode' in data or resp.status != 200:
                        print(f"⚠️ Erro na API: {data.get('message', resp.status)}")
                        return await ctx.send("❌ Não consegui acessar os jogos no momento.")

                    if 'matches' not in data or not data['matches']:
                        return await ctx.send("⚽ Nenhum jogo das grandes ligas programado para os próximos 3 dias.")

                    jogos = data['matches'][:25]

                    embed = disnake.Embed(
                        title       = "⚽ BETS DA SELVA — PRÓXIMOS JOGOS",
                        description = "Selecione um jogo no menu abaixo para fazer sua aposta!\n💰 Odd fixa de **2.0x** · 📋 Veja seus bilhetes com `!pule`",
                        color       = disnake.Color.blue()
                    )

                    ligas_vistas = {}
                    for j in jogos:
                        liga_code = j.get('competition', {}).get('code', '')
                        liga_nome = j.get('competition', {}).get('name', liga_code)
                        emoji_l   = LIGAS_EMOJI.get(liga_code, "🏆")
                        key       = liga_nome

                        linha = f"• **{j['homeTeam']['name']}** vs **{j['awayTeam']['name']}** — ⏰ {hora_br(j['utcDate'])}"
                        if key not in ligas_vistas:
                            ligas_vistas[key] = {"emoji": emoji_l, "linhas": []}
                        ligas_vistas[key]["linhas"].append(linha)

                    for liga_nome, info in ligas_vistas.items():
                        embed.add_field(
                            name   = f"{info['emoji']} {liga_nome}",
                            value  = "\n".join(info["linhas"]),
                            inline = False
                        )

                    embed.set_footer(text=f"Atualizado às {agora.strftime('%H:%M')} • Cache de 30 min")

                    view = ViewSelectJogos(jogos)

                    self.cache_embed = embed
                    self.cache_jogos = jogos
                    self.cache_time  = agora

                    await ctx.send(embed=embed, view=view)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !futebol: {e}")
            await ctx.send("⚠️ Ocorreu um erro ao buscar os jogos. Tente novamente!")

    @commands.command(aliases=["cupom", "cupoms", "cupons"])
    async def pule(self, ctx):
        """Mostra os bilhetes pendentes do usuário"""
        try:
            await ctx.message.delete()
        except:
            pass

        msg = await ctx.send(f"🔎 {ctx.author.mention}, buscando seus bilhetes...")

        try:
            pendentes = db.obter_apostas_pendentes()
            minhas    = [a for a in pendentes if str(a['user_id']) == str(ctx.author.id)]

            if not minhas:
                return await msg.edit(content=f"⚽ {ctx.author.mention}, nenhum bilhete pendente no momento!")

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
                title       = "🎟️ SEUS BILHETES PENDENTES",
                description = (
                    f"**{len(minhas)} bilhete(s)** aguardando resultado\n"
                    f"💸 Total apostado: `{total_apostado:.2f} MC`  •  "
                    f"💰 Retorno potencial: `{total_retorno:.2f} MC`"
                ),
                color = disnake.Color.orange()
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)

            EMOJI_P = {"casa": "🏠", "fora": "✈️", "empate": "🤝"}

            for aposta in minhas[:15]:
                ganho = round(aposta['valor'] * aposta['odd'], 2)
                m_id  = str(aposta['match_id'])
                info  = info_jogos.get(m_id, {})

                time_casa = info.get("home", "Time da Casa")
                time_fora = info.get("away", "Time Visitante")
                horario   = info.get("hora", "—")
                liga      = info.get("liga", "—")
                emoji_l   = LIGAS_EMOJI.get(info.get("liga_code", ""), "🏆")

                p = aposta['palpite'].lower()
                palpite_fmt = time_casa if p == "casa" else (time_fora if p == "fora" else "Empate")

                embed.add_field(
                    name  = f"⚽ {time_casa} vs {time_fora}",
                    value = (
                        f"{emoji_l} {liga}  •  ⏰ {horario}\n"
                        f"{EMOJI_P.get(p,'🎯')} **Palpite:** {palpite_fmt}\n"
                        f"💸 `{aposta['valor']:.2f} MC` → 💰 `{ganho:.2f} MC`\n"
                        f"🆔 ID: `{m_id}`"
                    ),
                    inline = False
                )

            embed.set_footer(text="Os prêmios são pagos automaticamente ao fim de cada partida")
            await msg.edit(content=None, embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !pule de {ctx.author}: {e}")
            await msg.edit(content=f"⚠️ {ctx.author.mention}, erro ao buscar bilhetes.")

    # ──────────────────────────────────────────
    #  Loop — checa resultados a cada 60 min
    #  FIX BUG 11: retry automático em caso de falha na API, com logging detalhado
    # ──────────────────────────────────────────
    @tasks.loop(minutes=15, reconnect=True)
    async def checar_resultados(self):
        print(f"🔄 [{datetime.utcnow().strftime('%H:%M:%S')}] checar_resultados: verificando {0} apostas por ID individual...")

        apostas_pendentes = db.obter_apostas_pendentes()
        if not apostas_pendentes:
            return

        # Agrupa IDs únicos para minimizar chamadas à API
        match_ids   = list(set(str(a['match_id']) for a in apostas_pendentes))
        processadas = 0
        canal_cassino = disnake.utils.get(self.bot.get_all_channels(), name='🎰・akbet')

        print(f"📋 checar_resultados: {len(apostas_pendentes)} aposta(s) pendente(s) em {len(match_ids)} jogo(s).")

        async with aiohttp.ClientSession() as session:
            for match_id in match_ids:
                try:
                    url = f"{self.api_url}/matches/{match_id}"
                    async with session.get(url, headers=self.headers,
                                           timeout=aiohttp.ClientTimeout(total=20)) as resp:

                        if resp.status == 429:
                            print(f"⚠️ Rate limit na API — aguardando 12s antes de continuar.")
                            await asyncio.sleep(12)
                            continue

                        if resp.status != 200:
                            print(f"⚠️ API retornou {resp.status} para jogo {match_id} — pulando.")
                            await asyncio.sleep(6)
                            continue

                        match_data = await resp.json()
                        status     = match_data.get('status')

                        # Só processa jogos efetivamente finalizados
                        if status not in ("FINISHED", "AWARDED"):
                            await asyncio.sleep(6)
                            continue

                        gols_casa = match_data.get('score', {}).get('fullTime', {}).get('home')
                        gols_fora = match_data.get('score', {}).get('fullTime', {}).get('away')

                        # Placar ainda não disponível (alguns instantes após o fim)
                        if gols_casa is None or gols_fora is None:
                            await asyncio.sleep(6)
                            continue

                        home_nome = match_data['homeTeam']['name']
                        away_nome = match_data['awayTeam']['name']
                        placar    = f"{gols_casa} x {gols_fora}"
                        liga_nome = match_data.get('competition', {}).get('name', '')

                        if gols_casa > gols_fora:   resultado_real = "casa"
                        elif gols_fora > gols_casa: resultado_real = "fora"
                        else:                       resultado_real = "empate"

                        LABEL = {"casa": home_nome, "fora": away_nome, "empate": "Empate"}

                        apostas_deste_jogo = [a for a in apostas_pendentes if str(a['match_id']) == match_id]

                        for aposta in apostas_deste_jogo:
                            palpite_key = aposta['palpite'].lower()
                            palpite_fmt = LABEL.get(palpite_key, aposta['palpite'])
                            se_venceu   = (palpite_key == resultado_real)
                            processadas += 1

                            try:
                                jogador = self.bot.get_user(int(aposta['user_id'])) or                                           await self.bot.fetch_user(int(aposta['user_id']))
                            except Exception:
                                jogador = None

                            if se_venceu:
                                db.atualizar_status_aposta(aposta['row'], 'Venceu')
                                user_db = db.get_user_data(str(aposta['user_id']))
                                if user_db:
                                    saldo_atual = db.parse_float(user_db['data'][2])
                                    premio      = round(aposta['valor'] * aposta['odd'], 2)
                                    db.update_value(user_db['row'], 3, round(saldo_atual + premio, 2))

                                    if canal_cassino and jogador:
                                        embed = disnake.Embed(title="🏆 APOSTA VENCEDORA!", color=disnake.Color.green())
                                        embed.set_author(name=jogador.display_name, icon_url=jogador.display_avatar.url)
                                        embed.add_field(name="⚽ Partida",  value=f"**{home_nome}** vs **{away_nome}**",      inline=False)
                                        embed.add_field(name="🏆 Liga",     value=liga_nome or "—",                           inline=True)
                                        embed.add_field(name="📊 Placar",   value=f"**{placar}**",                            inline=True)
                                        embed.add_field(name="​",      value="​",                                   inline=True)
                                        embed.add_field(name="🎯 Palpite",  value=palpite_fmt,                                inline=True)
                                        embed.add_field(name="💸 Apostado", value=f"`{formatar_moeda(aposta['valor'])} MC`",  inline=True)
                                        embed.add_field(name="💰 Prêmio",   value=f"**{formatar_moeda(premio)} MC**",         inline=True)
                                        embed.set_footer(text="O saldo já foi creditado na sua conta!")
                                        await canal_cassino.send(content=f"🎉 {jogador.mention}", embed=embed)
                            else:
                                db.atualizar_status_aposta(aposta['row'], 'Perdeu')
                                if canal_cassino and jogador:
                                    embed = disnake.Embed(title="💀 APOSTA PERDIDA", color=disnake.Color.red())
                                    embed.set_author(name=jogador.display_name, icon_url=jogador.display_avatar.url)
                                    embed.add_field(name="⚽ Partida",     value=f"**{home_nome}** vs **{away_nome}**",      inline=False)
                                    embed.add_field(name="🏆 Liga",        value=liga_nome or "—",                           inline=True)
                                    embed.add_field(name="📊 Placar",      value=f"**{placar}**",                            inline=True)
                                    embed.add_field(name="​",         value="​",                                   inline=True)
                                    embed.add_field(name="✅ Resultado",   value=LABEL.get(resultado_real, resultado_real),  inline=True)
                                    embed.add_field(name="❌ Seu Palpite", value=palpite_fmt,                                inline=True)
                                    embed.add_field(name="💸 Perdido",     value=f"`{formatar_moeda(aposta['valor'])} MC`",  inline=True)
                                    embed.set_footer(text="Veja os próximos jogos com !futebol")
                                    await canal_cassino.send(content=f"{jogador.mention}", embed=embed)

                except Exception as e:
                    print(f"❌ Erro ao checar jogo {match_id}: {e}")

                # Respeita o rate limit da API: máx ~6 chamadas/min no plano free
                await asyncio.sleep(6.5)

        if processadas > 0:
            print(f"✅ checar_resultados: {processadas} aposta(s) processada(s).")

    @checar_resultados.before_loop
    async def before_checar_resultados(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)
        print("✅ Bot pronto, iniciando loop de apostas esportivas.")


def setup(bot):
    bot.add_cog(Esportes(bot))