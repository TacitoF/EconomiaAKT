import disnake
from disnake.ext import commands, tasks
import aiohttp
import os
import database as db
from datetime import datetime, timedelta
import asyncio

OWNER_ID = 757752617722970243

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

def formatar_moeda(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ──────────────────────────────────────────────
#  MODAL E VIEWS DE APOSTAS
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

        label_str = f"{EMOJI.get(palpite,'🎯')} Palpite: {LABELS.get(palpite, palpite)}"[:45]
        title_str = f"💰 {time_casa} x {time_fora}"[:45]

        components = [
            disnake.ui.TextInput(
                label=label_str,
                placeholder="Digite o valor em MC (ex: 100)",
                custom_id="valor_aposta",
                style=disnake.TextInputStyle.short,
                min_length=1,
                max_length=12,
            )
        ]
        super().__init__(title=title_str, components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)

        valor_raw = inter.text_values.get("valor_aposta", "").strip().replace(",", ".")
        try:
            valor = round(float(valor_raw), 2)
        except ValueError:
            return await inter.edit_original_response(content="❌ Valor inválido! Digite apenas números.")

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
                content=f"❌ Saldo insuficiente! Você tem **{formatar_moeda(saldo)} MC**."
            )
        if valor > limite:
            return await inter.edit_original_response(
                content=f"🚫 Limite de aposta para **{cargo}** é de **{formatar_moeda(limite)} MC**!"
            )

        odd_fixa = 2.0
        ganho_potencial = round(valor * odd_fixa, 2)

        db.update_value(user['row'], 3, round(saldo - valor, 2))
        db.registrar_aposta_esportiva(inter.author.id, self.match_id, self.palpite, valor, odd_fixa)

        EMOJI  = {"casa": "🏠", "empate": "🤝", "fora": "✈️"}
        LABELS = {"casa": self.time_casa, "empate": "Empate", "fora": self.time_fora}

        embed = disnake.Embed(title="🎟️ BILHETE REGISTRADO!", color=disnake.Color.gold())
        embed.set_author(name=inter.author.display_name, icon_url=inter.author.display_avatar.url)
        embed.add_field(name="⚽ Partida",                              value=f"**{self.time_casa}** vs **{self.time_fora}**", inline=False)
        embed.add_field(name="🏆 Liga",                                 value=self.liga or "—",                               inline=True)
        embed.add_field(name="⏰ Data/Hora",                            value=self.horario or "—",                            inline=True)
        embed.add_field(name="🆔 ID",                                   value=f"`{self.match_id}`",                           inline=True)
        embed.add_field(name=f"{EMOJI.get(self.palpite,'🎯')} Palpite", value=f"**{LABELS.get(self.palpite, self.palpite)}**",inline=True)
        embed.add_field(name="💸 Apostado",                             value=f"`{formatar_moeda(valor)} MC`",                inline=True)
        embed.add_field(name="💰 Retorno",                              value=f"`{formatar_moeda(ganho_potencial)} MC`",      inline=True)
        embed.set_footer(text="Pagamento automático ao fim da partida • !pule para ver seus bilhetes")
        await inter.edit_original_response(content=None, embed=embed)

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
            match_id=self.match_id, palpite=palpite, time_casa=self.time_casa,
            time_fora=self.time_fora, liga=self.liga, horario=self.horario
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

