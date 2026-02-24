import disnake
from disnake.ext import commands
import database as db

# Limites de aposta alinhados com a nova economia
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
        embed = disnake.Embed(
            title="🛒 Loja de Itens e Maldades",
            description="Compre usando `!comprar <nome do item>`",
            color=disnake.Color.blue()
        )
        embed.add_field(
            name="📈 Cargos (Aumenta Salário e Limite de Aposta)",
            value=(
                "🐒 **Macaquinho** — `1.200 MC` | Sal: 130–230 MC/h | Aposta: 1.500 MC\n"
                "🐒 **Babuíno** — `5.500 MC` | Sal: 320–530 MC/h | Aposta: 4.500 MC\n"
                "🦧 **Chimpanzé** — `14.000 MC` | Sal: 780–1.320 MC/h | Aposta: 12.000 MC\n"
                "🦧 **Orangutango** — `35.000 MC` | Sal: 1.900–3.200 MC/h | Aposta: 30.000 MC\n"
                "🦍 **Gorila** — `85.000 MC` | Sal: 4.700–7.800 MC/h | Aposta: 80.000 MC\n"
                "🗿 **Ancestral** — `210.000 MC` | Sal: 11.500–19.000 MC/h | Aposta: 250.000 MC\n"
                "👑 **Rei Símio** — `600.000 MC` | Sal: 27.000–45.000 MC/h | Aposta: 1.500.000 MC"
            ), inline=False
        )
        embed.add_field(
            name="🛡️ Equipamentos",
            value=(
                "🛡️ **Escudo** — `700 MC` | Bloqueia 1 roubo.\n"
                "🕵️ **Pé de Cabra** — `1.100 MC` | Aumenta chance de roubo para 62%.\n"
                "📄 **Seguro** — `950 MC` | Recupera 60% do valor se for roubado."
            ), inline=False
        )
        embed.add_field(
            name="😈 Sabotagens e Maldades",
            value=(
                "🍌 **Casca de Banana** — `300 MC` | Próximo trabalho/roubo do alvo falha. `!casca @user`\n"
                "🦍 **Imposto do Gorila** — `2.000 MC` | Rouba 25% do trabalho do alvo por 24h. `!taxar @user`\n"
                "🪄 **Troca de Nick** — `3.000 MC` | Altera o nick do alvo por 30min. `!apelidar @user <nick>`\n\n"
                "⚡ **Comandos Diretos (sem item):**\n"
                "🙊 **Maldição Símia** — `500 MC` | Alvo fala como macaco por 1min. `!amaldicoar @user`\n"
                "🎭 **Impostor** — `500 MC` | Envia mensagem falsa como o alvo. `!impostor @user <msg>`"
            ), inline=False
        )
        embed.set_footer(text="Use !salarios para ver a progressão completa")
        await ctx.send(embed=embed)

    @commands.command()
    async def comprar(self, ctx, *, item: str = None):
        if item is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!comprar <nome do item>`")

        try:
            user_id = str(ctx.author.id)
            user = db.get_user_data(user_id)
            if not user:
                return await ctx.send("❌ Use `!trabalhar` primeiro para se registrar!")

            # ════════════════════════════════════════════════════════════════
            # PREÇOS — custo ≈ 20–22× salário médio do cargo ATUAL
            # Sem jogos: ~20h de trabalho puro por evolução.
            # Com jogos/roubos: ~10–12h por evolução.
            # Rei Símio só alcançável por jogadores muito dedicados.
            # ════════════════════════════════════════════════════════════════
            loja = {
                "macaquinho":        {"nome": "Macaquinho",        "preco": 1200.0,   "tipo": "cargo"},
                "babuíno":           {"nome": "Babuíno",           "preco": 5500.0,   "tipo": "cargo"},
                "babuino":           {"nome": "Babuíno",           "preco": 5500.0,   "tipo": "cargo"},
                "chimpanzé":         {"nome": "Chimpanzé",         "preco": 14000.0,  "tipo": "cargo"},
                "chimpanze":         {"nome": "Chimpanzé",         "preco": 14000.0,  "tipo": "cargo"},
                "orangutango":       {"nome": "Orangutango",       "preco": 35000.0,  "tipo": "cargo"},
                "gorila":            {"nome": "Gorila",            "preco": 85000.0,  "tipo": "cargo"},
                "ancestral":         {"nome": "Ancestral",         "preco": 210000.0, "tipo": "cargo"},
                "rei símio":         {"nome": "Rei Símio",         "preco": 600000.0, "tipo": "cargo"},
                "rei simio":         {"nome": "Rei Símio",         "preco": 600000.0, "tipo": "cargo"},
                "escudo":            {"nome": "Escudo",            "preco": 700.0,    "tipo": "item"},
                "pé de cabra":       {"nome": "Pé de Cabra",       "preco": 1100.0,   "tipo": "item"},
                "pe de cabra":       {"nome": "Pé de Cabra",       "preco": 1100.0,   "tipo": "item"},
                "seguro":            {"nome": "Seguro",            "preco": 950.0,    "tipo": "item"},
                "casca de banana":   {"nome": "Casca de Banana",   "preco": 300.0,    "tipo": "item"},
                "imposto do gorila": {"nome": "Imposto do Gorila", "preco": 2000.0,   "tipo": "item"},
                "troca de nick":     {"nome": "Troca de Nick",     "preco": 3000.0,   "tipo": "item"},
            }

            escolha = item.lower()
            if escolha not in loja:
                return await ctx.send("❌ Item inválido! Digite exatamente como está na `!loja`.")

            item_data = loja[escolha]
            saldo = db.parse_float(user['data'][2])
            if saldo < item_data["preco"]:
                faltam = round(item_data["preco"] - saldo, 2)
                return await ctx.send(
                    f"❌ Saldo insuficiente! Você precisa de **{item_data['preco']:.2f} MC** "
                    f"(faltam **{faltam:.2f} MC**)."
                )

            db.update_value(user['row'], 3, round(saldo - item_data["preco"], 2))

            if item_data["tipo"] == "cargo":
                db.update_value(user['row'], 4, item_data["nome"])
                await ctx.send(f"✅ {ctx.author.mention} evoluiu para o cargo **{item_data['nome']}**! 🎉")
            else:
                inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
                inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
                inv_list.append(item_data["nome"])
                db.update_value(user['row'], 6, ", ".join(inv_list))
                await ctx.send(f"🛍️ {ctx.author.mention} comprou **{item_data['nome']}** e guardou no inventário!")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !comprar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(Shop(bot))