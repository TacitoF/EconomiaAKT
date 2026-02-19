import disnake
from disnake.ext import commands
import database as db
import random
import asyncio

class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        """Restringe todos os comandos deste Cog ao canal #🎰・akbet."""
        if ctx.channel.name != '🎰・akbet':
            # Tenta encontrar o canal para criar a menção azul clicável
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            
            await ctx.send(f"🐒 Ei {ctx.author.mention}, macaco esperto joga no lugar certo! Vai para o canal {mencao}.")
            raise commands.CommandError("Canal de apostas incorreto.")

    # --- 1. CORRIDA DE MACACOS ---
    @commands.command(name="corrida")
    async def corrida_macaco(self, ctx, escolha: str, aposta: int):
        """Aposte em um macaco: macaquinho, gorila ou orangutango."""
        opcoes = {
            "macaquinho": "🐒",
            "gorila": "🦍",
            "orangutango": "🦧"
        }
        
        escolha = escolha.lower()
        if escolha not in opcoes:
            return await ctx.send(f"❌ {ctx.author.mention}, escolha um competidor válido: `macaquinho`, `gorila` ou `orangutango`.")

        user = db.get_user_data(str(ctx.author.id))
        if not user or aposta > int(user['data'][2]) or aposta <= 0:
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        macacos_lista = list(opcoes.values())
        nomes_lista = list(opcoes.keys())
        pistas = [0, 0, 0]
        chegada = 10
        
        msg = await ctx.send(f"🏁 **A CORRIDA COMEÇOU!** {ctx.author.mention} apostou no **{escolha.capitalize()}**!\n\n" + 
                             "\n".join([f"{macacos_lista[i]} 🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦 🏁" for i in range(3)]))

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
        
        if escolha == nome_vencedor:
            ganho = aposta * 3
            res_msg = f"🏆 **VITÓRIA!** O {nome_vencedor.capitalize()} cruzou primeiro! Você ganhou **{ganho} conguitos**."
        else:
            ganho = -aposta
            res_msg = f"💀 **DERROTA!** O {nome_vencedor.capitalize()} venceu a corrida. Você perdeu **{aposta} conguitos**."

        db.update_value(user['row'], 3, int(user['data'][2]) + ganho)
        await ctx.send(f"{ctx.author.mention} {res_msg}")

    # --- 2. JOGO DO BICHO ---
    @commands.command(name="bicho")
    async def jogo_bicho(self, ctx, bicho: str, aposta: int):
        bichos = ["leao", "cobra", "jacare", "arara", "elefante"]
        bicho = bicho.lower()
        if bicho not in bichos:
            return await ctx.send(f"❌ {ctx.author.mention}, escolha entre: `leao, cobra, jacare, arara, elefante`")

        user = db.get_user_data(str(ctx.author.id))
        if not user or aposta > int(user['data'][2]) or aposta <= 0:
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        resultado = random.choice(bichos)
        msg = await ctx.send(f"🎰 Sorteando... {ctx.author.mention} apostou no **{bicho.upper()}**!")
        await asyncio.sleep(2)

        ganho = aposta * 5 if bicho == resultado else -aposta
        txt = f"🎉 DEU **{resultado.upper()}**! Você ganhou **{ganho} C**!" if ganho > 0 else f"💀 DEU **{resultado.upper()}**! Perdeu **{aposta} C**."
        
        await msg.edit(content=f"{ctx.author.mention} {txt}")
        db.update_value(user['row'], 3, int(user['data'][2]) + ganho)

    # --- 3. CAMPO MINADO ---
    @commands.command(name="minas")
    async def campo_minado(self, ctx, bombas: int, aposta: int):
        if not (1 <= bombas <= 5):
            return await ctx.send(f"❌ {ctx.author.mention}, escolha entre 1 e 5 bombas.")

        user = db.get_user_data(str(ctx.author.id))
        if not user or aposta > int(user['data'][2]) or aposta <= 0:
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        await ctx.send(f"💣 {ctx.author.mention} entrando no campo com {bombas} bombas...")
        await asyncio.sleep(1.5)

        if random.randint(1, 10) > (bombas * 1.5):
            mult = 1.5 + (bombas * 0.5)
            ganho = int(aposta * mult)
            status = f"🚩 **LIMPO!** {ctx.author.mention} ganhou **{ganho} conguitos**! ({mult}x)"
        else:
            ganho = -aposta
            status = f"💥 **BOOOOM!** {ctx.author.mention} pisou em uma mina e perdeu **{aposta} C**."

        db.update_value(user['row'], 3, int(user['data'][2]) + ganho)
        await ctx.send(status)

    # --- 4. BRIGA DE MACACO (PvP) ---
    @commands.command(name="briga")
    async def briga_macaco(self, ctx, vitima: disnake.Member, aposta: int):
        if vitima.id == ctx.author.id: return await ctx.send(f"🐒 {ctx.author.mention}, não brigue consigo mesmo!")
        
        ladrao = db.get_user_data(str(ctx.author.id))
        alvo = db.get_user_data(str(vitima.id))

        if not ladrao or not alvo or int(alvo['data'][2]) < aposta or int(ladrao['data'][2]) < aposta:
            return await ctx.send(f"❌ {ctx.author.mention}, alguém não tem saldo para essa briga!")

        await ctx.send(f"🥊 {vitima.mention}, {ctx.author.mention} te desafiou para uma briga por **{aposta} C**! Digite `aceitar` para lutar!")

        def check(m): return m.author == vitima and m.content.lower() == 'aceitar' and m.channel == ctx.channel
        try:
            await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send(f"⏱️ {vitima.mention} amarelou e fugiu da briga!")

        vencedor = random.choice([ctx.author, vitima])
        perdedor = vitima if vencedor == ctx.author else ctx.author
        
        v_db = db.get_user_data(str(vencedor.id))
        p_db = db.get_user_data(str(perdedor.id))

        db.update_value(v_db['row'], 3, int(v_db['data'][2]) + aposta)
        db.update_value(p_db['row'], 3, int(p_db['data'][2]) - aposta)
        await ctx.send(f"🏆 **{vencedor.mention}** nocauteou {perdedor.mention} e levou o pote de **{aposta} C**!")

    # --- 5. MOEDA E CASSINO ---
    @commands.command(name="moeda")
    async def cara_coroa(self, ctx, lado: str, aposta: int):
        user = db.get_user_data(str(ctx.author.id))
        if not user or aposta > int(user['data'][2]) or aposta <= 0: return
        res = random.choice(["cara", "coroa"])
        ganho = aposta if lado.lower() == res else -aposta
        db.update_value(user['row'], 3, int(user['data'][2]) + ganho)
        await ctx.send(f"🪙 {ctx.author.mention} | Caiu {res.upper()}! {'✅ Ganhou' if ganho > 0 else '❌ Perdeu'}.")

    @commands.command(name="cassino")
    async def cassino_slots(self, ctx, aposta: int):
        user = db.get_user_data(str(ctx.author.id))
        if not user or aposta > int(user['data'][2]) or aposta <= 0: return
        emojis = ["🍌", "🐒", "⚡", "🥥", "💎"]
        res = [random.choice(emojis) for _ in range(3)]
        ganho = aposta * 10 if res[0] == res[1] == res[2] else (aposta * 2 if res[0] == res[1] or res[1] == res[2] or res[0] == res[2] else -aposta)
        db.update_value(user['row'], 3, int(user['data'][2]) + ganho)
        await ctx.send(f"🎰 [ {' | '.join(res)} ] | {ctx.author.mention}: {ganho} C")

def setup(bot):
    bot.add_cog(Games(bot))