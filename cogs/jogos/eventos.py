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
        await inter.response.send_message(f"🥥 {inter.author.mention} entrou na roda da morte! (Pote: **{pote_atual:.2f} C**)")

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class Eventos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loteria_participantes = []
        self.loteria_pote = 0.0
        self.coco_active = False
        self.coco_players = []
        self.coco_aposta = 0.0

    async def cog_before_invoke(self, ctx):
        cmd = ctx.command.name
        canais_loteria = ['loteria', 'bilhete', 'loto', 'sortear_loteria', 'pote', 'premio', 'acumulado']
        if cmd in canais_loteria:
            if ctx.channel.name not in ['🐒・conguitos', '🎰・akbet']:
                await ctx.send(f"⚠️ {ctx.author.mention}, use a loteria no canal #🐒・conguitos ou #🎰・akbet.")
                raise commands.CommandError("Canal incorreto para loteria.")
            return
        if cmd != 'jogos' and ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, macaco esperto joga no lugar certo! Vai para {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["premio", "acumulado"])
    async def pote(self, ctx):
        if self.loteria_pote == 0.0:
            return await ctx.send(f"🎫 {ctx.author.mention}, o pote está zerado! Seja o primeiro com `!loteria` (500 C).")
        embed = disnake.Embed(
            title="💰 Pote da Loteria da Selva",
            description=f"Prêmio acumulado: **{self.loteria_pote:.2f} C**\n\n👥 **Bilhetes vendidos:** `{len(self.loteria_participantes)}`",
            color=disnake.Color.gold()
        )
        embed.set_footer(text="Garanta sua chance com !loteria")
        await ctx.send(embed=embed)

    @commands.command(aliases=["bilhete", "loto"])
    async def loteria(self, ctx):
        custo = 500.0
        user_id = ctx.author.id
        if user_id in self.loteria_participantes:
            return await ctx.send(f"🎫 {ctx.author.mention}, você já tem um bilhete! Pote atual: **{self.loteria_pote:.2f} C**.")

        try:
            user = db.get_user_data(str(user_id))
            saldo = db.parse_float(user['data'][2]) if user else 0.0
            if not user or saldo < custo:
                return await ctx.send(f"❌ {ctx.author.mention}, você precisa de **{custo:.2f} C** para um bilhete!")

            db.update_value(user['row'], 3, round(saldo - custo, 2))
            self.loteria_participantes.append(user_id)
            self.loteria_pote += custo
            await ctx.send(f"🎫 **BILHETE COMPRADO!** {ctx.author.mention} entrou na loteria.\n💰 Pote agora em **{self.loteria_pote:.2f} C**!")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !loteria de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    @commands.command()
    async def sortear_loteria(self, ctx):
        if ctx.author.id != OWNER_ID:
            return await ctx.send("❌ Apenas o Admin pode sortear a loteria!")
        if not self.loteria_participantes:
            return await ctx.send("❌ Nenhum bilhete foi vendido para esta rodada.")

        await ctx.send("🎰 **O GLOBO ESTÁ GIRANDO...**")
        await asyncio.sleep(3)

        try:
            ganhador_id = random.choice(self.loteria_participantes)
            ganhador = await self.bot.fetch_user(ganhador_id)
            premio = round(self.loteria_pote, 2)

            user_db = db.get_user_data(str(ganhador_id))
            if not user_db:
                return await ctx.send("❌ Erro ao encontrar o ganhador no banco de dados!")

            db.update_value(user_db['row'], 3, round(db.parse_float(user_db['data'][2]) + premio, 2))

            embed = disnake.Embed(
                title="🎉 TEMOS UM VENCEDOR! 🎉",
                description=f"O sortudo é **{ganhador.mention}**!\nEle faturou **{premio:.2f} C**!",
                color=disnake.Color.gold()
            )
            embed.set_footer(text="A próxima rodada começa agora!")
            await ctx.send(embed=embed)

            self.loteria_participantes = []
            self.loteria_pote = 0.0

        except Exception as e:
            print(f"❌ Erro no !sortear_loteria: {e}")
            await ctx.send("⚠️ Ocorreu um erro ao sortear. Tente novamente!")

    @commands.command(aliases=["roleta_coco", "coco_explosivo"])
    async def coco(self, ctx, aposta: float = None):
        if aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!coco <valor>`")
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
                return await ctx.send(f"🚫 Limite de aposta para **{cargo}** é de **{get_limite(cargo)} C**!")

            db.update_value(user['row'], 3, round(saldo - aposta, 2))
            self.coco_active = True
            self.coco_aposta = aposta
            self.coco_players = [ctx.author]

            view = CocoEntrarView(self, aposta)
            embed = disnake.Embed(
                title="🚨 ROLETA DO COCO EXPLOSIVO! 🚨",
                description=f"{ctx.author.mention} abriu uma roda mortal!\n\n💰 **Entrada:** `{aposta:.2f} C`\n⏳ **60 segundos** para entrar!\n\nClique no botão abaixo para participar.",
                color=disnake.Color.dark_red()
            )
            await ctx.send(embed=embed, view=view)
            await asyncio.sleep(60)

            # Disable the button after time
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

            await ctx.send(f"🔥 **A RODA FECHOU!** {total_jogadores} macacos corajosos — pote de **{pote_bruto:.2f} C**!\nQue os jogos comecem...")
            self.coco_active = False

            rodada = 1
            while len(jogadores) > 1:
                await asyncio.sleep(2.5)
                await ctx.send("🥥 *O coco está passando de mão em mão...*")
                await asyncio.sleep(2)
                await ctx.send("⏱️ *Tic... Tac... Tic...*")
                await asyncio.sleep(2.5)

                eliminado = random.choice(jogadores)
                jogadores.remove(eliminado)
                await ctx.send(f"💥 **KABOOOM!** O coco explodiu na cara de {eliminado.mention}! Fora da roda.")

                if rodada == 1 and total_jogadores >= 4:
                    m_db = db.get_user_data(str(eliminado.id))
                    if m_db: save_achievement(m_db, "ima_desgraca")
                rodada += 1

            vencedor = jogadores[0]
            v_db = db.get_user_data(str(vencedor.id))
            if not v_db:
                return await ctx.send("❌ Erro ao encontrar vencedor no banco de dados!")

            lucro = round(pote_bruto - self.coco_aposta, 2)
            db.update_value(v_db['row'], 3, round(db.parse_float(v_db['data'][2]) + pote_bruto, 2))
            await ctx.send(f"🏆 **FIM DE JOGO!** {vencedor.mention} sobreviveu e faturou **{lucro:.2f} C** de lucro!")

            if total_jogadores >= 5:
                save_achievement(v_db, "veterano_coco")

            self.coco_players = []
            self.coco_aposta = 0.0

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

        embed = disnake.Embed(title="🎰 AK-BET JOGOS", description="Transforme seus conguitos em fortuna!", color=disnake.Color.purple())
        embed.add_field(name="🎮 Comandos Disponíveis", inline=False, value=(
            "🚀 **!crash <valor>** - Foguetinho! Suba no cipó e clique em **Sacar**.\n"
            "🃏 **!carta @user <valor>** - Duelo de Cartas (aceite via botão).\n"
            "♠️ **!21 <valor>** - Blackjack contra o dealer (lobby com botões).\n"
            "🎰 **!cassino <valor>** - Caça-níquel clássico.\n"
            "🥥 **!coco <valor>** - Roleta do Coco Explosivo (entre via botão).\n"
            "🐒 **!corrida <animal> <valor>** - Aposte no Macaquinho, Gorila ou Orangutango.\n"
            "🦁 **!bicho <animal> <valor>** - Aposte em: Leao, Cobra, Jacare, Arara, Elefante.\n"
            "💣 **!minas <1-5> <valor>** - Sobreviva ao campo minado.\n"
            "⚔️ **!briga @user <valor>** - PvP (aceite via botão)!\n"
            "🎫 **!loteria** - Bilhete por 500 C para concorrer ao pote.\n"
            "💰 **!pote** - Veja o pote atual da loteria.\n"
            "🎰 **!roleta** - Mesa de Roleta Multiplayer! (30s)\n"
            "🪙 **!apostar <valor> <opção>** - Entre na rodada da Roleta.\n"
            "  ↳ *Cores/Par/Ímpar pagam **2x** | Números exatos pagam **36x**!*\n"
            "⚽ **!futebol** - Ver os jogos atuais.\n"
            "  ↳ Use `!palpite <ID> <casa/empate/fora> <valor>` para apostar!\n"
            "  ↳ Use `!palpites` para ver seus bilhetes ativos."
        ))
        embed.set_footer(text="Todos os jogos agora com interação por botões! 🐒")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Eventos(bot))