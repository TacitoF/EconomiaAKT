import disnake
import database as db
from .constantes import (
    ODDS_21_3, ODDS_PERFECT_PAIRS, NAIPE_COR, ORDEM_CARTA, NOME_PT,
)


# ──────────────────────────────────────────────
#  FUNÇÕES DE AVALIAÇÃO
# ──────────────────────────────────────────────

def avaliar_21_3(c1: dict, c2: dict, cd: dict) -> tuple[str | None, int]:
    cartas = [c1, c2, cd]
    valores = [c["valor"] for c in cartas]
    naipes  = [c["naipe"] for c in cartas]
    ordens  = sorted([ORDEM_CARTA[v] for v in valores])

    mesmo_naipe = len(set(naipes)) == 1
    mesmo_valor = len(set(valores)) == 1
    sequencia   = (ordens[2] - ordens[0] == 2 and len(set(ordens)) == 3)

    # Casos especiais de sequência com Ás
    if set(valores) in ({"A", "Q", "K"}, {"A", "2", "3"}):
        sequencia = True

    if mesmo_valor and mesmo_naipe: return "trio_perfeito",   ODDS_21_3["trio_perfeito"]
    if mesmo_valor:                 return "trio",            ODDS_21_3["trio"]
    if sequencia and mesmo_naipe:   return "sequencia_color", ODDS_21_3["sequencia_color"]
    if sequencia:                   return "sequencia",       ODDS_21_3["sequencia"]
    if mesmo_naipe:                 return "flush",           ODDS_21_3["flush"]
    return None, 0


def avaliar_perfect_pairs(c1: dict, c2: dict) -> tuple[str | None, int]:
    if c1["valor"] != c2["valor"]:
        return None, 0
    if c1["naipe"] == c2["naipe"]:
        return "par_perfeito", ODDS_PERFECT_PAIRS["par_perfeito"]
    if NAIPE_COR[c1["naipe"]] == NAIPE_COR[c2["naipe"]]:
        return "par_colorido", ODDS_PERFECT_PAIRS["par_colorido"]
    return "par_misto", ODDS_PERFECT_PAIRS["par_misto"]


# ──────────────────────────────────────────────
#  MODAL — valor de um side bet específico
# ──────────────────────────────────────────────

class ModalValorSideBet(disnake.ui.Modal):
    def __init__(self, tipo: str, aposta_principal: float, lobby,
                 p_id: int, view_inter: disnake.MessageInteraction):
        self.tipo             = tipo
        self.aposta_principal = aposta_principal
        self.lobby            = lobby
        self.p_id             = p_id
        self.view_inter       = view_inter

        nome   = "21+3" if tipo == "21_3" else "Perfect Pairs"
        maximo = round(aposta_principal * 0.50, 2)

        sb_atual   = lobby.side_bets.get(p_id, {}).get(tipo)
        dica_atual = (
            f"Aposta atual: {sb_atual:.2f} MC — envie 0 para cancelar"
            if sb_atual else
            f"Entre 0.01 e {maximo:.2f} MC"
        )

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
        except Exception:
            pass

    async def _atualizar_lobby(self):
        try:
            if self.lobby.msg:
                await self.lobby.msg.edit(content=self.lobby._lobby_text())
        except Exception:
            pass


# ──────────────────────────────────────────────
#  VIEW — escolha do tipo de side bet (ephemeral)
# ──────────────────────────────────────────────

class ViewEscolhaSideBet(disnake.ui.View):
    def __init__(self, aposta_principal: float, lobby, p_id: int):
        super().__init__(timeout=60)
        self.aposta_principal = aposta_principal
        self.lobby            = lobby
        self.p_id             = p_id

    def _content(self) -> str:
        maximo    = round(self.aposta_principal * 0.50, 2)
        sb        = self.lobby.side_bets.get(self.p_id, {})
        val_21    = sb.get("21_3")
        val_pp    = sb.get("pp")
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
        await inter.response.send_modal(ModalValorSideBet(
            tipo="21_3", aposta_principal=self.aposta_principal,
            lobby=self.lobby, p_id=self.p_id, view_inter=inter,
        ))

    @disnake.ui.button(label="💎 Perfect Pairs", style=disnake.ButtonStyle.blurple, row=0)
    async def btn_pp(self, button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(ModalValorSideBet(
            tipo="pp", aposta_principal=self.aposta_principal,
            lobby=self.lobby, p_id=self.p_id, view_inter=inter,
        ))