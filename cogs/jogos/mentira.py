import disnake
from disnake.ext import commands
import database as db
import random
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

def get_limite(cargo):
    return LIMITES_CARGO.get(cargo, 400)

def save_achievement(user_data, slug):
    conquistas = str(user_data['data'][9]) if len(user_data['data']) > 9 else ""
    lista = [c.strip() for c in conquistas.split(',') if c.strip()]
    if slug not in lista:
        lista.append(slug)
        db.update_value(user_data['row'], 10, ", ".join(lista))

# ─────────────────────────────────────────────────────────────────────────────
#  REGRAS
#
#  Cada jogador recebe 5 dados secretos (1–6).
#  Na sua vez, o jogador faz uma aposta: "existem pelo menos X dados com face Y
#  na mesa no total (contando os dados de todos)".
#  A aposta deve ser maior que a anterior: aumentar a quantidade OU manter a
#  quantidade e aumentar a face.
#  Qualquer jogador pode chamar "MENTIRA!" no turno do jogador atual.
#  Todos os dados são revelados. Se a aposta for verdadeira → quem chamou perde
#  a rodada. Se for falsa → quem apostou perde a rodada.
#  O perdedor da rodada perde a aposta em MC para o grupo (dividida entre os
#  vencedores). Jogo termina depois de uma rodada.
# ─────────────────────────────────────────────────────────────────────────────

DADOS_POR_JOGADOR = 5
FACES = 6
TIMEOUT_LOBBY    = 60   # segundos esperando jogadores
TIMEOUT_TURNO    = 45   # segundos por turno
MIN_JOGADORES    = 2
MAX_JOGADORES    = 6

EMOJI_DADO = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣"}


def rolar_dados(n: int) -> list[int]:
    return [random.randint(1, 6) for _ in range(n)]


def contar_face(todos_dados: list[list[int]], face: int) -> int:
    """Conta quantos dados com a face especificada existem no total."""
    return sum(d.count(face) for d in todos_dados)


def dados_str(dados: list[int]) -> str:
    return "  ".join(EMOJI_DADO[d] for d in sorted(dados))


def aposta_str(qtd: int, face: int) -> str:
    return f"**{qtd}x** {EMOJI_DADO[face]} `[{face}]`"


def aposta_maior(nova_qtd: int, nova_face: int, ant_qtd: int, ant_face: int) -> bool:
    """Verifica se a nova aposta é estritamente maior que a anterior."""
    return (nova_qtd, nova_face) > (ant_qtd, ant_face)


# ─────────────────────────────────────────────────────────────────────────────
#  VIEW: LOBBY (entrar na mesa)
# ─────────────────────────────────────────────────────────────────────────────

