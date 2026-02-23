import disnake
from disnake.ext import commands
import database as db
import random
import asyncio

def get_limite(cargo):
    """Limites da V4.4 para os jogos"""
    limites = {
        "Lêmure": 250, "Macaquinho": 800, "Babuíno": 2000, "Chimpanzé": 6000,
        "Orangutango": 15000, "Gorila": 45000, "Ancestral": 150000, "Rei Símio": 1500000
    }
    return limites.get(cargo, 250)

def save_achievement(user_data, slug):
    conquistas_atuais = str(user_data['data'][9]) if len(user_data['data']) > 9 else ""
    lista = [c.strip() for c in conquistas_atuais.split(',') if c.strip()]
    if slug not in lista:
        lista.append(slug)
        db.update_value(user_data['row'], 10, ", ".join(lista))

class Eventos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = 757752617722970243
        
        # Variáveis Globais dos Eventos
        self.loteria_participantes = []
        self.loteria_pote = 0.0
        
        self.coco_active = False
        self.coco_players = []
        self.coco_aposta = 0.0

    async def cog_before_invoke(self, ctx):
        if ctx.command.name in ['loteria', 'bilhete', 'loto', 'sortear_loteria', 'pote', 'premio', 'acumulado']:
            if ctx.channel.name not in ['🐒・conguitos', '🎰・akbet']:
                await ctx.send(f"⚠️ {ctx.author.mention}, vá à loteria no canal #🐒・conguitos ou #🎰・akbet.")
                raise commands.CommandError("Canal incorreto para loteria.")
            return

        if ctx.channel.name != '🎰・akbet' and ctx.command.name != 'jogos':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, macaco esperto joga no lugar certo! Vai para o canal {mencao}.")
            raise commands.CommandError("Canal de apostas incorreto.")

    # --- 🎫 SISTEMA DE LOTERIA ---
    @commands.command(aliases=["premio", "acumulado"])
    async def pote(self, ctx):
        if self.loteria_pote == 0.0:
            return await ctx.send(f"🎫 {ctx.author.mention}, o pote da loteria está zerado! Seja o primeiro a comprar usando `!loteria` (500 C).")
        
        qtd_participantes = len(self.loteria_participantes)
        embed = disnake.Embed(
            title="💰 Pote da Loteria da Selva",
            description=f"O prêmio acumulado atual é de **{self.loteria_pote:.2f} Conguitos**!\n\n👥 **Bilhetes vendidos:** `{qtd_participantes}`",
            color=disnake.Color.gold()
        )
        embed.set_footer(text="Garanta sua chance digitando !loteria")
        await ctx.send(embed=embed)

    @commands.command(aliases=["bilhete", "loto"])
    async def loteria(self, ctx):
        custo_bilhete = 500.0
        user_id = ctx.author.id

        if user_id in self.loteria_participantes:
            return await ctx.send(f"🎫 {ctx.author.mention}, você já tem um bilhete! O pote atual está em **{self.loteria_pote:.2f} C**.")

        user = db.get_user_data(str(user_id))
        if not user or float(user['data'][2]) < custo_bilhete:
            return await ctx.send(f"❌ {ctx.author.mention}, você precisa de **{custo_bilhete:.2f} C** para comprar um bilhete!")

        db.update_value(user['row'], 3, round(float(user['data'][2]) - custo_bilhete, 2))
        self.loteria_participantes.append(user_id)
        self.loteria_pote += custo_bilhete
        
        await ctx.send(f"🎫 **BILHETE COMPRADO!** {ctx.author.mention} entrou na loteria.\n💰 O prêmio acumulado agora é de **{self.loteria_pote:.2f} Conguitos**!")

    @commands.command()
    async def sortear_loteria(self, ctx):
        if ctx.author.id != self.owner_id: 
            return await ctx.send("❌ Apenas o Rei da Selva pode girar o globo da loteria!")
            
        if not self.loteria_participantes: 
            return await ctx.send("❌ Nenhum bilhete foi vendido para esta rodada.")

        await ctx.send("🎰 **O GLOBO ESTÁ GIRANDO... QUEM SERÁ O NOVO MILIONÁRIO?**")
        await asyncio.sleep(3)

        ganhador_id = random.choice(self.loteria_participantes)
        ganhador = await self.bot.fetch_user(ganhador_id)
        premio = round(self.loteria_pote, 2)

        user_db = db.get_user_data(str(ganhador_id))
        db.update_value(user_db['row'], 3, round(float(user_db['data'][2]) + premio, 2))

        embed = disnake.Embed(
            title="🎉 TEMOS UM VENCEDOR! 🎉",
            description=f"O grande sortudo da rodada é **{ganhador.mention}**!\nEle acaba de faturar **{premio:.2f} Conguitos** (Livre de taxas)!",
            color=disnake.Color.gold()
        )
        embed.set_footer(text="A próxima rodada começa agora! Compre seu bilhete.")
        await ctx.send(embed=embed)

        self.loteria_participantes = []
        self.loteria_pote = 0.0

    # --- 🥥 MINIGAME: COCO EXPLOSIVO ---
    @commands.command(aliases=["roleta_coco", "coco_explosivo"])
    async def coco(self, ctx, aposta: float = None):
        if aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!coco <valor>`")

        if self.coco_active: 
            return await ctx.send(f"⚠️ {ctx.author.mention}, já existe uma roda aberta! Digite `!entrar_coco`.")
            
        if aposta <= 0: return await ctx.send("❌ Aposta inválida!")
        aposta = round(aposta, 2)

        user = db.get_user_data(str(ctx.author.id))
        if not user or float(user['data'][2]) < aposta: 
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        cargo = user['data'][3]
        limite = get_limite(cargo)
        if aposta > limite: 
            return await ctx.send(f"🚫 Limite de aposta para **{cargo}** é de **{limite} C**!")

        db.update_value(user['row'], 3, round(float(user['data'][2]) - aposta, 2))
        self.coco_active = True
        self.coco_aposta = aposta
        self.coco_players = [ctx.author]

        embed = disnake.Embed(
            title="🚨 ROLETA DO COCO EXPLOSIVO! 🚨",
            description=f"{ctx.author.mention} abriu uma roda mortal!\n\n💰 **Entrada:** `{aposta:.2f} C`\n⏳ **Tempo:** 60 segundos para entrar!\n\nDigite **`!entrar_coco`** para participar.",
            color=disnake.Color.dark_red()
        )
        await ctx.send(embed=embed)

        await asyncio.sleep(60)

        if len(self.coco_players) < 2:
            user_refund = db.get_user_data(str(ctx.author.id))
            db.update_value(user_refund['row'], 3, round(float(user_refund['data'][2]) + aposta, 2))
            self.coco_active = False
            self.coco_players = []
            self.coco_aposta = 0.0
            return await ctx.send(f"🥥 Ninguém teve coragem. O jogo foi cancelado e o dinheiro devolvido para {ctx.author.mention}.")

        jogadores = self.coco_players.copy()
        total_jogadores = len(jogadores)
        pote_bruto = round(self.coco_aposta * total_jogadores, 2)

        await ctx.send(f"🔥 **A RODA FECHOU!** Temos {total_jogadores} macacos corajosos e um pote de **{pote_bruto:.2f} Conguitos**.\nQue os jogos comecem...")
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

            await ctx.send(f"💥 **KABOOOM!** O coco explodiu na cara do {eliminado.mention}! Fora da roda.")

            if rodada == 1 and total_jogadores >= 4:
                m_db = db.get_user_data(str(eliminado.id))
                if m_db: save_achievement(m_db, "ima_desgraca")
            rodada += 1

        vencedor = jogadores[0]
        v_db = db.get_user_data(str(vencedor.id))
        
        lucro_liquido = round(pote_bruto - self.coco_aposta, 2)

        # Repassa o valor total do pote sem descontos
        db.update_value(v_db['row'], 3, round(float(v_db['data'][2]) + pote_bruto, 2))

        await asyncio.sleep(1)
        await ctx.send(f"🏆 **FIM DE JOGO!** {vencedor.mention} foi o único que não perdeu a cabeça e faturou **{lucro_liquido:.2f} C** de lucro (Isento de taxas)!")

        if total_jogadores >= 5:
            save_achievement(v_db, "veterano_coco")
            
        self.coco_players = []
        self.coco_aposta = 0.0

    @commands.command(name="entrar_coco")
    async def entrar_coco(self, ctx):
        if not self.coco_active: 
            return await ctx.send(f"⚠️ {ctx.author.mention}, não há roda de coco aberta! Crie uma com `!coco <valor>`.")
            
        if ctx.author in self.coco_players: 
            return await ctx.send(f"🐒 {ctx.author.mention}, você já está na roda!")

        user = db.get_user_data(str(ctx.author.id))
        if not user or float(user['data'][2]) < self.coco_aposta: 
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        cargo = user['data'][3]
        limite = get_limite(cargo)
        if self.coco_aposta > limite: 
            return await ctx.send(f"🚫 Limite de aposta para **{cargo}** é de **{limite} C**! Você não pode entrar nesta roda.")

        db.update_value(user['row'], 3, round(float(user['data'][2]) - self.coco_aposta, 2))
        self.coco_players.append(ctx.author)
        pote_atual = round(len(self.coco_players) * self.coco_aposta, 2)
        
        await ctx.send(f"🥥 {ctx.author.mention} entrou na roda da morte! (Pote atual: **{pote_atual:.2f} C**)")

    # --- 📜 MENU GERAL DE JOGOS ---
    @commands.command()
    async def jogos(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            return await ctx.send(f"⚠️ {ctx.author.mention}, apostas e jogos são permitidos apenas no canal {mencao}!")

        embed = disnake.Embed(
            title="🎰 AK-BET JOGOS",
            description="Transforme seus conguitos em fortuna!",
            color=disnake.Color.purple()
        )
        embed.add_field(
            name="🎮 Comandos Disponíveis",
            value=(
                "🚀 **!crash <valor>** - Foguetinho! Suba no cipó e digite `parar`.\n"
                "🃏 **!carta @user <valor>** - Desafie alguém para um duelo de Cartas.\n"
                "♠️ **!21 <valor>** - Jogue Blackjack contra o dealer.\n"
                "🎰 **!cassino <valor>** - Caça-níquel clássico.\n"
                "🥥 **!coco <valor>** - Crie uma Roleta do Coco Explosivo.\n"
                "🏃 **!entrar_coco** - Entre na roda antes do tempo acabar!\n"
                "🐒 **!corrida <animal> <valor>** - Aposte no Macaquinho, Gorila ou Orangutango.\n"
                "🦁 **!bicho <animal> <valor>** - Aposte em: Leao, Cobra, Jacare, Arara, Elefante.\n"
                "💣 **!minas <1 a 5> <valor>** - Sobreviva ao campo minado.\n"
                "⚔️ **!briga @user <valor>** - Desafie alguém para PvP!\n"
                "🎫 **!loteria** - Compre um bilhete por 500 C para concorrer ao pote acumulado.\n"
                "💰 **!pote** - Veja o valor atual do pote da loteria.\n"
                "🎰 **!roleta** - Abre a mesa de Roleta Multiplayer! (30s de apostas)\n"
                "🪙 **!apostar <valor> <opção>** - Entre na rodada atual da Roleta.\n"
                "  ↳ *Cores ou Par/Ímpar pagam **2x** | Números exatos pagam **36x**!* 🎯\n"
            ),
            inline=False
        )
        embed.set_footer(text="Aproveite os jogos 100% isentos de impostos! 🐒")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Eventos(bot))