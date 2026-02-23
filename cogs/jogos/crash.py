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

class CrashGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, macaco esperto voa no canal {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    # --- 🚀 CRASH DO CIPÓ (FOGUETINHO) ---
    @commands.command(aliases=["cipo", "foguetinho"])
    async def crash(self, ctx, aposta: float = None):
        # MENSAGEM DE AJUDA
        if aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, formato incorreto!\nUse: `!crash <valor>`")

        if aposta <= 0: 
            return await ctx.send(f"❌ {ctx.author.mention}, a aposta deve ser maior que zero!")
            
        aposta = round(aposta, 2)
        user = db.get_user_data(str(ctx.author.id))
        
        if not user or float(user['data'][2]) < aposta: 
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        cargo = user['data'][3]
        limite = get_limite(cargo)
        if aposta > limite: 
            return await ctx.send(f"🚫 Limite de aposta para **{cargo}** é de **{limite} C**!")

        # 🛡️ Cobrança adiantada (Anti-Fraude)
        db.update_value(user['row'], 3, round(float(user['data'][2]) - aposta, 2))

        # Algoritmo de Probabilidade do Crash
        chance = random.random()
        if chance < 0.05: crash_point = 1.0 
        elif chance < 0.65: crash_point = random.uniform(1.1, 2.0)
        elif chance < 0.90: crash_point = random.uniform(2.0, 4.0)
        else: crash_point = random.uniform(4.0, 10.0)
        
        crash_point = round(crash_point, 1)
        current_mult = 1.0

        embed = disnake.Embed(
            title="📈 CRASH DO CIPÓ 🐒",
            description=f"{ctx.author.mention} apostou **{aposta:.2f} C**!\n\n🌿 O macaco começou a subir...\n**Multiplicador:** `{current_mult}x`\n\n⚠️ *Digite `parar` no chat para pular!*",
            color=disnake.Color.green()
        )
        msg = await ctx.send(embed=embed)

        if crash_point == 1.0:
            await asyncio.sleep(1)
            embed.color = disnake.Color.red()
            embed.description = f"💥 **ARREBENTOU INSTANTANEAMENTE!**\nO cipó rasgou no `{crash_point}x`.\n\n💀 {ctx.author.mention} perdeu **{aposta:.2f} C** direto na lama."
            await msg.edit(embed=embed)
            user_atual = db.get_user_data(str(ctx.author.id))
            save_achievement(user_atual, "queda_livre")
            return

        stop_event = asyncio.Event()
        async def listen_for_parar():
            def check(m): return m.author == ctx.author and m.content.lower() == 'parar' and m.channel == ctx.channel
            try:
                await self.bot.wait_for('message', check=check, timeout=30.0)
                stop_event.set()
            except asyncio.TimeoutError: pass

        listen_task = self.bot.loop.create_task(listen_for_parar())

        while current_mult < crash_point:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=1.5)
                break
            except asyncio.TimeoutError:
                current_mult += round(random.uniform(0.1, 0.4), 1)
                current_mult = round(current_mult, 1)
                if current_mult > crash_point: current_mult = crash_point

                embed.description = f"{ctx.author.mention} apostou **{aposta:.2f} C**!\n\n🌿 Subindo alto...\n**Multiplicador:** `{current_mult}x`\n\n⚠️ *Digite `parar` no chat para pular!*"
                try: await msg.edit(embed=embed)
                except: pass

        listen_task.cancel()
        user_atual = db.get_user_data(str(ctx.author.id))

        if stop_event.is_set():
            # Saiu a tempo! (Isento de taxas)
            ganho_total = round(aposta * current_mult, 2)
            lucro_bruto = round(ganho_total - aposta, 2)

            # Devolve o saldo original + o lucro total
            db.update_value(user_atual['row'], 3, round(float(user_atual['data'][2]) + ganho_total, 2))
            
            embed.color = disnake.Color.blue()
            embed.description = f"✅ **PULOU A TEMPO!**\nO macaco soltou o cipó no `{current_mult}x`.\n\n💰 {ctx.author.mention} lucrou **{lucro_bruto:.2f} C** (Livre de taxas!)"
            await msg.edit(embed=embed)
            
            if current_mult >= 5.0:
                save_achievement(user_atual, "astronauta_cipo")
        else:
            # Demorou demais
            embed.color = disnake.Color.red()
            embed.description = f"💥 **ARREBENTOU!**\nO cipó não aguentou o peso e rasgou no `{crash_point}x`.\n\n💀 {ctx.author.mention} caiu na lama e perdeu **{aposta:.2f} C**."
            await msg.edit(embed=embed)

def setup(bot):
    bot.add_cog(CrashGame(bot))