class MentiraLobbyView(disnake.ui.View):
    def __init__(self, ctx, aposta: float):
        super().__init__(timeout=TIMEOUT_LOBBY)
        self.ctx      = ctx
        self.aposta   = aposta
        self.players  = []   # list[disnake.Member]
        self.started  = False
        self.msg      = None

    def _lobby_text(self) -> str:
        nomes = ", ".join(f"**{p.display_name}**" for p in self.players)
        return (
            f"🎲 **BLEFE DE DADOS** — Aposta: `{self.aposta:.2f} MC` por jogador\n"
            f"👥 **Na mesa ({len(self.players)}/{MAX_JOGADORES}):** {nomes or '—'}\n\n"
            f"Clique **Entrar** para participar ou **▶️ Começar** para iniciar!\n"
            f"*Mínimo {MIN_JOGADORES} jogadores · Aguardando {TIMEOUT_LOBBY}s*"
        )

    @disnake.ui.button(label="🎲 Entrar", style=disnake.ButtonStyle.success, row=0)
    async def entrar(self, button, inter: disnake.MessageInteraction):
        if inter.author in self.players:
            return await inter.response.send_message("🐒 Você já está na mesa!", ephemeral=True)
        if len(self.players) >= MAX_JOGADORES:
            return await inter.response.send_message(
                f"🚫 Mesa cheia! Máximo de **{MAX_JOGADORES} jogadores**.", ephemeral=True
            )

        u_db = db.get_user_data(str(inter.author.id))
        if not u_db:
            return await inter.response.send_message("❌ Conta não encontrada! Use `!trabalhar` primeiro.", ephemeral=True)

        cargo = u_db['data'][3] if len(u_db['data']) > 3 else "Lêmure"
        if self.aposta > get_limite(cargo):
            return await inter.response.send_message(
                f"🚫 Aposta excede seu limite de **{cargo}** (`{get_limite(cargo)} MC`).", ephemeral=True
            )
        if db.parse_float(u_db['data'][2]) < self.aposta:
            return await inter.response.send_message("❌ Saldo insuficiente!", ephemeral=True)

        # Debita aposta na entrada
        db.update_value(u_db['row'], 3, round(db.parse_float(u_db['data'][2]) - self.aposta, 2))
        self.players.append(inter.author)
        await inter.response.edit_message(content=self._lobby_text())

    @disnake.ui.button(label="▶️ Começar", style=disnake.ButtonStyle.primary, row=0)
    async def comecar(self, button, inter: disnake.MessageInteraction):
        if inter.author.id != self.ctx.author.id:
            return await inter.response.send_message("❌ Só o criador da mesa pode iniciar!", ephemeral=True)
        if len(self.players) < MIN_JOGADORES:
            return await inter.response.send_message(
                f"❌ Mínimo de **{MIN_JOGADORES} jogadores** para começar!", ephemeral=True
            )
        self.started = True
        for item in self.children:
            item.disabled = True
        await inter.response.edit_message(content="✅ Jogo iniciado!", view=self)
        self.stop()

    async def on_timeout(self):
        self.stop()
        for item in self.children:
            item.disabled = True
        try:
            if self.msg and not self.started:
                await self.msg.edit(
                    content="⏰ Tempo esgotado! Jogadores insuficientes. Apostas devolvidas.",
                    view=self
                )
        except:
            pass


# ─────────────────────────────────────────────────────────────────────────────
#  VIEW: TURNO — o jogador ativo faz a aposta ou passa a vez
# ─────────────────────────────────────────────────────────────────────────────

