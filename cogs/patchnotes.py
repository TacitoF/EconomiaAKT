import disnake
from disnake.ext import commands

OWNER_ID = 757752617722970243

class Patchnotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def patchnotes(self, ctx):
        """Publica as notas de atualização do Coqueiro no canal oficial."""
        try:
            await ctx.message.delete()
        except:
            pass

        if ctx.author.id != OWNER_ID:
            return

        canal_id = 1475606959247065118
        canal_patchnotes = self.bot.get_channel(canal_id)

        if not canal_patchnotes:
            return await ctx.author.send("❌ Erro: Canal de patchnotes não encontrado.")

        embed = disnake.Embed(
            title="🌴 ATUALIZAÇÃO DA SELVA: O COQUEIRO CHEGOU! 🌴",
            description=(
                "A selva acaba de ganhar um novo jogo! Vá até o canal de apostas e experimente o **Coqueiro** (Plinko)."
            ),
            color=disnake.Color.dark_green()
        )

        embed.add_field(
            name="🥥 Como Jogar",
            inline=False,
            value=(
                "Use o comando `!coqueiro <valor> [quantidade de cocos]`.\n"
                "Você pode jogar de **1 a 5 cocos** de uma vez. "
                "Eles cairão pela palmeira rebatendo nos galhos até chegarem na base."
            )
        )

        embed.add_field(
            name="💰 Multiplicadores",
            inline=False,
            value=(
                "O objetivo é que o seu coco caia nas **bordas** para pegar os Jackpots!\n"
                "• **Bordas:** Lucros altos (Até 15x)\n"
                "• **Centro:** Paga menos que a aposta (0.2x a 0.5x)\n\n"
                "*(Dica: Jogar vários cocos ao mesmo tempo pode equilibrar as perdas do centro com os ganhos das bordas)*"
            )
        )

        embed.add_field(
            name="⚠️ AVISO IMPORTANTE: FASE DE TESTES (BETA)",
            inline=False,
            value=(
                "O jogo foi recém-lançado e está em período de **testes de balanceamento**. "
                "Isso significa que os multiplicadores podem mudar nos próximos dias. "
                "**Quaisquer valores ganhos indevidamente (ou perdidos) devido a bugs graves ou falhas de economia poderão ser revertidos sem aviso prévio.** "
                "Jogue com responsabilidade!"
            )
        )

        embed.set_footer(text="Koba: Que a sorte dos ancestrais guie os seus cocos! 🐒")

        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await canal_patchnotes.send(
            content="🚨 **NOVO JOGO DISPONÍVEL! (BETA)** @everyone 🚨\n",
            embed=embed
        )

def setup(bot):
    bot.add_cog(Patchnotes(bot))