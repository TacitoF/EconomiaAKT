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
    return LIMITES_CARGO.get(cargo, 250)

def save_achievement(user_data, slug):
    conquistas = str(user_data['data'][9]) if len(user_data['data']) > 9 else ""
    lista = [c.strip() for c in conquistas.split(',') if c.strip()]
    if slug not in lista:
        lista.append(slug)
        db.update_value(user_data['row'], 10, ", ".join(lista))


# ══════════════════════════════════════════════════════════════════════════════
#  JOGO DO BICHO — constantes globais (usadas pelo Cog e pela View)
# ══════════════════════════════════════════════════════════════════════════════

# 5 animais, cada um cobre 20 números (0-19, 20-39, ... 80-99)
# número sorteado: 0-99  →  bicho = número // 20
BICHOS = [
    ("🦁", "Leão",     "00–19"),
    ("🐍", "Cobra",    "20–39"),
    ("🐊", "Jacaré",   "40–59"),
    ("🦜", "Arara",    "60–79"),
    ("🐘", "Elefante", "80–99"),
]
BICHO_MULT = 4.0   # paga 4× o apostado

def numero_para_bicho(n: int):
    """Recebe 0-99, devolve (emoji, nome, faixa_str)."""
    return BICHOS[n // 20]


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW — 5 botões de escolha
# ══════════════════════════════════════════════════════════════════════════════

class BichoEscolhaView(disnake.ui.View):
    def __init__(self, ctx, aposta: float):
        super().__init__(timeout=30)
        self.ctx    = ctx
        self.aposta = aposta
        self.jogou  = False

        for emoji, nome, faixa in BICHOS:
            btn = disnake.ui.Button(
                label     = nome,
                emoji     = emoji,
                style     = disnake.ButtonStyle.primary,
                custom_id = f"bicho_{nome}",
            )
            btn.callback = self._make_callback(emoji, nome)
            self.add_item(btn)

    def _make_callback(self, emoji_escolhido: str, nome_escolhido: str):
        async def callback(inter: disnake.MessageInteraction):
            # ── Validações ──────────────────────────────────────────────
            if inter.author.id != self.ctx.author.id:
                return await inter.response.send_message("❌ Não é o seu jogo!", ephemeral=True)
            if self.jogou:
                return await inter.response.defer()

            self.jogou = True
            for item in self.children:
                item.disabled = True

            # ── Busca e debita saldo ─────────────────────────────────────
            user = db.get_user_data(str(inter.author.id))
            if not user:
                await inter.response.edit_message(view=self)
                return await inter.followup.send("❌ Conta não encontrada!", ephemeral=True)

            saldo = db.parse_float(user['data'][2])
            if saldo < self.aposta:
                await inter.response.edit_message(view=self)
                return await inter.followup.send("❌ Saldo insuficiente no momento!", ephemeral=True)

            db.update_value(user['row'], 3, round(saldo - self.aposta, 2))

            # ── Embed de sorteio ─────────────────────────────────────────
            embed_spin = disnake.Embed(
                title       = "🎲 JOGO DO BICHO",
                description = (
                    f"{inter.author.mention} apostou no **{emoji_escolhido} {nome_escolhido}**!\n\n"
                    f"🎡  *A roleta está girando...*"
                ),
                color = disnake.Color.yellow(),
            )
            embed_spin.set_footer(text=f"Aposta: {self.aposta:.2f} MC  ·  Prêmio possível: {self.aposta * BICHO_MULT:.2f} MC")
            await inter.response.edit_message(embed=embed_spin, view=self)
            await asyncio.sleep(2)

            # ── Sorteio ──────────────────────────────────────────────────
            numero = random.randint(0, 99)
            emoji_saiu, nome_saiu, faixa_saiu = numero_para_bicho(numero)
            ganhou = (nome_saiu == nome_escolhido)

            # ── Paga ou registra perda ───────────────────────────────────
            user_atual  = db.get_user_data(str(inter.author.id))
            saldo_atual = db.parse_float(user_atual['data'][2])

            if ganhou:
                premio = round(self.aposta * BICHO_MULT, 2)
                lucro  = round(premio - self.aposta, 2)
                db.update_value(user_atual['row'], 3, round(saldo_atual + premio, 2))

                embed_result = disnake.Embed(
                    title       = "🎉 ACERTOU O BICHO!",
                    description = (
                        f"O número sorteado foi **{numero:02d}** → {emoji_saiu} **{nome_saiu}** *(faixa {faixa_saiu})*\n\n"
                        f"✅ {inter.author.mention} apostou em **{emoji_escolhido} {nome_escolhido}** e **GANHOU**!\n"
                        f"💰 Prêmio: **{premio:.2f} MC** *(lucro de {lucro:.2f} MC)*"
                    ),
                    color = disnake.Color.green(),
                )
                embed_result.set_footer(text="Sorte grande! Use !bicho para jogar novamente.")
            else:
                embed_result = disnake.Embed(
                    title       = "💀 ERROU O BICHO!",
                    description = (
                        f"O número sorteado foi **{numero:02d}** → {emoji_saiu} **{nome_saiu}** *(faixa {faixa_saiu})*\n\n"
                        f"❌ {inter.author.mention} apostou em **{emoji_escolhido} {nome_escolhido}** e **perdeu**.\n"
                        f"💸 Perdeu: **{self.aposta:.2f} MC**"
                    ),
                    color = disnake.Color.red(),
                )
                embed_result.set_footer(text="Tente de novo com !bicho")

            await inter.edit_original_response(embed=embed_result, view=self)

        return callback

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.ctx.send(
                f"⏰ {self.ctx.author.mention}, o tempo esgotou! Nenhum valor foi debitado."
            )
        except:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════════════════════════════════════

class Cassino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, macaco esperto joga no lugar certo! Vai para {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    # ── Slots ─────────────────────────────────────────────────────────────────
    @commands.command(name="cassino")
    async def cassino_slots(self, ctx, aposta: float = None):
        if aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!cassino <valor>`")
        if aposta <= 0:
            return await ctx.send(f"⚠️ {ctx.author.mention}, valor inválido!")
        aposta = round(aposta, 2)

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send(f"❌ {ctx.author.mention}, conta não encontrada!")

            saldo = db.parse_float(user['data'][2])
            if saldo < aposta:
                return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

            cargo = user['data'][3] if len(user['data']) > 3 else "Lêmure"
            if aposta > get_limite(cargo):
                return await ctx.send(f"🚫 Limite de aposta para **{cargo}** é de **{get_limite(cargo)} MC**!")

            db.update_value(user['row'], 3, round(saldo - aposta, 2))

            emojis = ["🍌", "🐒", "⚡", "🥥", "💎", "🦍", "🌴", "🌊"]
            res = [random.choice(emojis) for _ in range(3)]

            user_atual  = db.get_user_data(str(ctx.author.id))
            saldo_atual = db.parse_float(user_atual['data'][2])

            if res[0] == res[1] == res[2]:
                lucro_total = round(aposta * 10.0, 2)
                db.update_value(user_atual['row'], 3, round(saldo_atual + lucro_total, 2))
                save_achievement(user_atual, "filho_da_sorte")
                status_msg = f"🎰 **JACKPOT!** 🎰\nVocê lucrou **{lucro_total:.2f} MC**!"
            elif res[0] == res[1] or res[1] == res[2] or res[0] == res[2]:
                lucro = round(aposta * 1.0, 2)
                db.update_value(user_atual['row'], 3, round(saldo_atual + aposta + lucro, 2))
                status_msg = f"Você lucrou **{lucro:.2f} MC**!"
            else:
                status_msg = f"Você perdeu **{aposta:.2f} MC**."

            await ctx.send(f"🎰 **CASSINO AKTrovão** 🎰\n**[ {res[0]} | {res[1]} | {res[2]} ]**\n{ctx.author.mention}, {status_msg}")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !cassino de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ── Jogo do Bicho ─────────────────────────────────────────────────────────
    @commands.command(name="bicho")
    async def jogo_bicho(self, ctx, aposta: float = None):
        """Jogo do Bicho com seleção por botões. Use: !bicho <valor>"""
        if aposta is None:
            linhas = "\n".join(f"{e} **{n}** *(faixa {f})*" for e, n, f in BICHOS)
            return await ctx.send(
                f"⚠️ {ctx.author.mention}, use: `!bicho <valor>`\n\n"
                f"🎲 **Como funciona:** Um número de **00 a 99** é sorteado.\n"
                f"Cada animal cobre uma faixa de 20 números. Acertou? Ganha **{BICHO_MULT:.0f}x**!\n\n"
                f"{linhas}"
            )
        if aposta <= 0:
            return await ctx.send("❌ Aposta inválida!")
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

            linhas = "\n".join(f"{e} **{n}** — faixa `{f}`" for e, n, f in BICHOS)

            embed = disnake.Embed(
                title       = "🎲 JOGO DO BICHO",
                description = (
                    f"{ctx.author.mention}, escolha o seu animal!\n\n"
                    f"{linhas}\n\n"
                    f"💰 Aposta: **{aposta:.2f} MC**   ·   "
                    f"Prêmio: **{aposta * BICHO_MULT:.2f} MC** `({BICHO_MULT:.0f}x)`"
                ),
                color = disnake.Color.from_rgb(34, 139, 34),
            )
            embed.set_footer(text="Você tem 30s para escolher • Um número 00–99 será sorteado")

            view = BichoEscolhaView(ctx, aposta)
            await ctx.send(embed=embed, view=view)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !bicho de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ── Corrida de Macacos ────────────────────────────────────────────────────
    @commands.command(name="corrida")
    async def corrida_macaco(self, ctx, escolha: str = None, aposta: float = None):
        if escolha is None or aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!corrida <animal> <valor>`\nAnimais: `macaquinho`, `gorila`, `orangutango`")

        opcoes = {"macaquinho": "🐒", "gorila": "🦍", "orangutango": "🦧"}
        escolha = escolha.lower()
        if escolha not in opcoes:
            return await ctx.send(f"❌ {ctx.author.mention}, escolha: `macaquinho`, `gorila` ou `orangutango`.")
        if aposta <= 0:
            return await ctx.send("❌ Aposta inválida!")
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

            db.update_value(user['row'], 3, round(saldo - aposta, 2))

            macacos_lista = list(opcoes.values())
            nomes_lista   = list(opcoes.keys())
            pistas  = [0, 0, 0]
            chegada = 10

            msg = await ctx.send(
                f"🏁 **A CORRIDA COMEÇOU!** {ctx.author.mention} apostou no **{escolha.capitalize()}**!\n\n" +
                "\n".join([f"{macacos_lista[i]} 🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦 🏁" for i in range(3)])
            )

            vencedor_idx = -1
            while vencedor_idx == -1:
                await asyncio.sleep(1.2)
                for i in range(3):
                    pistas[i] += random.randint(1, 3)
                    if pistas[i] >= chegada:
                        vencedor_idx = i
                        break
                frame = []
                for i in range(3):
                    progresso = min(pistas[i], chegada)
                    frame.append(f"{macacos_lista[i]} {'🟩' * progresso}{'🟦' * (chegada - progresso)} 🏁")
                await msg.edit(content="🏁 **A CORRIDA ESTÁ QUENTE!**\n\n" + "\n".join(frame))

            nome_vencedor = nomes_lista[vencedor_idx]
            user_atual    = db.get_user_data(str(ctx.author.id))
            saldo_atual   = db.parse_float(user_atual['data'][2])

            if escolha == nome_vencedor:
                lucro = round(aposta * 2.0, 2)
                db.update_value(user_atual['row'], 3, round(saldo_atual + aposta + lucro, 2))
                await ctx.send(f"🏆 {ctx.author.mention} **VITÓRIA!** O {nome_vencedor.capitalize()} cruzou primeiro! Lucrou **{lucro:.2f} MC**!")
            else:
                await ctx.send(f"💀 {ctx.author.mention} **DERROTA!** O {nome_vencedor.capitalize()} venceu. Você perdeu **{aposta:.2f} MC**.")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !corrida de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")


def setup(bot):
    bot.add_cog(Cassino(bot))