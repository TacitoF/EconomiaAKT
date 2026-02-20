import disnake
from disnake.ext import commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, comandos gerais no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(name="ajuda", aliases=["comandos", "info"])
    async def ajuda_comando(self, ctx):
        embed = disnake.Embed(title="📖 Guia do Gerente Conguito", description=f"Olá {ctx.author.mention}, manual de sobrevivência!", color=disnake.Color.green())
        embed.add_field(name="💵 ECONOMIA E PERFIL", value="💰 `!trabalhar`\n👤 `!perfil [@user]`\n🏅 `!conquistas`\n🏆 `!rank`\n🛒 `!loja`\n💳 `!comprar <item>`\n💸 `!pagar @user <valor>`", inline=False)
        embed.add_field(name="😈 ROUBOS, CAÇADAS E SABOTAGEM", value="🥷 `!roubar @user`\n🚨 `!recompensa @user <valor>`\n📜 `!recompensas`\n🍌 `!casca @user`\n🦍 `!taxar @user`\n🪄 `!apelidar @user <nick>`", inline=False)
        embed.add_field(name="🏦 BANCO E INVESTIMENTOS", value="🏛️ `!investir fixo <valor>`\n📈 `!investir cripto <valor>`", inline=False)
        embed.add_field(name="🎲 JOGOS (Canal #🎰・akbet)", value="🚀 `!crash` | 🎰 `!cassino` | 🥥 `!coco` | 🏁 `!corrida` | 🪙 `!moeda` | 🦁 `!bicho` | 💣 `!minas` | 🥊 `!briga` | 🎫 `!loteria` | 💰 `!pote` | 🃏 `!carta` | ♠️ `!bj`", inline=False)
        embed.add_field(name="🤐 CASTIGOS DE VOZ", value="🔇 `!castigo mudo <t> @user`\n🎧 `!castigo surdo <t> @user`\n🤐 `!castigo surdomudo <t> @user`\n👟 `!desconectar @user`", inline=False)
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(General(bot))