import disnake
from disnake.ext import commands
import database as db
import random
import asyncio

def get_limite(cargo):
    """Limites da V4.4 para os jogos"""
    limites = {
        "Lêmure": 250, "Macaquinho": 800, "Babuíno": 2000, "Chimpanzé": 6000,
        "Orangutango": 15000, "Gorila": 45000, "Ancestral": 150000, "Rei Símio": 1500000
    }
    return limites.get(cargo, 250)

def save_achievement(user_data, slug):
    conquistas_atuais = str(user_data['data'][9]) if len(user_data['data']) > 9 else ""
    lista = [c.strip() for c in conquistas_atuais.split(',') if c.strip()]
    if slug not in lista:
        lista.append(slug)
        db.update_value(user_data['row'], 10, ", ".join(lista))

class PvP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, resolva suas rixas no canal {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    # --- 🃏 DUELO DE CARTAS ---
    @commands.command(aliases=["cartas", "duelo_carta", "draw"])
    async def carta(self, ctx, oponente: disnake.Member = None, aposta: float = None):
        # MENSAGEM DE AJUDA
        if oponente is None or aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, formato incorreto!\nUse: `!carta @usuario <valor>`")

        if oponente.id == ctx.author.id: 
            return await ctx.send(f"🃏 {ctx.author.mention}, você não pode jogar cartas contra o espelho!")
            
        if aposta <= 0: return await ctx.send(f"❌ {ctx.author.mention}, a aposta deve ser maior que zero!")
        aposta = round(aposta, 2)

        desafiante_db = db.get_user_data(str(ctx.author.id))
        oponente_db = db.get_user_data(str(oponente.id))

        if not desafiante_db or not oponente_db:
            return await ctx.send("❌ Uma das contas não foi encontrada no banco da selva!")

        if float(oponente_db['data'][2]) < aposta or float(desafiante_db['data'][2]) < aposta: 
            return await ctx.send(f"❌ {ctx.author.mention}, alguém na mesa não tem saldo para cobrir essa aposta!")

        limite = get_limite(desafiante_db['data'][3])
        if aposta > limite: 
            return await ctx.send(f"🚫 Limite de aposta para **{desafiante_db['data'][3]}** é de **{limite} C**!")

        await ctx.send(f"🃏 {oponente.mention}, você foi desafiado por {ctx.author.mention} para um Duelo de Cartas valendo **{aposta:.2f} C**! Digite `comprar` no chat para aceitar e sacar sua carta!")

        def check(m): return m.author == oponente and m.content.lower() == 'comprar' and m.channel == ctx.channel
        
        try: 
            await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError: 
            return await ctx.send(f"⏱️ {oponente.mention} demorou demais. O duelo foi cancelado!")

        # Re-checagem de saldo anti-fraude
        d_db_atual = db.get_user_data(str(ctx.author.id))
        o_db_atual = db.get_user_data(str(oponente.id))
        if float(d_db_atual['data'][2]) < aposta or float(o_db_atual['data'][2]) < aposta:
            return await ctx.send("🚨 Fraude detectada! Alguém gastou o dinheiro antes do duelo começar. Partida cancelada.")

        valores = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        naipes = ["♠️", "♥️", "♦️", "♣️"]
        
        carta_desafiante_valor = random.choice(valores)
        carta_oponente_valor = random.choice(valores)
        carta_desafiante_naipe = random.choice(naipes)
        carta_oponente_naipe = random.choice(naipes)
        
        while carta_desafiante_valor == carta_oponente_valor and carta_desafiante_naipe == carta_oponente_naipe:
            carta_oponente_naipe = random.choice(naipes)

        peso_desafiante = valores.index(carta_desafiante_valor)
        peso_oponente = valores.index(carta_oponente_valor)

        embed = disnake.Embed(title="🃏 DUELO DE CARTAS 🃏", color=disnake.Color.dark_theme())
        embed.add_field(name=f"Sacado por {ctx.author.display_name}:", value=f"**{carta_desafiante_valor}** {carta_desafiante_naipe}", inline=True)
        embed.add_field(name=f"Sacado por {oponente.display_name}:", value=f"**{carta_oponente_valor}** {carta_oponente_naipe}", inline=True)

