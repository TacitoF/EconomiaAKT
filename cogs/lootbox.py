import disnake
from disnake.ext import commands
import database as db
import random
import asyncio

def formatar_moeda(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

class Lootbox(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, use as caixas no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    def sortear_comum(self):
        # 🪵 CAIXOTE DE MADEIRA (Valor base: 800 MC)
        chance = random.randint(1, 100)
        if chance <= 40:
            return {"tipo": "mc", "valor": random.randint(500, 1100), "nome": "Macacoins", "emoji": "💵"}
        elif chance <= 65:
            return {"tipo": "item", "nome": "Casca de Banana", "emoji": "🍌"}
        elif chance <= 90:
            return {"tipo": "item", "nome": "Energético Símio", "emoji": "🧪"}
        else:
            return {"tipo": "item", "nome": "Bomba de Fumaça", "emoji": "💨"}

    def sortear_raro(self):
        # 🪙 BAÚ DO CAÇADOR (Valor base: 3.500 MC)
        chance = random.randint(1, 100)
        if chance <= 35:
            return {"tipo": "mc", "valor": random.randint(2000, 4500), "nome": "Macacoins", "emoji": "💵"}
        elif chance <= 55:
            return {"tipo": "item", "nome": "Escudo", "emoji": "🛡️"}
        elif chance <= 75:
            return {"tipo": "item", "nome": "Pé de Cabra", "emoji": "🕵️"}
        elif chance <= 90:
            return {"tipo": "item", "nome": "Carga de C4", "emoji": "🧨"}
        else:
            return {"tipo": "item", "nome": "Seguro", "emoji": "📄"}

    def sortear_lendario(self):
        # 🏺 RELÍQUIA ANCESTRAL (Valor base: 15.000 MC)
        chance = random.randint(1, 100)
        if chance <= 30:
            return {"tipo": "mc", "valor": random.randint(10000, 25000), "nome": "Macacoins Fortificados", "emoji": "💰"}
        elif chance <= 55:
            return {"tipo": "item", "nome": "Estátua de Ouro", "emoji": "🗿"}
        elif chance <= 75:
            return {"tipo": "item", "nome": "Imposto do Gorila", "emoji": "🦍"}
        elif chance <= 90:
            return {"tipo": "item", "nome": "Diamante Bruto", "emoji": "💎"}
        else:
            return {"tipo": "item", "nome": "Troca de Nick", "emoji": "🪄"}

    @commands.command(aliases=["abrir"])
    async def abrir_caixa(self, ctx, *, nome_caixa: str = None):
        if nome_caixa is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, uso: `!abrir <Caixote / Baú / Relíquia>`")

        nome_caixa = nome_caixa.lower()
        if "caixote" in nome_caixa or "madeira" in nome_caixa:
            caixa_alvo = "Caixote de Madeira"
            emoji_caixa = "🪵"
            sorteio_func = self.sortear_comum
            cor_final = disnake.Color.from_rgb(139, 69, 19) # Marrom
        elif "baú" in nome_caixa or "bau" in nome_caixa or "caçador" in nome_caixa:
            caixa_alvo = "Baú do Caçador"
            emoji_caixa = "🪙"
            sorteio_func = self.sortear_raro
            cor_final = disnake.Color.blue()
        elif "relíquia" in nome_caixa or "reliquia" in nome_caixa or "ancestral" in nome_caixa:
            caixa_alvo = "Relíquia Ancestral"
            emoji_caixa = "🏺"
            sorteio_func = self.sortear_lendario
            cor_final = disnake.Color.gold()
        else:
            return await ctx.send("❌ Caixa inválida! Escolha entre: `Caixote`, `Baú` ou `Relíquia`.")

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user: return await ctx.send("❌ Você não tem conta!")

            inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]

            if caixa_alvo not in inv_list:
                return await ctx.send(f"❌ Você não tem nenhum **{caixa_alvo}** no inventário!")

            # Remove a caixa
            inv_list.remove(caixa_alvo)
            db.update_value(user['row'], 6, ", ".join(inv_list))

            # Roda o RNG
            premio = sorteio_func()

            # Suspense visual
            msg = await ctx.send(f"🔓 {ctx.author.mention} está quebrando o cadeado do **{caixa_alvo}**...")
            await asyncio.sleep(1.5)
            await msg.edit(content=f"✨ A tampa está se abrindo...")
            await asyncio.sleep(1.5)

            # Entrega o prêmio
            if premio["tipo"] == "mc":
                saldo = db.parse_float(user['data'][2])
                db.update_value(user['row'], 3, round(saldo + premio["valor"], 2))
                texto_premio = f"`{formatar_moeda(premio['valor'])} MC`"
            else:
                inv_list.append(premio["nome"])
                db.update_value(user['row'], 6, ", ".join(inv_list))
                texto_premio = f"1x **{premio['nome']}**"

            embed = disnake.Embed(
                title=f"🎉 {emoji_caixa} LOUT OBTIDO!",
                description=f"O {caixa_alvo} abriu e dentro dele você encontrou:\n\n{premio['emoji']} {texto_premio}",
                color=cor_final
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            
            if premio["nome"] in ["Energético Símio", "Bomba de Fumaça", "Carga de C4"]:
                embed.set_footer(text="Dica: Itens consumíveis são usados diretamente. Ex: !energetico")
            elif premio["nome"] in ["Estátua de Ouro", "Diamante Bruto"]:
                embed.set_footer(text="Dica: Use !vender <nome> para trocar esse tesouro por Macacoins no mercado negro!")

            await msg.edit(content="", embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !abrir de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro ao abrir a caixa. Seu item não foi perdido, tente novamente!")

def setup(bot):
    bot.add_cog(Lootbox(bot))