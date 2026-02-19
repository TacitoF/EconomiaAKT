import disnake
from disnake.ext import commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ajuda", aliases=["comandos", "info"])
    async def ajuda_comando(self, ctx):
        embed = disnake.Embed(title="📖 Guia do AKTrovão", color=disnake.Color.green())
        embed.add_field(name="💰 Economia", value="`!trabalhar`, `!perfil`, `!loja`, `!comprar`", inline=False)
        embed.add_field(name="🎲 Jogos", value="`!slots`, `!roubar` (Apenas no #cassino-conguito)", inline=False)
        embed.add_field(name="🤐 Castigos", value="`!castigo <mute/deaf/total> <1/5/10> @user`", inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def postar_regras(self, ctx):
        embed = disnake.Embed(title="🍌 Regras da Selva AKTrovão", color=disnake.Color.gold())
        embed.add_field(name="⚒️ Trabalho", value="`!trabalhar` a cada 1h. Melhore seu cargo para ganhar mais!", inline=False)
        embed.add_field(name="🥷 Roubos", value="40% de chance. Se falhar, paga multa. Compre `Escudo` para se proteger!", inline=False)
        embed.add_field(name="🎰 Cassino", value="Use o canal apropriado para evitar poluição no chat geral.", inline=False)
        msg = await ctx.send(embed=embed)
        await msg.pin()
        await ctx.send("✅ Regras fixadas!")

def setup(bot):
    bot.add_cog(General(bot))