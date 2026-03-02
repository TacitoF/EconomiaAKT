import disnake
from disnake.ext import commands
import database as db
import time

ESCUDO_CARGAS = 3

def formatar_moeda(valor: float) -> str:
    """Formata um float para o padrão brasileiro de moeda. Ex: 1234.56 -> 1.234,56"""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

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
            description="Compra usando `!comprar <nome do item>`",
            color=disnake.Color.blue()
        )
        embed.add_field(
            name="📈 Cargos (Aumenta Salário e Limite de Aposta)",
            value=(
                "🐒 **Macaquinho** — `1.200 MC` | Sal: 130–230 MC/h | Aposta: 1.500 MC\n"
                "🐵 **Babuíno** — `5.500 MC` | Sal: 320–530 MC/h | Aposta: 4.500 MC\n"
                "🌴 **Chimpanzé** — `14.000 MC` | Sal: 780–1.320 MC/h | Aposta: 12.000 MC\n"
                "🦧 **Orangutango** — `35.000 MC` | Sal: 1.900–3.200 MC/h | Aposta: 30.000 MC\n"
                "🦍 **Gorila** — `85.000 MC` | Sal: 4.700–7.800 MC/h | Aposta: 80.000 MC\n"
                "🗿 **Ancestral** — `210.000 MC` | Sal: 11.500–19.000 MC/h | Aposta: 250.000 MC\n"
                "👑 **Rei Símio** — `600.000 MC` | Sal: 27.000–45.000 MC/h | Aposta: 1.500.000 MC"
            ), inline=False
        )
        embed.add_field(
            name="🛡️ Equipamentos",
            value=(
                "🛡️ **Escudo** — `1.000 MC` | Bloqueia **3 tentativas de roubo**. Limite: **1 por dia**.\n"
                "🕵️ **Pé de Cabra** — `1.200 MC` | Aumenta chance de roubo para 65% e perfura o Escudo.\n"
                "📄 **Seguro** — `950 MC` | Recupera 60% do valor se fores roubado."
            ), inline=False
        )
        embed.add_field(
            name="😈 Sabotagens e Maldades",
            value=(
                "🍌 **Casca de Banana** — `300 MC` | Próximo trabalho/roubo do alvo falha. `!casca @user`\n"
                "🦍 **Imposto do Gorila** — `1.500 MC` | Rouba 25% dos próximos **5 trabalhos** do alvo. `!taxar @user`\n"
                "🪄 **Troca de Nick** — `3.000 MC` | Altera o nick do alvo por 30min. `!apelidar @user <nick>`\n\n"
                "⚡ **Comandos Diretos (sem item):**\n"
                "🙊 **Maldição Símia** — `500 MC` | O alvo fala como macaco por 1min. `!amaldicoar @user`\n"
                "🎭 **Impostor** — `500 MC` | Envia mensagem falsa como o alvo. `!impostor @user <msg>`"
            ), inline=False
        )
        embed.set_footer(text="Usa !salarios para ver a progressão completa")
        await ctx.send(embed=embed)

    @commands.command()
    async def comprar(self, ctx, *, item: str = None):
        if item is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, uso: `!comprar <nome do item>`")

        try:
            user_id = str(ctx.author.id)
            user = db.get_user_data(user_id)
            if not user:
                return await ctx.send("❌ Usa `!trabalhar` primeiro para te registares!")

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
                "escudo":            {"nome": "Escudo",            "preco": 1000.0,   "tipo": "item"},
                "pé de cabra":       {"nome": "Pé de Cabra",       "preco": 1200.0,   "tipo": "item"},
                "pe de cabra":       {"nome": "Pé de Cabra",       "preco": 1200.0,   "tipo": "item"},
                "seguro":            {"nome": "Seguro",            "preco": 950.0,    "tipo": "item"},
                "casca de banana":   {"nome": "Casca de Banana",   "preco": 300.0,    "tipo": "item"},
                "imposto do gorila": {"nome": "Imposto do Gorila", "preco": 1500.0,   "tipo": "item"},
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
                    f"❌ Saldo insuficiente! Precisas de **{formatar_moeda(item_data['preco'])} MC** "
                    f"(faltam **{formatar_moeda(faltam)} MC**)."
                )

            db.update_value(user['row'], 3, round(saldo - item_data["preco"], 2))

            if item_data["tipo"] == "cargo":
                db.update_value(user['row'], 4, item_data["nome"])
                await ctx.send(f"✅ {ctx.author.mention} evoluiu para o cargo **{item_data['nome']}**! 🎉")

            else:
                inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
                inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]

                # ── ESCUDO: preço fixo 1.000 MC, máx 1 compra por dia ────────
                if item_data["nome"] == "Escudo":
                    agora = time.time()

                    escudo_ativo = hasattr(self.bot, 'escudos_ativos') and \
                                   self.bot.escudos_ativos.get(user_id, 0) > 0
                    if "Escudo" in inv_list or escudo_ativo:
                        db.update_value(user['row'], 3, round(saldo, 2))  # estorna
                        return await ctx.send(
                            f"❌ {ctx.author.mention}, você já tem um **Escudo** "
                            f"{'ativo' if escudo_ativo else 'no inventário'}! "
                            f"Só pode ter 1 de cada vez."
                        )

                    historico = self.bot.escudo_compras.get(user_id, (0, 0.0))
                    ultima_compra_ts = historico[1]

                    if agora - ultima_compra_ts < 86400:
                        libera_em = int(ultima_compra_ts + 86400)
                        db.update_value(user['row'], 3, round(saldo, 2))  # estorna
                        return await ctx.send(
                            f"⏳ {ctx.author.mention}, você já comprou um **Escudo** hoje! "
                            f"Pode comprar outro <t:{libera_em}:R>."
                        )

                    self.bot.escudo_compras[user_id] = (1, agora)

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