class SelectJogo(disnake.ui.StringSelect):
    def __init__(self, jogos: list):
        self.jogos_map = {str(j['id']): j for j in jogos}
        options = []
        for j in jogos:
            liga_code = j.get('competition', {}).get('code', '')
            emoji_str = LIGAS_EMOJI.get(liga_code, "🏆")
            options.append(disnake.SelectOption(
                label       = f"{j['homeTeam']['name']} vs {j['awayTeam']['name']}"[:100],
                description = f"{j.get('competition',{}).get('name','')}  •  {hora_br(j['utcDate'])}"[:100],
                value       = str(j['id']),
                emoji       = emoji_str,
            ))
        super().__init__(placeholder="⚽ Selecione um jogo para apostar...", options=options, min_values=1, max_values=1)

    async def callback(self, inter: disnake.MessageInteraction):
        match_id  = self.values[0]
        jogo      = self.jogos_map[match_id]
        time_casa = jogo['homeTeam']['name']
        time_fora = jogo['awayTeam']['name']
        liga_code = jogo.get('competition', {}).get('code', '')
        liga_nome = jogo.get('competition', {}).get('name', liga_code)
        horario   = hora_br(jogo['utcDate'])

        embed = disnake.Embed(
            title=f"⚽ {time_casa} vs {time_fora}",
            description=f"{LIGAS_EMOJI.get(liga_code, '🏆')} **{liga_nome}** • ⏰ {horario}\n\nEscolha o seu palpite:",
            color=disnake.Color.blue()
        )
        embed.add_field(name="🏠 Casa", value=time_casa, inline=True)
        embed.add_field(name="🤝 Empate", value="Empate", inline=True)
        embed.add_field(name="✈️ Fora", value=time_fora, inline=True)
        embed.add_field(name="💰 Odd fixa", value="**2.0x** para qualquer resultado", inline=False)
        embed.set_footer(text=f"ID: {match_id}")

        view = ViewPalpiteJogo(int(match_id), time_casa, time_fora, liga_nome, horario)
        await inter.response.send_message(embed=embed, view=view, ephemeral=True)

class ViewSelectJogos(disnake.ui.View):
    def __init__(self, jogos: list):
        super().__init__(timeout=None)
        self.add_item(SelectJogo(jogos))

