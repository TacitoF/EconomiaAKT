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

NUM_BARALHOS = 6
LIMITE_CORTE = 0.25

# ──────────────────────────────────────────────
#  ODDS DAS APOSTAS LATERAIS
# ──────────────────────────────────────────────
# 21+3 (suas 2 cartas + carta aberta do dealer)
ODDS_21_3 = {
    "flush":            5,   # mesma naipe, sem sequência
    "sequencia":        10,  # sequência, naipes diferentes
    "trio":             30,  # mesmo valor, naipes diferentes
    "sequencia_color":  40,  # sequência do mesmo naipe
    "trio_perfeito":    100, # mesmo valor e mesmo naipe (3 cartas iguais)
}

# Perfect Pairs (suas 2 cartas iniciais)
ODDS_PERFECT_PAIRS = {
    "par_misto":     6,   # mesmo valor, cores diferentes
    "par_colorido": 12,   # mesmo valor, mesma cor, naipes diferentes
    "par_perfeito": 25,   # mesmo valor e mesmo naipe
}


# ──────────────────────────────────────────────
#  SAPATO
# ──────────────────────────────────────────────
class Sapato:
    def __init__(self):
        self.cartas: list = []
        self.total_inicial: int = 0
        self.embaralhar()

    def embaralhar(self):
        naipes = ["♠️", "♥️", "♦️", "♣️"]
        valores = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        self.cartas = [{"valor": v, "naipe": n} for v in valores for n in naipes] * NUM_BARALHOS
        random.shuffle(self.cartas)
        self.total_inicial = len(self.cartas)

    def puxar(self) -> dict:
        if len(self.cartas) / self.total_inicial < LIMITE_CORTE:
            self.embaralhar()
        return self.cartas.pop()

    @property
    def precisa_embaralhar(self) -> bool:
        return len(self.cartas) / self.total_inicial < LIMITE_CORTE

    @property
    def cartas_restantes(self) -> int:
        return len(self.cartas)


def get_limite(cargo):
    return LIMITES_CARGO.get(cargo, 250)


# ──────────────────────────────────────────────
#  LÓGICA DAS APOSTAS LATERAIS
# ──────────────────────────────────────────────
NAIPE_COR = {
    "♠️": "preta", "♣️": "preta",
    "♥️": "vermelha", "♦️": "vermelha",
}

ORDEM_CARTA = {"A": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
               "7": 7, "8": 8, "9": 9, "10": 10, "J": 11, "Q": 12, "K": 13}


def avaliar_21_3(c1: dict, c2: dict, cd: dict) -> tuple[str | None, int]:
    cartas = [c1, c2, cd]
    valores = [c["valor"] for c in cartas]
    naipes  = [c["naipe"] for c in cartas]
    ordens  = sorted([ORDEM_CARTA[v] for v in valores])

    mesmo_naipe  = len(set(naipes)) == 1
    mesmo_valor  = len(set(valores)) == 1
    sequencia    = (ordens[2] - ordens[0] == 2 and len(set(ordens)) == 3)
    if set(valores) == {"A", "Q", "K"}:
        sequencia = True
    if set(valores) == {"A", "2", "3"}:
        sequencia = True

    if mesmo_valor and mesmo_naipe:
        return "trio_perfeito",    ODDS_21_3["trio_perfeito"]
    if mesmo_valor:
        return "trio",             ODDS_21_3["trio"]
    if sequencia and mesmo_naipe:
        return "sequencia_color",  ODDS_21_3["sequencia_color"]
    if sequencia:
        return "sequencia",        ODDS_21_3["sequencia"]
    if mesmo_naipe:
        return "flush",            ODDS_21_3["flush"]
    return None, 0


def avaliar_perfect_pairs(c1: dict, c2: dict) -> tuple[str | None, int]:
    if c1["valor"] != c2["valor"]:
        return None, 0

    if c1["naipe"] == c2["naipe"]:
        return "par_perfeito",   ODDS_PERFECT_PAIRS["par_perfeito"]

    cor1 = NAIPE_COR[c1["naipe"]]
    cor2 = NAIPE_COR[c2["naipe"]]
    if cor1 == cor2:
        return "par_colorido",  ODDS_PERFECT_PAIRS["par_colorido"]

    return "par_misto",         ODDS_PERFECT_PAIRS["par_misto"]


NOME_PT = {
    "flush":           "Flush (mesmo naipe)",
    "sequencia":       "Sequência",
    "trio":            "Trio",
    "sequencia_color": "Sequência Colorida",
    "trio_perfeito":   "Trio Perfeito",
    "par_misto":       "Par Misto",
    "par_colorido":    "Par Colorido",
    "par_perfeito":    "Par Perfeito",
}


