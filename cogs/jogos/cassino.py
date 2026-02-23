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
    """Salva a conquista na coluna 10"""
    conquistas_atuais = str(user_data['data'][9]) if len(user_data['data']) > 9 else ""
    lista = [c.strip() for c in conquistas_atuais.split(',') if c.strip()]
    if slug not in lista:
        lista.append(slug)
        db.update_value(user_data['row'], 10, ", ".join(lista))

class Cassino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, macaco esperto joga no lugar certo! Vai para o canal {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    # --- 🎰 CASSINO (SLOTS) ---
    @commands.command(name="cassino")
    async def cassino_slots(self, ctx, aposta: float = None):
        if aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!cassino <valor>`")
            
        if aposta <= 0: return await ctx.send(f"⚠️ {ctx.author.mention}, valor inválido!")
        aposta = round(aposta, 2)

        user = db.get_user_data(str(ctx.author.id))
        if not user or aposta > float(user['data'][2]): 
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        cargo = user['data'][3]
        limite = get_limite(cargo)
        if aposta > limite: 
            return await ctx.send(f"🚫 Limite de aposta para **{cargo}** é de **{limite} C**!")

        # Cobra a aposta antes de rolar
        db.update_value(user['row'], 3, round(float(user['data'][2]) - aposta, 2))

        emojis = ["🍌", "🐒", "⚡", "🥥", "💎", "🦍", "🌴", "🌊"]
        res = [random.choice(emojis) for _ in range(3)]
        
        user_atual = db.get_user_data(str(ctx.author.id))

        if res[0] == res[1] == res[2]:
            lucro_bruto = round(aposta * 9.0, 2)  # Ganha 10x total (9x de lucro)
            db.update_value(user_atual['row'], 3, round(float(user_atual['data'][2]) + aposta + lucro_bruto, 2))
            
            status_msg = f"🎰 **JACKPOT!** 🎰\nVocê lucrou **{lucro_bruto:.2f} C** (Livre de taxas!)"
            save_achievement(user_atual, "filho_da_sorte")
            
        elif res[0] == res[1] or res[1] == res[2] or res[0] == res[2]:
            lucro_bruto = round(aposta * 1.0, 2)  # Ganha 2x total (1x de lucro)
            db.update_value(user_atual['row'], 3, round(float(user_atual['data'][2]) + aposta + lucro_bruto, 2))
            
            status_msg = f"Você lucrou **{lucro_bruto:.2f} C** (Livre de taxas!)"
        else:
            status_msg = f"Você perdeu **{aposta:.2f} C**"

        await ctx.send(f"🎰 **CASSINO AKTrovão** 🎰\n**[ {res[0]} | {res[1]} | {res[2]} ]**\n{ctx.author.mention}, {status_msg}!")

    # --- 🦁 JOGO DO BICHO ---
    @commands.command(name="bicho")
    async def jogo_bicho(self, ctx, bicho: str = None, aposta: float = None):
        if bicho is None or aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!bicho <animal> <valor>`\nAnimais: `leao`, `cobra`, `jacare`, `arara`, `elefante`")

        bichos = ["leao", "cobra", "jacare", "arara", "elefante"]
        bicho = bicho.lower()
        if bicho not in bichos: 
            return await ctx.send(f"❌ {ctx.author.mention}, escolha: `leao, cobra, jacare, arara, elefante`")

        if aposta <= 0: return await ctx.send("❌ Aposta inválida!")
        aposta = round(aposta, 2)

        user = db.get_user_data(str(ctx.author.id))
        if not user or aposta > float(user['data'][2]): 
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        cargo = user['data'][3]
        limite = get_limite(cargo)
        if aposta > limite: 
            return await ctx.send(f"🚫 Limite de aposta para **{cargo}** é de **{limite} C**!")

        # Cobra aposta inicial
        db.update_value(user['row'], 3, round(float(user['data'][2]) - aposta, 2))