# ──────────────────────────────────────────────
#  COG PRINCIPAL
# ──────────────────────────────────────────────
class Esportes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://api.football-data.org/v4"
        self.headers = {"X-Auth-Token": os.getenv("FOOTBALL_API_KEY") or ""}
        self.cache_embed = None
        self.cache_jogos = None
        self.cache_time = None
        self.checar_resultados.start()

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"⚽ {ctx.author.mention}, apostas esportivas ficam no {mencao}!", delete_after=10)
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["jogos_hoje"])
    async def futebol(self, ctx):
        agora = datetime.now()
        if self.cache_embed and self.cache_jogos and self.cache_time and (agora - self.cache_time) < timedelta(minutes=30):
            return await ctx.send(embed=self.cache_embed, view=ViewSelectJogos(self.cache_jogos))

        aviso = await ctx.send("🔎 Consultando o calendário... Aguarde!", delete_after=5)

        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "competitions": "BSA,PL,PD,CL,SA,BL1,PPL",
                    "status": "SCHEDULED",
                    "dateFrom": agora.strftime("%Y-%m-%d"),
                    "dateTo": (agora + timedelta(days=3)).strftime("%Y-%m-%d"),
                }
                async with session.get(f"{self.api_url}/matches", headers=self.headers, params=params) as resp:
                    if resp.status != 200:
                        return await ctx.send("❌ Não consegui acessar os jogos no momento.")

                    data = await resp.json()
                    if 'matches' not in data or not data['matches']:
                        return await ctx.send("⚽ Nenhum jogo das grandes ligas programado para os próximos 3 dias.")

                    jogos = data['matches'][:25]
                    embed = disnake.Embed(
                        title="⚽ BETS DA SELVA — PRÓXIMOS JOGOS",
                        description="Selecione um jogo no menu abaixo para apostar!\n💰 Odd fixa de **2.0x** · 📋 Seus bilhetes: `!pule`",
                        color=disnake.Color.blue()
                    )

                    ligas_vistas = {}
                    for j in jogos:
                        liga_code = j.get('competition', {}).get('code', '')
                        liga_nome = j.get('competition', {}).get('name', liga_code)
                        if liga_nome not in ligas_vistas:
                            ligas_vistas[liga_nome] = {"emoji": LIGAS_EMOJI.get(liga_code, "🏆"), "linhas": []}
                        ligas_vistas[liga_nome]["linhas"].append(f"• **{j['homeTeam']['name']}** vs **{j['awayTeam']['name']}** — ⏰ {hora_br(j['utcDate'])}")

                    for liga_nome, info in ligas_vistas.items():
                        embed.add_field(name=f"{info['emoji']} {liga_nome}", value="\n".join(info["linhas"]), inline=False)
                    embed.set_footer(text=f"Atualizado às {agora.strftime('%H:%M')} • Cache de 30 min")

                    self.cache_embed, self.cache_jogos, self.cache_time = embed, jogos, agora
                    await ctx.send(embed=embed, view=ViewSelectJogos(jogos))

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro !futebol: {e}")
            await ctx.send("⚠️ Erro ao buscar os jogos.")

    @commands.command(aliases=["cupom", "cupons"])
    async def pule(self, ctx):
        try: await ctx.message.delete()
        except: pass

        msg = await ctx.send(f"🔎 {ctx.author.mention}, buscando seus bilhetes...")
        try:
            minhas = [a for a in db.obter_apostas_pendentes() if str(a['user_id']) == str(ctx.author.id)]
            if not minhas:
                return await msg.edit(content=f"⚽ {ctx.author.mention}, nenhum bilhete pendente!")

            total_apostado = sum(a['valor'] for a in minhas)
            total_retorno  = sum(round(a['valor'] * a['odd'], 2) for a in minhas)

            embed = disnake.Embed(
                title="🎟️ SEUS BILHETES PENDENTES",
                description=f"**{len(minhas)} bilhete(s)**\n💸 Apostado: `{formatar_moeda(total_apostado)} MC` • 💰 Retorno: `{formatar_moeda(total_retorno)} MC`",
                color=disnake.Color.orange()
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)

            EMOJI_P = {"casa": "🏠", "fora": "✈️", "empate": "🤝"}

            # Para agilizar o comando, informamos apenas os IDs ou usamos dados salvos se não quisermos consumir a API
            for aposta in minhas[:15]:
                embed.add_field(
                    name=f"🆔 Jogo ID: {aposta['match_id']}",
                    value=f"{EMOJI_P.get(aposta['palpite'].lower(),'🎯')} **Palpite:** {aposta['palpite'].capitalize()}\n💸 `{formatar_moeda(aposta['valor'])} MC` → 💰 `{formatar_moeda(aposta['valor']*aposta['odd'])} MC`",
                    inline=False
                )
            embed.set_footer(text="Os prêmios são pagos automaticamente quando a partida termina.")
            await msg.edit(content=None, embed=embed)
        except Exception as e:
            print(f"❌ Erro !pule: {e}")
            await msg.edit(content="⚠️ Erro ao buscar bilhetes.")

    # ──────────────────────────────────────────────
    # LOOP AUTOMÁTICO (NOVA LÓGICA DE PRECISÃO)
    # ──────────────────────────────────────────────
    @tasks.loop(minutes=15, reconnect=True)
    async def checar_resultados(self):
        print(f"🔄 [{datetime.utcnow().strftime('%H:%M:%S')}] checar_resultados: iniciando verificação exata...")

        apostas_pendentes = db.obter_apostas_pendentes()
        if not apostas_pendentes:
            return
        
        match_ids = list(set(str(a['match_id']) for a in apostas_pendentes))
        processadas = 0

        async with aiohttp.ClientSession() as session:
            for match_id in match_ids:
                try:
                    url = f"{self.api_url}/matches/{match_id}"
                    async with session.get(url, headers=self.headers) as resp:
                        if resp.status == 429:
                            await asyncio.sleep(10) # Limite excedido, pausa
                            continue
                        if resp.status != 200:
                            await asyncio.sleep(6)
                            continue

                        match_data = await resp.json()
                        status = match_data.get('status')

                        if status in ["FINISHED", "AWARDED"]:
                            p = await self._processar_pagamento_jogo(match_data, apostas_pendentes)
                            processadas += p
                            
                except Exception as e:
                    print(f"❌ Erro ao checar jogo {match_id}: {e}")
                
                # Pausa obrigatória para a API grátis (10 requests por minuto = 1 a cada 6 seg)
                await asyncio.sleep(6.5)

        if processadas > 0:
            print(f"✅ checar_resultados: {processadas} aposta(s) paga(s)!")

    async def _processar_pagamento_jogo(self, match_data, apostas_pendentes):
        """Função isolada para processar os ganhos e perdas de um jogo já terminado."""
        aposta_id = str(match_data['id'])
        gols_casa = match_data.get('score', {}).get('fullTime', {}).get('home')
        gols_fora = match_data.get('score', {}).get('fullTime', {}).get('away')

        if gols_casa is None or gols_fora is None:
            return 0

        home_nome = match_data['homeTeam']['name']
        away_nome = match_data['awayTeam']['name']
        placar    = f"{gols_casa} x {gols_fora}"
        liga_nome = match_data.get('competition', {}).get('name', '')

        if gols_casa > gols_fora:   resultado_real = "casa"
        elif gols_fora > gols_casa: resultado_real = "fora"
        else:                       resultado_real = "empate"

        apostas_deste_jogo = [a for a in apostas_pendentes if str(a['match_id']) == aposta_id]
        canal_cassino = disnake.utils.get(self.bot.get_all_channels(), name='🎰・akbet')
        
        count = 0
        LABEL = {"casa": home_nome, "fora": away_nome, "empate": "Empate"}

        for aposta in apostas_deste_jogo:
            try:
                jogador = self.bot.get_user(int(aposta['user_id'])) or await self.bot.fetch_user(int(aposta['user_id']))
            except Exception:
                jogador = None
            
            mencao_jogador = jogador.mention if jogador else f"<@{aposta['user_id']}>"
            se_venceu = aposta['palpite'].lower() == resultado_real

            if se_venceu:
                db.atualizar_status_aposta(aposta['row'], 'Venceu')
                user_db = db.get_user_data(str(aposta['user_id']))
                if user_db:
                    saldo_atual = db.parse_float(user_db['data'][2])
                    premio      = round(aposta['valor'] * aposta['odd'], 2)
                    db.update_value(user_db['row'], 3, round(saldo_atual + premio, 2))
                    if canal_cassino:
                        embed = disnake.Embed(title="🏆 APOSTA VENCEDORA!", color=disnake.Color.green())
                        embed.add_field(name="⚽ Partida",  value=f"**{home_nome}** vs **{away_nome}**",     inline=False)
                        embed.add_field(name="🏆 Liga",     value=liga_nome or "—",                          inline=True)
                        embed.add_field(name="📊 Placar",   value=f"**{placar}**",                           inline=True)
                        embed.add_field(name="\u200b",      value="\u200b",                                  inline=True)
                        embed.add_field(name="🎯 Palpite",  value=LABEL.get(aposta['palpite'].lower(), "—"), inline=True)
                        embed.add_field(name="💸 Apostado", value=f"`{formatar_moeda(aposta['valor'])} MC`", inline=True)
                        embed.add_field(name="💰 Prêmio",   value=f"**{formatar_moeda(premio)} MC**",        inline=True)
                        embed.set_footer(text="O saldo já foi creditado na sua conta!")
                        await canal_cassino.send(content=f"🎉 {mencao_jogador}", embed=embed)
            else:
                db.atualizar_status_aposta(aposta['row'], 'Perdeu')
                if canal_cassino:
                    embed = disnake.Embed(title="💀 APOSTA PERDIDA", color=disnake.Color.red())
                    embed.add_field(name="⚽ Partida",      value=f"**{home_nome}** vs **{away_nome}**",     inline=False)
                    embed.add_field(name="🏆 Liga",         value=liga_nome or "—",                          inline=True)
                    embed.add_field(name="📊 Placar",       value=f"**{placar}**",                           inline=True)
                    embed.add_field(name="\u200b",          value="\u200b",                                  inline=True)
                    embed.add_field(name="✅ Resultado",    value=LABEL.get(resultado_real, resultado_real), inline=True)
                    embed.add_field(name="❌ Seu Palpite",  value=LABEL.get(aposta['palpite'].lower(), "—"), inline=True)
                    embed.add_field(name="💸 Perdido",      value=f"`{formatar_moeda(aposta['valor'])} MC`", inline=True)
                    embed.set_footer(text="Veja jogos com !futebol")
                    await canal_cassino.send(content=f"{mencao_jogador}", embed=embed)
            
            count += 1
            
        return count

    @checar_resultados.before_loop
    async def before_checar_resultados(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)
        print("✅ Bot pronto, loop exato de apostas esportivas iniciado.")

def setup(bot):
    bot.add_cog(Esportes(bot))