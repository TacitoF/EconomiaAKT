import disnake
from disnake.ext import commands
import database as db
import random
import asyncio
from typing import Optional

# ══════════════════════════════════════════════════════════════════════════════
#  BARALHO — Truco Paulista (sem 8, 9, A de espadas/paus no deck normal)
#  Manilhas fixas (vira não existe no paulista — manilhas são sempre as mesmas)
#  Ordem: 4♣ > A♥ > 7♦ > 7♠ > 3 > 2 > A > K > J > Q > 7 > 6 > 5 > 4
# ══════════════════════════════════════════════════════════════════════════════

NAIPES   = ["♠", "♥", "♦", "♣"]
NAIPE_EM = {"♠": "♠️", "♥": "♥️", "♦": "♦️", "♣": "♣️"}

# Força de cada carta (maior = mais forte). Manilhas têm força 14+
FORCA_CARTA = {
    ("4", "♣"): 14,  # zap — manilha mais forte
    ("A", "♥"): 13,  # copas
    ("7", "♦"): 12,  # espadinha
    ("7", "♠"): 11,  # espadão
    "3":  10,
    "2":   9,
    "A":   8,
    "K":   7,
    "J":   6,
    "Q":   5,
    "7":   4,
    "6":   3,
    "5":   2,
    "4":   1,
}

VALORES = ["4", "5", "6", "7", "Q", "J", "K", "A", "2", "3"]

NOME_MANILHA = {
    ("4", "♣"): "Zap",
    ("A", "♥"): "Copas",
    ("7", "♦"): "Espadinha",
    ("7", "♠"): "Espadão",
}

def forca(valor: str, naipe: str) -> int:
    if (valor, naipe) in FORCA_CARTA:
        return FORCA_CARTA[(valor, naipe)]
    return FORCA_CARTA.get(valor, 0)

def label_carta(valor: str, naipe: str, oculta: bool = False) -> str:
    if oculta:
        return "🂠"
    em = NAIPE_EM[naipe]
    nome = NOME_MANILHA.get((valor, naipe), "")
    suffix = f" *{nome}*" if nome else ""
    return f"`{valor}{em}`{suffix}"

def criar_baralho():
    baralho = [(v, n) for v in VALORES for n in NAIPES]
    random.shuffle(baralho)
    return baralho

