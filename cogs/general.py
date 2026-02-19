import disnake
from disnake.ext import commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Removido o alias "help" para evitar conflitos com o sistema
    @commands.command(name="ajuda", aliases=["comandos", "info"])
    async def ajuda_comando(self, ctx):
        """Lista todos os comandos resumidamente"""
        embed = disnake.Embed(
            title="📖 Guia de Comandos - Gerente Conguito",
            description="Use os comandos abaixo para interagir no AKTrovão!",
            color=disnake.Color.green()
        )

        embed.add_field(
            name="💰 Economia",
            value="`!trabalhar`, `!perfil`, `!loja`, `!comprar`.",
            inline=False
        )

        embed.add_field(
            name="🎲 Jogos & Fun",
            value="`!slots`, `!roubar`, `!castigo`.",
            inline=False
        )

        embed.set_footer(text="AKTrovão Economy")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(General(bot))