        if peso_desafiante == peso_oponente:
            db.update_value(d_db_atual['row'], 3, round(float(d_db_atual['data'][2]) - aposta, 2))
            db.update_value(o_db_atual['row'], 3, round(float(o_db_atual['data'][2]) - aposta, 2))
            embed.description = f"🤝 **EMPATE!** Vossas cartas têm o mesmo peso.\nAmbos perdem a aposta de **{aposta:.2f} C** para o Cassino!"
            return await ctx.send(embed=embed)

        vencedor = ctx.author if peso_desafiante > peso_oponente else oponente
        perdedor = oponente if peso_desafiante > peso_oponente else ctx.author

        v_db = db.get_user_data(str(vencedor.id))
        p_db = db.get_user_data(str(perdedor.id))
        
        # O vencedor lucra o valor da aposta (isento de taxas), o perdedor perde a aposta
        db.update_value(v_db['row'], 3, round(float(v_db['data'][2]) + aposta, 2))
        db.update_value(p_db['row'], 3, round(float(p_db['data'][2]) - aposta, 2))

        embed.description = f"🏆 A carta de **{vencedor.mention}** foi maior! Faturou **{aposta:.2f} C** de lucro (Livre de taxas!)."
        await ctx.send(embed=embed)

    # --- 🥊 BRIGA DE MACACO ---
    @commands.command(aliases=["briga", "brigar", "luta", "lutar", "x1"])
    async def briga_macaco(self, ctx, vitima: disnake.Member = None, aposta: float = None):
        # MENSAGEM DE AJUDA
        if vitima is None or aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, formato incorreto!\nUse: `!briga @usuario <valor>`")

        if vitima.id == ctx.author.id: 
            return await ctx.send(f"🐒 {ctx.author.mention}, não brigue consigo mesmo!")
        
        if aposta <= 0: return await ctx.send("❌ Aposta inválida!")
        aposta = round(aposta, 2)
        
        ladrao = db.get_user_data(str(ctx.author.id))
        alvo = db.get_user_data(str(vitima.id))

        if not ladrao or not alvo:
            return await ctx.send("❌ Uma das contas não foi encontrada!")

        if float(alvo['data'][2]) < aposta or float(ladrao['data'][2]) < aposta: 
            return await ctx.send(f"❌ {ctx.author.mention}, alguém não tem saldo para essa briga!")

        limite = get_limite(ladrao['data'][3])
        if aposta > limite: 
            return await ctx.send(f"🚫 Limite de aposta para **{ladrao['data'][3]}** é de **{limite} C**!")

        if aposta == 1.0:
            save_achievement(ladrao, "briga_de_bar")

        await ctx.send(f"🥊 {vitima.mention}, {ctx.author.mention} te desafiou para uma briga por **{aposta:.2f} C**! Digite `aceitar` para lutar!")

        def check(m): return m.author == vitima and m.content.lower() == 'aceitar' and m.channel == ctx.channel
        
        try:
            await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send(f"⏱️ {vitima.mention} amarelou e fugiu da briga!")

        # Re-checagem anti-fraude
        l_db_atual = db.get_user_data(str(ctx.author.id))
        a_db_atual = db.get_user_data(str(vitima.id))
        if float(l_db_atual['data'][2]) < aposta or float(a_db_atual['data'][2]) < aposta:
            return await ctx.send("🚨 Fraude detectada! Alguém gastou o dinheiro antes da porrada comer. Briga cancelada.")

        vencedor = random.choice([ctx.author, vitima])
        perdedor = vitima if vencedor == ctx.author else ctx.author
        
        v_db = db.get_user_data(str(vencedor.id))
        p_db = db.get_user_data(str(perdedor.id))

        # O vencedor lucra o valor da aposta (isento de taxas), o perdedor perde a aposta
        db.update_value(v_db['row'], 3, round(float(v_db['data'][2]) + aposta, 2))
        db.update_value(p_db['row'], 3, round(float(p_db['data'][2]) - aposta, 2))
        
        await ctx.send(f"🏆 **{vencedor.mention}** nocauteou {perdedor.mention} e lucrou **{aposta:.2f} C** (Livre de taxas!)")

def setup(bot):
    bot.add_cog(PvP(bot))