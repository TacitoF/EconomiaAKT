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

def save_achievement(user_data, slug):
    conquistas = str(user_data['data'][9]) if len(user_data['data']) > 9 else ""
    lista = [c.strip() for c in conquistas.split(',') if c.strip()]
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
            await ctx.send(f"🐒 Ei {ctx.author.mention}, voa para o canal {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["cipo", "foguetinho"])
    async def crash(self, ctx, aposta: float = None):
        if aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!crash <valor>`")
        if aposta <= 0:
            return await ctx.send(f"❌ {ctx.author.mention}, a aposta deve ser maior que zero!")
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

            # Algoritmo de probabilidade: 5% crash imediato, 60% baixo, 25% médio, 10% alto
            chance = random.random()
            if chance < 0.05:      crash_point = 1.0
            elif chance < 0.65:    crash_point = random.uniform(1.1, 2.0)
            elif chance < 0.90:    crash_point = random.uniform(2.0, 4.0)
            else:                  crash_point = random.uniform(4.0, 10.0)
            crash_point = round(crash_point, 1)

            embed = disnake.Embed(
                title="📈 CRASH DO CIPÓ 🐒",
                description=f"{ctx.author.mention} apostou **{aposta:.2f} C**!\n\n🌿 O macaco começou a subir...\n**Multiplicador:** `1.0x`\n\n⚠️ *Digite `parar` para sacar!*",
                color=disnake.Color.green()
            )
            msg = await ctx.send(embed=embed)

            if crash_point == 1.0:
                await asyncio.sleep(1)
                embed.color = disnake.Color.red()
                embed.description = f"💥 **ARREBENTOU INSTANTANEAMENTE!**\nO cipó rasgou no `1.0x`.\n\n💀 {ctx.author.mention} perdeu **{aposta:.2f} C**."
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
                except asyncio.TimeoutError:
                    pass

            listen_task = self.bot.loop.create_task(listen_for_parar())
            current_mult = 1.0

            while current_mult < crash_point:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=1.5)
                    break
                except asyncio.TimeoutError:
                    current_mult = round(min(current_mult + round(random.uniform(0.1, 0.4), 1), crash_point), 1)
                    embed.description = f"{ctx.author.mention} apostou **{aposta:.2f} C**!\n\n🌿 Subindo alto...\n**Multiplicador:** `{current_mult}x`\n\n⚠️ *Digite `parar` para sacar!*"
                    try: await msg.edit(embed=embed)
                    except: pass

            listen_task.cancel()
            user_atual = db.get_user_data(str(ctx.author.id))

            if stop_event.is_set():
                ganho_total = round(aposta * current_mult, 2)
                lucro = round(ganho_total - aposta, 2)
                db.update_value(user_atual['row'], 3, round(db.parse_float(user_atual['data'][2]) + ganho_total, 2))
                embed.color = disnake.Color.blue()
                embed.description = f"✅ **SACOU A TEMPO!**\nNo `{current_mult}x`.\n\n💰 {ctx.author.mention} lucrou **{ganho_total:.2f} C**!"
                await msg.edit(embed=embed)
                if current_mult >= 5.0:
                    save_achievement(user_atual, "astronauta_cipo")
            else:
                embed.color = disnake.Color.red()
                embed.description = f"💥 **ARREBENTOU!**\nO cipó rasgou no `{crash_point}x`.\n\n💀 {ctx.author.mention} perdeu **{aposta:.2f} C**."
                await msg.edit(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !crash de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(CrashGame(bot))