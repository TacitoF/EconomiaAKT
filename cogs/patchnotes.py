import disnake
from disnake.ext import commands

OWNER_ID = 757752617722970243

class Patchnotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def patchnotes(self, ctx):
        """Publica as notas de atualização no canal oficial."""
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
            title="⚔️ ATUALIZAÇÃO DA SELVA: v7.2 — A GUERRA DOS ITENS ⚔️",
            description=(
                "A disputa por moedas acabou de ficar muito mais estratégica. "
                "O Escudo de 6 horas recebeu um predador natural: O Pé de Cabra foi forjado!"
            ),
            color=disnake.Color.dark_red()
        )

        embed.add_field(
            name="🛠️ Pé de Cabra — O Pesadelo dos Ricos",
            inline=False,
            value=(
                "**Antes:** Apenas aumentava a chance de roubo.\n"
                "**Agora:** Além de aumentar a chance de sucesso para **65%**, o Pé de Cabra **IGNORA A PROTEÇÃO DO ESCUDO!**\n\n"
                "• **Invasão:** Se o alvo tiver um Escudo ativo (das 6 horas), o Pé de Cabra vai arrombar a porta e realizar o roubo normalmente.\n"
                "• **Consumo:** O Pé de Cabra quebra após o uso (sendo consumido do seu inventário), quer o roubo dê certo ou não."
            )
        )

        embed.add_field(
            name="🛡️ Como fica o Escudo?",
            inline=False,
            value=(
                "O Escudo ainda é essencial! Mesmo que um ladrão de elite use um Pé de Cabra para te roubar, o seu **Escudo NÃO é destruído**. "
                "Ele continuará ativo e protegendo você contra todos os outros ladrões comuns pelas horas que restarem da sua duração."
            )
        )

        embed.add_field(
            name="⚖️ Por que essa mudança?",
            inline=False,
            value=(
                "O Escudo de 6 horas estava deixando os jogadores mais ricos intocáveis. "
                "Agora, quem quiser investir **3.000 MC** em um Pé de Cabra tem a ferramenta certa para caçar os grandes alvos, "
                "criando uma economia de risco e recompensa muito mais dinâmica."
            )
        )

        embed.add_field(
            name="📋 Resumo da Guerra",
            inline=False,
            value=(
                "🥷 **Ladrão Normal vs Escudo:** O Ladrão é bloqueado, leva multa e perde o turno.\n"
                "🛠️ **Pé de Cabra vs Escudo:** O Escudo é ignorado! O Ladrão tem 65% de chance de levar o dinheiro.\n"
                "🛡️ **Sobrevivência do Escudo:** O Escudo da vítima continua ativo contra futuros ataques sem Pé de Cabra."
            )
        )

        embed.set_footer(text="Koba: Proteção é boa, mas nenhuma porta é inquebrável. 🌴")

        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await canal_patchnotes.send(
            content="🚨 **ATUALIZAÇÃO DE BALANCEAMENTO!** @everyone 🚨\n",
            embed=embed
        )

def setup(bot):
    bot.add_cog(Patchnotes(bot))