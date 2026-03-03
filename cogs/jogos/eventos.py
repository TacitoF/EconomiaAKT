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

OWNER_ID = 757752617722970243

def get_limite(cargo):
    return LIMITES_CARGO.get(cargo, 250)

def save_achievement(user_data, slug):
    conquistas = str(user_data['data'][9]) if len(user_data['data']) > 9 else ""
    lista = [c.strip() for c in conquistas.split(',') if c.strip()]
    if slug not in lista:
        lista.append(slug)
        db.update_value(user_data['row'], 10, ", ".join(lista))

class CocoEntrarView(disnake.ui.View):
    """Botão para entrar na Roleta do Coco Explosivo."""
    def __init__(self, cog, aposta: float):
        super().__init__(timeout=60)
        self.cog = cog
        self.aposta = aposta

    @disnake.ui.button(label="🥥 Entrar na Roda", style=disnake.ButtonStyle.danger)
    async def entrar(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author in self.cog.coco_players:
            return await inter.response.send_message("🐒 Você já está na roda!", ephemeral=True)
        user = db.get_user_data(str(inter.author.id))
        if not user:
            return await inter.response.send_message("❌ Conta não encontrada!", ephemeral=True)
        saldo = db.parse_float(user['data'][2])
        cargo = user['data'][3] if len(user['data']) > 3 else "Lêmure"
        if saldo < self.aposta:
            return await inter.response.send_message("❌ Saldo insuficiente!", ephemeral=True)
        if self.aposta > get_limite(cargo):
            return await inter.response.send_message(f"🚫 A aposta excede seu limite de **{cargo}**!", ephemeral=True)
        db.update_value(user['row'], 3, round(saldo - self.aposta, 2))
        self.cog.coco_players.append(inter.author)
        pote_atual = round(len(self.cog.coco_players) * self.aposta, 2)
        await inter.response.send_message(f"🥥 {inter.author.mention} entrou na roda da morte! (Pote: **{pote_atual:.2f} MC**)")

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

class Eventos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.coco_active = False
        self.coco_players = []
        self.coco_aposta = 0.0
        self.coco_streak = {}

    async def cog_before_invoke(self, ctx):
        cmd = ctx.command.name
        if cmd != 'jogos' and ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, macaco esperto joga no lugar certo! Vai para {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["roleta_coco", "coco_explosivo"])
    async def coco(self, ctx, aposta: float = None):
        if aposta is None:
            embed = disnake.Embed(
                title="🥥 ROLETA DO COCO EXPLOSIVO — Como funciona",
                description=(
                    "Um grupo de jogadores entra na roda. A cada rodada, o coco passa de mão em mão "
                    "até **explodir** na cara de um sortudo — que é eliminado!\n\n"
                    "O último sobrevivente leva o pote inteiro.\n"
                    "Quanto mais jogadores entram, maior o prêmio.\n\n"
                    "**Entrada:** 30 segundos para outros jogadores clicarem em **🥥 Entrar**.\n"
                    "Mínimo de **2 jogadores** para começar.\n\n"
                    "**Uso:** `!coco <valor>`"
                ),
                color=disnake.Color.dark_red()
            )
            return await ctx.send(embed=embed)
        if self.coco_active:
            return await ctx.send(f"⚠️ {ctx.author.mention}, já existe uma roda aberta!")
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
            self.coco_active = True
            self.coco_aposta = aposta
            self.coco_players = [ctx.author]

            view = CocoEntrarView(self, aposta)
            embed = disnake.Embed(
                title="🚨 ROLETA DO COCO EXPLOSIVO! 🚨",
                description=f"{ctx.author.mention} abriu uma roda mortal!\n\n💰 **Entrada:** `{aposta:.2f} MC`\n⏳ **30 segundos** para entrar!\n\nClique no botão abaixo para participar.",
                color=disnake.Color.dark_red()
            )
            await ctx.send(embed=embed, view=view)
            await asyncio.sleep(30)

            for item in view.children:
                item.disabled = True

            if len(self.coco_players) < 2:
                user_refund = db.get_user_data(str(ctx.author.id))
                if user_refund:
                    db.update_value(user_refund['row'], 3, round(db.parse_float(user_refund['data'][2]) + aposta, 2))
                self.coco_active = False
                self.coco_players = []
                self.coco_aposta = 0.0
                return await ctx.send(f"🥥 Ninguém teve coragem. O jogo foi cancelado e o dinheiro devolvido para {ctx.author.mention}.")

            jogadores = self.coco_players.copy()
            total_jogadores = len(jogadores)
            pote_bruto = round(self.coco_aposta * total_jogadores, 2)

            await ctx.send(f"🔥 **A RODA FECHOU!** {total_jogadores} macacos corajosos — pote de **{pote_bruto:.2f} MC**!\nQue os jogos comecem...")

            rodada = 1
            while len(jogadores) > 1:
                await asyncio.sleep(2.5)
                await ctx.send("🥥 *O coco está passando de mão em mão...*")
                await asyncio.sleep(2)
                await ctx.send("⏱️ *Tic... Tac... Tic...*")
                await asyncio.sleep(2.5)

                eliminado = random.choice(jogadores)
                jogadores.remove(eliminado)

                str_id_elim = str(eliminado.id)
                if str_id_elim in self.coco_streak:
                    self.coco_streak[str_id_elim] = 0

                await ctx.send(f"💥 **KABOOOM!** O coco explodiu na cara de {eliminado.mention}! Fora da roda.")

                if rodada == 1 and total_jogadores >= 4:
                    m_db = db.get_user_data(str(eliminado.id))
                    if m_db: save_achievement(m_db, "ima_desgraca")
                rodada += 1

            vencedor = jogadores[0]
            vencedor_id = str(vencedor.id)
            v_db = db.get_user_data(vencedor_id)
            if not v_db:
                return await ctx.send("❌ Erro ao encontrar vencedor no banco de dados!")

            self.coco_streak[vencedor_id] = self.coco_streak.get(vencedor_id, 0) + 1
            vit_seguidas = self.coco_streak[vencedor_id]

            lucro = round(pote_bruto - self.coco_aposta, 2)
            lucro_total = lucro + aposta
            db.update_value(v_db['row'], 3, round(db.parse_float(v_db['data'][2]) + pote_bruto, 2))

            await ctx.send(f"🏆 **FIM DE JOGO!** {vencedor.mention} sobreviveu e faturou **{lucro_total:.2f} MC** de lucro!")

            if total_jogadores >= 5:
                save_achievement(v_db, "veterano_coco")

            if vit_seguidas >= 3:
                save_achievement(v_db, "invicto_coco")
                await ctx.send(f"🔥 {vencedor.mention} venceu 3 vezes seguidas e garantiu a conquista **Mestre dos Cocos**! 🥥")
                self.coco_streak[vencedor_id] = 0

            self.coco_players = []
            self.coco_aposta = 0.0
            self.coco_active = False

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !coco de {ctx.author}: {e}")
            self.coco_active = False
            self.coco_players = []
            self.coco_aposta = 0.0
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. O jogo foi cancelado.")

    @commands.command()
    async def jogos(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            return await ctx.send(f"⚠️ {ctx.author.mention}, use este comando no canal {mencao}!")

        embed = disnake.Embed(
            title       = "🎰 AK-BET — CASSINO DA SELVA",
            description = "Escolha seu veneno e transforme seus **Macacoins** em fortuna!\nTodos os jogos usam **botões interativos**. 🐒\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color       = disnake.Color.from_rgb(255, 180, 0),
        )

        embed.add_field(
            name  = "🎰 JOGOS SOLO",
            value = (
                "🚀 **`!crash <valor>`**\n"
                "└ *Suba no gráfico e saque antes de arrebentar!*\n"
                "🎰 **`!cassino <valor>`**\n"
                "└ *Caça-níquel — 3 iguais = JACKPOT 10x!*\n"
                "💣 **`!minas <bombas> <valor>`**\n"
                "└ *Campo minado — mais risco, mais lucro!*\n"
                "🎲 **`!bicho <valor>`**\n"
                "└ *Escolha um animal via botão e torça (Paga 4x)!*\n"
                "🎫 **`!raspadinha <valor>`**\n"
                "└ *Raspe instantaneamente por prêmios de até 10x.*"
            ),
            inline = False,
        )

        embed.add_field(
            name  = "⚔️ 1X1 (PVP)",
            value = (
                "✂️ **`!duelo @user <valor>`**\n"
                "└ *Jokenpô da selva (Gorila, Caçador, Casca).*\n"
                "🌿 **`!cipo @user <valor>`**\n"
                "└ *Roleta Russa — um cai, o outro ganha tudo.*\n"
                "🔫 **`!bang @user <valor>`**\n"
                "└ *Gatilho Rápido — quem clicar primeiro vence.*\n"
                "🥊 **`!rinha @user <valor>`**\n"
                "└ *Rinha Símia — Luta tática de mentes e reflexos.*\n"
                "🗺️ **`!explorar @user <valor>`**\n"
                "└ *Caça ao tesouro (mini campo minado 5x5).*"
            ),
            inline = False,
        )

        embed.add_field(
            name  = "🎮 MULTIPLAYER",
            value = (
                "♠️ **`!21 <valor>`**\n"
                "└ *Blackjack — derrote o dealer (Mesa p/ até 5).*\n"
                "🎡 **`!roleta`** → Depois **`!apostar <valor> <opção>`**\n"
                "└ *Aposte em Cores (2x), Par/Ímpar (2x) ou Números (36x).*\n"
                "🏆 **`!torneio <valor>`**\n"
                "└ *Torneio mata-mata extremo de Jokenpô (até 8 jogadores).*\n"
                "🥥 **`!coco <valor>`**\n"
                "└ *Roleta do Coco Explosivo — sobreviva e leve o pote!*"
            ),
            inline = False,
        )

        embed.add_field(
            name  = "⚽ APOSTAS ESPORTIVAS",
            value = (
                "⚽ **`!futebol`**\n"
                "└ *Veja os próximos jogos e aposte pelo menu interativo.*\n"
                "🎟️ **`!pule`**\n"
                "└ *Veja seus bilhetes pendentes (Odd fixa 2.0x e auto-pagamento).*"
            ),
            inline = False,
        )

        embed.set_footer(text="💡 Dica: use !perfil para ver seus MC antes de apostar.")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Eventos(bot))