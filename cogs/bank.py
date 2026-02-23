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
    async def investir(self, ctx, tipo: str = None, valor: float = None):
        if not tipo or tipo.lower() not in ['cripto', 'fixo'] or valor is None or valor <= 0:
            embed = disnake.Embed(title="🏦 Banco da Selva AKTrovão", color=disnake.Color.green())
            embed.add_field(name="📈 `!investir cripto <valor>`", value="Risco alto! Rende de **-25% a +25%** em 1 minuto.", inline=False)
            embed.add_field(name="🏛️ `!investir fixo <valor>`", value="Seguro! Rende **+10%** na hora. *Limite: 5.000 C por dia.*", inline=False)
            return await ctx.send(embed=embed)

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send(f"❌ {ctx.author.mention}, conta não encontrada!")

            tipo = tipo.lower()
            agora = time.time()
            valor = round(valor, 2)
            saldo = db.parse_float(user['data'][2])

            if saldo < valor:
                return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

            if tipo == 'fixo':
                if valor > 5000.0:
                    return await ctx.send("❌ O banco só aceita até **5.000 C** na Renda Fixa por operação!")

                ultimo_invest = db.parse_float(user['data'][7] if len(user['data']) > 7 else None)
                if agora - ultimo_invest < 86400:
                    return await ctx.send(f"⏳ {ctx.author.mention}, limite diário esgotado! Volte <t:{int(ultimo_invest + 86400)}:R>.")

                lucro = round(valor * 0.10, 2)
                db.update_value(user['row'], 3, round(saldo + lucro, 2))
                db.update_value(user['row'], 8, agora)
                await ctx.send(f"🏛️ **RENDA FIXA!** Rendimento de 10% aplicado. Você ganhou **+{lucro:.2f} C**, {ctx.author.mention}!")

            elif tipo == 'cripto':
                db.update_value(user['row'], 3, round(saldo - valor, 2))
                await ctx.send(f"📈 {ctx.author.mention} comprou **{valor:.2f} C** em MacacoCoin. O mercado fecha em 1 minuto... 💸")
                await asyncio.sleep(60)

                user_atual = db.get_user_data(str(ctx.author.id))
                variacao = random.uniform(-0.25, 0.25)
                retorno = round(valor * (1 + variacao), 2)
                lucro = round(retorno - valor, 2)

                db.update_value(user_atual['row'], 3, round(db.parse_float(user_atual['data'][2]) + retorno, 2))

                if lucro >= 0:
                    await ctx.send(f"🚀 **ALTA!** {ctx.author.mention} resgatou **{retorno:.2f} C** (Lucro: `+{lucro:.2f} C`).")
                else:
                    await ctx.send(f"📉 **CRASH!** {ctx.author.mention} resgatou apenas **{retorno:.2f} C** (Prejuízo: `{lucro:.2f} C`).")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !investir de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(Bank(bot))