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
    def __init__(self, match_id, palpite, time_casa, time_fora, liga, horario):
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
            return await inter.edit_original_response(content="❌ Valor inválido!")
        if valor <= 0:
            return await inter.edit_original_response(content="❌ O valor deve ser maior que zero!")
        user = db.get_user_data(str(inter.author.id))
        if not user:
            return await inter.edit_original_response(content="❌ Conta não encontrada!")
        saldo  = db.parse_float(user["data"][2])
        cargo  = user["data"][3] if len(user["data"]) > 3 else "Lêmure"
        limite = get_limite(cargo)
        if saldo < valor:
            return await inter.edit_original_response(
                content=f"❌ Saldo insuficiente! Tens **{formatar_moeda(saldo)} MC** e tentaste apostar **{formatar_moeda(valor)} MC**."
            )
        if valor > limite:
            return await inter.edit_original_response(
                content=f"🚫 Limite de aposta para **{cargo}** é de **{formatar_moeda(limite)} MC**!"
            )
        odd_fixa        = 2.0
        ganho_potencial = round(valor * odd_fixa, 2)
        db.update_value(user["row"], 3, round(saldo - valor, 2))
        db.registrar_aposta_esportiva(
            inter.author.id, self.match_id, self.palpite, valor, odd_fixa,
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
        embed.add_field(name="💰 Retorno",  value=f"`{formatar_moeda(ganho_potencial)} MC`", inline=True)
        embed.set_footer(text="Pagamento automático ao fim da partida • !pule para ver seus bilhetes")
        await inter.edit_original_response(content=None, embed=embed)


class ViewPalpiteJogo(disnake.ui.View):
    def __init__(self, match_id, time_casa, time_fora, liga, horario):
        super().__init__(timeout=120)
        self.match_id  = match_id
        self.time_casa = time_casa
        self.time_fora = time_fora
        self.liga      = liga
        self.horario   = horario

    async def _abrir_modal(self, inter, palpite):
        await inter.response.send_modal(ModalValorAposta(
            match_id=self.match_id, palpite=palpite,
            time_casa=self.time_casa, time_fora=self.time_fora,
            liga=self.liga, horario=self.horario,
        ))

    @disnake.ui.button(label="🏠 Casa",   style=disnake.ButtonStyle.primary)
    async def btn_casa(self, button, inter):   await self._abrir_modal(inter, "casa")

    @disnake.ui.button(label="🤝 Empate", style=disnake.ButtonStyle.secondary)
    async def btn_empate(self, button, inter): await self._abrir_modal(inter, "empate")

    @disnake.ui.button(label="✈️ Fora",   style=disnake.ButtonStyle.danger)
    async def btn_fora(self, button, inter):   await self._abrir_modal(inter, "fora")

    @disnake.ui.button(label="↩️ Voltar", style=disnake.ButtonStyle.secondary, row=1)
    async def btn_voltar(self, button, inter):
        await inter.response.defer()
        await inter.delete_original_response()


class SelectJogo(disnake.ui.StringSelect):
    def __init__(self, jogos):
        self.jogos_map = {str(j["id"]): j for j in jogos}
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
        mid       = self.values[0]
        jogo      = self.jogos_map[mid]
        time_casa = jogo["homeTeam"]["name"]
        time_fora = jogo["awayTeam"]["name"]
        liga_code = jogo.get("competition", {}).get("code", "")
        liga_nome = jogo.get("competition", {}).get("name", liga_code)
        horario   = hora_br(jogo["utcDate"])
        embed = disnake.Embed(
            title=f"⚽ {time_casa} vs {time_fora}",
            description=f"{LIGAS_EMOJI.get(liga_code,'🏆')} **{liga_nome}**  •  ⏰ {horario}\n\nEscolha o seu palpite abaixo:",
            color=disnake.Color.blue()
        )
        embed.add_field(name="🏠 Casa",     value=time_casa, inline=True)
        embed.add_field(name="🤝 Empate",   value="Empate",  inline=True)
        embed.add_field(name="✈️ Fora",     value=time_fora, inline=True)
        embed.add_field(name="💰 Odd fixa", value="**2.0x** para qualquer resultado", inline=False)
        embed.set_footer(text=f"ID: {mid}")
        await inter.response.send_message(embed=embed, view=ViewPalpiteJogo(int(mid), time_casa, time_fora, liga_nome, horario), ephemeral=True)


class ViewSelectJogos(disnake.ui.View):
    def __init__(self, jogos):
        super().__init__(timeout=None)
        self.add_item(SelectJogo(jogos))


class Esportes(commands.Cog):
    def __init__(self, bot):
        self.bot         = bot
        self.api_url     = "https://api.football-data.org/v4"
        self.headers     = {"X-Auth-Token": os.getenv("FOOTBALL_API_KEY") or ""}
        self.cache_embed = None
        self.cache_jogos = None
        self.cache_time  = None
        self.checar_resultados.start()

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
            return await ctx.send(embed=self.cache_embed, view=ViewSelectJogos(self.cache_jogos))
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
                        description="Selecione um jogo no menu abaixo!\n💰 Odd fixa **2.0x** · 📋 Bilhetes com `!pule`",
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
                    await ctx.send(embed=embed, view=ViewSelectJogos(jogos))
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
            agora = datetime.now()
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
                        f"💸 `{formatar_moeda(aposta['valor'])} MC` → 💰 `{formatar_moeda(ganho)} MC`  🆔 `{m_id}`"
                    ),
                    inline=False
                )
            embed.set_footer(text="Os prêmios são pagos automaticamente ao fim de cada partida")
            await msg.edit(content=None, embed=embed)
        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !pule de {ctx.author}: {e}")
            await msg.edit(content=f"⚠️ {ctx.author.mention}, erro ao buscar bilhetes.")

    # ─────────────────────────────────────────────────────────────────────────
    #  CORREÇÃO PRINCIPAL DO BUG DE PAGAMENTO:
    #
    #  Antes: chamava GET /matches/{id} individualmente → API retorna 400 para
    #  IDs de certas ligas no plano free, pulando todas as apostas.
    #
    #  Agora: uma única chamada GET /matches?competitions=...&dateFrom=...
    #  retorna todos os jogos da janela, e filtramos localmente pelos IDs
    #  pendentes. Zero chamadas individuais, zero erros 400.
    # ─────────────────────────────────────────────────────────────────────────
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
                print(f"⏳ Jogo {match_id} ainda não finalizado (status: {status}).")
                continue

            gols_casa = match_data.get("score", {}).get("fullTime", {}).get("home")
            gols_fora = match_data.get("score", {}).get("fullTime", {}).get("away")
            if gols_casa is None or gols_fora is None:
                print(f"⏳ Jogo {match_id}: placar indisponível — aguardando.")
                continue

            home_nome = match_data["homeTeam"]["name"]
            away_nome = match_data["awayTeam"]["name"]
            placar    = f"{gols_casa} x {gols_fora}"
            liga_nome = match_data.get("competition", {}).get("name", "")

            if gols_casa > gols_fora:   resultado_real = "casa"
            elif gols_fora > gols_casa: resultado_real = "fora"
            else:                       resultado_real = "empate"

            LABEL = {"casa": home_nome, "fora": away_nome, "empate": "Empate"}
            apostas_deste_jogo = [a for a in apostas_pendentes if str(a["match_id"]) == match_id]
            print(f"⚽ {home_nome} {placar} {away_nome} — {len(apostas_deste_jogo)} aposta(s).")

            for aposta in apostas_deste_jogo:
                palpite_key = aposta["palpite"].lower()
                palpite_fmt = LABEL.get(palpite_key, aposta["palpite"])
                se_venceu   = (palpite_key == resultado_real)
                processadas += 1

                # FIX: get_user + fetch_user separados (or com await é bug silencioso)
                jogador = self.bot.get_user(int(aposta["user_id"]))
                if jogador is None:
                    try:
                        jogador = await self.bot.fetch_user(int(aposta["user_id"]))
                    except Exception:
                        jogador = None

                if se_venceu:
                    db.atualizar_status_aposta(aposta["row"], "Venceu")
                    user_db = db.get_user_data(str(aposta["user_id"]))
                    premio  = 0.0
                    if user_db:
                        saldo_atual = db.parse_float(user_db["data"][2])
                        premio      = round(aposta["valor"] * aposta["odd"], 2)
                        db.update_value(user_db["row"], 3, round(saldo_atual + premio, 2))
                        print(f"  ✅ User {aposta['user_id']} VENCEU +{formatar_moeda(premio)} MC")
                    if canal_cassino and jogador:
                        embed = disnake.Embed(title="🏆 APOSTA VENCEDORA!", color=disnake.Color.green())
                        embed.set_author(name=jogador.display_name, icon_url=jogador.display_avatar.url)
                        embed.add_field(name="⚽ Partida",  value=f"**{home_nome}** vs **{away_nome}**",     inline=False)
                        embed.add_field(name="🏆 Liga",     value=liga_nome or "—",                          inline=True)
                        embed.add_field(name="📊 Placar",   value=f"**{placar}**",                           inline=True)
                        embed.add_field(name="\u200b",     value="\u200b",                                 inline=True)
                        embed.add_field(name="🎯 Palpite",  value=palpite_fmt,                               inline=True)
                        embed.add_field(name="💸 Apostado", value=f"`{formatar_moeda(aposta['valor'])} MC`",inline=True)
                        embed.add_field(name="💰 Prêmio",   value=f"**{formatar_moeda(premio)} MC**",        inline=True)
                        embed.set_footer(text="Saldo creditado! 🎉")
                        try:
                            await canal_cassino.send(content=f"🎉 {jogador.mention}", embed=embed)
                        except Exception as e:
                            print(f"  ⚠️ Falha ao notificar vitória: {e}")
                else:
                    db.atualizar_status_aposta(aposta["row"], "Perdeu")
                    print(f"  ❌ User {aposta['user_id']} PERDEU ({palpite_key} vs {resultado_real})")
                    if canal_cassino and jogador:
                        embed = disnake.Embed(title="💀 APOSTA PERDIDA", color=disnake.Color.red())
                        embed.set_author(name=jogador.display_name, icon_url=jogador.display_avatar.url)
                        embed.add_field(name="⚽ Partida",     value=f"**{home_nome}** vs **{away_nome}**",     inline=False)
                        embed.add_field(name="🏆 Liga",        value=liga_nome or "—",                          inline=True)
                        embed.add_field(name="📊 Placar",      value=f"**{placar}**",                           inline=True)
                        embed.add_field(name="\u200b",        value="\u200b",                                 inline=True)
                        embed.add_field(name="✅ Resultado",   value=LABEL.get(resultado_real, resultado_real), inline=True)
                        embed.add_field(name="❌ Seu Palpite", value=palpite_fmt,                               inline=True)
                        embed.add_field(name="💸 Perdido",     value=f"`{formatar_moeda(aposta['valor'])} MC`",inline=True)
                        embed.set_footer(text="Veja os próximos jogos com !futebol")
                        try:
                            await canal_cassino.send(content=f"{jogador.mention}", embed=embed)
                        except Exception as e:
                            print(f"  ⚠️ Falha ao notificar derrota: {e}")

        if processadas:
            print(f"✅ {processadas} aposta(s) processada(s).")
        else:
            print("💤 Nenhuma aposta processada neste ciclo.")

    @checar_resultados.before_loop
    async def before_checar_resultados(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)
        print("✅ Bot pronto, iniciando loop de apostas esportivas.")


def setup(bot):
    bot.add_cog(Esportes(bot))