# ──────────────────────────────────────────────
#  MODAL — valor de um side bet específico
# ──────────────────────────────────────────────
class ModalValorSideBet(disnake.ui.Modal):
    def __init__(self, tipo: str, aposta_principal: float, lobby: "LobbyView",
                 p_id: int, view_inter: disnake.MessageInteraction):
        self.tipo             = tipo
        self.aposta_principal = aposta_principal
        self.lobby            = lobby
        self.p_id             = p_id
        self.view_inter       = view_inter

        nome   = "21+3" if tipo == "21_3" else "Perfect Pairs"
        maximo = round(aposta_principal * 0.50, 2)

        sb_atual   = lobby.side_bets.get(p_id, {}).get(tipo)
        dica_atual = f"Aposta atual: {sb_atual:.2f} MC — envie 0 para cancelar" if sb_atual else f"Entre 0.01 e {maximo:.2f} MC"

        components = [
            disnake.ui.TextInput(
                label       = f"Valor — máximo {maximo:.2f} MC (50% da aposta)",
                placeholder = dica_atual,
                custom_id   = "valor",
                style       = disnake.TextInputStyle.short,
                min_length  = 1,
                max_length  = 12,
            ),
        ]
        super().__init__(title=f"🎰 Aposta Lateral: {nome}", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)

        tipo   = self.tipo
        nome   = "21+3" if tipo == "21_3" else "Perfect Pairs"
        maximo = round(self.aposta_principal * 0.50, 2)

        val_raw = inter.text_values.get("valor", "").strip().replace(",", ".")
        try:
            valor = round(float(val_raw), 2)
        except ValueError:
            return await inter.edit_original_response(content="❌ Valor inválido! Digite apenas números.")

        sb_anterior = self.lobby.side_bets.get(self.p_id, {}).get(tipo)

        if valor == 0:
            if sb_anterior:
                u_db = db.get_user_data(str(self.p_id))
                if u_db:
                    saldo_atual = db.parse_float(u_db['data'][2])
                    db.update_value(u_db['row'], 3, round(saldo_atual + sb_anterior, 2))
                self.lobby.side_bets.setdefault(self.p_id, {})[tipo] = None
                resultado = f"🗑️ **{nome}** cancelado — **{sb_anterior:.2f} MC** devolvidos."
            else:
                resultado = f"ℹ️ Você não tinha aposta no **{nome}**."

            await self._colapsar_view(resultado)
            await inter.delete_original_response()
            await self._atualizar_lobby()
            return

        if valor < 0.01 or valor > maximo:
            return await inter.edit_original_response(
                content=f"❌ Valor deve ser entre **0.01** e **{maximo:.2f} MC** (ou **0** para cancelar)."
            )

        u_db = db.get_user_data(str(self.p_id))
        if not u_db:
            return await inter.edit_original_response(content="❌ Conta não encontrada!")

        saldo_real = db.parse_float(u_db['data'][2])
        if sb_anterior:
            saldo_real = round(saldo_real + sb_anterior, 2)

        if saldo_real < valor:
            return await inter.edit_original_response(
                content=f"❌ Saldo insuficiente! Você tem **{saldo_real:.2f} MC** disponíveis."
            )

        db.update_value(u_db['row'], 3, round(saldo_real - valor, 2))
        self.lobby.side_bets.setdefault(self.p_id, {})[tipo] = valor

        acao      = "atualizada" if sb_anterior else "registrada"
        resultado = f"✅ **{nome}** {acao}: **{valor:.2f} MC**"

        await self._colapsar_view(resultado)
        await inter.delete_original_response()
        await self._atualizar_lobby()

    async def _colapsar_view(self, texto: str):
        try:
            await self.view_inter.edit_original_response(content=texto, view=None)
        except:
            pass

    async def _atualizar_lobby(self):
        try:
            if self.lobby.msg:
                await self.lobby.msg.edit(content=self.lobby._lobby_text())
        except:
            pass


