import disnake
from disnake.ext import commands
import database as db
import random

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

# ── Multiplicadores ───────────────────────────────────────────────────────
# Fórmula: mult = round((1 + fator) ^ casas_reveladas, 2)
#
# Equivalente aos outros jogos do servidor:
#   Corrida (3x, 33% chance) ≈ minas 3 bombas revelando ~7 casas
#   Bicho   (5x, 20% chance) ≈ minas 4–5 bombas revelando tudo
#   Crash   (raramente >4x)  ≈ minas 4 bombas revelando 10+ casas
#
# Tetos máximos (revelar TODAS as casas seguras):
#   1 bomba  (15 casas) → 1.75x   baixo risco, retorno conservador
#   2 bombas (14 casas) → 2.26x
#   3 bombas (13 casas) → 3.07x   equivalente à corrida
#   4 bombas (12 casas) → 4.11x   equivalente ao bicho
#   5 bombas (11 casas) → 5.37x   extremamente difícil (~0.06%)
#
# Ganhos em jogadas típicas (3–5 casas reveladas antes de sacar):
#   1 bomba,  4 casas → 1.16x   2 bombas, 4 casas → 1.26x
#   3 bombas, 4 casas → 1.41x   4 bombas, 4 casas → 1.60x
#   5 bombas, 4 casas → 1.84x
# ─────────────────────────────────────────────────────────────────────────
FATORES = {1: 0.038, 2: 0.060, 3: 0.090, 4: 0.125, 5: 0.165}

def calcular_mult(bombas: int, casas_reveladas: int) -> float:
    if casas_reveladas == 0:
        return 1.0
    fator = FATORES.get(bombas, 0.038)
    return round((1 + fator) ** casas_reveladas, 2)


