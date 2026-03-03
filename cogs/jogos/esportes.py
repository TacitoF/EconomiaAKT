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
    dt = datetime.fromisoformat(utc_str.replace("Z", ""))
    return (dt - timedelta(hours=3)).strftime("%d/%m às %H:%M")

def formatar_moeda(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class ModalValorAposta(disnake.ui.Modal):
    def __init__(self, match_id, palpite, odd_fixa, time_casa, time_fora, liga, horario, api_url=None, api_headers=None):
        self.match_id    = match_id
        self.palpite     = palpite
        self.odd_fixa    = odd_fixa
        self.time_casa   = time_casa
        self.time_fora   = time_fora
        self.liga        = liga
        self.horario     = horario
        self.api_url     = api_url or "https://api.football-data.org/v4"
        self.api_headers = api_headers or {}
        
        EMOJI  = {"casa": "🏠", "empate": "🤝", "fora": "✈️"}
        LABELS = {"casa": time_casa, "empate": "Empate", "fora": time_fora}
        
        components = [
            disnake.ui.TextInput(
                label=f"{EMOJI.get(palpite,'🎯')} Aposta: {LABELS.get(palpite, palpite)} ({odd_fixa}x)",
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
            return await inter.edit_original_response(content="❌ Valor inválido!")
        if valor <= 0:
            return await inter.edit_original_response(content="❌ O valor deve ser maior que zero!")

        # ── 1. Verificar status do jogo na API ──────────────
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/matches/{self.match_id}",
                    headers=self.api_headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        match_data = await resp.json()
                        match_status = match_data.get("status", "")
                        if match_status not in ("SCHEDULED", "TIMED"):
                            status_msg = {
                                "IN_PLAY":  "🔴 Este jogo já está **em andamento**!",
                                "PAUSED":   "⏸️ Este jogo está **pausado** (intervalo).",
                                "FINISHED": "🏁 Este jogo já foi **finalizado**!",
                                "AWARDED":  "🏁 Este jogo já foi **encerrado**!",
                                "POSTPONED":"⚠️ Este jogo foi **adiado**.",
                                "CANCELLED":"⚠️ Este jogo foi **cancelado**.",
                                "SUSPENDED":"⚠️ Este jogo foi **suspenso**.",
                            }.get(match_status, f"⚠️ Status do jogo: `{match_status}`")
                            return await inter.edit_original_response(
                                content=f"{status_msg}\nNão é possível apostar nesta partida."
                            )
        except asyncio.TimeoutError:
            return await inter.edit_original_response(content="⚠️ Não foi possível verificar o status do jogo. Tente novamente.")
        except Exception as e:
            print(f"⚠️ Erro ao verificar status do jogo {self.match_id}: {e}")
            return await inter.edit_original_response(content="⚠️ Erro ao verificar o jogo. Tente novamente em instantes.")

        # ── 2. Verificar Trava de 1 Aposta por Jogo ──────────────
        pendentes = db.obter_apostas_pendentes()
        ja_apostou = any(str(a["user_id"]) == str(inter.author.id) and str(a["match_id"]) == str(self.match_id) for a in pendentes)
        if ja_apostou:
            return await inter.edit_original_response(
                content="🚫 **Aposta bloqueada!**\nVocê já tem um palpite registrado para este jogo. A selva só permite **1 aposta por partida**.\n*(Use `!pule` se quiser cancelar a aposta anterior e refazer).*"
            )

        # ── 3. Verificar Saldo e Limites ──────────────
        user = db.get_user_data(str(inter.author.id))
        if not user:
            return await inter.edit_original_response(content="❌ Conta não encontrada!")
        
        saldo  = db.parse_float(user["data"][2])
        cargo  = user["data"][3] if len(user["data"]) > 3 else "Lêmure"
        limite = get_limite(cargo)
        
        if saldo < valor:
            return await inter.edit_original_response(
                content=f"❌ Saldo insuficiente! Você tem **{formatar_moeda(saldo)} MC** e tentou apostar **{formatar_moeda(valor)} MC**."
            )
        if valor > limite:
            return await inter.edit_original_response(
                content=f"🚫 Limite de aposta para **{cargo}** é de **{formatar_moeda(limite)} MC**!"
            )
            
        ganho_potencial = round(valor * self.odd_fixa, 2)
        db.update_value(user["row"], 3, round(saldo - valor, 2))
        
        db.registrar_aposta_esportiva(
            inter.author.id, self.match_id, self.palpite, valor, self.odd_fixa,
            time_casa=self.time_casa, time_fora=self.time_fora,
            liga=self.liga, horario=self.horario,
        )
        
        EMOJI  = {"casa": "🏠", "empate": "🤝", "fora": "✈️"}
        LABELS = {"casa": self.time_casa, "empate": "Empate", "fora": self.time_fora}
        embed = disnake.Embed(title="🎟️ BILHETE REGISTRADO!", color=disnake.Color.gold())
        embed.set_author(name=inter.author.display_name, icon_url=inter.author.display_avatar.url)
        embed.add_field(name="⚽ Partida",  value=f"**{self.time_casa}** vs **{self.time_fora}**", inline=False)
        embed.add_field(name="🏆 Liga",     value=self.liga or "—",   inline=True)
        embed.add_field(name="⏰ Data/Hora",value=self.horario or "—", inline=True)
        embed.add_field(name="🆔 ID",       value=f"`{self.match_id}`",inline=True)
        embed.add_field(name=f"{EMOJI.get(self.palpite,'🎯')} Palpite", value=f"**{LABELS.get(self.palpite, self.palpite)}**", inline=True)
        embed.add_field(name="💸 Apostado", value=f"`{formatar_moeda(valor)} MC`",           inline=True)
        embed.add_field(name="💰 Retorno",  value=f"`{formatar_moeda(ganho_potencial)} MC` (Odd: {self.odd_fixa}x)", inline=True)
        embed.set_footer(text="Pagamento automático ao fim da partida • !pule para gerenciar seus bilhetes")
        await inter.edit_original_response(content=None, embed=embed)


class ViewPalpiteJogo(disnake.ui.View):
    def __init__(self, match_id, time_casa, time_fora, liga, horario, odds, api_url=None, api_headers=None):
        super().__init__(timeout=120)
        self.match_id    = match_id
        self.time_casa   = time_casa
        self.time_fora   = time_fora
        self.liga        = liga
        self.horario     = horario
        self.odds        = odds
        self.api_url     = api_url
        self.api_headers = api_headers or {}
        
        self.btn_casa.label = f"🏠 Casa ({odds['casa']}x)"
        self.btn_empate.label = f"🤝 Empate ({odds['empate']}x)"
        self.btn_fora.label = f"✈️ Fora ({odds['fora']}x)"

    async def _abrir_modal(self, inter, palpite):
        odd_escolhida = self.odds.get(palpite, 2.0)
        await inter.response.send_modal(ModalValorAposta(
            match_id=self.match_id, palpite=palpite, odd_fixa=odd_escolhida,
            time_casa=self.time_casa, time_fora=self.time_fora,
            liga=self.liga, horario=self.horario,
            api_url=self.api_url, api_headers=self.api_headers,
        ))

    @disnake.ui.button(style=disnake.ButtonStyle.primary, custom_id="btn_casa")
    async def btn_casa(self, button, inter):   await self._abrir_modal(inter, "casa")

    @disnake.ui.button(style=disnake.ButtonStyle.secondary, custom_id="btn_empate")
    async def btn_empate(self, button, inter): await self._abrir_modal(inter, "empate")

    @disnake.ui.button(style=disnake.ButtonStyle.danger, custom_id="btn_fora")
    async def btn_fora(self, button, inter):   await self._abrir_modal(inter, "fora")

    @disnake.ui.button(label="↩️ Voltar", style=disnake.ButtonStyle.secondary, row=1)
    async def btn_voltar(self, button, inter):
        await inter.response.defer()
        await inter.delete_original_response()


class SelectJogo(disnake.ui.StringSelect):
    def __init__(self, jogos, bot, api_url=None, api_headers=None):
        self.bot         = bot
        self.jogos_map   = {str(j["id"]): j for j in jogos}
        self.api_url     = api_url
        self.api_headers = api_headers or {}
        options = []
        for j in jogos:
            liga_code = j.get("competition", {}).get("code", "")
            options.append(disnake.SelectOption(
                label       = f"{j['homeTeam']['name']} vs {j['awayTeam']['name']}"[:100],
                description = f"{j.get('competition',{}).get('name','')}  •  {hora_br(j['utcDate'])}"[:100],
                value       = str(j["id"]),
                emoji       = LIGAS_EMOJI.get(liga_code, "🏆"),
            ))
        super().__init__(placeholder="⚽ Selecione um jogo para apostar...", options=options, min_values=1, max_values=1)

    async def callback(self, inter):
        await inter.response.defer(ephemeral=True)
        mid       = self.values[0]
        jogo      = self.jogos_map[mid]
        
        time_casa = jogo["homeTeam"]["name"]
        time_fora = jogo["awayTeam"]["name"]
        liga_code = jogo.get("competition", {}).get("code", "")
        liga_nome = jogo.get("competition", {}).get("name", liga_code)
        horario   = hora_br(jogo["utcDate"])
        
        # Odds fixadas em 2.0x
        odds = {"casa": 2.0, "empate": 2.0, "fora": 2.0}
        nota_analise = "💰 **Odd fixa:** `2.0x` para qualquer resultado."

        embed = disnake.Embed(
            title=f"⚽ {time_casa} vs {time_fora}",
            description=f"{LIGAS_EMOJI.get(liga_code,'🏆')} **{liga_nome}** •  ⏰ {horario}\n\n{nota_analise}\n*Escolha o seu palpite clicando nos botões:*",
            color=disnake.Color.blue()
        )
        embed.add_field(name="🏠 Casa",   value=f"**{time_casa}**", inline=True)
        embed.add_field(name="🤝 Empate", value="**Empate**",       inline=True)
        embed.add_field(name="✈️ Fora",   value=f"**{time_fora}**", inline=True)
        embed.set_footer(text=f"ID: {mid}  •  Limite de 1 aposta por jogo.")
        
        view = ViewPalpiteJogo(int(mid), time_casa, time_fora, liga_nome, horario, odds, api_url=self.api_url, api_headers=self.api_headers)
        await inter.edit_original_response(embed=embed, view=view)


class ViewSelectJogos(disnake.ui.View):
    def __init__(self, jogos, bot, api_url=None, api_headers=None):
        super().__init__(timeout=None)
        self.add_item(SelectJogo(jogos, bot, api_url=api_url, api_headers=api_headers))


# ── MENU DE CANCELAMENTO DE APOSTAS ──────────────────────────────────────────
class SelectCancelarAposta(disnake.ui.StringSelect):
    def __init__(self, apostas, info_jogos):
        self.apostas_map = {str(a["row"]): a for a in apostas}
        options = []
        
        for aposta in apostas[:25]: # Limite do Discord
            row_str = str(aposta["row"])
            m_id = str(aposta["match_id"])
            info = info_jogos.get(m_id, {})
            
            tc = info.get("home", aposta.get("time_casa", "Casa"))
            tf = info.get("away", aposta.get("time_fora", "Fora"))
            
            # Bloqueia cancelar se o jogo já começou ou acabou
            game_started = False
            if info and "utcDate" in info:
                try:
                    dt_game = datetime.strptime(info["utcDate"], "%Y-%m-%dT%H:%M:%SZ")
                    if datetime.utcnow() >= dt_game or info.get("status") in ["IN_PLAY", "PAUSED", "FINISHED"]:
                        game_started = True
                except:
                    pass
            
            if game_started:
                continue
                
            palpite = aposta["palpite"].capitalize()
            valor = aposta["valor"]
            
            options.append(disnake.SelectOption(
                label=f"{tc} x {tf}"[:100],
                description=f"Palpite: {palpite} | {formatar_moeda(valor)} MC",
                value=row_str,
                emoji="❌"
            ))
        
        if not options:
            options.append(disnake.SelectOption(label="Nenhuma aposta livre para cancelar", value="none"))
            super().__init__(placeholder="🚫 Nenhuma aposta pode ser cancelada agora", options=options, disabled=True)
        else:
            super().__init__(placeholder="🚫 Selecione uma aposta para cancelar...", options=options)

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.defer(ephemeral=True)
        row_str = self.values[0]
        if row_str == "none": return
        
        aposta = self.apostas_map.get(row_str)
        if not aposta:
            return await inter.edit_original_response(content="❌ Aposta não encontrada.")
            
        user_db = db.get_user_data(str(inter.author.id))
        if not user_db:
            return await inter.edit_original_response(content="❌ Conta não encontrada.")
            
        # Puxa tudo de novo para ter certeza de que ninguém já cancelou/liquidou
        all_pendentes = db.obter_apostas_pendentes()
        aposta_atualizada = next((a for a in all_pendentes if str(a["row"]) == row_str), None)
        
        if not aposta_atualizada or aposta_atualizada["status"] != "Pendente":
            return await inter.edit_original_response(content="❌ Esta aposta já foi liquidada ou cancelada!")
            
        saldo_atual = db.parse_float(user_db["data"][2])
        valor_reembolso = aposta_atualizada["valor"]
        novo_saldo = round(saldo_atual + valor_reembolso, 2)
        
        # Devolve o dinheiro e bota status "Reembolso"
        db.update_value(user_db["row"], 3, novo_saldo)
        db.atualizar_status_aposta(aposta_atualizada["row"], "Reembolso")
        
        await inter.edit_original_response(content=f"✅ Aposta cancelada com sucesso! **{formatar_moeda(valor_reembolso)} MC** foram devolvidos ao seu saldo.\n*Use o comando `!pule` novamente para atualizar a sua lista visual.*")


class ViewGerenciarBilhetes(disnake.ui.View):
    def __init__(self, author_id, apostas, info_jogos):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.add_item(SelectCancelarAposta(apostas, info_jogos))

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        if inter.author.id != self.author_id:
            await inter.response.send_message("❌ Estes bilhetes não são seus!", ephemeral=True)
            return False
        return True
        
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass


class Esportes(commands.Cog):
    def __init__(self, bot):
        self.bot         = bot
        self.api_url     = "https://api.football-data.org/v4"
        self.headers     = {"X-Auth-Token": os.getenv("FOOTBALL_API_KEY") or ""}
        self.cache_embed = None
        self.cache_jogos = None
        self.cache_time  = None
        
        self.checar_resultados.start()
        self.rotina_limpeza_apostas.start()

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != "🎰・akbet":
            canal  = disnake.utils.get(ctx.guild.channels, name="🎰・akbet")
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"⚽ {ctx.author.mention}, as apostas esportivas ficam no {mencao}!", delete_after=10)
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["jogos_hoje"])
    async def futebol(self, ctx):
        agora = datetime.now()
        if self.cache_embed and self.cache_jogos and self.cache_time and (agora - self.cache_time) < timedelta(minutes=30):
            return await ctx.send(embed=self.cache_embed, view=ViewSelectJogos(self.cache_jogos, self.bot, api_url=self.api_url, api_headers=self.headers))
        
        await ctx.send("🔎 Consultando o calendário... Aguarde!", delete_after=5)
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "competitions": "BSA,PL,PD,CL,SA,BL1,PPL",
                    "status": "SCHEDULED",
                    "dateFrom": agora.strftime("%Y-%m-%d"),
                    "dateTo": (agora + timedelta(days=3)).strftime("%Y-%m-%d"),
                }
                async with session.get(f"{self.api_url}/matches", headers=self.headers, params=params) as resp:
                    print(f"🔄 API Futebol restantes: {resp.headers.get('X-Requests-Available-Minute')}")
                    data = await resp.json()
                    if "errorCode" in data or resp.status != 200:
                        return await ctx.send("❌ Não consegui acessar os jogos no momento.")
                    if not data.get("matches"):
                        return await ctx.send("⚽ Nenhum jogo das grandes ligas nos próximos 3 dias.")
                    
                    jogos = data["matches"][:25]
                    embed = disnake.Embed(
                        title="⚽ BETS DA SELVA — PRÓXIMOS JOGOS",
                        description="Selecione um jogo abaixo para apostar!\n💰 Odd fixa **2.0x** · 📋 Bilhetes com `!pule`",
                        color=disnake.Color.blue()
                    )
                    ligas_vistas = {}
                    for j in jogos:
                        lc = j.get("competition", {}).get("code", "")
                        ln = j.get("competition", {}).get("name", lc)
                        if ln not in ligas_vistas:
                            ligas_vistas[ln] = {"emoji": LIGAS_EMOJI.get(lc, "🏆"), "linhas": []}
                        ligas_vistas[ln]["linhas"].append(
                            f"• **{j['homeTeam']['name']}** vs **{j['awayTeam']['name']}** — ⏰ {hora_br(j['utcDate'])}"
                        )
                    for ln, info in ligas_vistas.items():
                        embed.add_field(name=f"{info['emoji']} {ln}", value="\n".join(info["linhas"]), inline=False)
                    embed.set_footer(text=f"Atualizado às {agora.strftime('%H:%M')} • Cache de 30 min")
                    
                    self.cache_embed = embed
                    self.cache_jogos = jogos
                    self.cache_time  = agora
                    await ctx.send(embed=embed, view=ViewSelectJogos(jogos, self.bot, api_url=self.api_url, api_headers=self.headers))
        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !futebol: {e}")
            await ctx.send("⚠️ Ocorreu um erro ao buscar os jogos. Tente novamente!")

    @commands.command(aliases=["cupom", "cupoms", "cupons"])
    async def pule(self, ctx):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        msg = await ctx.send(f"🔎 {ctx.author.mention}, buscando seus bilhetes...")
        try:
            pendentes = db.obter_apostas_pendentes()
            minhas    = [a for a in pendentes if str(a["user_id"]) == str(ctx.author.id)]
            if not minhas:
                return await msg.edit(content=f"⚽ {ctx.author.mention}, nenhum bilhete pendente!")
            
            agora = datetime.utcnow()
            info_jogos = {}
            async with aiohttp.ClientSession() as session:
                params = {
                    "dateFrom": (agora - timedelta(days=3)).strftime("%Y-%m-%d"),
                    "dateTo":   (agora + timedelta(days=7)).strftime("%Y-%m-%d"),
                }
                async with session.get(f"{self.api_url}/matches", headers=self.headers, params=params) as resp:
                    if resp.status == 200:
                        for match in (await resp.json()).get("matches", []):
                            info_jogos[str(match["id"])] = {
                                "home": match["homeTeam"]["name"],
                                "away": match["awayTeam"]["name"],
                                "hora": hora_br(match["utcDate"]),
                                "liga": match.get("competition", {}).get("name", ""),
                                "liga_code": match.get("competition", {}).get("code", ""),
                                "utcDate": match["utcDate"],
                                "status": match.get("status", "")
                            }
            
            total_ap = sum(a["valor"] for a in minhas)
            total_rt = sum(round(a["valor"] * a["odd"], 2) for a in minhas)
            embed = disnake.Embed(
                title="🎟️ SEUS BILHETES PENDENTES",
                description=f"**{len(minhas)} bilhete(s)**\n💸 Apostado: `{formatar_moeda(total_ap)} MC`  •  💰 Retorno potencial: `{formatar_moeda(total_rt)} MC`",
                color=disnake.Color.orange()
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            EMOJI_P = {"casa": "🏠", "fora": "✈️", "empate": "🤝"}
            
            for aposta in minhas[:15]:
                ganho = round(aposta["valor"] * aposta["odd"], 2)
                m_id  = str(aposta["match_id"])
                info  = info_jogos.get(m_id, {})
                tc    = info.get("home", "Time da Casa")
                tf    = info.get("away", "Time Visitante")
                p     = aposta["palpite"].lower()
                embed.add_field(
                    name  = f"⚽ {tc} vs {tf}",
                    value = (
                        f"{LIGAS_EMOJI.get(info.get('liga_code',''),'🏆')} {info.get('liga','—')}  •  ⏰ {info.get('hora','—')}\n"
                        f"{EMOJI_P.get(p,'🎯')} **Palpite:** {tc if p=='casa' else (tf if p=='fora' else 'Empate')}\n"
                        f"💸 `{formatar_moeda(aposta['valor'])} MC` → 💰 `{formatar_moeda(ganho)} MC` (Odd: {aposta['odd']}x)  🆔 `{m_id}`"
                    ),
                    inline=False
                )
            embed.set_footer(text="O Menu abaixo permite cancelar apostas em jogos que ainda NÃO começaram.")
            
            view = ViewGerenciarBilhetes(ctx.author.id, minhas, info_jogos)
            await msg.edit(content=None, embed=embed, view=view)
            
        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !pule de {ctx.author}: {e}")
            await msg.edit(content=f"⚠️ {ctx.author.mention}, erro ao buscar bilhetes.")

    @tasks.loop(minutes=15, reconnect=True)
    async def checar_resultados(self):
        apostas_pendentes = db.obter_apostas_pendentes()
        ts = datetime.utcnow().strftime("%H:%M:%S")
        print(f"🔄 [{ts}] checar_resultados: {len(apostas_pendentes)} aposta(s) pendente(s).")
        if not apostas_pendentes:
            return

        match_ids_pendentes = set(str(a["match_id"]) for a in apostas_pendentes)
        canal_cassino = disnake.utils.get(self.bot.get_all_channels(), name="🎰・akbet")
        if not canal_cassino:
            print("⚠️ Canal '🎰・akbet' não encontrado — notificações desativadas.")

        agora   = datetime.utcnow()
        data_de = (agora - timedelta(days=5)).strftime("%Y-%m-%d")
        data_at = (agora + timedelta(days=1)).strftime("%Y-%m-%d")
        resultados_api = {}

        try:
            async with aiohttp.ClientSession() as session:
                params = {"competitions": "BSA,PL,PD,CL,SA,BL1,PPL", "dateFrom": data_de, "dateTo": data_at}
                async with session.get(f"{self.api_url}/matches", headers=self.headers, params=params,
                                       timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 429:
                        print("⚠️ Rate limit — tentará no próximo ciclo.")
                        return
                    if resp.status != 200:
                        print(f"⚠️ API retornou {resp.status} — abortando.")
                        return
                    for match in (await resp.json()).get("matches", []):
                        mid = str(match["id"])
                        if mid in match_ids_pendentes:
                            resultados_api[mid] = match
        except asyncio.TimeoutError:
            print("⚠️ Timeout — tentará no próximo ciclo.")
            return
        except Exception as e:
            print(f"❌ Erro na API: {e}")
            return

        print(f"📋 {len(resultados_api)}/{len(match_ids_pendentes)} jogo(s) encontrado(s) na API.")
        processadas = 0

        for match_id, match_data in resultados_api.items():
            status = match_data.get("status")
            if status not in ("FINISHED", "AWARDED"):
                continue

            gols_casa = match_data.get("score", {}).get("fullTime", {}).get("home")
            gols_fora = match_data.get("score", {}).get("fullTime", {}).get("away")
            if gols_casa is None or gols_fora is None:
                continue

            home_nome = match_data["homeTeam"]["name"]
            away_nome = match_data["awayTeam"]["name"]
            placar    = f"{gols_casa} x {gols_fora}"
            liga_nome = match_data.get("competition", {}).get("name", "")
            liga_code = match_data.get("competition", {}).get("code", "")

            if gols_casa > gols_fora:   resultado_real = "casa"
            elif gols_fora > gols_casa: resultado_real = "fora"
            else:                       resultado_real = "empate"

            LABEL = {"casa": home_nome, "fora": away_nome, "empate": "Empate"}
            apostas_deste_jogo = [a for a in apostas_pendentes if str(a["match_id"]) == match_id]
            
            if not apostas_deste_jogo:
                continue

            print(f"⚽ {home_nome} {placar} {away_nome} — {len(apostas_deste_jogo)} aposta(s).")

            lista_vencedores = []
            lista_perdedores = []
            mencoes_unicas = set()

            for aposta in apostas_deste_jogo:
                palpite_key = aposta["palpite"].lower()
                se_venceu   = (palpite_key == resultado_real)
                mencoes_unicas.add(f"<@{aposta['user_id']}>")
                processadas += 1

                if se_venceu:
                    db.atualizar_status_aposta(aposta["row"], "Venceu")
                    user_db = db.get_user_data(str(aposta["user_id"]))
                    if user_db:
                        saldo_atual = db.parse_float(user_db["data"][2])
                        premio      = round(aposta["valor"] * aposta["odd"], 2)
                        db.update_value(user_db["row"], 3, round(saldo_atual + premio, 2))
                        lista_vencedores.append(f"<@{aposta['user_id']}>: `+{formatar_moeda(premio)} MC` ({aposta['odd']}x)")
                else:
                    db.atualizar_status_aposta(aposta["row"], "Perdeu")
                    lista_perdedores.append(f"<@{aposta['user_id']}>: `-{formatar_moeda(aposta['valor'])} MC`")

            if canal_cassino:
                embed = disnake.Embed(
                    title=f"🏁 FIM DE JOGO: {home_nome} vs {away_nome}",
                    description=f"{LIGAS_EMOJI.get(liga_code,'🏆')} **{liga_nome}**\n**Placar Final:** `{placar}`\n**Resultado:** {LABEL.get(resultado_real, resultado_real)}",
                    color=disnake.Color.blurple()
                )
                
                if lista_vencedores:
                    texto_v = "\n".join(lista_vencedores)
                    embed.add_field(name="🏆 Vencedores", value=texto_v[:1020] + ("..." if len(texto_v) > 1020 else ""), inline=False)
                
                if lista_perdedores:
                    texto_p = "\n".join(lista_perdedores)
                    embed.add_field(name="💀 Perdedores", value=texto_p[:1020] + ("..." if len(texto_p) > 1020 else ""), inline=False)

                embed.set_footer(text="Apostas liquidadas! O saldo foi atualizado automaticamente.")
                
                texto_mencoes = " ".join(mencoes_unicas)[:2000]
                try:
                    await canal_cassino.send(content=texto_mencoes, embed=embed)
                except Exception as e:
                    print(f"⚠️ Falha ao enviar resumo da partida: {e}")

        if processadas:
            print(f"✅ {processadas} aposta(s) processada(s).")
        else:
            print("💤 Nenhuma aposta processada neste ciclo.")

    @checar_resultados.before_loop
    async def before_checar_resultados(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)
        print("✅ Bot pronto, iniciando loop de apostas esportivas.")

    @tasks.loop(hours=24)
    async def rotina_limpeza_apostas(self):
        print("🧹 [Auto-Faxina] Iniciando limpeza diária de apostas finalizadas...")
        try:
            apagadas = db.limpar_apostas_finalizadas()
            if apagadas > 0:
                print(f"✅ [Auto-Faxina] Sucesso: {apagadas} apostas antigas foram removidas da planilha.")
            else:
                print("✨ [Auto-Faxina] A planilha já estava limpa.")
        except Exception as e:
            print(f"❌ [Auto-Faxina] Erro ao limpar apostas na rotina: {e}")

    @rotina_limpeza_apostas.before_loop
    async def before_rotina_limpeza_apostas(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(5) 

    @commands.command(name="limpar_apostas")
    @commands.has_permissions(administrator=True)
    async def limpar_apostas_cmd(self, ctx):
        msg = await ctx.send("🧹 Iniciando a faxina nas apostas esportivas... Isso pode levar alguns segundos!")
        try:
            apagadas = db.limpar_apostas_finalizadas()
            if apagadas > 0:
                await msg.edit(content=f"✅ Faxina concluída! **{apagadas}** apostas antigas foram apagadas da planilha.")
            else:
                await msg.edit(content="✨ A planilha já está limpa! Nenhuma aposta finalizada foi encontrada.")
        except Exception as e:
            print(f"❌ Erro ao limpar apostas: {e}")
            await msg.edit(content="⚠️ Ocorreu um erro ao tentar limpar a planilha. Verifique o console.")


def setup(bot):
    bot.add_cog(Esportes(bot))