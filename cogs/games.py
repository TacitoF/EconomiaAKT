import disnake
from disnake.ext import commands
import database as db
import random

class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def roubar(self, ctx, vitima: disnake.Member):
        if vitima.id == ctx.author.id: return await ctx.send("🐒 Não te podes roubar a ti mesmo!")
        
        ladrão = db.get_user_data(str(ctx.author.id))
        alvo = db.get_user_data(str(vitima.id))

        if not ladrão or not alvo: return await ctx.send("❌ Ambos precisam de conta!")
        
        if "Escudo" in alvo['data'][5]:
            return await ctx.send(f"🛡️ {vitima.name} tem um Escudo! Falhaste.")

        if random.randint(1, 100) <= 40:
            valor = int(int(alvo['data'][2]) * 0.2)
            db.update_value(ladrão['row'], 3, int(ladrão['data'][2]) + valor)
            db.update_value(alvo['row'], 3, int(alvo['data'][2]) - valor)
            await ctx.send(f"🥷 Sucesso! Roubaste **{valor} Conguitos**!")
        else:
            multa = int(int(ladrão['data'][2]) * 0.1)
            db.update_value(ladrão['row'], 3, int(ladrão['data'][2]) - multa)
            await ctx.send(f"👮 Foste apanhado! Pagaste **{multa} Conguitos** de multa.")

    @commands.command()
    async def slots(self, ctx, aposta: int):
        user = db.get_user_data(str(ctx.author.id))
        if not user or aposta > int(user['data'][2]): return await ctx.send("❌ Saldo insuficiente!")

        emojis = ["🍌", "🐒", "⚡"]
        res = [random.choice(emojis) for _ in range(3)]
        
        if res[0] == res[1] == res[2]:
            ganho = aposta * 5
            await ctx.send(f"🎰 [{'|'.join(res)}] - JACKPOT! Ganhaste **{ganho}**!")
        else:
            ganho = -aposta
            await ctx.send(f"🎰 [{'|'.join(res)}] - Perdeste **{aposta}**.")
            
        db.update_value(user['row'], 3, int(user['data'][2]) + ganho)

def setup(bot):
    bot.add_cog(Games(bot))