class MinasView(disnake.ui.View):
    GRID = 16  # 4×4

    def __init__(self, ctx, aposta: float, bombas: int, user_row: int):
        super().__init__(timeout=120)
        self.ctx       = ctx
        self.aposta    = aposta
        self.bombas    = bombas
        self.user_row  = user_row
        self.terminado = False
        self.reveladas = 0

        self.minas   = set(random.sample(range(self.GRID), bombas))
        self.abertas: set[int] = set()

        self._build_buttons()

    def _build_buttons(self):
        self.clear_items()

        for i in range(self.GRID):
            aberta   = i in self.abertas
            eh_mina  = i in self.minas
            disabled = self.terminado or aberta

            if aberta:
                label = "💣" if eh_mina else "✅"
                style = disnake.ButtonStyle.danger if eh_mina else disnake.ButtonStyle.success
            else:
                label = "?"
                style = disnake.ButtonStyle.secondary

            btn = disnake.ui.Button(
                label=label,
                style=style,
                custom_id=f"casa_{i}",
                row=i // 4,
                disabled=disabled,
            )
            btn.callback = self._make_callback(i)
            self.add_item(btn)

        # Botão sacar — aparece após revelar ao menos 1 casa segura
        if self.reveladas > 0 and not self.terminado:
            mult  = calcular_mult(self.bombas, self.reveladas)
            ganho = round(self.aposta * mult, 2)
            sacar = disnake.ui.Button(
                label=f"💰 Sacar  {mult}x  ({ganho:.2f} C)",
                style=disnake.ButtonStyle.success,
                custom_id="sacar",
                row=4,
            )
            sacar.callback = self._sacar_callback
            self.add_item(sacar)

    def _make_callback(self, index: int):
        async def callback(inter: disnake.MessageInteraction):
            if inter.author.id != self.ctx.author.id:
                return await inter.response.send_message("❌ Não é o seu jogo!", ephemeral=True)
            if self.terminado or index in self.abertas:
                return await inter.response.defer()

            self.abertas.add(index)

            if index in self.minas:
                # ── EXPLODIU ────────────────────────────────────
                self.terminado = True
                self.abertas = set(range(self.GRID))
                self._build_buttons()

                if self.bombas == 1:
                    u = db.get_user_data(str(inter.author.id))
                    if u:
                        conquistas = str(u['data'][9]) if len(u['data']) > 9 else ""
                        lista = [c.strip() for c in conquistas.split(',') if c.strip()]
                        if "escorregou_banana" not in lista:
                            lista.append("escorregou_banana")
                            db.update_value(u['row'], 10, ", ".join(lista))

                await inter.response.edit_message(
                    embed=self._build_embed(explodiu=True), view=self
                )

            else:
                # ── CASA SEGURA ──────────────────────────────────
                self.reveladas += 1
                casas_seguras_total = self.GRID - self.bombas

                if self.reveladas == casas_seguras_total:
                    # Revelou tudo — vitória automática
                    self.terminado = True
                    self.abertas = set(range(self.GRID))
                    mult  = calcular_mult(self.bombas, self.reveladas)
                    ganho = round(self.aposta * mult, 2)

                    u = db.get_user_data(str(inter.author.id))
                    if u:
                        db.update_value(u['row'], 3, round(db.parse_float(u['data'][2]) + ganho, 2))
                        if self.bombas == 5:
                            conquistas = str(u['data'][9]) if len(u['data']) > 9 else ""
                            lista = [c.strip() for c in conquistas.split(',') if c.strip()]
                            if "esquadrao_suicida" not in lista:
                                lista.append("esquadrao_suicida")
                                db.update_value(u['row'], 10, ", ".join(lista))

                    self._build_buttons()
                    await inter.response.edit_message(
                        embed=self._build_embed(vitoria=True, ganho=ganho, mult=mult), view=self
                    )
                else:
                    self._build_buttons()
                    await inter.response.edit_message(
                        embed=self._build_embed(), view=self
                    )

        return callback

    async def _sacar_callback(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.ctx.author.id:
            return await inter.response.send_message("❌ Não é o seu jogo!", ephemeral=True)
        if self.terminado:
            return await inter.response.defer()

        self.terminado = True
        mult  = calcular_mult(self.bombas, self.reveladas)
        ganho = round(self.aposta * mult, 2)

        u = db.get_user_data(str(inter.author.id))
        if u:
            db.update_value(u['row'], 3, round(db.parse_float(u['data'][2]) + ganho, 2))

        self._build_buttons()
        await inter.response.edit_message(
            embed=self._build_embed(sacou=True, ganho=ganho, mult=mult), view=self
        )

    def _build_embed(
        self,
        explodiu: bool = False,
        vitoria:  bool = False,
        sacou:    bool = False,
        ganho:    float = 0.0,
        mult:     float = 1.0,
    ) -> disnake.Embed:

        mult_atual  = calcular_mult(self.bombas, self.reveladas)
        saque_atual = round(self.aposta * mult_atual, 2)

        if explodiu:
            cor    = disnake.Color.red()
            titulo = "💥 BOOOOM! Você pisou numa mina!"
            desc   = f"{self.ctx.author.mention} perdeu **{self.aposta:.2f} C**."
        elif vitoria:
            cor    = disnake.Color.gold()
            titulo = "🏆 CAMPO LIMPO! Todas as casas seguras reveladas!"
            desc   = f"{self.ctx.author.mention} ganhou **{ganho:.2f} C** (`{mult}x`)!"
        elif sacou:
            cor    = disnake.Color.green()
            titulo = "💰 Saque realizado com segurança!"
            desc   = f"{self.ctx.author.mention} sacou **{ganho:.2f} C** (`{mult}x`)."
        else:
            cor    = disnake.Color.blurple()
            titulo = f"💣 Campo Minado — {self.bombas} {'mina' if self.bombas == 1 else 'minas'}"
            desc   = (
                f"Aposta: **{self.aposta:.2f} C**\n"
                f"Casas seguras reveladas: **{self.reveladas}**\n"
                f"Multiplicador atual: **{mult_atual}x** → Saque: **{saque_atual:.2f} C**"
            )

        embed = disnake.Embed(title=titulo, description=desc, color=cor)

        if not self.terminado:
            embed.set_footer(text="Clique numa casa para revelar | 💰 Sacar para garantir seus ganhos")

        return embed

    async def on_timeout(self):
        if not self.terminado:
            self.terminado = True
            for item in self.children:
                item.disabled = True
            try:
                await self.ctx.channel.send(
                    f"⏰ {self.ctx.author.mention}, o tempo acabou! "
                    f"Sua aposta de **{self.aposta:.2f} C** foi perdida."
                )
            except:
                pass


class MinasGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, vá para o canal {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(name="minas")
    async def campo_minado(self, ctx, bombas: int = None, aposta: float = None):
        if bombas is None or aposta is None:
            return await ctx.send(
                f"⚠️ {ctx.author.mention}, use: `!minas <1-5 bombas> <valor>`\n"
                f"Mais bombas = mais risco = multiplicador maior por casa revelada!"
            )
        if not (1 <= bombas <= 5):
            return await ctx.send(f"❌ {ctx.author.mention}, escolha entre 1 e 5 bombas.")
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
                return await ctx.send(
                    f"🚫 Limite de aposta para **{cargo}** é de **{get_limite(cargo)} C**!"
                )

            db.update_value(user['row'], 3, round(saldo - aposta, 2))

            view  = MinasView(ctx, aposta, bombas, user['row'])
            embed = view._build_embed()
            await ctx.send(embed=embed, view=view)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !minas de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(MinasGame(bot))