        resultado = random.choice(bichos)
        msg = await ctx.send(f"🎰 Sorteando... {ctx.author.mention} apostou no **{bicho.upper()}**!")
        await asyncio.sleep(2)

        user_atual = db.get_user_data(str(ctx.author.id))

        if bicho == resultado:
            lucro_bruto = round(aposta * 4.0, 2) # Prêmio 5x total (4x de lucro)
            db.update_value(user_atual['row'], 3, round(float(user_atual['data'][2]) + aposta + lucro_bruto, 2))
            
            await msg.edit(content=f"🎉 {ctx.author.mention} DEU **{resultado.upper()}**! Você faturou **{lucro_bruto:.2f} C** de lucro (Isento de taxas)!")
        else:
            await msg.edit(content=f"💀 {ctx.author.mention} DEU **{resultado.upper()}**! Perdeu **{aposta:.2f} C**.")

    # --- 🐒 CORRIDA SÍMIA ---
    @commands.command(name="corrida")
    async def corrida_macaco(self, ctx, escolha: str = None, aposta: float = None):
        if escolha is None or aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!corrida <animal> <valor>`\nAnimais: `macaquinho`, `gorila`, `orangutango`")

        opcoes = {"macaquinho": "🐒", "gorila": "🦍", "orangutango": "🦧"}
        escolha = escolha.lower()
        if escolha not in opcoes: 
            return await ctx.send(f"❌ {ctx.author.mention}, escolha: `macaquinho`, `gorila` ou `orangutango`.")

        if aposta <= 0: return await ctx.send("❌ Aposta inválida!")
        aposta = round(aposta, 2)

        user = db.get_user_data(str(ctx.author.id))
        if not user or aposta > float(user['data'][2]): 
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        cargo = user['data'][3]
        limite = get_limite(cargo)
        if aposta > limite: 
            return await ctx.send(f"🚫 Limite de aposta para **{cargo}** é de **{limite} C**!")

        # Cobra aposta inicial
        db.update_value(user['row'], 3, round(float(user['data'][2]) - aposta, 2))

        macacos_lista = list(opcoes.values())
        nomes_lista = list(opcoes.keys())
        pistas = [0, 0, 0]
        chegada = 10
        
        msg = await ctx.send(f"🏁 **A CORRIDA COMEÇOU!** {ctx.author.mention} apostou no **{escolha.capitalize()}**!\n\n" + "\n".join([f"{macacos_lista[i]} 🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦 🏁" for i in range(3)]))

        vencedor_idx = -1
        while vencedor_idx == -1:
            await asyncio.sleep(1.2)
            for i in range(3):
                pistas[i] += random.randint(1, 3)
                if pistas[i] >= chegada:
                    vencedor_idx = i
                    break
            
            frame = []
            for i in range(3):
                progresso = min(pistas[i], chegada)
                pista_str = "🟩" * progresso + "🟦" * (chegada - progresso)
                frame.append(f"{macacos_lista[i]} {pista_str} 🏁")
            await msg.edit(content=f"🏁 **A CORRIDA ESTÁ QUENTE!**\n\n" + "\n".join(frame))

        nome_vencedor = nomes_lista[vencedor_idx]
        user_atual = db.get_user_data(str(ctx.author.id))

        if escolha == nome_vencedor:
            lucro_bruto = round(aposta * 2.0, 2) # Prêmio total é 3x (lucro de 2x)
            db.update_value(user_atual['row'], 3, round(float(user_atual['data'][2]) + aposta + lucro_bruto, 2))
            
            await ctx.send(f"🏆 {ctx.author.mention} **VITÓRIA!** O {nome_vencedor.capitalize()} cruzou primeiro! Lucrou **{lucro_bruto:.2f} C** (Livre de taxas!).")
        else:
            await ctx.send(f"💀 {ctx.author.mention} **DERROTA!** O {nome_vencedor.capitalize()} venceu a corrida. Você perdeu **{aposta:.2f} C**.")

def setup(bot):
    bot.add_cog(Cassino(bot))