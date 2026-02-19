import disnake
from disnake.ext import commands
import database as db
import random

class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != 'cassino-conguito':
            # Procuramos o objeto do canal pelo nome para criar a menção clicável
            canal = disnake.utils.get(ctx.guild.channels, name='cassino-conguito')
            mencao = canal.mention if canal else "#cassino-conguito"
            
            await ctx.send(f"🐒 Ei {ctx.author.mention}, macaco esperto joga no lugar certo! Vai para o canal {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    @commands.command()
    async def slots(self, ctx, aposta: int):
        user = db.get_user_data(str(ctx.author.id))
        if not user or aposta > int(user['data'][2]) or aposta <= 0:
            return await ctx.send("❌ Saldo insuficiente ou aposta inválida!")

        emojis = ["🍌", "🐒", "⚡", "🥥", "💎"]
        res = [random.choice(emojis) for _ in range(3)]
        
        if res[0] == res[1] == res[2]:
            ganho = aposta * 10
            status = "🎉 JACKPOT!"
        elif res[0] == res[1] or res[1] == res[2] or res[0] == res[2]:
            ganho = aposta * 2
            status = "🍌 PAR!"
        else:
            ganho = -aposta
            status = "💀 PERDEU"

        db.update_value(user['row'], 3, int(user['data'][2]) + ganho)
        await ctx.send(f"🎰 [ {' | '.join(res)} ]\n{status} Resultado: **{ganho} Conguitos**.")

    @commands.command()
    async def roubar(self, ctx, vitima: disnake.Member):
        if vitima.id == ctx.author.id: return await ctx.send("🐒 Não pode roubar de você mesmo!")
        
        ladrão = db.get_user_data(str(ctx.author.id))
        alvo = db.get_user_data(str(vitima.id))

        if not ladrão or not alvo: return await ctx.send("❌ Ambos precisam de conta!")
        
        if "Escudo" in alvo['data'][5]:
            db.update_value(alvo['row'], 6, "") # Remove o escudo após o uso
            return await ctx.send(f"🛡️ {vitima.name} tinha um Escudo! O item quebrou, mas o roubo falhou.")

        if random.randint(1, 100) <= 40:
            valor = int(int(alvo['data'][2]) * 0.2)
            db.update_value(ladrão['row'], 3, int(ladrão['data'][2]) + valor)
            db.update_value(alvo['row'], 3, int(alvo['data'][2]) - valor)
            await ctx.send(f"🥷 SUCESSO! Você roubou **{valor} Conguitos** de {vitima.name}!")
        else:
            multa = int(int(ladrão['data'][2]) * 0.15)
            db.update_value(ladrão['row'], 3, int(ladrão['data'][2]) - multa)
            db.update_value(alvo['row'], 3, int(alvo['data'][2]) + multa)
            await ctx.send(f"👮 O macaco policial te pegou! Você pagou **{multa} Conguitos** para a  vítima.")

def setup(bot):
    bot.add_cog(Games(bot))