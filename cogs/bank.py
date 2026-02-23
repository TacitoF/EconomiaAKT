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
        # PAINEL DE AJUDA SE FALTAR DADOS OU VALOR INVÁLIDO
        if not tipo or tipo.lower() not in ['cripto', 'fixo'] or valor is None or valor <= 0:
            embed = disnake.Embed(title="🏦 Banco da Selva AKTrovão", color=disnake.Color.green())
            embed.add_field(name="📈 `!investir cripto <valor>`", value="Risco alto! Rende de **-25% a +25%** em 1 minuto.\n*Sem limite de valor.*", inline=False)
            embed.add_field(name="🏛️ `!investir fixo <valor>`", value="Seguro! Rende **+10%** na hora.\n*Limite: 5.000 C por dia.*", inline=False)
            embed.set_footer(text="Use números decimais se quiser, ex: !investir cripto 150.50")
            return await ctx.send(embed=embed)

        user = db.get_user_data(str(ctx.author.id))
        if not user or float(user['data'][2]) < valor: 
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        tipo = tipo.lower()
        agora = time.time()
        valor = round(valor, 2)

        if tipo == 'fixo':
            limite_valor = 5000.0
            if valor > limite_valor: 
                return await ctx.send(f"❌ O banco só aceita até **{limite_valor} C** na Renda Fixa por operação!")

            # Verifica o cooldown diário (coluna 8 / índice 7)
            ultimo_invest = float(user['data'][7]) if len(user['data']) > 7 and user['data'][7] else 0
            if agora - ultimo_invest < 86400: 
                tempo_liberacao = int(ultimo_invest + 86400)
                return await ctx.send(f"⏳ {ctx.author.mention}, limite diário esgotado! Você poderá investir novamente <t:{tempo_liberacao}:R>.")

            lucro = round(valor * 0.10, 2)
            db.update_value(user['row'], 3, round(float(user['data'][2]) + lucro, 2))
            db.update_value(user['row'], 8, agora) 
            
            await ctx.send(f"🏛️ **RENDA FIXA!** Seu rendimento de 10% foi aplicado com sucesso.\nVocê ganhou **+{lucro:.2f} C**, {ctx.author.mention}!")

        elif tipo == 'cripto':
            # Retira o investimento inicial
            db.update_value(user['row'], 3, round(float(user['data'][2]) - valor, 2))
            await ctx.send(f"📈 {ctx.author.mention} comprou **{valor:.2f} C** em MacacoCoin (MC). O mercado fechará em 1 minuto... 💸")

            await asyncio.sleep(60)
            user_atual = db.get_user_data(str(ctx.author.id))
            
            # Variação de -25% a +25%
            variacao = random.uniform(-0.25, 0.25)
            retorno = round(valor * (1 + variacao), 2)
            lucro = round(retorno - valor, 2)

            db.update_value(user_atual['row'], 3, round(float(user_atual['data'][2]) + retorno, 2))
            
            if lucro >= 0:
                await ctx.send(f"🚀 **ALTA NO MERCADO!** A MacacoCoin valorizou! {ctx.author.mention} resgatou **{retorno:.2f} C** (Lucro: `+{lucro:.2f} C`).")
            else:
                await ctx.send(f"📉 **CRASH NO MERCADO!** A MacacoCoin desabou... {ctx.author.mention} resgatou apenas **{retorno:.2f} C** (Prejuízo: `{lucro:.2f} C`).")

def setup(bot):
    bot.add_cog(Bank(bot))