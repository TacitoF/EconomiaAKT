import disnake
from disnake.ext import commands
import database as db
from .constantes import get_limite
from .side_bets import ViewEscolhaSideBet


class LobbyView(disnake.ui.View):
    MAX_JOGADORES = 6

    def __init__(self, ctx, bot, aposta: float, players: list, sapato):
        super().__init__(timeout=60)
        self.ctx       = ctx
        self.bot       = bot
        self.aposta    = aposta
        self.players   = players
        self.sapato    = sapato
        self.started   = False
        self.cancelled = False
        self.msg       = None
        self.side_bets: dict = {}

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
            aposta_principal=self.aposta, lobby=self, p_id=inter.author.id,
        )
        await inter.response.send_message(
            content=view_escolha._content(), view=view_escolha, ephemeral=True,
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
        nomes = ", ".join(p.display_name for p in self.players)

        sb_linhas = []
        for p in self.players:
            sb = self.side_bets.get(p.id, {})
            partes = []
            if sb.get("21_3"): partes.append(f"21+3: {sb['21_3']:.2f} MC")
            if sb.get("pp"):   partes.append(f"PP: {sb['pp']:.2f} MC")
            if partes:
                sb_linhas.append(f"  • {p.display_name}: {' | '.join(partes)}")

        sb_texto = ("\n🎰 **Apostas Laterais:**\n" + "\n".join(sb_linhas)) if sb_linhas else ""

        return (
            f"🃏 **BLACKJACK!** Dono: {self.ctx.author.mention} | Aposta: `{self.aposta:.2f} MC`\n"
            f"👥 **Jogadores ({len(self.players)}):** {nomes}"
            f"{sb_texto}\n"
            f"Clique **Entrar** para participar, **🎰 Aposta Lateral** para apostas laterais, ou **Começar** para iniciar!\n"
            f"💡 *Para retirar uma aposta lateral, clique em **🎰 Aposta Lateral**, escolha o tipo e envie **0**.*"
        )

    async def on_timeout(self):
        self.cancelled = True

        # Devolve aposta principal + side bets dos jogadores que entraram pelo botão
        for p in self.players[1:]:
            total = round(self.aposta + sum(v for v in self.side_bets.get(p.id, {}).values() if v), 2)
            if total <= 0:
                continue
            try:
                u_db = db.get_user_data(str(p.id))
                if u_db:
                    db.update_value(u_db['row'], 3, round(db.parse_float(u_db['data'][2]) + total, 2))
            except Exception as e:
                print(f"❌ Erro ao devolver aposta no timeout do lobby para {p.id}: {e}")

        # Devolve só os side bets do criador (aposta principal dele é tratada no cog)
        criador = self.players[0] if self.players else None
        if criador:
            total_sb = round(sum(v for v in self.side_bets.get(criador.id, {}).values() if v), 2)
            if total_sb > 0:
                try:
                    u_db = db.get_user_data(str(criador.id))
                    if u_db:
                        db.update_value(u_db['row'], 3, round(db.parse_float(u_db['data'][2]) + total_sb, 2))
                except Exception as e:
                    print(f"❌ Erro ao devolver side bet do criador no timeout: {e}")

        self.stop()