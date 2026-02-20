import disnake
from disnake.ext import commands
import database as db
import random
import asyncio
import time

class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = 757752617722970243
        # Memória temporária para a loteria
        self.loteria_participantes = []
        self.loteria_pote = 0

        # --- AJUSTE: Inicializa a memória global completa aqui também ---
        if not hasattr(bot, 'tracker_emblemas'):
            bot.tracker_emblemas = {
                'trabalhos': {},           
                'roubos_sucesso': {},      
                'roubos_falha': {},        
                'esquadrao_suicida': set(),
                'palhaco': set(),          
                'filho_da_sorte': set(),
                'escorregou_banana': set(),
                'pix_irritante': set(),
                'casca_grossa': set(),
                'briga_de_bar': set()
            }

    async def cog_before_invoke(self, ctx):
        """Restringe comandos deste Cog, com exceção do banco e loteria."""
        # Permite investir e loteria nos canais de economia e apostas
        if ctx.command.name in ['investir', 'banco', 'depositar', 'loteria', 'bilhete', 'loto', 'sortear_loteria', 'pote', 'premio', 'acumulado']:
            if ctx.channel.name not in ['🐒・conguitos', '🎰・akbet']:
                await ctx.send(f"⚠️ {ctx.author.mention}, vá ao banco/loteria no canal #🐒・conguitos ou #🎰・akbet.")
                raise commands.CommandError("Canal incorreto para banco/loteria.")
            return

        # Restringe o resto (jogos reais) apenas ao canal akbet
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            
            await ctx.send(f"🐒 Ei {ctx.author.mention}, macaco esperto joga no lugar certo! Vai para o canal {mencao}.")
            raise commands.CommandError("Canal de apostas incorreto.")

    # --- NOVO: COMANDO PARA VER O POTE ---
    @commands.command(aliases=["premio", "acumulado"])
    async def pote(self, ctx):
        """Mostra o valor total acumulado na loteria e a quantidade de participantes."""
        if self.loteria_pote == 0:
            return await ctx.send(f"🎫 {ctx.author.mention}, o pote da loteria está zerado! Seja o primeiro a comprar usando `!loteria` (500 C).")
        
        qtd_participantes = len(self.loteria_participantes)
        embed = disnake.Embed(
            title="💰 Pote da Loteria da Selva",
            description=f"O prêmio acumulado atual é de **{self.loteria_pote} Conguitos**!\n\n👥 **Bilhetes vendidos:** `{qtd_participantes}`",
            color=disnake.Color.gold()
        )
        embed.set_footer(text="Garanta sua chance digitando !loteria")
        await ctx.send(embed=embed)

    # --- SISTEMA DE LOTERIA DA SELVA ---
    @commands.command(aliases=["bilhete", "loto"])
    async def loteria(self, ctx):
        """Compra um bilhete para a loteria atual ou vê o pote."""
        custo_bilhete = 500
        user_id = ctx.author.id

        # Se o usuário já tiver comprado
        if user_id in self.loteria_participantes:
            return await ctx.send(f"🎫 {ctx.author.mention}, você já tem um bilhete! O pote atual está em **{self.loteria_pote} C**.")

        user = db.get_user_data(str(user_id))
        if not user or int(user['data'][2]) < custo_bilhete:
            return await ctx.send(f"❌ {ctx.author.mention}, você precisa de **{custo_bilhete} C** para comprar um bilhete!")

        # Processa a compra
        db.update_value(user['row'], 3, int(user['data'][2]) - custo_bilhete)
        self.loteria_participantes.append(user_id)
        self.loteria_pote += custo_bilhete

        await ctx.send(f"🎫 **BILHETE COMPRADO!** {ctx.author.mention} entrou na loteria.\n💰 O prêmio acumulado agora é de **{self.loteria_pote} Conguitos**!")

    @commands.command()
    async def sortear_loteria(self, ctx):
        """Sorteia o prêmio acumulado entre os participantes. (Apenas Dono)"""
        if ctx.author.id != self.owner_id:
            return await ctx.send("❌ Apenas o Rei da Selva pode girar o globo da loteria!")

        if not self.loteria_participantes:
            return await ctx.send("❌ Nenhum bilhete foi vendido para esta rodada.")

        await ctx.send("🎰 **O GLOBO ESTÁ GIRANDO... QUEM SERÁ O NOVO MILIONÁRIO?**")
        await asyncio.sleep(3)

        ganhador_id = random.choice(self.loteria_participantes)
        ganhador = await self.bot.fetch_user(ganhador_id)
        premio = self.loteria_pote

        user_db = db.get_user_data(str(ganhador_id))
        db.update_value(user_db['row'], 3, int(user_db['data'][2]) + premio)

        embed = disnake.Embed(
            title="🎉 TEMOS UM VENCEDOR! 🎉",
            description=f"O grande sortudo da rodada é **{ganhador.mention}**!\nEle acaba de faturar **{premio} Conguitos**!",
            color=disnake.Color.gold()
        )
        embed.set_footer(text="A próxima rodada começa agora! Compre seu bilhete.")
        await ctx.send(embed=embed)

        # Reseta a loteria para a próxima rodada
        self.loteria_participantes = []
        self.loteria_pote = 0

    # --- SISTEMA DE BANCO DUPLO (FIXO e CRIPTO) ---
    @commands.command(aliases=["banco", "depositar"])
    async def investir(self, ctx, tipo: str = None, valor: int = 0):
        """Sistema de investimentos: Seguro (Fixo) ou Volátil (Cripto)."""
        if not tipo or tipo.lower() not in ['cripto', 'fixo'] or valor <= 0:
            embed = disnake.Embed(title="🏦 Banco da Selva AKTrovão", color=disnake.Color.green())
            embed.add_field(name="📈 `!investir cripto <valor>`", value="Risco alto! Rende de **-25% a +25%** em 1 minuto.\n*Sem limite de valor.*", inline=False)
            embed.add_field(name="🏛️ `!investir fixo <valor>`", value="Seguro! Rende **+10%** na hora.\n*Limite: 5.000 C por dia.*", inline=False)
            return await ctx.send(embed=embed)

        user = db.get_user_data(str(ctx.author.id))
        if not user or int(user['data'][2]) < valor:
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        tipo = tipo.lower()
        agora = time.time()

        if tipo == 'fixo':
            limite = 5000
            if valor > limite:
                return await ctx.send(f"❌ O banco só aceita até **{limite} C** na Renda Fixa! Para investir mais, use a Cripto.")

            ultimo_invest = float(user['data'][7]) if len(user['data']) > 7 and user['data'][7] else 0
            if agora - ultimo_invest < 86400: 
                restante_horas = int((86400 - (agora - ultimo_invest)) / 3600)
                restante_min = int(((86400 - (agora - ultimo_invest)) % 3600) / 60)
                return await ctx.send(f"⏳ {ctx.author.mention}, seu limite diário esgotou. Volte em **{restante_horas}h {restante_min}m** para a Renda Fixa.")

            lucro = int(valor * 0.10)
            db.update_value(user['row'], 3, int(user['data'][2]) + lucro)
            db.update_value(user['row'], 8, agora) 
            
            await ctx.send(f"🏛️ **RENDA FIXA!** Seu rendimento de 10% foi aplicado na hora. Você ganhou **+{lucro} C** limpos, {ctx.author.mention}!")

        elif tipo == 'cripto':
            db.update_value(user['row'], 3, int(user['data'][2]) - valor)
            await ctx.send(f"📈 {ctx.author.mention} comprou **{valor} C** em MacacoCoin (MC). O mercado fechará em 1 minuto...")

            await asyncio.sleep(60)

            user_atual = db.get_user_data(str(ctx.author.id))
            
            variacao = random.uniform(-0.25, 0.25)
            retorno = int(valor * (1 + variacao))
            lucro = retorno - valor

            db.update_value(user_atual['row'], 3, int(user_atual['data'][2]) + retorno)
            
            if lucro > 0:
                await ctx.send(f"🚀 **ALTA NO MERCADO!** A MacacoCoin valorizou! {ctx.author.mention} recebeu **{retorno} C** (Lucro: `+{lucro} C`).")
            else:
                await ctx.send(f"📉 **CRASH NO MERCADO!** A MacacoCoin desabou... {ctx.author.mention} recebeu apenas **{retorno} C** (Prejuízo: `{lucro} C`).")

    # --- 1. CORRIDA DE MACACOS ---
    @commands.command(name="corrida")
    async def corrida_macaco(self, ctx, escolha: str, aposta: int):
        opcoes = {
            "macaquinho": "🐒",
            "gorila": "🦍",
            "orangutango": "🦧"
        }
        
        escolha = escolha.lower()
        if escolha not in opcoes:
            return await ctx.send(f"❌ {ctx.author.mention}, escolha um competidor válido: `macaquinho`, `gorila` ou `orangutango`.")

        user = db.get_user_data(str(ctx.author.id))
        if not user or aposta > int(user['data'][2]) or aposta <= 0:
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        macacos_lista = list(opcoes.values())
        nomes_lista = list(opcoes.keys())
        pistas = [0, 0, 0]
        chegada = 10
        
        msg = await ctx.send(f"🏁 **A CORRIDA COMEÇOU!** {ctx.author.mention} apostou no **{escolha.capitalize()}**!\n\n" + 
                             "\n".join([f"{macacos_lista[i]} 🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦 🏁" for i in range(3)]))

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
                pista_str = "🟩" * progresso + "🟦" * (chegada - progresso)
                frame.append(f"{macacos_lista[i]} {pista_str} 🏁")
            
            await msg.edit(content=f"🏁 **A CORRIDA ESTÁ QUENTE!**\n\n" + "\n".join(frame))

        nome_vencedor = nomes_lista[vencedor_idx]
        
        if escolha == nome_vencedor:
            ganho = aposta * 3
            res_msg = f"🏆 **VITÓRIA!** O {nome_vencedor.capitalize()} cruzou primeiro! Você ganhou **{ganho} conguitos**."
        else:
            ganho = -aposta
            res_msg = f"💀 **DERROTA!** O {nome_vencedor.capitalize()} venceu a corrida. Você perdeu **{aposta} conguitos**."

        db.update_value(user['row'], 3, int(user['data'][2]) + ganho)
        await ctx.send(f"{ctx.author.mention} {res_msg}")

    # --- 2. JOGO DO BICHO ---
    @commands.command(name="bicho")
    async def jogo_bicho(self, ctx, bicho: str, aposta: int):
        bichos = ["leao", "cobra", "jacare", "arara", "elefante"]
        bicho = bicho.lower()
        if bicho not in bichos:
            return await ctx.send(f"❌ {ctx.author.mention}, escolha entre: `leao, cobra, jacare, arara, elefante`")

        user = db.get_user_data(str(ctx.author.id))
        if not user or aposta > int(user['data'][2]) or aposta <= 0:
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        resultado = random.choice(bichos)
        msg = await ctx.send(f"🎰 Sorteando... {ctx.author.mention} apostou no **{bicho.upper()}**!")
        await asyncio.sleep(2)

        ganho = aposta * 5 if bicho == resultado else -aposta
        txt = f"🎉 DEU **{resultado.upper()}**! Você ganhou **{ganho} C**!" if ganho > 0 else f"💀 DEU **{resultado.upper()}**! Perdeu **{aposta} C**."
        
        await msg.edit(content=f"{ctx.author.mention} {txt}")
        db.update_value(user['row'], 3, int(user['data'][2]) + ganho)

    # --- 3. CAMPO MINADO ---
    @commands.command(name="minas")
    async def campo_minado(self, ctx, bombas: int, aposta: int):
        if not (1 <= bombas <= 5):
            return await ctx.send(f"❌ {ctx.author.mention}, escolha entre 1 e 5 bombas.")

        user = db.get_user_data(str(ctx.author.id))
        if not user or aposta > int(user['data'][2]) or aposta <= 0:
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        await ctx.send(f"💣 {ctx.author.mention} entrando no campo com {bombas} bombas...")
        await asyncio.sleep(1.5)

        # Lógica de vitória/derrota
        if random.randint(1, 10) > (bombas * 1.5):
            if bombas == 5:
                # --- TRACKER: Esquadrão Suicida ---
                if 'esquadrao_suicida' not in self.bot.tracker_emblemas:
                    self.bot.tracker_emblemas['esquadrao_suicida'] = set()
                self.bot.tracker_emblemas['esquadrao_suicida'].add(str(ctx.author.id))
                
            mult = 1.5 + (bombas * 0.5)
            ganho = int(aposta * mult)
            status = f"🚩 **LIMPO!** {ctx.author.mention} ganhou **{ganho} conguitos**! ({mult}x)"
        else:
            ganho = -aposta
            status = f"💥 **BOOOOM!** {ctx.author.mention} pisou em uma mina e perdeu **{aposta} C**."
            
            # --- TRACKER SECRETO: Escorregou na Banana ---
            if bombas == 1:
                if 'escorregou_banana' not in self.bot.tracker_emblemas:
                    self.bot.tracker_emblemas['escorregou_banana'] = set()
                self.bot.tracker_emblemas['escorregou_banana'].add(str(ctx.author.id))

        db.update_value(user['row'], 3, int(user['data'][2]) + ganho)
        await ctx.send(status)

    # --- 4. BRIGA DE MACACO (PvP) ---
    @commands.command(aliases=["briga", "brigar", "luta", "lutar", "x1"])
    async def briga_macaco(self, ctx, vitima: disnake.Member, aposta: int):
        if vitima.id == ctx.author.id: return await ctx.send(f"🐒 {ctx.author.mention}, não brigue consigo mesmo!")
        
        ladrao = db.get_user_data(str(ctx.author.id))
        alvo = db.get_user_data(str(vitima.id))

        if not ladrao or not alvo or int(alvo['data'][2]) < aposta or int(ladrao['data'][2]) < aposta:
            return await ctx.send(f"❌ {ctx.author.mention}, alguém não tem saldo para essa briga!")

        # --- TRACKER SECRETO: Briga de Bar ---
        if aposta == 1:
            if 'briga_de_bar' not in self.bot.tracker_emblemas:
                self.bot.tracker_emblemas['briga_de_bar'] = set()
            self.bot.tracker_emblemas['briga_de_bar'].add(str(ctx.author.id))

        await ctx.send(f"🥊 {vitima.mention}, {ctx.author.mention} te desafiou para uma briga por **{aposta} C**! Digite `aceitar` para lutar!")

        def check(m): return m.author == vitima and m.content.lower() == 'aceitar' and m.channel == ctx.channel
        try:
            await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send(f"⏱️ {vitima.mention} amarelou e fugiu da briga!")

        vencedor = random.choice([ctx.author, vitima])
        perdedor = vitima if vencedor == ctx.author else ctx.author
        
        v_db = db.get_user_data(str(vencedor.id))
        p_db = db.get_user_data(str(perdedor.id))

        db.update_value(v_db['row'], 3, int(v_db['data'][2]) + aposta)
        db.update_value(p_db['row'], 3, int(p_db['data'][2]) - aposta)
        await ctx.send(f"🏆 **{vencedor.mention}** nocauteou {perdedor.mention} e levou o pote de **{aposta} C**!")

    # --- 5. MOEDA E CASSINO ---
    @commands.command(name="moeda", aliases=["cara_coroa", "coinflip", "cf"])
    async def cara_coroa(self, ctx, lado: str, aposta: int):
        user = db.get_user_data(str(ctx.author.id))
        
        # Verificações básicas
        if not user or aposta > int(user['data'][2]) or aposta <= 0:
            return await ctx.send(f"⚠️ {ctx.author.mention}, você não tem Conguitos suficientes ou a aposta é inválida!")

        lado = lado.lower()
        if lado not in ["cara", "coroa"]:
            return await ctx.send(f"⚠️ {ctx.author.mention}, escolha entre `cara` ou `coroa`!")

        res = random.choice(["cara", "coroa"])
        venceu = (lado == res)
        
        if venceu:
            ganho = aposta  
            msg = f"✅ **Ganhou, +{aposta} C!**"
        else:
            ganho = -aposta
            msg = f"❌ **Perdeu, -{aposta} C!**"

        novo_saldo = int(user['data'][2]) + ganho
        db.update_value(user['row'], 3, novo_saldo)

        await ctx.send(f"🪙 {ctx.author.mention} | Caiu **{res.upper()}**! {msg}")

    @commands.command(name="cassino")
    async def cassino_slots(self, ctx, aposta: int):
        user = db.get_user_data(str(ctx.author.id))
        if not user or aposta > int(user['data'][2]) or aposta <= 0: 
            return await ctx.send(f"⚠️ {ctx.author.mention}, saldo insuficiente ou aposta inválida!")

        emojis = ["🍌", "🐒", "⚡", "🥥", "💎", "🦍"]
        res = [random.choice(emojis) for _ in range(3)]
        
        # Lógica de ganhos
        if res[0] == res[1] == res[2]:
            ganho = aposta * 10
            status_msg = f"🎰 **JACKPOT!** 🎰\nVocê ganhou **+{ganho} C**"
            
            # --- TRACKER SECRETO: Filho da Sorte ---
            if 'filho_da_sorte' not in self.bot.tracker_emblemas:
                self.bot.tracker_emblemas['filho_da_sorte'] = set()
            self.bot.tracker_emblemas['filho_da_sorte'].add(str(ctx.author.id))
            
        elif res[0] == res[1] or res[1] == res[2] or res[0] == res[2]:
            ganho = aposta * 2
            status_msg = f"Você ganhou **+{ganho} C**"
        else:
            ganho = -aposta
            status_msg = f"Você perdeu **{ganho} C**" 

        # Atualiza no banco de dados
        db.update_value(user['row'], 3, int(user['data'][2]) + ganho)

        # Mensagem formatada
        await ctx.send(
            f"🎰 **CASSINO AKTrovão** 🎰\n"
            f"**[ {res[0]} | {res[1]} | {res[2]} ]**\n"
            f"{ctx.author.mention}, {status_msg}!"
        )

def setup(bot):
    bot.add_cog(Games(bot))