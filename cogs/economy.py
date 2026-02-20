import disnake
from disnake.ext import commands
import database as db
import time
import random

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = 757752617722970243
        self.recompensas = {}
        
        # Inicializa os trackers de emblemas na memória do bot (acessível por outros arquivos)
        if not hasattr(bot, 'tracker_emblemas'):
            bot.tracker_emblemas = {
                'trabalhos': {},           # {user_id: [timestamp1, timestamp2]}
                'roubos_sucesso': {},      # {user_id: [timestamp1, timestamp2]}
                'roubos_falha': {},        # {user_id: quantidade_falhas_seguidas}
                'esquadrao_suicida': set(),# IDs de quem ganhou com 5 bombas
                'palhaco': set(),          # IDs de quem tentou roubar a si mesmo
                'filho_da_sorte': set(),   # IDs de quem tirou Jackpot no cassino
                'escorregou_banana': set(),# IDs de quem perdeu na mina com 1 bomba
                'pix_irritante': set(),    # IDs de quem fez um pix de 1 C
                'casca_grossa': set(),     # IDs de quem bateu no Escudo
                'briga_de_bar': set(),     # IDs de quem brigou por 1 C
                'ima_desgraca': set(),     # IDs de quem explodiu primeiro no coco (>=4)
                'veterano_coco': set(),    # IDs de quem sobreviveu ao coco (>=5)
                'queda_livre': set(),      # NOVO: Azar no Crash (1.0x)
                'astronauta_cipo': set()   # NOVO: Coragem no Crash (>=5.0x)
            }

    async def cog_before_invoke(self, ctx):
        """Restringe comandos de economia ao canal #🐒・conguitos, exceto os permitidos globalmente."""
        if ctx.command.name in ['jogos', 'rank', 'top', 'conquistas', 'emblemas']:
            return

        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, assuntos de dinheiro e perfil são apenas no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["emblemas"])
    async def conquistas(self, ctx):
        """Mostra todas as conquistas disponíveis no servidor."""
        embed = disnake.Embed(
            title="🏆 Guia de Conquistas AKTrovão",
            description="Complete os desafios para exibir esses emblemas no seu `!perfil`!",
            color=disnake.Color.gold()
        )

        embed.add_field(
            name="🥇 Conquistas de Rank",
            value=(
                "🥇 **O Alfa da Selva:** Seja o Top 1 do servidor em Conguitos.\n"
                "🥈 **Vice-Líder:** Seja o Top 2 do servidor.\n"
                "🥉 **Bronze de Ouro:** Seja o Top 3 do servidor."
            ),
            inline=False
        )

        embed.add_field(
            name="💰 Conquistas de Riqueza e Status",
            value=(
                "💎 **Magnata:** Acumule mais de 20.000 Conguitos.\n"
                "👑 **Rei da Selva:** Compre o cargo máximo de Gorila.\n"
                "📉 **Falência Técnica:** Fique com menos de 100 Conguitos no saldo. \n"
                "🦴 **Passa fome:** Chegue a exatamente 0 Conguitos."
            ),
            inline=False
        )

        embed.add_field(
            name="🏃‍♂️ Conquistas de Ação (Diárias)",
            value=(
                "🐒 **Proletário Padrão:** Trabalhe 5 vezes em um período de 24h.\n"
                "🥷 **Mestre das Sombras:** Faça 5 roubos com sucesso em 24h.\n"
                "⛓️ **Freguês da Delegacia:** Seja preso (falhe no roubo) 3 vezes seguidas.\n"
                "🕵️ **Invasor:** Tenha um Pé de Cabra no inventário."
            ),
            inline=False
        )

        embed.add_field(
            name="🤫 Conquistas Secretas",
            value=(
                "❓ **???** - *Dizem que quem brinca com fogo, sai explodido.*\n"
                "❓ **???** - *Tem gente que tenta passar a perna até no espelho.*\n"
                "❓ **???** - *A benção dos deuses do cassino recaiu sobre você.*\n"
                "❓ **???** - *Como alguém consegue pisar na única casca do chão?*\n"
                "❓ **???** - *Até a menor das moedas pode causar a maior das irritações.*\n"
                "❓ **???** - *Deu de cara no muro tentando levar o que não é seu.*\n"
                "❓ **???** - *Brigar por uma única moeda? Isso é falta de amor à vida.*\n"
                "❓ **???** - *Alguém precisava ser o primeiro a tomar na cabeça...*\n"
                "❓ **???** - *Um verdadeiro sobrevivente do caos coletivo.*\n"
                "❓ **???** - *O cipó arrebentou antes mesmo de você segurar.*\n"
                "❓ **???** - *Coragem de aço! Ou seria burrice?*"
            ),
            inline=False
        )

        embed.set_footer(text="Dica: Algumas conquistas somem se você não mantiver o ritmo!")
        await ctx.send(embed=embed)

    @commands.command(aliases=["top", "ricos", "placar"])
    async def rank(self, ctx):
        """Exibe o ranking dos usuários mais ricos do servidor."""
        all_data = db.sheet.get_all_records()
        
        if not all_data:
            return await ctx.send("❌ Não há dados suficientes para gerar o ranking.")

        try:
            sorted_users = sorted(all_data, key=lambda x: int(x.get('saldo', 0)), reverse=True)
        except Exception as e:
            return await ctx.send(f"⚠️ Erro ao processar o ranking: {e}")

        embed = disnake.Embed(
            title="🏆 Ranking de Conguitos - AKTrovão",
            description="Estes são os primatas mais ricos da selva!",
            color=disnake.Color.gold()
        )

        lista_rank = ""
        for i, user in enumerate(sorted_users[:10]):
            nome = user.get('nome', 'Desconhecido')
            saldo = user.get('saldo', 0)
            
            if i == 0:
                linha = f"🥇 **{nome}** — `{saldo} C`"
            elif i == 1:
                linha = f"🥈 **{nome}** — `{saldo} C`"
            elif i == 2:
                linha = f"🥉 **{nome}** — `{saldo} C`"
            else:
                linha = f"**{i+1}.** {nome} — `{saldo} C`"
            
            lista_rank += linha + "\n"

        embed.add_field(name="Top 10 Jogadores", value=lista_rank, inline=False)
        embed.set_footer(text="Trabalhe e suba no ranking! 🐒")
        await ctx.send(embed=embed)

    @commands.command()
    async def trabalhar(self, ctx):
        user_id = str(ctx.author.id)
        user = db.get_user_data(user_id)
        
        if not user:
            db.create_user(user_id, ctx.author.name)
            user = db.get_user_data(user_id)

        agora = time.time()
        ultimo_work = float(user['data'][4]) if len(user['data']) > 4 and user['data'][4] else 0

        if agora - ultimo_work < 3600:
            restante = int((3600 - (agora - ultimo_work)) / 60)
            return await ctx.send(f"⏳ {ctx.author.mention}, você está exausto! Volte em **{restante} minutos**.")

        cargo = user['data'][3]
        mults = {"Macaquinho": 1.0, "Chimpanzé": 1.5, "Orangutango": 2.5, "Gorila": 4.0}
        ganho = int(random.randint(100, 300) * mults.get(cargo, 1.0))
        
        db.update_value(user['row'], 3, int(user['data'][2]) + ganho)
        db.update_value(user['row'], 5, agora)
        
        # --- TRACKER: Emblema Proletário Padrão ---
        if user_id not in self.bot.tracker_emblemas['trabalhos']:
            self.bot.tracker_emblemas['trabalhos'][user_id] = []
        # Remove registros mais antigos que 24h
        self.bot.tracker_emblemas['trabalhos'][user_id] = [t for t in self.bot.tracker_emblemas['trabalhos'][user_id] if agora - t < 86400]
        self.bot.tracker_emblemas['trabalhos'][user_id].append(agora)

        await ctx.send(f"✅ {ctx.author.mention}, como **{cargo}**, você ganhou **{ganho} conguitos**!")

    @commands.command(aliases=["p", "status", "pefil", "perfil_privado"])
    async def perfil(self, ctx, membro: disnake.Member = None):
        membro = membro or ctx.author
        user_id = str(membro.id)
        user = db.get_user_data(user_id)
        if not user: return await ctx.send(f"❌ {membro.mention} não tem conta!")

        saldo = int(user['data'][2])
        cargo = user['data'][3]
        inventario = user['data'][5] if len(user['data']) > 5 and user['data'][5] != "" else "Nenhum"

        # --- Lógica de Emblemas / Conquistas ---
        emblemas = []
        agora = time.time()

        # Básicos
        if saldo >= 20000: emblemas.append("💎 **Magnata**")
        if cargo == "Gorila": emblemas.append("👑 **Rei da Selva**")
        if "Pé de Cabra" in inventario: emblemas.append("🕵️ **Invasor**")
        
        # Novo: Falência Técnica
        if saldo < 100: emblemas.append("📉 **Falência Técnica**")
        if saldo == 0: emblemas.append("🦴 **Passa fome**")

        # Emblemas Dinâmicos de Ranking (À prova de KeyError)
        all_data = db.sheet.get_all_records()
        if all_data:
            sorted_users = sorted(all_data, key=lambda x: int(x.get('saldo', 0)), reverse=True)
            
            rank_idx = None
            for i, u in enumerate(sorted_users):
                # Tenta ler 'id', 'ID', 'Id' ou 'id_usuario' dependendo de como está na planilha
                coluna_id = str(u.get('id', u.get('ID', u.get('Id', u.get('id_usuario', '')))))
                if coluna_id == user_id:
                    rank_idx = i
                    break
                    
            if rank_idx == 0: emblemas.append("🥇 **O Alfa da Selva**")
            elif rank_idx == 1: emblemas.append("🥈 **Vice-Líder**")
            elif rank_idx == 2: emblemas.append("🥉 **Bronze de Ouro**")

        # Emblemas baseados em Memória/Tracker
        if hasattr(self.bot, 'tracker_emblemas'):
            tracker = self.bot.tracker_emblemas
            
            # Proletário (5x trabalhou)
            trabalhos = tracker['trabalhos'].get(user_id, [])
            if len([t for t in trabalhos if agora - t < 86400]) >= 5:
                emblemas.append("🐒 **Proletário Padrão**")
                
            # Mestre das Sombras (5x roubou com sucesso)
            roubos_s = tracker['roubos_sucesso'].get(user_id, [])
            if len([t for t in roubos_s if agora - t < 86400]) >= 5:
                emblemas.append("🥷 **Mestre das Sombras**")
                
            # Freguês (Falhou 3x seguidas)
            if tracker['roubos_falha'].get(user_id, 0) >= 3:
                emblemas.append("⛓️ **Freguês da Delegacia**")
                
            # Secretas Originais
            if user_id in tracker.get('esquadrao_suicida', set()):
                emblemas.append("💣 **Esquadrão Suicida**")
            
            if user_id in tracker.get('palhaco', set()):
                emblemas.append("🤡 **Palhaço da Selva**")
                
            if user_id in tracker.get('filho_da_sorte', set()):
                emblemas.append("🍀 **Filho da Sorte**")
                
            if user_id in tracker.get('escorregou_banana', set()):
                emblemas.append("🍌 **Escorregou na Banana**")
                
            if user_id in tracker.get('pix_irritante', set()):
                emblemas.append("💸 **Pix Irritante**")
                
            if user_id in tracker.get('casca_grossa', set()):
                emblemas.append("🐢 **Casca Grossa**")
                
            if user_id in tracker.get('briga_de_bar', set()):
                emblemas.append("🥊 **Briga de Bar**")
                
            # Novas do Coco Explosivo
            if user_id in tracker.get('ima_desgraca', set()):
                emblemas.append("🧲 **Imã de Desgraça**")
                
            if user_id in tracker.get('veterano_coco', set()):
                emblemas.append("🥥 **Veterano de Guerra**")
                
            # Novas do Crash
            if user_id in tracker.get('queda_livre', set()):
                emblemas.append("📉 **Queda Livre**")
                
            if user_id in tracker.get('astronauta_cipo', set()):
                emblemas.append("🚀 **Astronauta de Cipó**")
        
        emblemas_str = " | ".join(emblemas) if emblemas else "Nenhum"

        embed = disnake.Embed(title=f"🐒 Perfil AKTrovão", color=disnake.Color.gold())
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.add_field(name="💰 Saldo", value=f"{saldo} C", inline=True)
        embed.add_field(name="💼 Cargo", value=cargo, inline=True)
        embed.add_field(name="🎒 Inventário", value=f"`{inventario}`", inline=False)
        embed.add_field(name="🏆 Conquistas", value=emblemas_str, inline=False)
        
        # Mostra se o usuário tem recompensa pela cabeça dele
        if user_id in self.recompensas and self.recompensas[user_id] > 0:
            embed.add_field(name="🚨 RECOMPENSA ATIVA", value=f"`{self.recompensas[user_id]} C` pela sua cabeça!", inline=False)

        await ctx.send(embed=embed)

    @commands.command(aliases=["shop", "mercado", "itens"])
    async def loja(self, ctx):
        """Lista os itens e serviços disponíveis."""
        embed = disnake.Embed(
            title="🛒 Loja de Itens e Maldades AKTrovão",
            description="Use seu saldo para evoluir, se proteger ou interagir!",
            color=disnake.Color.blue()
        )

        embed.add_field(
            name="📈 EVOLUÇÃO (Cargos)",
            value=(
                "🐒 **Chimpanzé**: 1.500 C (1.5x)\n"
                "🦧 **Orangutango**: 5.000 C (2.5x)\n"
                "🦍 **Gorila**: 15.000 C (4.0x)\n"
                "------------------------------------------------------------------"
            ),
            inline=False
        )

        embed.add_field(
            name="🛡️ ITENS DE PROTEÇÃO E AÇÃO",
            value=(
                "🛡️ **Escudo**: 800 C\n"
                "*(Evita 1 roubo. O item quebra após o uso!)*\n\n"
                "🕵️ **Pé de Cabra**: 1.200 C\n"
                "*(Aumenta sua chance de roubo para 70%. O item quebra após o uso!)*\n"
                "------------------------------------------------------------------"
            ),
            inline=False
        )

        embed.add_field(
            name="🥷 INTERAÇÃO & EVENTOS",
            value=(
                "💰 **Roubar**: `!roubar @user` (Chance de 40%)\n"
                "💸 **Pix**: `!pagar @user <valor>` (Transfira dinheiro!)\n"
                "🚨 **Recompensa**: `!recompensa @user <valor>` (Coloque alguém a prêmio)\n"
                "🎫 **Loteria**: `!loteria` (Compre um bilhete por 500 C)\n"
                "------------------------------------------------------------------"
            ),
            inline=False
        )

        embed.add_field(
            name="😬 SERVIÇOS (Castigos)",
            value=(
                "🔇 **Mudo/Surdo**: 300 - 1.5k - 3k C\n"
                "😬 **Surdomudo**: 600 - 3k - 6k C\n"
                "⏱️ Tempos: 1, 5 ou 10 minutos.\n"
                "👟 **Desconectar**: 1.2k C\n"
                "------------------------------------------------------------------"
            ),
            inline=False
        )

        embed.add_field(
            name="📝 Como usar?",
            value=(
                "• Para comprar itens/cargos: `!comprar <nome>`\n"
                "• Para ranking: `!rank` ou `!top`"
            ),
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def comprar(self, ctx, *, item: str):
        user_id = str(ctx.author.id)
        user = db.get_user_data(user_id)
        if not user: return await ctx.send("❌ Use `!trabalhar` primeiro!")

        loja = {
            "chimpanzé": {"nome": "Chimpanzé", "preco": 1500, "tipo": "cargo"},
            "chimpanze": {"nome": "Chimpanzé", "preco": 1500, "tipo": "cargo"},
            "orangutango": {"nome": "Orangutango", "preco": 5000, "tipo": "cargo"},
            "gorila": {"nome": "Gorila", "preco": 15000, "tipo": "cargo"},
            "escudo": {"nome": "Escudo", "preco": 800, "tipo": "item"},
            "pé de cabra": {"nome": "Pé de Cabra", "preco": 1200, "tipo": "item"},
            "pe de cabra": {"nome": "Pé de Cabra", "preco": 1200, "tipo": "item"}
        }

        escolha = item.lower()
        if escolha not in loja: return await ctx.send("❌ Item inválido!")
        
        item_data = loja[escolha]
        
        if item_data["tipo"] == "item" and item_data["nome"] in user['data'][5]:
            return await ctx.send(f"⚠️ {ctx.author.mention}, você já tem um(a) **{item_data['nome']}** ativo!")

        saldo = int(user['data'][2])

        if saldo < item_data["preco"]: return await ctx.send("❌ Saldo insuficiente!")

        db.update_value(user['row'], 3, saldo - item_data["preco"])
        coluna = 4 if item_data["tipo"] == "cargo" else 6
        db.update_value(user['row'], coluna, item_data["nome"])
        await ctx.send(f"✅ {ctx.author.mention} comprou **{item_data['nome']}**!")

    @commands.command(aliases=["bounty", "cacada"])
    async def recompensa(self, ctx, vitima: disnake.Member, valor: int):
        """Coloca a cabeça de um usuário a prêmio para incentivar roubos."""
        if vitima.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, você não pode colocar uma recompensa na própria cabeça!")
        
        if valor <= 0:
            return await ctx.send(f"❌ {ctx.author.mention}, o valor da recompensa precisa ser maior que zero!")

        pagador_data = db.get_user_data(str(ctx.author.id))
        
        if not pagador_data or int(pagador_data['data'][2]) < valor:
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente para pagar essa recompensa!")

        db.update_value(pagador_data['row'], 3, int(pagador_data['data'][2]) - valor)

        vitima_id = str(vitima.id)
        self.recompensas[vitima_id] = self.recompensas.get(vitima_id, 0) + valor
        total_acumulado = self.recompensas[vitima_id]

        embed = disnake.Embed(
            title="🚨 CAÇADA INICIADA! 🚨",
            description=f"**{ctx.author.mention}** acabou de colocar a cabeça de **{vitima.mention}** a prêmio!\n\n💰 **Recompensa Acumulada:** `{total_acumulado} Conguitos`\n\n*O primeiro mercenário que conseguir roubar esse primata com sucesso leva a recompensa extra!*",
            color=disnake.Color.red()
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=["assaltar", "furtar", "rob"])
    async def roubar(self, ctx, vitima: disnake.Member):
        ladrao_id = str(ctx.author.id)
        
        # --- TRACKER SECRETO: Palhaço da Selva ---
        if vitima.id == ctx.author.id: 
            if hasattr(self.bot, 'tracker_emblemas'):
                if 'palhaco' not in self.bot.tracker_emblemas:
                    self.bot.tracker_emblemas['palhaco'] = set()
                self.bot.tracker_emblemas['palhaco'].add(ladrao_id)
            return await ctx.send("🐒 Achou que eu não ia perceber? Ganhou a conquista de Palhaço por tentar se roubar!")
        
        ladrao_data = db.get_user_data(ladrao_id)
        alvo_data = db.get_user_data(str(vitima.id))
        if not ladrao_data or not alvo_data: return await ctx.send("❌ Conta não encontrada!")

        agora = time.time()
        vitima_id = str(vitima.id)

        ultimo_roubo = float(ladrao_data['data'][6]) if len(ladrao_data['data']) > 6 and ladrao_data['data'][6] else 0
        if agora - ultimo_roubo < 7200:
            restante = int((7200 - (agora - ultimo_roubo)) / 60)
            return await ctx.send(f"👮 Espere **{restante} minutos** para roubar novamente.")

        chance_sucesso = 40
        if "Pé de Cabra" in ladrao_data['data'][5]:
            chance_sucesso = 70
            db.update_value(ladrao_data['row'], 6, "") # Item quebra

        # Verifica Escudo
        if "Escudo" in alvo_data['data'][5]:
            db.update_value(alvo_data['row'], 6, "")
            db.update_value(ladrao_data['row'], 7, agora)
            
            # --- TRACKER SECRETO: Casca Grossa ---
            if hasattr(self.bot, 'tracker_emblemas'):
                if 'casca_grossa' not in self.bot.tracker_emblemas:
                    self.bot.tracker_emblemas['casca_grossa'] = set()
                self.bot.tracker_emblemas['casca_grossa'].add(ladrao_id)
                
            return await ctx.send(f"🛡️ {vitima.mention} estava protegido por um Escudo e você perdeu o seu ataque!")

        if random.randint(1, 100) <= chance_sucesso:
            valor_roubado = int(int(alvo_data['data'][2]) * 0.2)
            bounty_ganho = 0
            
            # --- COLETA DE RECOMPENSA ---
            if vitima_id in self.recompensas and self.recompensas[vitima_id] > 0:
                bounty_ganho = self.recompensas.pop(vitima_id)

            ganho_total = valor_roubado + bounty_ganho

            db.update_value(ladrao_data['row'], 3, int(ladrao_data['data'][2]) + ganho_total)
            db.update_value(alvo_data['row'], 3, int(alvo_data['data'][2]) - valor_roubado)
            db.update_value(ladrao_data['row'], 7, agora)
            
            # --- TRACKER: Mestre das Sombras (Sucesso) ---
            if ladrao_id not in self.bot.tracker_emblemas['roubos_sucesso']:
                self.bot.tracker_emblemas['roubos_sucesso'][ladrao_id] = []
            self.bot.tracker_emblemas['roubos_sucesso'][ladrao_id] = [t for t in self.bot.tracker_emblemas['roubos_sucesso'][ladrao_id] if agora - t < 86400]
            self.bot.tracker_emblemas['roubos_sucesso'][ladrao_id].append(agora)
            
            # Zera contagem de prisão para a badge de Freguês
            self.bot.tracker_emblemas['roubos_falha'][ladrao_id] = 0

            mensagem = f"🥷 **SUCESSO!** Roubou **{valor_roubado} C** de {vitima.mention}!"
            if chance_sucesso == 70:
                mensagem += " (Usou Pé de Cabra 🕵️)"
            
            if bounty_ganho > 0:
                mensagem += f"\n🎯 **MERCENÁRIO!** Você coletou a recompensa extra de **{bounty_ganho} C** que estava pela cabeça de {vitima.mention}!"
                
            await ctx.send(mensagem)
        else:
            multa = int(int(ladrao_data['data'][2]) * 0.15)
            db.update_value(ladrao_data['row'], 3, int(ladrao_data['data'][2]) - multa)
            db.update_value(alvo_data['row'], 3, int(alvo_data['data'][2]) + multa)
            db.update_value(ladrao_data['row'], 7, agora)
            
            # --- TRACKER: Freguês da Delegacia (Falha) ---
            self.bot.tracker_emblemas['roubos_falha'][ladrao_id] = self.bot.tracker_emblemas['roubos_falha'].get(ladrao_id, 0) + 1
            
            await ctx.send(f"👮 **PRESO!** Pagou **{multa} C** de multa.")

    @commands.command(aliases=["pix", "transferir", "enviar", "pay"])
    async def pagar(self, ctx, recebedor: disnake.Member, valor: int):
        """Transfere conguitos para outro usuário."""
        if recebedor.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, você não pode fazer um Pix para si mesmo!")
        
        if valor <= 0:
            return await ctx.send(f"❌ {ctx.author.mention}, o valor da transferência precisa ser maior que zero!")

        pagador_data = db.get_user_data(str(ctx.author.id))
        
        if not pagador_data or int(pagador_data['data'][2]) < valor:
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente para realizar essa transferência!")

        recebedor_data = db.get_user_data(str(recebedor.id))
        
        if not recebedor_data:
            db.create_user(str(recebedor.id), recebedor.display_name)
            recebedor_data = db.get_user_data(str(recebedor.id))

        db.update_value(pagador_data['row'], 3, int(pagador_data['data'][2]) - valor)
        db.update_value(recebedor_data['row'], 3, int(recebedor_data['data'][2]) + valor)
        
        # --- TRACKER SECRETO: Pix Irritante ---
        if valor == 1:
            if hasattr(self.bot, 'tracker_emblemas'):
                if 'pix_irritante' not in self.bot.tracker_emblemas:
                    self.bot.tracker_emblemas['pix_irritante'] = set()
                self.bot.tracker_emblemas['pix_irritante'].add(str(ctx.author.id))

        embed = disnake.Embed(
            title="💸 PIX REALIZADO COM SUCESSO!",
            description=f"**{ctx.author.mention}** transferiu **{valor} Conguitos** para **{recebedor.mention}**.",
            color=disnake.Color.green()
        )
        embed.set_footer(text="A economia da selva agradece a movimentação! 🐒")
        
        await ctx.send(embed=embed)

    @commands.command()
    async def setar(self, ctx, membro: disnake.Member, valor: int):
        if ctx.author.id != self.owner_id:
            return await ctx.send(f"❌ {ctx.author.mention}, você não tem permissão!")
        user = db.get_user_data(str(membro.id))
        if not user: return await ctx.send("❌ Usuário não encontrado!")
        db.update_value(user['row'], 3, valor)
        await ctx.send(f"✅ O saldo de {membro.mention} foi definido para **{valor} C**.")

    @commands.command()
    async def wipe(self, ctx):
        if ctx.author.id != self.owner_id:
            return await ctx.send(f"❌ {ctx.author.mention}, você não tem permissão!")
        await ctx.send("🧹 Iniciando o reset da economia...")
        try:
            db.wipe_database() 
            await ctx.send("✅ **WIPE CONCLUÍDO!**")
        except Exception as e:
            await ctx.send(f"⚠️ Erro: {e}")

def setup(bot):
    bot.add_cog(Economy(bot))