class MentiraTurnoView(disnake.ui.View):
    """
    Botões: [+Qtd] [-Qtd] [+Face] [-Face] [✅ Apostar] [🚨 Mentira!]
    Qualquer jogador (exceto o ativo) pode clicar Mentira.
    Só o jogador ativo pode apostar.
    """
    def __init__(self, jogo, jogador_ativo: disnake.Member):
        super().__init__(timeout=TIMEOUT_TURNO)
        self.jogo          = jogo
        self.jogador_ativo = jogador_ativo
        # Valores selecionados para a aposta (começa logo acima da anterior)
        prev_qtd, prev_face = jogo.aposta_atual
        # Próxima aposta mínima válida
        if prev_face < FACES:
            self.sel_qtd  = prev_qtd
            self.sel_face = prev_face + 1
        else:
            self.sel_qtd  = prev_qtd + 1
            self.sel_face = 1
        self.resultado = None   # "apostou" | "mentira"
        self.chamador  = None   # quem gritou mentira

    def _label_aposta(self) -> str:
        return f"✅ Apostar: {self.sel_qtd}x [{self.sel_face}]"

    def _rebuild(self):
        self.clear_items()

        btn_menos_qtd = disnake.ui.Button(label="◀ Qtd", style=disnake.ButtonStyle.secondary, custom_id="menos_qtd", row=0)
        btn_mais_qtd  = disnake.ui.Button(label="Qtd ▶", style=disnake.ButtonStyle.secondary, custom_id="mais_qtd",  row=0)
        btn_menos_fac = disnake.ui.Button(label="◀ Face", style=disnake.ButtonStyle.secondary, custom_id="menos_fac", row=1)
        btn_mais_fac  = disnake.ui.Button(label="Face ▶", style=disnake.ButtonStyle.secondary, custom_id="mais_fac",  row=1)
        btn_apostar   = disnake.ui.Button(
            label=self._label_aposta(), style=disnake.ButtonStyle.success, custom_id="apostar", row=2
        )
        btn_mentira   = disnake.ui.Button(
            label="🚨 MENTIRA!", style=disnake.ButtonStyle.danger, custom_id="mentira", row=2
        )

        btn_menos_qtd.callback = self._cb_menos_qtd
        btn_mais_qtd.callback  = self._cb_mais_qtd
        btn_menos_fac.callback = self._cb_menos_fac
        btn_mais_fac.callback  = self._cb_mais_fac
        btn_apostar.callback   = self._cb_apostar
        btn_mentira.callback   = self._cb_mentira

        self.add_item(btn_menos_qtd)
        self.add_item(btn_mais_qtd)
        self.add_item(btn_menos_fac)
        self.add_item(btn_mais_fac)
        self.add_item(btn_apostar)
        self.add_item(btn_mentira)

    # ── Callbacks de ajuste ────────────────────────────────────────────────
    async def _cb_menos_qtd(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.jogador_ativo.id:
            return await inter.response.send_message("❌ Não é a sua vez!", ephemeral=True)
        prev_qtd, prev_face = self.jogo.aposta_atual
        nova_qtd = max(self.sel_qtd - 1, prev_qtd)
        # garante que a aposta ainda é maior que a anterior
        if (nova_qtd, self.sel_face) <= (prev_qtd, prev_face):
            return await inter.response.send_message("❌ Aposta inválida! Deve ser maior que a anterior.", ephemeral=True)
        self.sel_qtd = nova_qtd
        self._rebuild()
        await inter.response.edit_message(embed=self.jogo._embed_turno(), view=self)

    async def _cb_mais_qtd(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.jogador_ativo.id:
            return await inter.response.send_message("❌ Não é a sua vez!", ephemeral=True)
        total_dados = len(self.jogo.players) * DADOS_POR_JOGADOR
        self.sel_qtd = min(self.sel_qtd + 1, total_dados)
        self._rebuild()
        await inter.response.edit_message(embed=self.jogo._embed_turno(), view=self)

    async def _cb_menos_fac(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.jogador_ativo.id:
            return await inter.response.send_message("❌ Não é a sua vez!", ephemeral=True)
        prev_qtd, prev_face = self.jogo.aposta_atual
        nova_face = max(self.sel_face - 1, 1)
        if (self.sel_qtd, nova_face) <= (prev_qtd, prev_face):
            return await inter.response.send_message("❌ Aposta inválida! Deve ser maior que a anterior.", ephemeral=True)
        self.sel_face = nova_face
        self._rebuild()
        await inter.response.edit_message(embed=self.jogo._embed_turno(), view=self)

    async def _cb_mais_fac(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.jogador_ativo.id:
            return await inter.response.send_message("❌ Não é a sua vez!", ephemeral=True)
        self.sel_face = min(self.sel_face + 1, FACES)
        self._rebuild()
        await inter.response.edit_message(embed=self.jogo._embed_turno(), view=self)

    # ── Apostar ────────────────────────────────────────────────────────────
    async def _cb_apostar(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.jogador_ativo.id:
            return await inter.response.send_message("❌ Não é a sua vez!", ephemeral=True)

        prev_qtd, prev_face = self.jogo.aposta_atual
        if not aposta_maior(self.sel_qtd, self.sel_face, prev_qtd, prev_face):
            return await inter.response.send_message("❌ Sua aposta deve ser maior que a anterior!", ephemeral=True)

        self.jogo.aposta_atual = (self.sel_qtd, self.sel_face)
        self.resultado = "apostou"
        for item in self.children:
            item.disabled = True
        await inter.response.edit_message(view=self)
        self.stop()

    # ── Mentira ────────────────────────────────────────────────────────────
    async def _cb_mentira(self, inter: disnake.MessageInteraction):
        # Qualquer jogador da mesa (exceto o ativo) pode chamar
        if inter.author.id == self.jogador_ativo.id:
            return await inter.response.send_message("❌ Você não pode chamar mentira na sua própria aposta!", ephemeral=True)
        if inter.author not in self.jogo.players:
            return await inter.response.send_message("❌ Você não está neste jogo!", ephemeral=True)

        self.chamador  = inter.author
        self.resultado = "mentira"
        for item in self.children:
            item.disabled = True
        await inter.response.edit_message(view=self)
        self.stop()

    async def on_timeout(self):
        # Jogador inativo no turno → perde automaticamente
        self.resultado = "timeout"
        self.stop()


# ─────────────────────────────────────────────────────────────────────────────
#  ESTADO DO JOGO
# ─────────────────────────────────────────────────────────────────────────────

class MentiraGame:
    def __init__(self, ctx, players: list[disnake.Member], aposta: float):
        self.ctx         = ctx
        self.players     = players
        self.aposta      = aposta
        # Dados de cada jogador: {member.id: [int, ...]}
        self.dados: dict = {p.id: rolar_dados(DADOS_POR_JOGADOR) for p in players}
        # Aposta atual na mesa: (quantidade, face) — começa em (0, 0)
        self.aposta_atual: tuple[int, int] = (0, 0)
        self.turno_idx   = 0   # índice do jogador ativo em self.players
        self.msg         = None

    @property
    def jogador_ativo(self) -> disnake.Member:
        return self.players[self.turno_idx % len(self.players)]

    @property
    def total_dados(self) -> int:
        return len(self.players) * DADOS_POR_JOGADOR

    def _embed_turno(self) -> disnake.Embed:
        ativo = self.jogador_ativo
        qtd, face = self.aposta_atual

        if qtd == 0:
            aposta_str_atual = "*Nenhuma aposta ainda — seja o primeiro!*"
        else:
            aposta_str_atual = f"Aposta na mesa: {aposta_str(qtd, face)}"

        desc = (
            f"🎯 **Vez de {ativo.mention}**\n\n"
            f"📢 {aposta_str_atual}\n\n"
            f"🎲 Total de dados na mesa: **{self.total_dados}**\n"
            f"👥 Jogadores: {', '.join(p.display_name for p in self.players)}\n\n"
            f"*Use os botões para ajustar e confirmar sua aposta, ou chame **🚨 MENTIRA!** se achar que a aposta atual é falsa.*"
        )
        embed = disnake.Embed(
            title="🎲 BLEFE DE DADOS",
            description=desc,
            color=disnake.Color.blurple()
        )
        embed.set_footer(text=f"Aposta: {self.aposta:.2f} MC/jogador · {TIMEOUT_TURNO}s por turno")
        return embed

    def _embed_revelacao(self, perdedor: disnake.Member, chamador: disnake.Member | None,
                         qtd_apostada: int, face_apostada: int, real: int, timeout: bool = False) -> disnake.Embed:
        # Monta tabela de dados revelados
        linhas = []
        for p in self.players:
            dados_p = self.dados[p.id]
            count_face = dados_p.count(face_apostada)
            linhas.append(
                f"**{p.display_name}:** {dados_str(dados_p)} → `{count_face}x [{face_apostada}]`"
            )

        todos_dados_fmt = "\n".join(linhas)

        if timeout:
            titulo = f"⏰ {perdedor.display_name} demorou demais e perdeu!"
            desc_resultado = f"**{perdedor.mention}** ficou inativo e perdeu a aposta automaticamente."
        elif chamador:
            if perdedor == chamador:
                titulo = "✅ A aposta era VERDADEIRA! Quem chamou mentira perdeu."
                desc_resultado = (
                    f"**{chamador.mention}** chamou MENTIRA, mas havia **{real}x** {EMOJI_DADO[face_apostada]} na mesa "
                    f"(aposta era de {aposta_str(qtd_apostada, face_apostada)}).\n"
                    f"💀 **{chamador.display_name}** perde a aposta!"
                )
            else:
                titulo = "🚨 ERA MENTIRA! Quem apostou perdeu."
                desc_resultado = (
                    f"**{chamador.mention}** chamou MENTIRA corretamente! Havia apenas **{real}x** {EMOJI_DADO[face_apostada]} na mesa "
                    f"(aposta era de {aposta_str(qtd_apostada, face_apostada)}).\n"
                    f"💀 **{perdedor.display_name}** perde a aposta!"
                )
        else:
            titulo = "✅ Campo limpo! Ninguém chamou mentira."
            desc_resultado = "A rodada terminou sem ninguém chamar mentira."

        vencedores = [p for p in self.players if p != perdedor]
        premio_unitario = round(
            (self.aposta * len(self.players)) / len(vencedores), 2
        ) if vencedores else 0.0

        embed = disnake.Embed(
            title=f"🎲 {titulo}",
            description=(
                f"{desc_resultado}\n\n"
                f"**📊 Dados revelados:**\n{todos_dados_fmt}\n\n"
                f"**Total de** {EMOJI_DADO[face_apostada]} **na mesa:** `{real}` de `{self.total_dados}`"
            ),
            color=disnake.Color.red() if perdedor != chamador else disnake.Color.green()
        )
        if vencedores:
            embed.add_field(
                name="🏆 Vencedores",
                value="\n".join(f"✅ {p.mention} +**{premio_unitario:.2f} MC**" for p in vencedores),
                inline=False
            )
        embed.add_field(
            name="💀 Perdedor",
            value=f"❌ {perdedor.mention} perdeu **{self.aposta:.2f} MC**",
            inline=False
        )
        return embed


# ─────────────────────────────────────────────────────────────────────────────
#  COG
# ─────────────────────────────────────────────────────────────────────────────

class Mentira(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, jogue no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["blefe", "dados", "liar"])
    async def mentira(self, ctx, aposta: float = None):
        if aposta is None:
            embed = disnake.Embed(
                title="🎲 BLEFE DE DADOS",
                description=(
                    "**Como jogar:**\n"
                    "Cada jogador recebe **5 dados secretos** (🤫 só você os vê via DM).\n"
                    "Na sua vez, você aposta: *\"existem pelo menos X dados com face Y na mesa, contando os dados de todos\"*.\n"
                    "Cada aposta deve ser maior que a anterior (mais quantidade OU mesma quantidade e face maior).\n"
                    "Qualquer jogador pode gritar **🚨 MENTIRA!** a qualquer momento.\n\n"
                    "**Resultado:**\n"
                    "Se a aposta era **verdadeira** → quem chamou mentira **perde**.\n"
                    "Se a aposta era **falsa** → quem apostou **perde**.\n"
                    "O perdedor perde sua aposta, os vencedores dividem o pote!\n\n"
                    "**Uso:** `!mentira <valor>`\n"
                    f"*{MIN_JOGADORES}–{MAX_JOGADORES} jogadores · Cada jogador aposta separadamente*"
                ),
                color=disnake.Color.blurple()
            )
            return await ctx.send(embed=embed)

        if aposta <= 0:
            return await ctx.send(f"❌ {ctx.author.mention}, aposta inválida!")
        aposta = round(aposta, 2)

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send(f"❌ {ctx.author.mention}, conta não encontrada!")

            saldo = db.parse_float(user['data'][2])
            cargo = user['data'][3] if len(user['data']) > 3 else "Lêmure"

            if saldo < aposta:
                return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")
            if aposta > get_limite(cargo):
                return await ctx.send(f"🚫 Limite de aposta para **{cargo}** é de **{get_limite(cargo)} MC**!")

            # Debita aposta do criador
            db.update_value(user['row'], 3, round(saldo - aposta, 2))

            # ── Lobby ─────────────────────────────────────────────────────────
            lobby_view = MentiraLobbyView(ctx, aposta)
            lobby_view.players.append(ctx.author)
            lobby_view.side_bets = {}   # compatibilidade futura
            msg_lobby = await ctx.send(content=lobby_view._lobby_text(), view=lobby_view)
            lobby_view.msg = msg_lobby
            await lobby_view.wait()

            if not lobby_view.started:
                # O jogo não começou (timeout ou cancelado). Devolve a aposta para TODOS que entraram.
                for p in lobby_view.players:
                    try:
                        u_ref = db.get_user_data(str(p.id))
                        if u_ref:
                            s = db.parse_float(u_ref['data'][2])
                            db.update_value(u_ref['row'], 3, round(s + aposta, 2))
                    except Exception as e:
                        print(f"❌ Erro ao devolver aposta para {p.id}: {e}")
                return

            players = lobby_view.players

            # ── Inicializa jogo e envia dados por DM ──────────────────────────
            jogo = MentiraGame(ctx, players, aposta)

            falhou_dm = []
            for p in players:
                dados_p = jogo.dados[p.id]
                try:
                    await p.send(
                        f"🎲 **BLEFE DE DADOS** — Seus dados secretos:\n"
                        f"{dados_str(dados_p)}\n"
                        f"*(Canal: {ctx.channel.mention})*"
                    )
                except disnake.Forbidden:
                    falhou_dm.append(p.display_name)

            if falhou_dm:
                aviso = await ctx.send(
                    f"⚠️ Não consegui enviar DM para: **{', '.join(falhou_dm)}**.\n"
                    f"Esses jogadores precisam habilitar DMs para receber seus dados secretos.\n"
                    f"*O jogo continuará em **10 segundos** — esses jogadores jogarão sem ver seus dados.*"
                )
                await asyncio.sleep(10)
                try:
                    await aviso.delete()
                except:
                    pass

            # ── Loop de turnos ────────────────────────────────────────────────
            msg_jogo = await ctx.send(embed=jogo._embed_turno())
            jogo.msg = msg_jogo

            perdedor  = None
            chamador  = None
            timeout_p = False

            while True:
                ativo = jogo.jogador_ativo
                turno_view = MentiraTurnoView(jogo, ativo)
                turno_view._rebuild()

                await msg_jogo.edit(embed=jogo._embed_turno(), view=turno_view)
                await turno_view.wait()

                resultado = turno_view.resultado

                # ── Mentira chamada ───────────────────────────────────────────
                if resultado == "mentira":
                    chamador = turno_view.chamador
                    qtd_apostada, face_apostada = jogo.aposta_atual

                    if qtd_apostada == 0:
                        # Impossível chamar mentira sem aposta — não deveria acontecer
                        await ctx.send("⚠️ Não há aposta na mesa para chamar mentira!")
                        continue

                    real = contar_face(list(jogo.dados.values()), face_apostada)
                    aposta_verdadeira = real >= qtd_apostada

                    perdedor = chamador if aposta_verdadeira else ativo
                    embed_rev = jogo._embed_revelacao(perdedor, chamador, qtd_apostada, face_apostada, real)
                    break

                # ── Timeout ───────────────────────────────────────────────────
                elif resultado == "timeout":
                    perdedor  = ativo
                    timeout_p = True
                    qtd_apostada, face_apostada = jogo.aposta_atual
                    real = contar_face(list(jogo.dados.values()), face_apostada) if face_apostada > 0 else 0
                    embed_rev = jogo._embed_revelacao(
                        perdedor, None, qtd_apostada, face_apostada, real, timeout=True
                    )
                    break

                # ── Apostou — próximo turno ───────────────────────────────────
                else:
                    jogo.turno_idx += 1
                    # Se der a volta completa sem mentira, termina a rodada sem perdedor
                    if jogo.turno_idx >= len(players) * 3:
                        # Segurança: encerra após 3 voltas completas sem mentira
                        await ctx.send("⏳ Três voltas completas sem mentira! O pote é devolvido.")
                        for p in players:
                            try:
                                u_ref = db.get_user_data(str(p.id))
                                if u_ref:
                                    s = db.parse_float(u_ref['data'][2])
                                    db.update_value(u_ref['row'], 3, round(s + aposta, 2))
                            except:
                                pass
                        return

            # ── Distribui ganhos ──────────────────────────────────────────────
            vencedores = [p for p in players if p != perdedor]
            if vencedores:
                pote_total      = round(aposta * len(players), 2)
                premio_unitario = round(pote_total / len(vencedores), 2)
                for p in vencedores:
                    try:
                        u_ref = db.get_user_data(str(p.id))
                        if u_ref:
                            s = db.parse_float(u_ref['data'][2])
                            db.update_value(u_ref['row'], 3, round(s + premio_unitario, 2))
                    except Exception as e:
                        print(f"❌ Erro ao pagar vencedor {p.id} no !mentira: {e}")

            # Conquista: ganhou blefando com a maior aposta possível
            if perdedor and perdedor != chamador:
                # O apostador foi pego na mentira → chamador e restantes ganham
                for p in vencedores:
                    try:
                        u_ref = db.get_user_data(str(p.id))
                        if u_ref:
                            save_achievement(u_ref, "detetive")
                    except:
                        pass

            # Conquista: blefou e ninguém chamou (não usado nesta versão de rodada única,
            # mas deixamos para expansão futura)

            # ── Mensagem final ────────────────────────────────────────────────
            for item in turno_view.children:
                item.disabled = True
            await msg_jogo.edit(embed=embed_rev, view=None)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !mentira de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")


def setup(bot):
    bot.add_cog(Mentira(bot))