def formatar_moeda(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ══════════════════════════════════════════════════════════════════════════════
#  ESTADO DA PARTIDA
# ══════════════════════════════════════════════════════════════════════════════

class Partida:
    """
    Representa uma partida de Truco Paulista completa.
    Suporta 1v1 e 2v2.
    Estado completamente em memória — Sheets só é tocado no fim.
    """

    def __init__(self, jogadores: list, aposta: float, canal_id: int, modo: str):
        """
        jogadores: lista de disnake.Member em ordem [j0, j1] ou [j0, j1, j2, j3]
        modo: "1v1" ou "2v2"
        Times: [0,2] vs [1,3] no 2v2; [0] vs [1] no 1v1
        """
        self.jogadores   = jogadores
        self.aposta      = aposta
        self.canal_id    = canal_id
        self.modo        = modo
        self.n           = len(jogadores)

        # Pontos da partida (por time)
        self.pontos      = [0, 0]       # pontos[0] = time 0, pontos[1] = time 1

        # Mão atual
        self.maos_ganhas = [0, 0]       # rodadas vencidas na mão atual
        self.vez_idx     = 0            # índice de quem joga agora
        self.rodada      = 1            # 1, 2 ou 3
        self.cartas_mesa = {}           # {idx_jogador: (valor, naipe)}
        self.ja_jogou    = set()        # jogadores que já jogaram na rodada
        self.maos_rodada = []           # resultado de cada rodada: 0, 1 ou "empate"
        self.primeiro_da_mao = 0        # quem começou a mão

        # Truco
        self.truco_ativo    = False
        self.truco_valor    = 1         # vale 1 ponto (sem truco), 3, 6, 9, 12
        self.truco_pediu_idx = None     # quem pediu truco
        self.aguardando_resposta = False

        # Mão de 11
        self.mao_de_11 = False
        self.mao_de_11_aceita = None   # True/False/None

        # Cartas na mão de cada jogador {idx: [(valor, naipe), ...]}
        self.maos: dict = {}

        self.encerrada = False
        self.vencedor_time = None       # 0 ou 1

        self._distribuir()

    def time_de(self, idx: int) -> int:
        """Retorna 0 ou 1 — o time do jogador pelo índice."""
        if self.modo == "1v1":
            return idx
        return idx % 2

    def parceiros(self, idx: int) -> list:
        """Índices dos parceiros de equipe (vazio no 1v1)."""
        meu_time = self.time_de(idx)
        return [i for i in range(self.n) if i != idx and self.time_de(i) == meu_time]

    def adversarios(self, idx: int) -> list:
        return [i for i in range(self.n) if self.time_de(i) != self.time_de(idx)]

    def _distribuir(self):
        baralho = criar_baralho()
        self.maos = {}
        for i, _ in enumerate(self.jogadores):
            self.maos[i] = [baralho.pop() for _ in range(3)]
        self.cartas_mesa = {}
        self.ja_jogou    = set()
        self.maos_ganhas = [0, 0]
        self.maos_rodada = []
        self.rodada      = 1
        self.truco_ativo      = False
        self.truco_valor      = 1
        self.truco_pediu_idx  = None
        self.aguardando_resposta = False
        self.mao_de_11        = False
        self.mao_de_11_aceita = None

        # Verifica mão de 11
        if 11 in self.pontos:
            self.mao_de_11 = True

    def proximo_jogador(self):
        """Avança vez para o próximo jogador que ainda não jogou na rodada."""
        inicio = self.vez_idx
        for _ in range(self.n):
            self.vez_idx = (self.vez_idx + 1) % self.n
            if self.vez_idx not in self.ja_jogou:
                return
        self.vez_idx = inicio

    def jogador_atual(self) -> disnake.Member:
        return self.jogadores[self.vez_idx]

    def jogar_carta(self, idx: int, carta_idx: int) -> bool:
        """Joga uma carta. Retorna True se a rodada fechou."""
        carta = self.maos[idx].pop(carta_idx)
        self.cartas_mesa[idx] = carta
        self.ja_jogou.add(idx)

        if len(self.ja_jogou) < self.n:
            self.proximo_jogador()
            return False
        return True

    def resolver_rodada(self) -> tuple:
        """
        Resolve a rodada atual.
        Retorna (time_vencedor_ou_"empate", detalhes)
        """
        # Encontra a carta mais forte
        melhor_forca = -1
        melhor_idxs  = []
        for idx, (v, n) in self.cartas_mesa.items():
            f = forca(v, n)
            if f > melhor_forca:
                melhor_forca = f
                melhor_idxs  = [idx]
            elif f == melhor_forca:
                melhor_idxs.append(idx)

        times_vencedores = list({self.time_de(i) for i in melhor_idxs})

        if len(times_vencedores) == 1:
            t = times_vencedores[0]
            self.maos_ganhas[t] += 1
            self.maos_rodada.append(t)
            return t, melhor_idxs
        else:
            self.maos_rodada.append("empate")
            return "empate", melhor_idxs

    def verificar_fim_mao(self) -> Optional[int]:
        """
        Verifica se a mão acabou após resolver a rodada.
        Retorna time vencedor (0 ou 1) ou None se a mão continua.
        Regras:
          - Vence quem ganhar 2 rodadas
          - Se empatar 1ª e vencer 2ª → vence 2ª
          - Se vencer 1ª e empatar 2ª → vence quem ganhou 1ª
          - 3 empates → time que começou a mão (vez_idx original)
        """
        r = self.maos_rodada

        if len(r) == 1:
            if r[0] == "empate":
                return None   # continua
            return None       # continua

        if len(r) == 2:
            if r[0] != "empate" and r[1] != "empate":
                if r[0] == r[1]: return r[0]
                return None   # 1 a 1, vai pra 3ª
            if r[0] == "empate":
                return r[1] if r[1] != "empate" else None
            if r[1] == "empate":
                return r[0]
            return None

        if len(r) == 3:
            # conta vitórias
            v = [r.count(0), r.count(1)]
            if v[0] > v[1]: return 0
            if v[1] > v[0]: return 1
            # empate geral → quem começou
            return self.time_de(self.primeiro_da_mao)

        return None

    def pontuar_mao(self, time_vencedor: int):
        """Adiciona pontos ao time vencedor e prepara próxima mão."""
        pts = self.truco_valor if self.truco_ativo else 1
        if self.mao_de_11 and self.mao_de_11_aceita:
            pts = 3  # mão de 11 vale 3
        self.pontos[time_vencedor] += pts

        # Verifica fim de partida
        if self.pontos[time_vencedor] >= 12:
            self.encerrada      = True
            self.vencedor_time  = time_vencedor
            return True

        # Prepara próxima mão
        self.primeiro_da_mao = (self.primeiro_da_mao + 1) % self.n
        self.vez_idx         = self.primeiro_da_mao
        self._distribuir()
        return False

    # ── Truco ─────────────────────────────────────────────────────────────────

    ESCALA_TRUCO = [3, 6, 9, 12]

    def pode_pedir_truco(self, idx: int) -> bool:
        if self.aguardando_resposta: return False
        if self.truco_valor == 12:   return False
        if self.truco_pediu_idx is not None and self.time_de(self.truco_pediu_idx) == self.time_de(idx):
            return False
        return True

    def proximo_valor_truco(self) -> int:
        for v in self.ESCALA_TRUCO:
            if v > self.truco_valor:
                return v
        return 12

    def aceitar_truco(self):
        self.truco_ativo         = True
        self.truco_valor         = self.proximo_valor_truco() if not self.truco_ativo else self.truco_valor
        self.aguardando_resposta = False

    def recusar_truco(self) -> int:
        """Recusa o truco. Retorna o time que ganhou os pontos."""
        pts_atuais = max(1, self.truco_valor - (3 if self.truco_valor > 3 else 2))
        # time que pediu truco ganha o que estava valendo antes
        time_pediu = self.time_de(self.truco_pediu_idx)
        self.aguardando_resposta = False
        return time_pediu

    def aumentar_truco(self, idx: int):
        """Contra-truco: aceita e já pede mais."""
        self.truco_ativo         = True
        self.truco_valor         = self.proximo_valor_truco()
        self.truco_pediu_idx     = idx
        self.aguardando_resposta = True


# ══════════════════════════════════════════════════════════════════════════════
#  GERENCIADOR DE PARTIDAS ATIVAS
# ══════════════════════════════════════════════════════════════════════════════

# partidas_ativas: {canal_id: Partida}
partidas_ativas: dict[int, Partida] = {}

# lobbies pendentes: {canal_id: {"dono": Member, "modo": str, "aposta": float,
#                                 "jogadores": [Member], "message": Message}}
lobbies_pendentes: dict[int, dict] = {}


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS DE EMBED
# ══════════════════════════════════════════════════════════════════════════════

def _cor_pontos(pts: int) -> int:
    if pts >= 9:  return 0xE53935
    if pts >= 6:  return 0xFF8C00
    return 0x4CAF50

def embed_partida(p: Partida, titulo: str = "🃏 TRUCO PAULISTA", msg: str = "") -> disnake.Embed:
    """Embed público da partida — mostra placar e mesa, sem revelar cartas."""
    if p.modo == "1v1":
        t0 = p.jogadores[0].display_name
        t1 = p.jogadores[1].display_name
        cabecalho = f"⚔️  **{t0}** `{p.pontos[0]}` × `{p.pontos[1]}` **{t1}**"
    else:
        t0 = f"{p.jogadores[0].display_name} & {p.jogadores[2].display_name}"
        t1 = f"{p.jogadores[1].display_name} & {p.jogadores[3].display_name}"
        cabecalho = f"⚔️  **{t0}**\n`{p.pontos[0]}` × `{p.pontos[1]}`\n**{t1}**"

    desc  = f"{cabecalho}\n"
    desc += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    desc += f"🎯 **Mão {p.rodada}/3**  "

    valor_str = {1: "1 ponto", 3: "Truco! (3)", 6: "Seis! (6)", 9: "Nove! (9)", 12: "Doze! (12)"}
    desc += f"💰 Apostado: **{formatar_moeda(p.aposta)} MC** × {valor_str.get(p.truco_valor, str(p.truco_valor))}\n"

    # Rodadas ganhas
    icones = []
    for r in p.maos_rodada:
        if r == 0:       icones.append("🟦")
        elif r == 1:     icones.append("🟥")
        else:            icones.append("⬜")
    while len(icones) < 3:
        icones.append("⬛")
    desc += f"📊 Rodadas: {'  '.join(icones)}\n\n"

    # Mesa
    if p.cartas_mesa:
        desc += "**🃏 Mesa:**\n"
        for idx, (v, n) in p.cartas_mesa.items():
            nome = p.jogadores[idx].display_name
            desc += f"  {nome}: {label_carta(v, n)}\n"
        desc += "\n"

    if msg:
        desc += f"💬 {msg}\n"

    if not p.encerrada and not p.aguardando_resposta:
        desc += f"\n🎮 Vez de **{p.jogador_atual().display_name}**"

    embed = disnake.Embed(
        title       = titulo,
        description = desc,
        color       = 0x1a6b1a,
    )
    return embed


def embed_mao_privada(p: Partida, idx: int) -> disnake.Embed:
    """Embed privado enviado por DM ou ephemeral com as cartas do jogador."""
    cartas = p.maos.get(idx, [])
    linhas = []
    for i, (v, n) in enumerate(cartas):
        linhas.append(f"`{i+1}.` {label_carta(v, n)}")
    txt = "\n".join(linhas) if linhas else "*Sem cartas*"

    embed = disnake.Embed(
        title       = "🤫 Suas cartas",
        description = txt,
        color       = 0x2C2F33,
    )
    embed.set_footer(text="Use os botões na partida para jogar. Ninguém mais vê isso!")
    return embed


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW: LOBBY
# ══════════════════════════════════════════════════════════════════════════════

class ViewLobby(disnake.ui.View):
    def __init__(self, canal_id: int, cog):
        super().__init__(timeout=120)
        self.canal_id = canal_id
        self.cog      = cog

    @disnake.ui.button(label="✅ Entrar", style=disnake.ButtonStyle.success)
    async def btn_entrar(self, button, inter: disnake.MessageInteraction):
        lobby = lobbies_pendentes.get(self.canal_id)
        if not lobby:
            return await inter.response.send_message("❌ Lobby não encontrado.", ephemeral=True)

        if inter.author in lobby["jogadores"]:
            return await inter.response.send_message("⚠️ Você já está no lobby!", ephemeral=True)

        max_j = 2 if lobby["modo"] == "1v1" else 4
        if len(lobby["jogadores"]) >= max_j:
            return await inter.response.send_message("❌ Lobby cheio!", ephemeral=True)

        lobby["jogadores"].append(inter.author)
        await inter.response.defer()

        # Atualiza embed do lobby
        await self._atualizar_lobby(inter, lobby, max_j)

        # Inicia se cheio
        if len(lobby["jogadores"]) == max_j:
            await asyncio.sleep(1)
            await self.cog._iniciar_partida(inter, self.canal_id)

    @disnake.ui.button(label="❌ Cancelar", style=disnake.ButtonStyle.danger)
    async def btn_cancelar(self, button, inter: disnake.MessageInteraction):
        lobby = lobbies_pendentes.get(self.canal_id)
        if not lobby:
            return await inter.response.defer()
        if inter.author != lobby["dono"] and not inter.author.guild_permissions.administrator:
            return await inter.response.send_message("❌ Só o dono pode cancelar.", ephemeral=True)

        lobbies_pendentes.pop(self.canal_id, None)
        await inter.response.edit_message(
            content="❌ Lobby cancelado.", embed=None, view=None
        )

    async def _atualizar_lobby(self, inter, lobby, max_j):
        jogadores_txt = "\n".join(f"• {j.mention}" for j in lobby["jogadores"])
        faltam = max_j - len(lobby["jogadores"])
        embed = disnake.Embed(
            title       = "🃏 TRUCO — AGUARDANDO JOGADORES",
            description = (
                f"**Modo:** `{lobby['modo'].upper()}`\n"
                f"**Aposta:** `{formatar_moeda(lobby['aposta'])} MC` por jogador\n\n"
                f"**Jogadores ({len(lobby['jogadores'])}/{max_j}):**\n{jogadores_txt}\n\n"
                f"{'⏳ Aguardando mais ' + str(faltam) + ' jogador(es)...' if faltam > 0 else '🚀 Iniciando!'}"
            ),
            color = 0xFFD700,
        )
        try:
            await lobby["message"].edit(embed=embed, view=self)
        except Exception:
            pass

    async def on_timeout(self):
        lobbies_pendentes.pop(self.canal_id, None)
        try:
            await self.message.edit(content="⏳ Lobby expirou.", embed=None, view=None)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW: JOGO
# ══════════════════════════════════════════════════════════════════════════════

class ViewTruco(disnake.ui.View):
    def __init__(self, canal_id: int, cog):
        super().__init__(timeout=300)
        self.canal_id = canal_id
        self.cog      = cog

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        p = partidas_ativas.get(self.canal_id)
        if not p:
            await inter.response.send_message("❌ Partida não encontrada.", ephemeral=True)
            return False
        if inter.author not in p.jogadores:
            await inter.response.send_message("❌ Você não está nesta partida.", ephemeral=True)
            return False
        return True

    @disnake.ui.button(label="🃏 Ver minhas cartas", style=disnake.ButtonStyle.primary, row=0)
    async def btn_ver_cartas(self, button, inter: disnake.MessageInteraction):
        p   = partidas_ativas.get(self.canal_id)
        idx = p.jogadores.index(inter.author)
        embed = embed_mao_privada(p, idx)
        await inter.response.send_message(embed=embed, ephemeral=True)

    @disnake.ui.button(label="1️⃣ Jogar carta 1", style=disnake.ButtonStyle.secondary, row=1)
    async def btn_carta1(self, button, inter): await self.cog._jogar(inter, self.canal_id, 0)

    @disnake.ui.button(label="2️⃣ Jogar carta 2", style=disnake.ButtonStyle.secondary, row=1)
    async def btn_carta2(self, button, inter): await self.cog._jogar(inter, self.canal_id, 1)

    @disnake.ui.button(label="3️⃣ Jogar carta 3", style=disnake.ButtonStyle.secondary, row=1)
    async def btn_carta3(self, button, inter): await self.cog._jogar(inter, self.canal_id, 2)

    @disnake.ui.button(label="🗣️ Truco!", style=disnake.ButtonStyle.danger, row=2)
    async def btn_truco(self, button, inter): await self.cog._pedir_truco(inter, self.canal_id)

    @disnake.ui.button(label="🏳️ Correr", style=disnake.ButtonStyle.danger, row=2)
    async def btn_correr(self, button, inter): await self.cog._correr(inter, self.canal_id)

    async def on_timeout(self):
        p = partidas_ativas.pop(self.canal_id, None)
        if p:
            try:
                canal = self.cog.bot.get_channel(self.canal_id)
                if canal:
                    await canal.send("⏳ Partida encerrada por inatividade.")
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW: RESPOSTA AO TRUCO
# ══════════════════════════════════════════════════════════════════════════════

class ViewRespostaTruco(disnake.ui.View):
    def __init__(self, canal_id: int, cog, proximo_valor: int):
        super().__init__(timeout=60)
        self.canal_id      = canal_id
        self.cog           = cog
        self.proximo_valor = proximo_valor
        # Atualiza label do botão de aumento
        if proximo_valor <= 12:
            self.btn_aumentar.label = f"⬆️ Aumentar pra {proximo_valor}"

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        p = partidas_ativas.get(self.canal_id)
        if not p:
            return False
        idx = p.jogadores.index(inter.author) if inter.author in p.jogadores else -1
        if idx < 0:
            await inter.response.send_message("❌ Você não está nesta partida.", ephemeral=True)
            return False
        # Só adversário de quem pediu pode responder
        if p.time_de(idx) == p.time_de(p.truco_pediu_idx):
            await inter.response.send_message("❌ Seu parceiro pediu truco — só o adversário pode responder.", ephemeral=True)
            return False
        return True

    @disnake.ui.button(label="✅ Aceitar", style=disnake.ButtonStyle.success)
    async def btn_aceitar(self, button, inter):
        await self.cog._responder_truco(inter, self.canal_id, "aceitar")
        self.stop()

    @disnake.ui.button(label="❌ Recusar (correr)", style=disnake.ButtonStyle.danger)
    async def btn_recusar(self, button, inter):
        await self.cog._responder_truco(inter, self.canal_id, "recusar")
        self.stop()

    @disnake.ui.button(label="⬆️ Aumentar", style=disnake.ButtonStyle.primary)
    async def btn_aumentar(self, button, inter):
        await self.cog._responder_truco(inter, self.canal_id, "aumentar")
        self.stop()

    async def on_timeout(self):
        p = partidas_ativas.get(self.canal_id)
        if p and p.aguardando_resposta:
            # Timeout na resposta = recusou
            canal = self.cog.bot.get_channel(self.canal_id)
            if canal:
                time_pediu = p.time_de(p.truco_pediu_idx)
                p.aguardando_resposta = False
                p.pontuar_mao(time_pediu)
                await canal.send("⏳ Tempo esgotado — adversário correu do truco!")


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW: MÃO DE 11
# ══════════════════════════════════════════════════════════════════════════════

class ViewMaoDe11(disnake.ui.View):
    def __init__(self, canal_id: int, cog, idx_perguntado: int):
        super().__init__(timeout=60)
        self.canal_id      = canal_id
        self.cog           = cog
        self.idx_perguntado = idx_perguntado

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        p   = partidas_ativas.get(self.canal_id)
        idx = p.jogadores.index(inter.author) if inter.author in p.jogadores else -1
        if idx != self.idx_perguntado:
            await inter.response.send_message("❌ Não é sua decisão.", ephemeral=True)
            return False
        return True

    @disnake.ui.button(label="✅ Aceitar mão de 11", style=disnake.ButtonStyle.success)
    async def btn_aceitar(self, button, inter):
        await self.cog._responder_mao11(inter, self.canal_id, True)
        self.stop()

    @disnake.ui.button(label="❌ Recusar (1 ponto pro adversário)", style=disnake.ButtonStyle.danger)
    async def btn_recusar(self, button, inter):
        await self.cog._responder_mao11(inter, self.canal_id, False)
        self.stop()


# ══════════════════════════════════════════════════════════════════════════════
#  COG PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

class Truco(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── !truco ────────────────────────────────────────────────────────────────

    @commands.command(aliases=["t"])
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def truco(self, ctx, modo: str = "1v1", aposta: float = 100.0):
        """
        Abre um lobby de Truco Paulista.
        Uso: !truco 1v1 500   →  1v1 com aposta de 500 MC
             !truco 2v2 1000  →  2v2 com aposta de 1000 MC por jogador
        """
        modo = modo.lower()
        if modo not in ("1v1", "2v2"):
            return await ctx.send(
                f"❌ Modo inválido! Use `!truco 1v1 <aposta>` ou `!truco 2v2 <aposta>`.",
                delete_after=8
            )
        if aposta < 50:
            return await ctx.send("❌ Aposta mínima: **50 MC**.", delete_after=6)

        canal_id = ctx.channel.id

        if canal_id in partidas_ativas:
            return await ctx.send("⚠️ Já há uma partida em andamento neste canal!", delete_after=6)
        if canal_id in lobbies_pendentes:
            return await ctx.send("⚠️ Já há um lobby aberto aqui! Aguarde ou cancele.", delete_after=6)

        # Verifica saldo do criador
        user = db.get_user_data(str(ctx.author.id))
        if not user:
            return await ctx.send("❌ Use `!trabalhar` primeiro para se registrar!")
        if db.parse_float(user["data"][2]) < aposta:
            return await ctx.send(f"❌ Saldo insuficiente! A aposta é **{formatar_moeda(aposta)} MC**.")

        max_j = 2 if modo == "1v1" else 4
        lobby = {
            "dono":      ctx.author,
            "modo":      modo,
            "aposta":    aposta,
            "jogadores": [ctx.author],
            "message":   None,
        }
        lobbies_pendentes[canal_id] = lobby

        embed = disnake.Embed(
            title       = "🃏 TRUCO — AGUARDANDO JOGADORES",
            description = (
                f"**Modo:** `{modo.upper()}`\n"
                f"**Aposta:** `{formatar_moeda(aposta)} MC` por jogador\n\n"
                f"**Jogadores (1/{max_j}):**\n• {ctx.author.mention}\n\n"
                f"⏳ Aguardando mais {max_j - 1} jogador(es)..."
            ),
            color = 0xFFD700,
        )
        view = ViewLobby(canal_id, self)
        msg  = await ctx.send(embed=embed, view=view)
        view.message = msg
        lobby["message"] = msg

    # ── Iniciar partida ───────────────────────────────────────────────────────

    async def _iniciar_partida(self, inter, canal_id: int):
        lobby = lobbies_pendentes.pop(canal_id, None)
        if not lobby:
            return

        jogadores = lobby["jogadores"]
        aposta    = lobby["aposta"]
        modo      = lobby["modo"]

        # Verifica saldo de todos
        for j in jogadores:
            u = db.get_user_data(str(j.id))
            if not u or db.parse_float(u["data"][2]) < aposta:
                canal = self.bot.get_channel(canal_id)
                if canal:
                    await canal.send(f"❌ {j.mention} não tem saldo suficiente! Partida cancelada.")
                return

        # Embaralha ordem (no 2v2 times ficam intercalados: 0,1,2,3 = t0,t1,t0,t1)
        random.shuffle(jogadores)

        p = Partida(jogadores, aposta, canal_id, modo)
        partidas_ativas[canal_id] = p

        # Edita mensagem do lobby
        embed = embed_partida(p, "🃏 TRUCO PAULISTA — PARTIDA INICIADA!")
        view  = ViewTruco(canal_id, self)
        try:
            await lobby["message"].edit(embed=embed, view=view)
        except Exception:
            canal = self.bot.get_channel(canal_id)
            if canal:
                await canal.send(embed=embed, view=view)

        # Envia cartas por ephemeral para cada jogador (via DM simulada ou embed)
        await self._enviar_cartas_todos(canal_id, inter)

        # Se mão de 11, pergunta quem tem 11
        if p.mao_de_11:
            await self._processar_mao11(canal_id)

    async def _enviar_cartas_todos(self, canal_id: int, inter=None):
        """Avisa todos os jogadores para clicarem em 'Ver minhas cartas'."""
        p     = partidas_ativas.get(canal_id)
        canal = self.bot.get_channel(canal_id)
        if not p or not canal:
            return
        mencoes = " ".join(j.mention for j in p.jogadores)
        await canal.send(
            f"🃏 {mencoes} — cliquem em **🃏 Ver minhas cartas** para ver sua mão!\n"
            f"🎮 Vez de **{p.jogador_atual().display_name}** jogar.",
            delete_after=30
        )

    # ── Jogar carta ───────────────────────────────────────────────────────────

    async def _jogar(self, inter: disnake.MessageInteraction, canal_id: int, carta_idx: int):
        p = partidas_ativas.get(canal_id)
        if not p:
            return await inter.response.send_message("❌ Partida não encontrada.", ephemeral=True)

        idx = p.jogadores.index(inter.author)

        if p.aguardando_resposta:
            return await inter.response.send_message("⏳ Aguardando resposta ao truco!", ephemeral=True)

        if idx != p.vez_idx:
            return await inter.response.send_message("❌ Não é sua vez!", ephemeral=True)

        if idx in p.ja_jogou:
            return await inter.response.send_message("⚠️ Você já jogou nesta rodada!", ephemeral=True)

        if carta_idx >= len(p.maos.get(idx, [])):
            return await inter.response.send_message("❌ Carta inválida!", ephemeral=True)

        carta_jogada = p.maos[idx][carta_idx]
        rodada_fechou = p.jogar_carta(idx, carta_idx)

        msg = f"{inter.author.display_name} jogou {label_carta(*carta_jogada)}."

        if not rodada_fechou:
            embed = embed_partida(p, msg=msg)
            view  = ViewTruco(canal_id, self)
            await inter.response.edit_message(embed=embed, view=view)
            return

        # Rodada fechada — resolve
        resultado, _ = p.resolver_rodada()
        if resultado == "empate":
            msg_res = "🤝 Empate na rodada!"
        else:
            nome_time = (p.jogadores[0] if p.modo == "1v1" else
                         f"Time {resultado + 1}").display_name if p.modo == "1v1" else f"Time {resultado + 1}"
            if p.modo == "1v1":
                nome_time = p.jogadores[resultado].display_name
            msg_res = f"✅ Rodada {p.rodada} para **{nome_time}**!"

        p.rodada += 1

        fim_mao = p.verificar_fim_mao()
        if fim_mao is not None:
            fim_partida = p.pontuar_mao(fim_mao)
            if fim_partida:
                await self._encerrar_partida(inter, canal_id, fim_mao, msg_res)
                return
            else:
                msg_res += f" | 🃏 Nova mão! Placar: `{p.pontos[0]}` × `{p.pontos[1]}`"
                embed = embed_partida(p, msg=msg_res)
                view  = ViewTruco(canal_id, self)
                await inter.response.edit_message(embed=embed, view=view)
                await self._enviar_cartas_todos(canal_id)
                if p.mao_de_11:
                    await self._processar_mao11(canal_id)
                return

        # Continua a mão, próxima rodada
        p.cartas_mesa = {}
        p.ja_jogou    = set()
        # Quem ganhou a rodada começa a próxima
        if resultado != "empate":
            # Encontra o primeiro jogador do time vencedor
            for i, j in enumerate(p.jogadores):
                if p.time_de(i) == resultado:
                    p.vez_idx = i
                    break

        embed = embed_partida(p, msg=msg_res)
        view  = ViewTruco(canal_id, self)
        await inter.response.edit_message(embed=embed, view=view)

    # ── Truco ─────────────────────────────────────────────────────────────────

    async def _pedir_truco(self, inter: disnake.MessageInteraction, canal_id: int):
        p = partidas_ativas.get(canal_id)
        if not p:
            return await inter.response.send_message("❌ Partida não encontrada.", ephemeral=True)

        idx = p.jogadores.index(inter.author)

        if not p.pode_pedir_truco(idx):
            if p.truco_valor == 12:
                return await inter.response.send_message("❌ Já está no máximo (12)!", ephemeral=True)
            return await inter.response.send_message("❌ Não é possível pedir truco agora.", ephemeral=True)

        proximo = p.proximo_valor_truco()
        nomes   = {3: "Truco!", 6: "Seis!", 9: "Nove!", 12: "Doze!"}
        grito   = nomes.get(proximo, f"{proximo}!")

        p.truco_pediu_idx     = idx
        p.aguardando_resposta = True

        # Adversários que precisam responder
        adv_mencoes = " ".join(p.jogadores[i].mention for i in p.adversarios(idx))

        embed = embed_partida(
            p,
            titulo = f"🗣️ {inter.author.display_name} gritou {grito}",
            msg    = f"{adv_mencoes}, aceitar, recusar ou aumentar?"
        )
        view_resp = ViewRespostaTruco(canal_id, self, p.proximo_valor_truco())
        await inter.response.edit_message(embed=embed, view=view_resp)

    async def _responder_truco(self, inter: disnake.MessageInteraction, canal_id: int, resposta: str):
        p = partidas_ativas.get(canal_id)
        if not p:
            return await inter.response.send_message("❌ Partida não encontrada.", ephemeral=True)

        idx = p.jogadores.index(inter.author)

        if resposta == "aceitar":
            p.aceitar_truco()
            msg = f"✅ {inter.author.display_name} aceitou! Vale **{p.truco_valor} pontos**."
            embed = embed_partida(p, msg=msg)
            view  = ViewTruco(canal_id, self)
            await inter.response.edit_message(embed=embed, view=view)

        elif resposta == "recusar":
            time_pediu = p.recusar_truco()
            pts_ganhos = p.truco_valor if p.truco_ativo else 1
            p.pontos[time_pediu] += pts_ganhos
            msg = f"🏳️ {inter.author.display_name} correu! +{pts_ganhos} ponto(s) para o adversário."

            if p.pontos[time_pediu] >= 12:
                await self._encerrar_partida(inter, canal_id, time_pediu, msg)
                return

            # Nova mão
            p.primeiro_da_mao = (p.primeiro_da_mao + 1) % p.n
            p.vez_idx         = p.primeiro_da_mao
            p._distribuir()
            embed = embed_partida(p, msg=msg)
            view  = ViewTruco(canal_id, self)
            await inter.response.edit_message(embed=embed, view=view)
            await self._enviar_cartas_todos(canal_id)

        elif resposta == "aumentar":
            p.aumentar_truco(idx)
            proximo = p.proximo_valor_truco()
            nomes   = {3: "Truco!", 6: "Seis!", 9: "Nove!", 12: "Doze!"}
            grito   = nomes.get(p.truco_valor, f"{p.truco_valor}!")
            adv_mencoes = " ".join(p.jogadores[i].mention for i in p.adversarios(idx))
            msg = f"⬆️ {inter.author.display_name} aumentou pra **{grito}** {adv_mencoes}, e agora?"
            embed = embed_partida(p, titulo=f"🗣️ {grito}", msg=msg)
            view  = ViewRespostaTruco(canal_id, self, proximo)
            await inter.response.edit_message(embed=embed, view=view)

    # ── Correr ────────────────────────────────────────────────────────────────

    async def _correr(self, inter: disnake.MessageInteraction, canal_id: int):
        p = partidas_ativas.get(canal_id)
        if not p:
            return await inter.response.send_message("❌ Partida não encontrada.", ephemeral=True)

        idx      = p.jogadores.index(inter.author)
        time_adv = 1 - p.time_de(idx)
        pts = p.truco_valor if p.truco_ativo else 1
        p.pontos[time_adv] += pts
        msg = f"🏳️ {inter.author.display_name} desistiu da mão! +{pts} ponto(s) para o adversário."

        if p.pontos[time_adv] >= 12:
            await self._encerrar_partida(inter, canal_id, time_adv, msg)
            return

        p.primeiro_da_mao = (p.primeiro_da_mao + 1) % p.n
        p.vez_idx         = p.primeiro_da_mao
        p._distribuir()
        embed = embed_partida(p, msg=msg)
        view  = ViewTruco(canal_id, self)
        await inter.response.edit_message(embed=embed, view=view)
        await self._enviar_cartas_todos(canal_id)

    # ── Mão de 11 ─────────────────────────────────────────────────────────────

    async def _processar_mao11(self, canal_id: int):
        p     = partidas_ativas.get(canal_id)
        canal = self.bot.get_channel(canal_id)
        if not p or not canal:
            return

        # Quem tem 11 pontos decide (no 2v2, qualquer membro do time)
        for i, pts in enumerate(p.pontos):
            if pts == 11:
                time_com_11 = i
                break
        else:
            return

        # Encontra primeiro jogador desse time
        for idx, j in enumerate(p.jogadores):
            if p.time_de(idx) == time_com_11:
                perguntado_idx = idx
                break

        j_perguntado = p.jogadores[perguntado_idx]
        embed = disnake.Embed(
            title       = "🃏 MÃO DE 11",
            description = (
                f"{j_perguntado.mention}, você está com **11 pontos**!\n\n"
                f"Na mão de 11 **não há truco** — a mão vale **3 pontos**.\n"
                f"Você pode ver suas cartas antes de decidir.\n\n"
                f"❓ **Aceitar ou recusar a mão?**"
            ),
            color = 0xFF8C00,
        )
        view = ViewMaoDe11(canal_id, self, perguntado_idx)
        view.message = await canal.send(embed=embed, view=view)

    async def _responder_mao11(self, inter: disnake.MessageInteraction, canal_id: int, aceitar: bool):
        p = partidas_ativas.get(canal_id)
        if not p:
            return

        p.mao_de_11_aceita = aceitar
        if aceitar:
            msg = f"✅ {inter.author.display_name} aceitou a mão de 11! Vale **3 pontos**."
        else:
            # Recusou — adversário ganha 1 ponto
            idx      = p.jogadores.index(inter.author)
            time_adv = 1 - p.time_de(idx)
            p.pontos[time_adv] += 1
            msg = f"🏳️ {inter.author.display_name} recusou a mão de 11. +1 ponto para o adversário."
            p.mao_de_11 = False

            if p.pontos[time_adv] >= 12:
                await self._encerrar_partida(inter, canal_id, time_adv, msg)
                return

            p._distribuir()

        embed = embed_partida(p, msg=msg)
        view  = ViewTruco(canal_id, self)
        await inter.response.edit_message(embed=embed, view=view)
        if aceitar:
            await self._enviar_cartas_todos(canal_id)

    # ── Encerrar partida ──────────────────────────────────────────────────────

    async def _encerrar_partida(self, inter, canal_id: int, time_vencedor: int, msg_final: str = ""):
        p = partidas_ativas.pop(canal_id, None)
        if not p:
            return

        p.encerrada     = True
        p.vencedor_time = time_vencedor

        # Vencedores e perdedores
        vencedores = [j for i, j in enumerate(p.jogadores) if p.time_de(i) == time_vencedor]
        perdedores = [j for i, j in enumerate(p.jogadores) if p.time_de(i) != time_vencedor]

        total_aposta  = p.aposta * len(p.jogadores)
        ganho_por_venc = p.aposta * len(perdedores) / len(vencedores)

        # Atualiza Sheets
        erros = []
        for j in perdedores:
            u = db.get_user_data(str(j.id))
            if u:
                saldo = db.parse_float(u["data"][2])
                db.update_value(u["row"], 3, round(saldo - p.aposta, 2))
            else:
                erros.append(j.mention)

        for j in vencedores:
            u = db.get_user_data(str(j.id))
            if u:
                saldo = db.parse_float(u["data"][2])
                db.update_value(u["row"], 3, round(saldo + ganho_por_venc, 2))
            else:
                erros.append(j.mention)

        nomes_venc = " & ".join(j.display_name for j in vencedores)
        nomes_perd = " & ".join(j.display_name for j in perdedores)
        mencoes    = " ".join(j.mention for j in p.jogadores)

        desc = (
            f"### 🏆 {nomes_venc} venceu!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Placar final:** `{p.pontos[0]}` × `{p.pontos[1]}`\n\n"
            f"✅ **Vencedores:** {', '.join(j.mention for j in vencedores)}\n"
            f"   +`{formatar_moeda(ganho_por_venc)} MC` cada\n\n"
            f"❌ **Perdedores:** {', '.join(j.mention for j in perdedores)}\n"
            f"   -`{formatar_moeda(p.aposta)} MC` cada\n"
        )
        if msg_final:
            desc += f"\n💬 {msg_final}"
        if erros:
            desc += f"\n⚠️ Erro ao atualizar conta de: {', '.join(erros)}"

        embed = disnake.Embed(
            title       = "🏁 PARTIDA ENCERRADA",
            description = desc,
            color       = 0xFFD700,
        )
        try:
            await inter.response.edit_message(embed=embed, view=None)
        except Exception:
            canal = self.bot.get_channel(canal_id)
            if canal:
                await canal.send(embed=embed)

    # ── !truco_cancelar ───────────────────────────────────────────────────────

    @commands.command(aliases=["cancelar_truco", "sair_truco"])
    @commands.has_permissions(administrator=True)
    async def truco_cancelar(self, ctx):
        """[Admin] Cancela a partida de truco no canal atual."""
        canal_id = ctx.channel.id
        partidas_ativas.pop(canal_id, None)
        lobbies_pendentes.pop(canal_id, None)
        await ctx.send("🛑 Partida/lobby cancelado pelo administrador.")

    @truco.error
    async def truco_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Aguarde {error.retry_after:.1f}s.", delete_after=5)
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Uso: `!truco 1v1 <aposta>` ou `!truco 2v2 <aposta>`", delete_after=8)


def setup(bot):
    bot.add_cog(Truco(bot))