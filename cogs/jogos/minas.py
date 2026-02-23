import disnake
from disnake.ext import commands
import database as db
import random
import asyncio

LIMITES_CARGO = {
    "Lêmure": 250, "Macaquinho": 800, "Babuíno": 2000, "Chimpanzé": 6000,
    "Orangutango": 15000, "Gorila": 45000, "Ancestral": 150000, "Rei Símio": 1500000
}

def get_limite(cargo):
    return LIMITES_CARGO.get(cargo, 250)

class MinasGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, vá para o canal {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(name="minas")
    async def campo_minado(self, ctx, bombas: int = None, aposta: float = None):
        if bombas is None or aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!minas <1-5 bombas> <valor>`")
        if not (1 <= bombas <= 5):
            return await ctx.send(f"❌ {ctx.author.mention}, escolha entre 1 e 5 bombas.")
        if aposta <= 0:
            return await ctx.send(f"❌ {ctx.author.mention}, aposta inválida!")
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
            await ctx.send(f"💣 {ctx.author.mention} entra no campo com {bombas} minas... 🏃💨")
            await asyncio.sleep(1.5)

            tabela_risco = {
                1: {"chance": 85, "mult": 1.10},
                2: {"chance": 70, "mult": 1.30},
                3: {"chance": 60, "mult": 1.50},
                4: {"chance": 50, "mult": 1.75},
                5: {"chance": 40, "mult": 2.00}
            }
            config = tabela_risco[bombas]
            user_atual = db.get_user_data(str(ctx.author.id))
            saldo_atual = db.parse_float(user_atual['data'][2])

            if random.randint(1, 100) <= config["chance"]:
                ganho_total = round(aposta * config["mult"], 2)
                lucro = round(ganho_total - aposta, 2)
                db.update_value(user_atual['row'], 3, round(saldo_atual + ganho_total, 2))

                if bombas == 5:
                    conquistas = str(user_atual['data'][9]) if len(user_atual['data']) > 9 else ""
                    lista = [c.strip() for c in conquistas.split(',') if c.strip()]
                    if "esquadrao_suicida" not in lista:
                        lista.append("esquadrao_suicida")
                        db.update_value(user_atual['row'], 10, ", ".join(lista))

                await ctx.send(f"🚩 **LIMPO!** {ctx.author.mention} sobreviveu e faturou **{ganho_total:.2f} C** de lucro! (`{config['mult']}x`)")
            else:
                if bombas == 1:
                    conquistas = str(user_atual['data'][9]) if len(user_atual['data']) > 9 else ""
                    lista = [c.strip() for c in conquistas.split(',') if c.strip()]
                    if "escorregou_banana" not in lista:
                        lista.append("escorregou_banana")
                        db.update_value(user_atual['row'], 10, ", ".join(lista))

                await ctx.send(f"💥 **BOOOOM!** {ctx.author.mention} pisou em uma mina e virou paçoca. Perdeu **{aposta:.2f} C**.")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !minas de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(MinasGame(bot))