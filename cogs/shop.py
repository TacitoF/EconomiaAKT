import disnake
from disnake.ext import commands
import database as db

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, use a loja no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["shop", "mercado"])
    async def loja(self, ctx):
        embed = disnake.Embed(title="🛒 Loja de Itens e Maldades", description="Compre usando `!comprar <nome do item>`", color=disnake.Color.blue())
        
        embed.add_field(
            name="📈 Cargos (Aumenta Salário e Limite de Aposta)", 
            value=(
                "🐒 **Macaquinho** (1.200 C) - *Aposta Max: 750 C*\n"
                "🐒 **Babuíno** (4.000 C) - *Aposta Max: 2.500 C*\n"
                "🦧 **Chimpanzé** (10.000 C) - *Aposta Max: 6.000 C*\n"
                "🦧 **Orangutango** (25.000 C) - *Aposta Max: 15.000 C*\n"
                "🦍 **Gorila** (60.000 C) - *Aposta Max: 40.000 C*\n"
                "🗿 **Ancestral** (150.000 C) - *Aposta Max: 120.000 C*\n"
                "👑 **Rei Símio** (450.000 C) - *Aposta Max: 1.000.000 C*"
            ), 
            inline=False
        )
        
        embed.add_field(
            name="🛡️ Equipamentos (Acumulativos no Inventário)", 
            value="🛡️ **Escudo** (800 C): Evita que você seja roubado 1 vez.\n🕵️ **Pé de Cabra** (1.200 C): Aumenta chance de roubo para 70%.\n📄 **Seguro** (1.000 C): Banco te devolve 60% se for roubado.", 
            inline=False
        )
        
        embed.add_field(
            name="😈 Sabotagens e Maldades", 
            value=(
                "🛒 **Itens (Compre na loja para usar):**\n"
                "🍌 **Casca de Banana** (300 C): Próximo trabalho/roubo falha `!casca @user`.\n"
                "🦍 **Imposto do Gorila** (1.500 C): Roube 25% do alvo por 24h `!taxar @user`.\n"
                "🪄 **Troca de Nick** (2.500 C): Altera o nick do alvo por 30min `!apelidar @user <nick>`.\n\n"
                "⚡ **Comandos Diretos (Pagou, usou!):**\n"
                "🙊 **Maldição Símia** (500 C): O alvo fala como macaco por 1min `!amaldicoar @user`.\n"
                "🎭 **Impostor** (500 C): Envia uma mensagem falsa como o alvo `!impostor @user <msg>`.\n\n"
                "*O **Chimpanzézio** cobra os comandos diretos na hora!*"
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
            "macaquinho": {"nome": "Macaquinho", "preco": 1200, "tipo": "cargo"},
            "babuíno": {"nome": "Babuíno", "preco": 4000, "tipo": "cargo"}, 
            "babuino": {"nome": "Babuíno", "preco": 4000, "tipo": "cargo"},
            "chimpanzé": {"nome": "Chimpanzé", "preco": 10000, "tipo": "cargo"}, 
            "chimpanze": {"nome": "Chimpanzé", "preco": 10000, "tipo": "cargo"},
            "orangutango": {"nome": "Orangutango", "preco": 25000, "tipo": "cargo"}, 
            "gorila": {"nome": "Gorila", "preco": 60000, "tipo": "cargo"},
            "ancestral": {"nome": "Ancestral", "preco": 150000, "tipo": "cargo"},
            "rei símio": {"nome": "Rei Símio", "preco": 450000, "tipo": "cargo"}, 
            "rei simio": {"nome": "Rei Símio", "preco": 450000, "tipo": "cargo"},
            
            "escudo": {"nome": "Escudo", "preco": 800, "tipo": "item"}, 
            "pé de cabra": {"nome": "Pé de Cabra", "preco": 1200, "tipo": "item"}, 
            "pe de cabra": {"nome": "Pé de Cabra", "preco": 1200, "tipo": "item"},
            "seguro": {"nome": "Seguro", "preco": 1000, "tipo": "item"}, 
            "casca de banana": {"nome": "Casca de Banana", "preco": 300, "tipo": "item"},
            "imposto do gorila": {"nome": "Imposto do Gorila", "preco": 1500, "tipo": "item"}, 
            "troca de nick": {"nome": "Troca de Nick", "preco": 2500, "tipo": "item"}
        }

        escolha = item.lower()
        if escolha not in loja: return await ctx.send("❌ Item inválido! Digite exatamente como está na loja.")
        
        item_data = loja[escolha]
        saldo = int(user['data'][2])
        if saldo < item_data["preco"]: return await ctx.send("❌ Saldo insuficiente!")

        db.update_value(user['row'], 3, saldo - item_data["preco"])

        if item_data["tipo"] == "cargo":
            db.update_value(user['row'], 4, item_data["nome"])
            await ctx.send(f"✅ {ctx.author.mention} evoluiu para o cargo **{item_data['nome']}**!")
        elif item_data["tipo"] == "item":
            inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
            inv_list.append(item_data["nome"])
            db.update_value(user['row'], 6, ", ".join(inv_list))
            await ctx.send(f"🛍️ {ctx.author.mention} comprou **{item_data['nome']}** e guardou no inventário!")

def setup(bot):
    bot.add_cog(Shop(bot))  