import disnake
from disnake.ext import commands
import database as db
import time

class Profiles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, use este comando no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["emblemas"])
    async def conquistas(self, ctx):
        embed = disnake.Embed(title="🏆 Guia de Conquistas", color=disnake.Color.gold())
        embed.add_field(name="🥇 Rank", value="O Alfa da Selva (Top 1) | Vice-Líder (Top 2) | Bronze de Ouro (Top 3)", inline=False)
        embed.add_field(name="💰 Status", value="Magnata (20k C) | Rei da Selva (Cargo Gorila) | Falência Técnica (<100 C) | Passa fome (0 C)", inline=False)
        embed.add_field(name="🏃 Ação", value="Proletário Padrão (Trabalhou 5x no dia) | Mestre das Sombras (Roubou 5x no dia) | Freguês (Preso 3x seguidas) | Invasor (Tem Pé de Cabra)", inline=False)
        embed.add_field(name="🤫 Secretas", value="Existem 11 conquistas ocultas escondidas nos jogos e ações. Tente a sorte!", inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=["top", "ricos", "placar"])
    async def rank(self, ctx):
        all_data = db.sheet.get_all_records()
        if not all_data: return await ctx.send("❌ Sem dados suficientes.")

        sorted_users = sorted(all_data, key=lambda x: int(x.get('saldo', 0)), reverse=True)
        embed = disnake.Embed(title="🏆 Ranking de Conguitos", color=disnake.Color.gold())

        lista_rank = ""
        for i, user in enumerate(sorted_users[:10]):
            nome = user.get('nome', 'Desconhecido')
            saldo = user.get('saldo', 0)
            if i == 0: linha = f"🥇 **{nome}** — `{saldo} C`"
            elif i == 1: linha = f"🥈 **{nome}** — `{saldo} C`"
            elif i == 2: linha = f"🥉 **{nome}** — `{saldo} C`"
            else: linha = f"**{i+1}.** {nome} — `{saldo} C`"
            lista_rank += linha + "\n"

        embed.add_field(name="Top 10 Jogadores", value=lista_rank, inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=["p", "status"])
    async def perfil(self, ctx, membro: disnake.Member = None):
        membro = membro or ctx.author
        user_id = str(membro.id)
        user = db.get_user_data(user_id)
        if not user: return await ctx.send(f"❌ {membro.mention} não tem conta!")

        saldo = int(user['data'][2])
        cargo = user['data'][3]
        
        # --- LÓGICA DO INVENTÁRIO INFINITO ---
        inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
        inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
        
        # Conta e agrupa os itens iguais (Ex: 2x Escudo)
        if not inv_list:
            inv_formatado = "Nenhum item"
        else:
            contagem = {}
            for item in inv_list:
                contagem[item] = contagem.get(item, 0) + 1
            
            # Formata a string final
            itens_agrupados = []
            for item, qtd in contagem.items():
                if qtd > 1:
                    itens_agrupados.append(f"`{qtd}x {item}`")
                else:
                    itens_agrupados.append(f"`{item}`")
                    
            inv_formatado = " | ".join(itens_agrupados)
        # ----------------------------------------

        emblemas = []
        agora = time.time()

        if saldo >= 20000: emblemas.append("💎 **Magnata**")
        if cargo == "Gorila": emblemas.append("👑 **Rei da Selva**")
        if "Pé de Cabra" in inv_list: emblemas.append("🕵️ **Invasor**") # Atualizado para ler a lista
        if saldo < 100: emblemas.append("📉 **Falência Técnica**")
        if saldo == 0: emblemas.append("🦴 **Passa fome**")

        all_data = db.sheet.get_all_records()
        if all_data:
            sorted_users = sorted(all_data, key=lambda x: int(x.get('saldo', 0)), reverse=True)
            for i, u in enumerate(sorted_users):
                if str(u.get('id', u.get('ID', u.get('Id', '')))) == user_id:
                    if i == 0: emblemas.append("🥇 **O Alfa da Selva**")
                    elif i == 1: emblemas.append("🥈 **Vice-Líder**")
                    elif i == 2: emblemas.append("🥉 **Bronze de Ouro**")
                    break

        if hasattr(self.bot, 'tracker_emblemas'):
            tr = self.bot.tracker_emblemas
            if len([t for t in tr.get('trabalhos', {}).get(user_id, []) if agora - t < 86400]) >= 5: emblemas.append("🐒 **Proletário Padrão**")
            if len([t for t in tr.get('roubos_sucesso', {}).get(user_id, []) if agora - t < 86400]) >= 5: emblemas.append("🥷 **Mestre das Sombras**")
            if tr.get('roubos_falha', {}).get(user_id, 0) >= 3: emblemas.append("⛓️ **Freguês**")
            if user_id in tr.get('esquadrao_suicida', set()): emblemas.append("💣 **Esquadrão Suicida**")
            if user_id in tr.get('palhaco', set()): emblemas.append("🤡 **Palhaço**")
            if user_id in tr.get('filho_da_sorte', set()): emblemas.append("🍀 **Sortudo**")
            if user_id in tr.get('escorregou_banana', set()): emblemas.append("🍌 **Desastrado**")
            if user_id in tr.get('pix_irritante', set()): emblemas.append("💸 **Pix Irritante**")
            if user_id in tr.get('casca_grossa', set()): emblemas.append("🐢 **Casca Grossa**")
            if user_id in tr.get('briga_de_bar', set()): emblemas.append("🥊 **Briguento**")
            if user_id in tr.get('ima_desgraca', set()): emblemas.append("🧲 **Imã de Desgraça**")
            if user_id in tr.get('veterano_coco', set()): emblemas.append("🥥 **Veterano**")
            if user_id in tr.get('queda_livre', set()): emblemas.append("📉 **Queda Livre**")
            if user_id in tr.get('astronauta_cipo', set()): emblemas.append("🚀 **Astronauta**")

        embed = disnake.Embed(title=f"🐒 Perfil AKTrovão", color=disnake.Color.gold())
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.add_field(name="💰 Saldo", value=f"{saldo} C", inline=True)
        embed.add_field(name="💼 Cargo", value=cargo, inline=True)
        embed.add_field(name="🎒 Inventário", value=inv_formatado, inline=False)
        embed.add_field(name="🏆 Conquistas", value=" | ".join(emblemas) if emblemas else "Nenhuma", inline=False)
        
        rec = getattr(self.bot, 'recompensas', {}).get(user_id, 0)
        if rec > 0: embed.add_field(name="🚨 PROCURADO", value=f"`{rec} C` pela sua cabeça!", inline=False)

        await ctx.send(embed=embed)

    @commands.command(aliases=["shop", "mercado"])
    async def loja(self, ctx):
        embed = disnake.Embed(
            title="🛒 Loja de Itens e Maldades", 
            description="Compre usando `!comprar <nome do item>`",
            color=disnake.Color.blue()
        )
        
        embed.add_field(
            name="📈 Cargos (Mais dinheiro no !trabalhar)", 
            value="🐒 **Chimpanzé:** 1.500 C\n🦧 **Orangutango:** 5.000 C\n🦍 **Gorila:** 15.000 C", 
            inline=False
        )
        
        embed.add_field(
            name="🛡️ Equipamentos (Acumulativos)", 
            value="🛡️ **Escudo** (800 C): Evita que você seja roubado 1 vez.\n"
                  "🕵️ **Pé de Cabra** (1.200 C): Aumenta sua chance de roubo para 70%.\n"
                  "📄 **Seguro** (1.500 C): Se for roubado, o banco te devolve 60% do valor.", 
            inline=False
        )

        embed.add_field(
            name="😈 Itens de Sabotagem (Acumulativos)", 
            value="🍌 **Casca de Banana** (500 C): Faz o próximo trabalho ou roubo da vítima falhar `!casca @user`.\n"
                  "🦍 **Imposto do Gorila** (2.500 C): Roube 25% do próximo trabalho do alvo `!taxar @user`.\n"
                  "🪄 **Troca de Nick** (4.000 C): Altera o apelido de alguém no servidor por 30min `!apelidar @user <nick>`.", 
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
            "pe de cabra": {"nome": "Pé de Cabra", "preco": 1200, "tipo": "item"},
            "seguro": {"nome": "Seguro", "preco": 1500, "tipo": "item"},
            "casca de banana": {"nome": "Casca de Banana", "preco": 500, "tipo": "item"},
            "imposto do gorila": {"nome": "Imposto do Gorila", "preco": 2500, "tipo": "item"},
            "troca de nick": {"nome": "Troca de Nick", "preco": 4000, "tipo": "item"}
        }

        escolha = item.lower()
        if escolha not in loja: return await ctx.send("❌ Item inválido! Digite exatamente como está na loja.")
        
        item_data = loja[escolha]
        saldo = int(user['data'][2])
        if saldo < item_data["preco"]: return await ctx.send("❌ Saldo insuficiente!")

        # Atualiza Saldo
        db.update_value(user['row'], 3, saldo - item_data["preco"])

        if item_data["tipo"] == "cargo":
            # Cargo substitui o anterior
            db.update_value(user['row'], 4, item_data["nome"])
            await ctx.send(f"✅ {ctx.author.mention} evoluiu para o cargo **{item_data['nome']}**!")
            
        elif item_data["tipo"] == "item":
            # --- LÓGICA DE INVENTÁRIO INFINITO (Adicionar sem sobrescrever) ---
            inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
            
            inv_list.append(item_data["nome"]) # Adiciona o novo item na lista
            novo_inv_str = ", ".join(inv_list) # Junta tudo com vírgula
            
            db.update_value(user['row'], 6, novo_inv_str)
            await ctx.send(f"🛍️ {ctx.author.mention} comprou **{item_data['nome']}** e guardou no inventário!")

def setup(bot):
    bot.add_cog(Profiles(bot))