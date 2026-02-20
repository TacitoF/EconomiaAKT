import disnake
from disnake.ext import commands
import database as db

class Bounty(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, 'recompensas'): bot.recompensas = {}

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, assuntos de caçada são apenas no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["bounty", "cacada"])
    async def recompensa(self, ctx, vitima: disnake.Member, valor: int):
        if vitima.id == ctx.author.id: return await ctx.send(f"🐒 {ctx.author.mention}, você não pode se colocar a prêmio!")
        if valor <= 0: return await ctx.send(f"❌ O valor precisa ser maior que zero!")

        pagador = db.get_user_data(str(ctx.author.id))
        if not pagador or int(pagador['data'][2]) < valor: return await ctx.send(f"❌ Saldo insuficiente!")

        db.update_value(pagador['row'], 3, int(pagador['data'][2]) - valor)
        vitima_id = str(vitima.id)
        self.bot.recompensas[vitima_id] = self.bot.recompensas.get(vitima_id, 0) + valor
        
        embed = disnake.Embed(title="🚨 CAÇADA ATUALIZADA! 🚨", description=f"**{ctx.author.mention}** investiu na caçada contra **{vitima.mention}**!\n\n💰 **Prêmio Total Atual:** `{self.bot.recompensas[vitima_id]} Conguitos`", color=disnake.Color.red())
        await ctx.send(embed=embed)

    @commands.command(aliases=["procurados", "lista_bounty"])
    async def recompensas(self, ctx):
        if not self.bot.recompensas: return await ctx.send("🕊️ Ninguém com a cabeça a prêmio no momento!")
        embed = disnake.Embed(title="📜 Mural de Procurados", color=disnake.Color.dark_red())
        tem = False
        for u_id, val in self.bot.recompensas.items():
            if val > 0:
                user = self.bot.get_user(int(u_id))
                embed.add_field(name=f"Alvo: {user.display_name if user else 'ID: '+u_id}", value=f"➡️ **{val} C**", inline=False)
                tem = True
        if not tem: return await ctx.send("🕊️ Ninguém com a cabeça a prêmio!")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Bounty(bot))