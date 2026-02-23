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
        embed = disnake.Embed(
            title="📖 Guia do Gerente Conguito (V4.4)",
            description=f"Olá {ctx.author.mention}, este é o seu manual de sobrevivência na selva!\n\n🪙 **DICA:** A economia suporta **centavos**! Use valores como `150.50` em todos os comandos.",
            color=disnake.Color.green()
        )
        embed.add_field(name="💵 ECONOMIA E PERFIL", inline=False, value=(
            "💰 `!trabalhar`\n👤 `!perfil [@user]`\n🏅 `!conquistas`\n"
            "🏆 `!rank`\n🛒 `!loja`\n💳 `!comprar <item>`\n💸 `!pagar @user <valor>`\n💵 `!salarios`"
        ))
        embed.add_field(name="😈 ROUBOS, CAÇADAS E SABOTAGEM", inline=False, value=(
            "🥷 `!roubar @user`\n🚨 `!recompensa @user <valor>`\n📜 `!recompensas`\n"
            "🍌 `!casca @user`\n🦍 `!taxar @user`\n🪄 `!apelidar @user <nick>`\n"
            "🐒 `!amaldicoar @user`\n🎭 `!impostor @user <msg>`"
        ))
        embed.add_field(name="🏦 BANCO E INVESTIMENTOS", inline=False, value=(
            "🏛️ `!investir fixo <valor>`\n📈 `!investir cripto <valor>`"
        ))
        embed.add_field(name="🎲 JOGOS (Canal #🎰・akbet)", inline=False, value=(
            "🚀 `!crash` | 🎰 `!cassino` | 🎰 `!roleta` | 🥥 `!coco` | 🏁 `!corrida`\n"
            "🦁 `!bicho` | 🥊 `!briga` | 🎫 `!loteria` | 💰 `!pote` | 🃏 `!carta`\n"
            "💣 `!minas` | ♠️ `!21`"
        ))
        embed.add_field(name="🤐 CASTIGOS DE VOZ", inline=False, value=(
            "🔇 `!castigo mudo <t> @user`\n🎧 `!castigo surdo <t> @user`\n"
            "🤐 `!castigo surdomudo <t> @user`\n👟 `!desconectar @user`"
        ))
        embed.set_footer(text="A evolução não para! Jogue com sabedoria. 🦍👑")
        await ctx.send(embed=embed)

    @commands.command(aliases=["ganhos"])
    async def salarios(self, ctx):
        embed = disnake.Embed(
            title="🍌 TABELA SALARIAL DA SELVA",
            description="Confira quanto cada macaco recebe por turno de trabalho (`!trabalhar`):",
            color=disnake.Color.green()
        )

        tabela = {
            "🐒 Lêmure": "60.00 C — 120.00 C",
            "🐵 Macaquinho": "150.00 C — 300.00 C",
            "🦍 Babuíno": "400.00 C — 800.00 C",
            "🦧 Chimpanzé": "1.000.00 C — 2.000.00 C",
            "🌴 Orangutango": "3.000.00 C — 5.500.00 C",
            "🌋 Gorila": "8.000.00 C — 15.000.00 C",
            "🗿 Ancestral": "20.000.00 C — 40.000.00 C",
            "👑 Rei Símio": "60.000.00 C — 120.000.00 C"
        }

        for cargo, valor in tabela.items():
            embed.add_field(name=cargo, value=f"💰 `{valor}`", inline=True)

        embed.set_footer(text="Evolua seu cargo na !loja para ganhar mais!")

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(General(bot))