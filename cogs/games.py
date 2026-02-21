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
        
        self.loteria_participantes = []
        self.loteria_pote = 0
        self.coco_active = False
        self.coco_players = []
        self.coco_aposta = 0

        # Mantido para as diárias (trabalho/roubo) que resetam no dia
        if not hasattr(bot, 'tracker_emblemas'):
            bot.tracker_emblemas = {
                'trabalhos': {}, 'roubos_sucesso': {}, 'roubos_falha': {},
                'esquadrao_suicida': set(), 'palhaco': set(), 'filho_da_sorte': set(),
                'escorregou_banana': set(), 'pix_irritante': set(), 'casca_grossa': set(),
                'briga_de_bar': set(), 'ima_desgraca': set(), 'veterano_coco': set(),
                'queda_livre': set(), 'astronauta_cipo': set() 
            }

    async def save_achievement(self, user_data, slug):
        """Função auxiliar para salvar conquistas na Coluna J (Índice 9) da planilha."""
        conquistas_atuais = str(user_data['data'][9]) if len(user_data['data']) > 9 else ""
        lista = [c.strip() for c in conquistas_atuais.split(',') if c.strip()]

        if slug not in lista:
            lista.append(slug)
            db.update_value(user_data['row'], 10, ", ".join(lista))
            return True
        return False

    async def cog_before_invoke(self, ctx):
        if ctx.command.name in ['loteria', 'bilhete', 'loto', 'sortear_loteria', 'pote', 'premio', 'acumulado']:
            if ctx.channel.name not in ['🐒・conguitos', '🎰・akbet']:
                await ctx.send(f"⚠️ {ctx.author.mention}, vá à loteria no canal #🐒・conguitos ou #🎰・akbet.")
                raise commands.CommandError("Canal incorreto para loteria.")
            return

        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, macaco esperto joga no lugar certo! Vai para o canal {mencao}.")
            raise commands.CommandError("Canal de apostas incorreto.")

    # --- NOVO MINIGAME: MAIOR CARTA (DUELO PVP) ---
    @commands.command(aliases=["cartas", "duelo_carta", "draw"])
    async def carta(self, ctx, oponente: disnake.Member, aposta: int):
        """Desafia alguém para um duelo de cartas. Quem tirar a maior vence!"""
        if oponente.id == ctx.author.id: 
            return await ctx.send(f"🃏 {ctx.author.mention}, você não pode jogar cartas contra o espelho!")
        
        if aposta <= 0:
            return await ctx.send(f"❌ {ctx.author.mention}, a aposta deve ser maior que zero!")

        desafiante_db = db.get_user_data(str(ctx.author.id))
        oponente_db = db.get_user_data(str(oponente.id))

        if not desafiante_db or not oponente_db or int(oponente_db['data'][2]) < aposta or int(desafiante_db['data'][2]) < aposta: 
            return await ctx.send(f"❌ {ctx.author.mention}, alguém na mesa não tem saldo para cobrir essa aposta!")

        await ctx.send(f"🃏 {oponente.mention}, você foi desafiado por {ctx.author.mention} para um Duelo de Cartas valendo **{aposta} C**! Digite `comprar` no chat para aceitar e sacar sua carta!")

        def check(m): return m.author == oponente and m.content.lower() == 'comprar' and m.channel == ctx.channel
        try:
            await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send(f"⏱️ {oponente.mention} demorou demais para comprar a carta. O duelo foi cancelado!")

        valores = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        naipes = ["♠️", "♥️", "♦️", "♣️"]
        
        carta_desafiante_valor = random.choice(valores)
        carta_oponente_valor = random.choice(valores)
        
        carta_desafiante_naipe = random.choice(naipes)
        carta_oponente_naipe = random.choice(naipes)
        while carta_desafiante_valor == carta_oponente_valor and carta_desafiante_naipe == carta_oponente_naipe:
            carta_oponente_naipe = random.choice(naipes)

        peso_desafiante = valores.index(carta_desafiante_valor)
        peso_oponente = valores.index(carta_oponente_valor)

        embed = disnake.Embed(title="🃏 DUELO DE CARTAS 🃏", color=disnake.Color.dark_theme())
        embed.add_field(name=f"Sacado por {ctx.author.display_name}:", value=f"**{carta_desafiante_valor}** {carta_desafiante_naipe}", inline=True)
        embed.add_field(name=f"Sacado por {oponente.display_name}:", value=f"**{carta_oponente_valor}** {carta_oponente_naipe}", inline=True)

        if peso_desafiante > peso_oponente:
            vencedor = ctx.author
            perdedor = oponente
            resultado_txt = f"🏆 A carta de **{vencedor.mention}** foi maior! Faturou o pote de **{aposta} C**."
        elif peso_oponente > peso_desafiante:
            vencedor = oponente
            perdedor = ctx.author
            resultado_txt = f"🏆 A carta de **{vencedor.mention}** foi maior! Faturou o pote de **{aposta} C**."
        else:
            db.update_value(desafiante_db['row'], 3, int(desafiante_db['data'][2]) - aposta)
            db.update_value(oponente_db['row'], 3, int(oponente_db['data'][2]) - aposta)
            embed.description = f"🤝 **EMPATE!** Vossas cartas têm o mesmo peso.\nAmbos perdem a aposta de **{aposta} C** para o Cassino!"
            return await ctx.send(embed=embed)

        v_db = db.get_user_data(str(vencedor.id))
        p_db = db.get_user_data(str(perdedor.id))
        db.update_value(v_db['row'], 3, int(v_db['data'][2]) + aposta)
        db.update_value(p_db['row'], 3, int(p_db['data'][2]) - aposta)

        embed.description = resultado_txt
        await ctx.send(embed=embed)

    # --- NOVO MINIGAME: CRASH DO CIPÓ (FOGUETINHO) ---
    @commands.command(aliases=["cipo", "foguetinho"])
    async def crash(self, ctx, aposta: int):
        if aposta <= 0:
            return await ctx.send(f"❌ {ctx.author.mention}, a aposta deve ser maior que zero!")

        user = db.get_user_data(str(ctx.author.id))
        if not user or int(user['data'][2]) < aposta:
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        db.update_value(user['row'], 3, int(user['data'][2]) - aposta)

        chance = random.random()
        if chance < 0.05: crash_point = 1.0 
        elif chance < 0.65: crash_point = random.uniform(1.1, 2.0)
        elif chance < 0.90: crash_point = random.uniform(2.0, 4.0)
        else: crash_point = random.uniform(4.0, 10.0)
        
        crash_point = round(crash_point, 1)
        current_mult = 1.0

        embed = disnake.Embed(
            title="📈 CRASH DO CIPÓ 🐒",
            description=f"{ctx.author.mention} apostou **{aposta} C**!\n\n🌿 O macaco começou a subir...\n**Multiplicador:** `{current_mult}x`\n\n⚠️ *Digite `parar` no chat para pular!*",
            color=disnake.Color.green()
        )
        msg = await ctx.send(embed=embed)

        if crash_point == 1.0:
            await asyncio.sleep(1)
            embed.color = disnake.Color.red()
            embed.description = f"💥 **ARREBENTOU INSTANTANEAMENTE!**\nO cipó rasgou no `{crash_point}x`.\n\n💀 {ctx.author.mention} perdeu **{aposta} C** direto na lama."
            await msg.edit(embed=embed)
            await self.save_achievement(user, "queda_livre")
            return

        stop_event = asyncio.Event()
        async def listen_for_parar():
            def check(m): return m.author == ctx.author and m.content.lower() == 'parar' and m.channel == ctx.channel
            try:
                await self.bot.wait_for('message', check=check, timeout=30.0)
                stop_event.set()
            except asyncio.TimeoutError: pass

        listen_task = self.bot.loop.create_task(listen_for_parar())

        while current_mult < crash_point:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=1.5)
                break
            except asyncio.TimeoutError:
                current_mult += round(random.uniform(0.1, 0.4), 1)
                current_mult = round(current_mult, 1)
                if current_mult > crash_point: current_mult = crash_point

                embed.description = f"{ctx.author.mention} apostou **{aposta} C**!\n\n🌿 Subindo alto...\n**Multiplicador:** `{current_mult}x`\n\n⚠️ *Digite `parar` no chat para pular!*"
                try: await msg.edit(embed=embed)
                except: pass

        listen_task.cancel()
        user_atual = db.get_user_data(str(ctx.author.id))

        if stop_event.is_set():
            ganho = int(aposta * current_mult)
            lucro = ganho - aposta
            db.update_value(user_atual['row'], 3, int(user_atual['data'][2]) + ganho)
            
            embed.color = disnake.Color.blue()
            embed.description = f"✅ **PULOU A TEMPO!**\nO macaco soltou o cipó no `{current_mult}x`.\n\n💰 {ctx.author.mention} faturou **{ganho} C** (Lucro: `+{lucro} C`)!"
            await msg.edit(embed=embed)
            
            if current_mult >= 5.0:
                await self.save_achievement(user_atual, "astronauta_cipo")
        else:
            embed.color = disnake.Color.red()
            embed.description = f"💥 **ARREBENTOU!**\nO cipó não aguentou o peso e rasgou no `{crash_point}x`.\n\n💀 {ctx.author.mention} caiu na lama e perdeu **{aposta} C**."
            await msg.edit(embed=embed)

    # --- SISTEMA DE LOTERIA ---
    @commands.command(aliases=["premio", "acumulado"])
    async def pote(self, ctx):
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

    @commands.command(aliases=["bilhete", "loto"])
    async def loteria(self, ctx):
        custo_bilhete = 500
        user_id = ctx.author.id

        if user_id in self.loteria_participantes:
            return await ctx.send(f"🎫 {ctx.author.mention}, você já tem um bilhete! O pote atual está em **{self.loteria_pote} C**.")

        user = db.get_user_data(str(user_id))
        if not user or int(user['data'][2]) < custo_bilhete:
            return await ctx.send(f"❌ {ctx.author.mention}, você precisa de **{custo_bilhete} C** para comprar um bilhete!")

        db.update_value(user['row'], 3, int(user['data'][2]) - custo_bilhete)
        self.loteria_participantes.append(user_id)
        self.loteria_pote += custo_bilhete
        await ctx.send(f"🎫 **BILHETE COMPRADO!** {ctx.author.mention} entrou na loteria.\n💰 O prêmio acumulado agora é de **{self.loteria_pote} Conguitos**!")

    @commands.command()
    async def sortear_loteria(self, ctx):
        if ctx.author.id != self.owner_id: return await ctx.send("❌ Apenas o Rei da Selva pode girar o globo da loteria!")
        if not self.loteria_participantes: return await ctx.send("❌ Nenhum bilhete foi vendido para esta rodada.")

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

        self.loteria_participantes = []
        self.loteria_pote = 0

    # --- MINIGAME: COCO EXPLOSIVO ---
    @commands.command(aliases=["roleta_coco", "coco_explosivo"])
    async def coco(self, ctx, aposta: int):
        if self.coco_active: return await ctx.send(f"⚠️ {ctx.author.mention}, já existe uma roda aberta! Digite `!entrar_coco`.")
        if aposta <= 0: return await ctx.send(f"❌ {ctx.author.mention}, a aposta deve ser maior que zero!")

        user = db.get_user_data(str(ctx.author.id))
        if not user or int(user['data'][2]) < aposta: return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        db.update_value(user['row'], 3, int(user['data'][2]) - aposta)
        self.coco_active = True
        self.coco_aposta = aposta
        self.coco_players = [ctx.author]

        embed = disnake.Embed(
            title="🚨 ROLETA DO COCO EXPLOSIVO! 🚨",
            description=f"{ctx.author.mention} abriu uma roda mortal!\n\n💰 **Entrada:** `{aposta} C`\n⏳ **Tempo:** 60 segundos para entrar!\n\nDigite **`!entrar_coco`** para participar.",
            color=disnake.Color.dark_red()
        )
        await ctx.send(embed=embed)

        await asyncio.sleep(60)

        if len(self.coco_players) < 2:
            user_refund = db.get_user_data(str(ctx.author.id))
            db.update_value(user_refund['row'], 3, int(user_refund['data'][2]) + aposta)
            self.coco_active = False
            self.coco_players = []
            self.coco_aposta = 0
            return await ctx.send(f"🥥 Ninguém teve coragem. O jogo foi cancelado e o dinheiro devolvido para {ctx.author.mention}.")

        jogadores = self.coco_players.copy()
        total_jogadores = len(jogadores)
        pote = self.coco_aposta * total_jogadores

        await ctx.send(f"🔥 **A RODA FECHOU!** Temos {total_jogadores} macacos corajosos e um pote de **{pote} Conguitos**.\nQue os jogos comecem...")
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
                if m_db: await self.save_achievement(m_db, "ima_desgraca")
            rodada += 1

        vencedor = jogadores[0]
        v_db = db.get_user_data(str(vencedor.id))
        db.update_value(v_db['row'], 3, int(v_db['data'][2]) + pote)

        await asyncio.sleep(1)
        await ctx.send(f"🏆 **FIM DE JOGO!** {vencedor.mention} foi o único que não perdeu a cabeça e faturou sozinho o pote de **{pote} C**!")

        if total_jogadores >= 5:
            await self.save_achievement(v_db, "veterano_coco")
            
        self.coco_players = []
        self.coco_aposta = 0

    @commands.command(name="entrar_coco")
    async def entrar_coco(self, ctx):
        if not self.coco_active: return await ctx.send(f"⚠️ {ctx.author.mention}, não há roda de coco aberta! Crie uma com `!coco <valor>`.")
        if ctx.author in self.coco_players: return await ctx.send(f"🐒 {ctx.author.mention}, você já está na roda!")

        user = db.get_user_data(str(ctx.author.id))
        if not user or int(user['data'][2]) < self.coco_aposta: return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        db.update_value(user['row'], 3, int(user['data'][2]) - self.coco_aposta)
        self.coco_players.append(ctx.author)
        pote_atual = len(self.coco_players) * self.coco_aposta
        await ctx.send(f"🥥 {ctx.author.mention} entrou na roda da morte! (Pote atual: **{pote_atual} C**)")

    # --- LISTA DE JOGOS ---
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
                "🪙 **!moeda <cara/coroa> <valor>** - Dobro ou nada.\n"
                "🦁 **!bicho <animal> <valor>** - Aposte em: Leao, Cobra, Jacare, Arara, Elefante.\n"
                "💣 **!minas <bombas> <valor>** - Escolha entre 1 e 5 bombas.\n"
                "⚔️ **!briga @user <valor>** - Desafie alguém para PvP!"
            ),
            inline=False
        )
        embed.set_footer(text="Lembre-se: A casa sempre ganha! 🐒")
        await ctx.send(embed=embed)

    # --- OUTROS JOGOS (Corrida, Bicho, Minas, Briga, Moeda, Cassino) ---
    @commands.command(name="corrida")
    async def corrida_macaco(self, ctx, escolha: str, aposta: int):
        opcoes = {"macaquinho": "🐒", "gorila": "🦍", "orangutango": "🦧"}
        escolha = escolha.lower()
        if escolha not in opcoes: return await ctx.send(f"❌ {ctx.author.mention}, escolha: `macaquinho`, `gorila` ou `orangutango`.")

        user = db.get_user_data(str(ctx.author.id))
        if not user or aposta > int(user['data'][2]) or aposta <= 0: return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        macacos_lista = list(opcoes.values())
        nomes_lista = list(opcoes.keys())
        pistas = [0, 0, 0]
        chegada = 10
        
        msg = await ctx.send(f"🏁 **A CORRIDA COMEÇOU!** {ctx.author.mention} apostou no **{escolha.capitalize()}**!\n\n" + "\n".join([f"{macacos_lista[i]} 🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦 🏁" for i in range(3)]))

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

    @commands.command(name="bicho")
    async def jogo_bicho(self, ctx, bicho: str, aposta: int):
        bichos = ["leao", "cobra", "jacare", "arara", "elefante"]
        bicho = bicho.lower()
        if bicho not in bichos: return await ctx.send(f"❌ {ctx.author.mention}, escolha: `leao, cobra, jacare, arara, elefante`")

        user = db.get_user_data(str(ctx.author.id))
        if not user or aposta > int(user['data'][2]) or aposta <= 0: return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        resultado = random.choice(bichos)
        msg = await ctx.send(f"🎰 Sorteando... {ctx.author.mention} apostou no **{bicho.upper()}**!")
        await asyncio.sleep(2)

        ganho = aposta * 5 if bicho == resultado else -aposta
        txt = f"🎉 DEU **{resultado.upper()}**! Você ganhou **{ganho} C**!" if ganho > 0 else f"💀 DEU **{resultado.upper()}**! Perdeu **{aposta} C**."
        
        await msg.edit(content=f"{ctx.author.mention} {txt}")
        db.update_value(user['row'], 3, int(user['data'][2]) + ganho)

    @commands.command(name="minas")
    async def campo_minado(self, ctx, bombas: int, aposta: int):
        if not (1 <= bombas <= 5): return await ctx.send(f"❌ {ctx.author.mention}, escolha entre 1 e 5 bombas.")

        user = db.get_user_data(str(ctx.author.id))
        if not user or aposta > int(user['data'][2]) or aposta <= 0: return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        await ctx.send(f"💣 {ctx.author.mention} entrando no campo com {bombas} bombas...")
        await asyncio.sleep(1.5)

        if random.randint(1, 10) > (bombas * 1.5):
            mult = 1.5 + (bombas * 0.5)
            ganho = int(aposta * mult)
            status = f"🚩 **LIMPO!** {ctx.author.mention} ganhou **{ganho} conguitos**! ({mult}x)"
            if bombas == 5: 
                await self.save_achievement(user, "esquadrao_suicida")
        else:
            ganho = -aposta
            status = f"💥 **BOOOOM!** {ctx.author.mention} pisou em uma mina e perdeu **{aposta} C**."
            if bombas == 1: 
                await self.save_achievement(user, "escorregou_banana")

        db.update_value(user['row'], 3, int(user['data'][2]) + ganho)
        await ctx.send(status)

    @commands.command(aliases=["briga", "brigar", "luta", "lutar", "x1"])
    async def briga_macaco(self, ctx, vitima: disnake.Member, aposta: int):
        if vitima.id == ctx.author.id: return await ctx.send(f"🐒 {ctx.author.mention}, não brigue consigo mesmo!")
        
        ladrao = db.get_user_data(str(ctx.author.id))
        alvo = db.get_user_data(str(vitima.id))

        if not ladrao or not alvo or int(alvo['data'][2]) < aposta or int(ladrao['data'][2]) < aposta: return await ctx.send(f"❌ {ctx.author.mention}, alguém não tem saldo para essa briga!")

        if aposta == 1:
            await self.save_achievement(ladrao, "briga_de_bar")

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

    @commands.command(name="moeda", aliases=["cara_coroa", "coinflip", "cf"])
    async def cara_coroa(self, ctx, lado: str, aposta: int):
        user = db.get_user_data(str(ctx.author.id))
        if not user or aposta > int(user['data'][2]) or aposta <= 0: return await ctx.send(f"⚠️ {ctx.author.mention}, saldo insuficiente!")

        lado = lado.lower()
        if lado not in ["cara", "coroa"]: return await ctx.send(f"⚠️ {ctx.author.mention}, escolha entre `cara` ou `coroa`!")

        res = random.choice(["cara", "coroa"])
        venceu = (lado == res)
        ganho = aposta if venceu else -aposta
        msg = f"✅ **Ganhou, +{aposta} C!**" if venceu else f"❌ **Perdeu, -{aposta} C!**"

        db.update_value(user['row'], 3, int(user['data'][2]) + ganho)
        await ctx.send(f"🪙 {ctx.author.mention} | Caiu **{res.upper()}**! {msg}")

    @commands.command(name="cassino")
    async def cassino_slots(self, ctx, aposta: int):
        user = db.get_user_data(str(ctx.author.id))
        if not user or aposta > int(user['data'][2]) or aposta <= 0: return await ctx.send(f"⚠️ {ctx.author.mention}, saldo insuficiente!")

        emojis = ["🍌", "🐒", "⚡", "🥥", "💎", "🦍", "🌴", "🌊"]
        res = [random.choice(emojis) for _ in range(3)]
        
        if res[0] == res[1] == res[2]:
            ganho = aposta * 10
            status_msg = f"🎰 **JACKPOT!** 🎰\nVocê ganhou **+{ganho} C**"
            await self.save_achievement(user, "filho_da_sorte")
        elif res[0] == res[1] or res[1] == res[2] or res[0] == res[2]:
            ganho = aposta * 2
            status_msg = f"Você ganhou **+{ganho} C**"
        else:
            ganho = -aposta
            status_msg = f"Você perdeu **{ganho} C**" 

        db.update_value(user['row'], 3, int(user['data'][2]) + ganho)
        await ctx.send(f"🎰 **CASSINO AKTrovão** 🎰\n**[ {res[0]} | {res[1]} | {res[2]} ]**\n{ctx.author.mention}, {status_msg}!")

def setup(bot):
    bot.add_cog(Games(bot))