# ──────────────────────────────────────────────
#  VIEW — escolha do tipo de side bet (ephemeral)
# ──────────────────────────────────────────────
class ViewEscolhaSideBet(disnake.ui.View):
    def __init__(self, aposta_principal: float, lobby: "LobbyView", p_id: int):
        super().__init__(timeout=60)
        self.aposta_principal = aposta_principal
        self.lobby            = lobby
        self.p_id             = p_id

    def _content(self) -> str:
        maximo  = round(self.aposta_principal * 0.50, 2)
        sb      = self.lobby.side_bets.get(self.p_id, {})
        val_21  = sb.get("21_3")
        val_pp  = sb.get("pp")

        status_21 = f"✅ {val_21:.2f} MC apostados" if val_21 else "Sem aposta"
        status_pp = f"✅ {val_pp:.2f} MC apostados" if val_pp else "Sem aposta"

        return (
            f"🎰 **Apostas Laterais** — máximo **{maximo:.2f} MC** por tipo (50% da aposta)\n\n"
            f"**🃏 21+3** — suas 2 cartas + carta aberta do dealer\n"
            f"Flush **5x** · Sequência **10x** · Trio **30x** · Seq. Colorida **40x** · Trio Perfeito **100x**\n"
            f"*{status_21}*\n\n"
            f"**💎 Perfect Pairs** — suas 2 primeiras cartas formam um par\n"
            f"Par Misto **6x** · Par Colorido **12x** · Par Perfeito **25x**\n"
            f"*{status_pp}*\n\n"
            f"Clique no tipo desejado para apostar. Envie **0** no valor para cancelar uma aposta."
        )

    @disnake.ui.button(label="🃏 21+3", style=disnake.ButtonStyle.blurple, row=0)
    async def btn_21_3(self, button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(
            ModalValorSideBet(
                tipo             = "21_3",
                aposta_principal = self.aposta_principal,
                lobby            = self.lobby,
                p_id             = self.p_id,
                view_inter       = inter,
            )
        )

    @disnake.ui.button(label="💎 Perfect Pairs", style=disnake.ButtonStyle.blurple, row=0)
    async def btn_pp(self, button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(
            ModalValorSideBet(
                tipo             = "pp",
                aposta_principal = self.aposta_principal,
                lobby            = self.lobby,
                p_id             = self.p_id,
                view_inter       = inter,
            )
        )


# ──────────────────────────────────────────────
#  LOBBY
# ──────────────────────────────────────────────
class LobbyView(disnake.ui.View):
    def __init__(self, ctx, bot, aposta: float, players: list, sapato: Sapato):
        super().__init__(timeout=60)
        self.ctx       = ctx
        self.bot       = bot
        self.aposta    = aposta
        self.players   = players  # lista de Members já dentro da mesa
        self.sapato    = sapato
        self.started   = False
        self.cancelled = False
        self.msg       = None
        self.side_bets: dict = {}

    MAX_JOGADORES = 6

    @disnake.ui.button(label="🃏 Entrar", style=disnake.ButtonStyle.success, row=0)
    async def entrar(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author in self.players:
            return await inter.response.send_message("🐒 Você já está na mesa!", ephemeral=True)
        if len(self.players) >= self.MAX_JOGADORES:
            return await inter.response.send_message(
                f"🚫 A mesa está cheia! Máximo de **{self.MAX_JOGADORES} jogadores**.", ephemeral=True
            )
        u_db = db.get_user_data(str(inter.author.id))
        if not u_db:
            return await inter.response.send_message("❌ Conta não encontrada!", ephemeral=True)
        cargo_p = u_db['data'][3] if len(u_db['data']) > 3 else "Lêmure"
        if self.aposta > get_limite(cargo_p):
            return await inter.response.send_message(
                f"🚫 Aposta excede seu limite de **{cargo_p}**.", ephemeral=True
            )
        if db.parse_float(u_db['data'][2]) < self.aposta:
            return await inter.response.send_message("❌ Saldo insuficiente!", ephemeral=True)

        db.update_value(u_db['row'], 3, round(db.parse_float(u_db['data'][2]) - self.aposta, 2))
        self.players.append(inter.author)
        self.side_bets[inter.author.id] = {"21_3": None, "pp": None}
        await inter.response.edit_message(content=self._lobby_text())

    @disnake.ui.button(label="🎰 Aposta Lateral", style=disnake.ButtonStyle.blurple, row=0)
    async def aposta_lateral(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author not in self.players:
            return await inter.response.send_message(
                "❌ Entre na mesa primeiro clicando em **🃏 Entrar**!", ephemeral=True
            )
        view_escolha = ViewEscolhaSideBet(
            aposta_principal = self.aposta,
            lobby            = self,
            p_id             = inter.author.id,
        )
        await inter.response.send_message(
            content   = view_escolha._content(),
            view      = view_escolha,
            ephemeral = True,
        )

    @disnake.ui.button(label="▶️ Começar", style=disnake.ButtonStyle.primary, row=0)
    async def comecar(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id != self.ctx.author.id:
            return await inter.response.send_message("❌ Só o dono da mesa pode iniciar!", ephemeral=True)
        self.started = True
        for item in self.children:
            item.disabled = True
        await inter.response.edit_message(content="✅ Mesa iniciada!", view=self)
        self.stop()

    def _lobby_text(self) -> str:
        nomes = ", ".join([p.display_name for p in self.players])

        sb_linhas = []
        for p in self.players:
            sb = self.side_bets.get(p.id, {})
            partes = []
            if sb.get("21_3"):
                partes.append(f"21+3: {sb['21_3']:.2f} MC")
            if sb.get("pp"):
                partes.append(f"PP: {sb['pp']:.2f} MC")
            if partes:
                sb_linhas.append(f"  • {p.display_name}: {' | '.join(partes)}")

        sb_texto = ""
        if sb_linhas:
            sb_texto = "\n🎰 **Apostas Laterais:**\n" + "\n".join(sb_linhas)

        return (
            f"🃏 **BLACKJACK!** Dono: {self.ctx.author.mention} | Aposta: `{self.aposta:.2f} MC`\n"
            f"👥 **Jogadores ({len(self.players)}):** {nomes}"
            f"{sb_texto}\n"
            f"Clique **Entrar** para participar, **🎰 Aposta Lateral** para alterar o valor ou fazer uma nova aposta lateral, ou **Começar** para iniciar!\n"
            f"💡 *Para retirar uma aposta lateral, clique em **🎰 Aposta Lateral**, escolha o tipo e envie o valor **0**.*"
        )

    async def on_timeout(self):
        """
        FIX BUG 1: Devolve aposta principal + side bets de TODOS os jogadores
        que entraram pelo botão (players[1:]), pois o criador (players[0]) é
        reembolsado separadamente no blackjack() ao detectar cancelled=True.
        """
        self.cancelled = True

        # Devolve aposta principal + side bets dos jogadores que entraram pelo botão
        for p in self.players[1:]:  # pula o criador (index 0), tratado no blackjack()
            total_devolver = self.aposta
            sb = self.side_bets.get(p.id, {})
            total_devolver += sum(v for v in sb.values() if v)
            total_devolver = round(total_devolver, 2)
            if total_devolver <= 0:
                continue
            try:
                u_db = db.get_user_data(str(p.id))
                if u_db:
                    saldo = db.parse_float(u_db['data'][2])
                    db.update_value(u_db['row'], 3, round(saldo + total_devolver, 2))
            except Exception as e:
                print(f"❌ Erro ao devolver aposta no timeout do lobby para {p.id}: {e}")

        # Devolve só os side bets do criador (aposta principal dele é tratada no blackjack())
        criador = self.players[0] if self.players else None
        if criador:
            sb_criador = self.side_bets.get(criador.id, {})
            total_sb_criador = round(sum(v for v in sb_criador.values() if v), 2)
            if total_sb_criador > 0:
                try:
                    u_db = db.get_user_data(str(criador.id))
                    if u_db:
                        saldo = db.parse_float(u_db['data'][2])
                        db.update_value(u_db['row'], 3, round(saldo + total_sb_criador, 2))
                except Exception as e:
                    print(f"❌ Erro ao devolver side bet do criador no timeout: {e}")

        self.stop()


# ──────────────────────────────────────────────
#  BLACKJACK VIEW PRINCIPAL
# ──────────────────────────────────────────────
class BlackjackView(disnake.ui.View):
    def __init__(self, ctx, bot, aposta_base, players, sapato: Sapato,
                 side_bets: dict | None = None):
        super().__init__(timeout=120)
        self.ctx         = ctx
        self.bot         = bot
        self.message     = None
        self.aposta_base = round(float(aposta_base), 2)
        self.sapato      = sapato
        self.side_bets   = side_bets or {}

        self.players_data = {
            p.id: {
                "member": p, "hand": [], "hand2": [], "status": "jogando",
                "aposta": round(float(aposta_base), 2), "splitted": False, "current_hand": 1,
                # flag para rastrear se o ás de cada mão já foi da mão inicial
                "hand_ases_iniciais": 0,
                "hand2_ases_iniciais": 0,
                "sb_21_3_resultado": None,
                "sb_pp_resultado":   None,
            }
            for p in players
        }
        self.dealer_hand          = []
        self.player_ids           = [p.id for p in players]
        self.current_player_idx   = 0
        self.terminado            = False
        self.dealer_jogando       = False
        self._insurance_resolvido = False

    def _puxar_carta(self) -> dict:
        return self.sapato.puxar()

    def _calcular_pontos(self, hand, ases_iniciais: int = None):
        """
        FIX BUG 5: Em vez de usar a posição da carta no array (i < 2) para decidir
        se um Ás vale 11, usamos o parâmetro ases_iniciais que rastreia quantos Ases
        vieram nas duas primeiras cartas da mão. Isso garante comportamento correto
        após Split, onde hand2 começa com índice 0 mas pode ter sido formada por hit.

        Se ases_iniciais não for fornecido, usa o comportamento legado (posição i<2)
        para compatibilidade com chamadas que não passam o contexto da mão.
        """
        pontos = 0
        ases_flexiveis = 0  # Ases que ainda valem 11 e podem ser rebaixados

        for i, carta in enumerate(hand):
            if carta["valor"] == "A":
                # Decide se este Ás pode valer 11 (flexível)
                if ases_iniciais is not None:
                    # Usa contagem explícita: só Ases das primeiras 2 cartas são flexíveis
                    if ases_flexiveis + (pontos // 11) < ases_iniciais:
                        pontos += 11
                        ases_flexiveis += 1
                    else:
                        pontos += 1
                else:
                    # Comportamento legado: Ás nas posições 0 e 1 valem 11
                    if i < 2:
                        pontos += 11
                        ases_flexiveis += 1
                    else:
                        pontos += 1
            else:
                valores_map = {"J": 10, "Q": 10, "K": 10}
                pontos += valores_map.get(carta["valor"],
                           int(carta["valor"]) if carta["valor"].isdigit() else 0)

        # Rebaixa Ases flexíveis de 11 para 1 se estourar
        while pontos > 21 and ases_flexiveis > 0:
            pontos -= 10
            ases_flexiveis -= 1

        return pontos

    def _get_pontos_mao(self, p_id: int, mao: int = 1) -> int:
        """Calcula pontos de uma mão usando o rastreamento correto de Ases iniciais."""
        p = self.players_data[p_id]
        if mao == 1:
            return self._calcular_pontos(p["hand"], p["hand_ases_iniciais"])
        else:
            return self._calcular_pontos(p["hand2"], p["hand2_ases_iniciais"])

    def _formatar_mao(self, hand, ocultar_primeira=False, dealer_aguardando=False):
        if not hand: return "Espere..."
        if ocultar_primeira: return f"❓, {hand[1]['valor']}{hand[1]['naipe']}"
        mao_formatada = ", ".join([f"{c['valor']}{c['naipe']}" for c in hand])
        if dealer_aguardando and self._calcular_pontos(hand) < 17:
            mao_formatada += ", ❓"
        return mao_formatada

    def _sapato_info(self) -> str:
        restantes = self.sapato.cartas_restantes
        total     = self.sapato.total_inicial
        pct       = restantes / total * 100
        return f"🃏 Sapato: {restantes}/{total} cartas ({pct:.0f}%)"

    def _resolver_side_bets_iniciais(self):
        msgs = []
        carta_dealer_aberta = self.dealer_hand[1]

        for p_id, p in self.players_data.items():
            sb = self.side_bets.get(p_id, {})
            c1, c2 = p["hand"][0], p["hand"][1]

            val_pp = sb.get("pp")
            if val_pp:
                nome_pp, mult_pp = avaliar_perfect_pairs(c1, c2)
                if nome_pp:
                    ganho_pp = round(val_pp * mult_pp, 2)
                    u_db = db.get_user_data(str(p_id))
                    if u_db:
                        db.update_value(u_db['row'], 3, round(db.parse_float(u_db['data'][2]) + ganho_pp, 2))
                    p["sb_pp_resultado"] = f"✅ {NOME_PT[nome_pp]} ({mult_pp}x) → +**{ganho_pp:.2f} MC**"
                    msgs.append(f"💎 **{p['member'].display_name}** — Perfect Pairs: {NOME_PT[nome_pp]} → **+{ganho_pp:.2f} MC**!")
                else:
                    p["sb_pp_resultado"] = f"❌ Sem par (perdeu {val_pp:.2f} MC)"

            val_21 = sb.get("21_3")
            if val_21:
                nome_21, mult_21 = avaliar_21_3(c1, c2, carta_dealer_aberta)
                if nome_21:
                    ganho_21 = round(val_21 * mult_21, 2)
                    u_db = db.get_user_data(str(p_id))
                    if u_db:
                        db.update_value(u_db['row'], 3, round(db.parse_float(u_db['data'][2]) + ganho_21, 2))
                    p["sb_21_3_resultado"] = f"✅ {NOME_PT[nome_21]} ({mult_21}x) → +**{ganho_21:.2f} MC**"
                    msgs.append(f"🃏 **{p['member'].display_name}** — 21+3: {NOME_PT[nome_21]} → **+{ganho_21:.2f} MC**!")
                else:
                    p["sb_21_3_resultado"] = f"❌ Sem combinação (perdeu {val_21:.2f} MC)"

        return msgs

    def _dealer_mostra_as(self) -> bool:
        return len(self.dealer_hand) > 1 and self.dealer_hand[1]["valor"] == "A"

    async def atualizar_embed(self):
        cor = disnake.Color.dark_purple() if not self.terminado else disnake.Color.gold()
        if self.dealer_jogando:
            cor = disnake.Color.blue()

        embed = disnake.Embed(title="🃏 MESA DE BLACKJACK (21)", color=cor)

        d_p = self._calcular_pontos(self.dealer_hand)
        mostrar_dealer = self.dealer_jogando or self.terminado
        mao_dealer_str = self._formatar_mao(self.dealer_hand, not mostrar_dealer, self.dealer_jogando)

        embed.add_field(
            name  = "🏦 Dealer (Bot)",
            value = f"Mão: `{mao_dealer_str}`\nPontos: {d_p if mostrar_dealer else '?'}",
            inline = False
        )

        p_atual_id = self.player_ids[self.current_player_idx] if self.current_player_idx < len(self.player_ids) else None

        if p_atual_id and not self.terminado and not self.dealer_jogando:
            p_atual_data = self.players_data[p_atual_id]
            v1 = self._calcular_pontos([p_atual_data["hand"][0]])
            v2 = self._calcular_pontos([p_atual_data["hand"][1]])
            pode_split  = len(p_atual_data["hand"]) == 2 and v1 == v2 and not p_atual_data["splitted"]
            pode_seguro = (
                self._dealer_mostra_as()
                and len(p_atual_data["hand"]) == 2
                and not p_atual_data["splitted"]
                and not self._insurance_resolvido
            )

            for child in self.children:
                if child.label == "Dividir (Split)": child.disabled = not pode_split
                if child.label == "Dobrar (Double)": child.disabled = p_atual_data["splitted"]
                if child.label == "Seguro (Insurance)":   child.disabled = not pode_seguro

        for p_id in self.player_ids:
            p = self.players_data[p_id]
            em_turno = (not self.terminado and not self.dealer_jogando and p_atual_id == p_id)
            status_emoji = (
                "⏳" if em_turno else
                "💥" if p["status"] == "estourou" else
                "🏳️" if p["status"] == "seguro"   else
                "✋" if p["status"] == "parou"     else "✅"
            )
            p_p = self._get_pontos_mao(p_id, 1)

            if p["splitted"]:
                p2_p  = self._get_pontos_mao(p_id, 2)
                ind1  = "👉 " if em_turno and p["current_hand"] == 1 else ""
                ind2  = "👉 " if em_turno and p["current_hand"] == 2 else ""
                mao_str = f"{ind1}Mão 1: `{self._formatar_mao(p['hand'])}` ({p_p})\n{ind2}Mão 2: `{self._formatar_mao(p['hand2'])}` ({p2_p})"
            else:
                mao_str = f"Mão: `{self._formatar_mao(p['hand'])}`\nPontos: `{p_p}`"

            res_txt = ""
            if self.terminado:
                def resultado_mao(pm, aposta_mao, status, dealer_pts=d_p):
                    if status == "seguro":                     return f"🛡️ Acionou Seguro (devolvido: **{(aposta_mao * 0.5):.2f} MC**)"
                    if pm > 21:                                return "❌ Estourou"
                    if dealer_pts > 21 or pm > dealer_pts:
                        lucro = aposta_mao
                        return f"🏆 Venceu (**{(aposta_mao + lucro):.2f} MC**)"
                    if pm == dealer_pts:                       return f"🤝 Empatou (**{aposta_mao:.2f} MC**)"
                    return "💀 Perdeu"

                if p["splitted"]:
                    p2_p_final = self._get_pontos_mao(p_id, 2)
                    res_txt = (f"\nResultados:\n"
                               f"Mão 1: **{resultado_mao(p_p, p['aposta'], p['status'])}**\n"
                               f"Mão 2: **{resultado_mao(p2_p_final, p['aposta'], p['status'])}**")
                else:
                    res_txt = f"\nResultado: **{resultado_mao(p_p, p['aposta'], p['status'])}**"

                sb_txt = ""
                if p.get("sb_pp_resultado"):
                    sb_txt += f"\n💎 PP: {p['sb_pp_resultado']}"
                if p.get("sb_21_3_resultado"):
                    sb_txt += f"\n🃏 21+3: {p['sb_21_3_resultado']}"
                res_txt += sb_txt
            else:
                sb_txt = ""
                if p.get("sb_pp_resultado"):
                    sb_txt += f"\n💎 PP: {p['sb_pp_resultado']}"
                if p.get("sb_21_3_resultado"):
                    sb_txt += f"\n🃏 21+3: {p['sb_21_3_resultado']}"
                res_txt = sb_txt

            embed.add_field(
                name  = f"{status_emoji} {p['member'].display_name}",
                value = f"{mao_str}\nAposta: `{p['aposta'] * (2 if p['splitted'] else 1):.2f} MC`{res_txt}",
                inline = True
            )

        if self.terminado:
            footer = f"Partida finalizada! Prêmios entregues. • {self._sapato_info()}"
        elif self.dealer_jogando:
            footer = f"Aguarde o Dealer... • {self._sapato_info()}"
        else:
            footer = self._sapato_info()

        embed.set_footer(text=footer)

        try:
            if self.message:
                await self.message.edit(embed=embed, view=None if (self.terminado or self.dealer_jogando) else self)
        except Exception as e:
            print(f"Erro ao atualizar embed do Blackjack: {e}")

    # ── Botões principais ──────────────────────────────────────────────────

    @disnake.ui.button(label="Pedir (Hit)", style=disnake.ButtonStyle.green)
    async def hit(self, button, inter):
        if self.terminado or self.current_player_idx >= len(self.player_ids): return
        if inter.author.id != self.player_ids[self.current_player_idx]:
            return await inter.response.send_message("❌ Não é sua vez!", ephemeral=True)

        await inter.response.defer()
        p = self.players_data[inter.author.id]
        nova_carta = self._puxar_carta()

        if p["splitted"] and p["current_hand"] == 2:
            p["hand2"].append(nova_carta)
            pontos_mao = self._get_pontos_mao(inter.author.id, 2)
        else:
            p["hand"].append(nova_carta)
            pontos_mao = self._get_pontos_mao(inter.author.id, 1)

        if pontos_mao >= 21:
            if p["splitted"] and p["current_hand"] == 1:
                p["current_hand"] = 2
                await self.atualizar_embed()
            else:
                p["status"] = "estourou" if pontos_mao > 21 else "parou"
                await self.atualizar_embed()
                await self._proximo_turno()
        else:
            await self.atualizar_embed()

    @disnake.ui.button(label="Parar (Stand)", style=disnake.ButtonStyle.grey)
    async def stand(self, button, inter):
        if self.terminado or self.current_player_idx >= len(self.player_ids): return
        if inter.author.id != self.player_ids[self.current_player_idx]:
            return await inter.response.send_message("❌ Não é sua vez!", ephemeral=True)

        await inter.response.defer()
        p = self.players_data[inter.author.id]
        if p["splitted"] and p["current_hand"] == 1:
            p["current_hand"] = 2
            await self.atualizar_embed()
        else:
            p["status"] = "parou"
            await self.atualizar_embed()
            await self._proximo_turno()

    @disnake.ui.button(label="Dobrar (Double)", style=disnake.ButtonStyle.blurple)
    async def double(self, button, inter):
        if self.terminado or self.current_player_idx >= len(self.player_ids): return
        p_id = inter.author.id
        if p_id != self.player_ids[self.current_player_idx]:
            return await inter.response.send_message("❌ Não é sua vez!", ephemeral=True)

        await inter.response.defer()
        p = self.players_data[p_id]
        try:
            u_db = db.get_user_data(str(p_id))
            if not u_db or db.parse_float(u_db['data'][2]) < p["aposta"]:
                return await inter.followup.send("❌ Saldo insuficiente para dobrar!", ephemeral=True)
            db.update_value(u_db['row'], 3, round(db.parse_float(u_db['data'][2]) - p["aposta"], 2))
            p["aposta"] *= 2
            p["hand"].append(self._puxar_carta())
            pontos = self._get_pontos_mao(p_id, 1)
            p["status"] = "estourou" if pontos > 21 else "parou"
            await self.atualizar_embed()
            await self._proximo_turno()
        except Exception as e:
            print(f"❌ Erro no Double: {e}")

    @disnake.ui.button(label="Dividir (Split)", style=disnake.ButtonStyle.danger, disabled=True)
    async def split(self, button, inter):
        if self.terminado or self.current_player_idx >= len(self.player_ids): return
        p_id = inter.author.id
        if p_id != self.player_ids[self.current_player_idx]:
            return await inter.response.send_message("❌ Não é sua vez!", ephemeral=True)

        await inter.response.defer()
        p = self.players_data[p_id]
        try:
            u_db = db.get_user_data(str(p_id))
            if not u_db or db.parse_float(u_db['data'][2]) < p["aposta"]:
                return await inter.followup.send("❌ Saldo insuficiente para o Split!", ephemeral=True)
            db.update_value(u_db['row'], 3, round(db.parse_float(u_db['data'][2]) - p["aposta"], 2))
            p["splitted"] = True
            carta_separada = p["hand"].pop()
            p["hand"].append(self._puxar_carta())
            p["hand2"] = [carta_separada, self._puxar_carta()]

            # FIX BUG 5: rastreia os Ases iniciais de cada mão após o split
            p["hand_ases_iniciais"]  = sum(1 for c in p["hand"][:2]  if c["valor"] == "A")
            p["hand2_ases_iniciais"] = sum(1 for c in p["hand2"][:2] if c["valor"] == "A")

            await self.atualizar_embed()
        except Exception as e:
            print(f"❌ Erro no Split: {e}")

    @disnake.ui.button(label="Seguro (Insurance)", style=disnake.ButtonStyle.secondary, disabled=True, row=1)
    async def insurance(self, button, inter):
        if self.terminado or self.current_player_idx >= len(self.player_ids): return
        p_id = inter.author.id
        if p_id != self.player_ids[self.current_player_idx]:
            return await inter.response.send_message("❌ Não é sua vez!", ephemeral=True)

        await inter.response.defer()
        p = self.players_data[p_id]

        valor_recuperado = round(p["aposta"] * 0.5, 2)

        try:
            u_db = db.get_user_data(str(p_id))
            if not u_db:
                return await inter.followup.send("❌ Conta não encontrada!", ephemeral=True)

            saldo = db.parse_float(u_db['data'][2])
            db.update_value(u_db['row'], 3, round(saldo + valor_recuperado, 2))

            p["status"] = "seguro"
            self._insurance_resolvido = True

            await self.atualizar_embed()
            await self._proximo_turno()

        except Exception as e:
            print(f"❌ Erro no Seguro: {e}")

    async def on_timeout(self):
        if self.terminado:
            return
        self.terminado = True
        for item in self.children:
            item.disabled = True
        for p_id, p in self.players_data.items():
            if p["status"] not in ("jogando", "parou"):
                continue
            try:
                u_db = db.get_user_data(str(p_id))
                if u_db:
                    saldo = db.parse_float(u_db['data'][2])
                    db.update_value(u_db['row'], 3, round(saldo + p["aposta"], 2))
            except Exception as e:
                print(f"❌ Erro ao devolver aposta no timeout: {e}")
        try:
            if self.message:
                embed = disnake.Embed(
                    title       = "⏰ Mesa de Blackjack encerrada por inatividade",
                    description = "As apostas dos jogadores ativos foram devolvidas.",
                    color       = disnake.Color.orange()
                )
                await self.message.edit(embed=embed, view=None)
        except:
            pass

    async def _proximo_turno(self):
        self.current_player_idx += 1
        while (self.current_player_idx < len(self.player_ids) and
               self.players_data[self.player_ids[self.current_player_idx]]["status"] != "jogando"):
            self.current_player_idx += 1

        if self.current_player_idx >= len(self.player_ids):
            precisa_animar = any(p["status"] == "parou" for p in self.players_data.values())

            if precisa_animar:
                self.dealer_jogando = True
                await self.atualizar_embed()
                await asyncio.sleep(1.5)
                while self._calcular_pontos(self.dealer_hand) < 17:
                    self.dealer_hand.append(self._puxar_carta())
                    await self.atualizar_embed()
                    if self._calcular_pontos(self.dealer_hand) < 17:
                        await asyncio.sleep(2.0)
                self.dealer_jogando = False

            self.terminado = True
            await self._processar_pagamentos()
            await self.atualizar_embed()

    async def _processar_pagamentos(self):
        d_p = self._calcular_pontos(self.dealer_hand)

        def lucro_mao(pontos, aposta_mao):
            if pontos > 21:                         return 0.0
            if d_p > 21 or pontos > d_p:           return aposta_mao * 2.0
            if pontos == d_p:                       return aposta_mao
            return 0.0

        for p_id, p in self.players_data.items():
            if p["status"] == "seguro":
                continue

            try:
                u_db = db.get_user_data(str(p_id))
                if not u_db: continue
                saldo = db.parse_float(u_db['data'][2])
                ganho = lucro_mao(self._get_pontos_mao(p_id, 1), p["aposta"])
                if p["splitted"]:
                    ganho += lucro_mao(self._get_pontos_mao(p_id, 2), p["aposta"])

                if ganho > 0:
                    db.update_value(u_db['row'], 3, round(saldo + ganho, 2))
            except Exception as e:
                print(f"❌ Erro ao pagar jogador {p_id}: {e}")


# ──────────────────────────────────────────────
#  COG
# ──────────────────────────────────────────────
class BlackjackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._sapatos: dict[int, Sapato] = {}

    def _get_sapato(self, channel_id: int) -> Sapato:
        if channel_id not in self._sapatos:
            self._sapatos[channel_id] = Sapato()
            print(f"🃏 Novo sapato criado para o canal {channel_id} ({NUM_BARALHOS} baralhos, {self._sapatos[channel_id].total_inicial} cartas)")
        return self._sapatos[channel_id]

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal  = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, vai para o canal {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["bj", "21"])
    async def blackjack(self, ctx, aposta: float = None):
        if aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!blackjack <valor>` ou `!21 <valor>`")
        if aposta <= 0:
            return await ctx.send("❌ Aposta inválida!")
        aposta = round(aposta, 2)

        try:
            u_c = db.get_user_data(str(ctx.author.id))
            if not u_c:
                return await ctx.send("❌ Conta não encontrada!")

            cargo = u_c['data'][3] if len(u_c['data']) > 3 else "Lêmure"
            saldo = db.parse_float(u_c['data'][2])
            if aposta > get_limite(cargo):
                return await ctx.send(f"🚫 Como **{cargo}**, seu limite é de **{get_limite(cargo)} MC**.")
            if saldo < aposta:
                return await ctx.send("❌ Saldo insuficiente!")

            sapato = self._get_sapato(ctx.channel.id)

            if sapato.precisa_embaralhar:
                aviso = await ctx.send("🔀 **O sapato está quase vazio — embaralhando novo sapato antes de começar...**")
                await asyncio.sleep(1.5)
                try: await aviso.delete()
                except: pass

            db.update_value(u_c['row'], 3, round(saldo - aposta, 2))
            players = [ctx.author]

            # ── Lobby ──────────────────────────────────────────────────────
            lobby_view = LobbyView(ctx, self.bot, aposta, players, sapato)
            msg = await ctx.send(lobby_view._lobby_text(), view=lobby_view)
            lobby_view.msg = msg
            await lobby_view.wait()

            if lobby_view.cancelled and not lobby_view.started:
                # Devolve aposta principal do criador (outros jogadores são devolvidos no on_timeout)
                p_db = db.get_user_data(str(ctx.author.id))
                if p_db:
                    db.update_value(p_db['row'], 3, round(db.parse_float(p_db['data'][2]) + aposta, 2))
                return await ctx.send("⏰ Mesa cancelada por inatividade. Valores devolvidos.")

            if not lobby_view.started:
                p_db = db.get_user_data(str(ctx.author.id))
                if p_db:
                    db.update_value(p_db['row'], 3, round(db.parse_float(p_db['data'][2]) + aposta, 2))
                return await ctx.send("⏰ Mesa cancelada. Valores devolvidos.")

            try:
                await lobby_view.msg.delete()
            except:
                pass

            # ── Inicia o jogo ──────────────────────────────────────────────
            view = BlackjackView(ctx, self.bot, aposta, lobby_view.players, sapato,
                                 side_bets=lobby_view.side_bets)

            view.dealer_hand = [view._puxar_carta(), view._puxar_carta()]
            for p_id in view.player_ids:
                p = view.players_data[p_id]
                p["hand"] = [view._puxar_carta(), view._puxar_carta()]
                # FIX BUG 5: registra quantos Ases vieram nas 2 primeiras cartas
                p["hand_ases_iniciais"] = sum(1 for c in p["hand"] if c["valor"] == "A")

            embed_loading = disnake.Embed(title="🃏 Distribuindo as cartas...", color=disnake.Color.dark_purple())
            msg = await ctx.send(embed=embed_loading)
            view.message = msg

            msgs_side = view._resolver_side_bets_iniciais()
            if msgs_side:
                await ctx.send("🎰 **Resultados das Apostas Laterais:**\n" + "\n".join(msgs_side), delete_after=15)

            # Blackjack Natural
            for p_id in view.player_ids:
                if view._get_pontos_mao(p_id, 1) == 21:
                    view.players_data[p_id]["status"] = "parou"

            await view.atualizar_embed()

            while (view.current_player_idx < len(view.player_ids) and
                   view.players_data[view.player_ids[view.current_player_idx]]["status"] == "parou"):
                view.current_player_idx += 1

            if view.current_player_idx >= len(view.player_ids):
                await view._proximo_turno()
                return

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !blackjack de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")


def setup(bot):
    bot.add_cog(BlackjackCog(bot))