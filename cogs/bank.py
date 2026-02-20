import disnake
from disnake.ext import commands
import database as db
import time
import random
import asyncio

class Bank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, vá ao banco no canal {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["banco", "depositar"])
    async def investir(self, ctx, tipo: str = None, valor: int = 0):
        if not tipo or tipo.lower() not in ['cripto', 'fixo'] or valor <= 0:
            embed = disnake.Embed(title="🏦 Banco da Selva AKTrovão", color=disnake.Color.green())
            embed.add_field(name="📈 `!investir cripto <valor>`", value="Risco alto! Rende de **-25% a +25%** em 1 minuto.\n*Sem limite de valor.*", inline=False)
            embed.add_field(name="🏛️ `!investir fixo <valor>`", value="Seguro! Rende **+10%** na hora.\n*Limite: 5.000 C por dia.*", inline=False)
            return await ctx.send(embed=embed)

        user = db.get_user_data(str(ctx.author.id))
        if not user or int(user['data'][2]) < valor: return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        tipo = tipo.lower()
        agora = time.time()

        if tipo == 'fixo':
            limite = 5000
            if valor > limite: return await ctx.send(f"❌ O banco só aceita até **{limite} C** na Renda Fixa!")

            ultimo_invest = float(user['data'][7]) if len(user['data']) > 7 and user['data'][7] else 0
            if agora - ultimo_invest < 86400: 
                rh = int((86400 - (agora - ultimo_invest)) / 3600)
                rm = int(((86400 - (agora - ultimo_invest)) % 3600) / 60)
                return await ctx.send(f"⏳ {ctx.author.mention}, limite diário esgotado. Volte em **{rh}h {rm}m**.")

            lucro = int(valor * 0.10)
            db.update_value(user['row'], 3, int(user['data'][2]) + lucro)
            db.update_value(user['row'], 8, agora) 
            await ctx.send(f"🏛️ **RENDA FIXA!** Seu rendimento de 10% foi aplicado. Você ganhou **+{lucro} C**, {ctx.author.mention}!")

        elif tipo == 'cripto':
            db.update_value(user['row'], 3, int(user['data'][2]) - valor)
            await ctx.send(f"📈 {ctx.author.mention} comprou **{valor} C** em MacacoCoin (MC). O mercado fechará em 1 minuto...")

            await asyncio.sleep(60)
            user_atual = db.get_user_data(str(ctx.author.id))
            
            variacao = random.uniform(-0.25, 0.25)
            retorno = int(valor * (1 + variacao))
            lucro = retorno - valor

            db.update_value(user_atual['row'], 3, int(user_atual['data'][2]) + retorno)
            if lucro > 0: await ctx.send(f"🚀 **ALTA NO MERCADO!** A MacacoCoin valorizou! {ctx.author.mention} recebeu **{retorno} C** (`+{lucro} C`).")
            else: await ctx.send(f"📉 **CRASH NO MERCADO!** A MacacoCoin desabou... {ctx.author.mention} recebeu **{retorno} C** (`{lucro} C`).")

def setup(bot):
    bot.add_cog(Bank(bot))