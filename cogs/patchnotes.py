import disnake
from disnake.ext import commands

OWNER_ID = 757752617722970243

class Patchnotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def patchnotes(self, ctx):
        """Publica as notas de atualização v7.5 no canal oficial."""
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
            title="📜 REGISTRO DE ATUALIZAÇÕES: v7.5 — DECRETO DO GORILA",
            description=(
                "Reformulação do sistema de Imposto do Gorila com persistência total — "
                "além de melhorias visuais na Loja e no Ranking da Selva."
            ),
            color=disnake.Color.dark_green()
        )

        embed.add_field(
            name="🦍 REFORMULADO: Imposto do Gorila",
            inline=False,
            value=(
                "O **Imposto do Gorila** foi completamente refeito e agora funciona por **cargas**, igual ao Escudo.\n\n"
                "**Antes:** drenava 25% do salário da vítima por **24 horas** fixas — independente de ela trabalhar ou não.\n"
                "**Agora:** drena 25% nos próximos **5 trabalhos** da vítima. "
                "Se ela não trabalhar, o imposto permanece ativo até ser consumido.\n\n"
                "Isso torna o item muito mais justo e estratégico: "
                "vale mais usá-lo contra jogadores que trabalham com frequência."
            )
        )

        embed.add_field(
            name="💾 NOVIDADE: Persistência do Imposto",
            inline=False,
            value=(
                "O estado do Imposto do Gorila agora é **salvo diretamente no banco de dados**.\n"
                "Reinicios do bot não apagam mais o imposto ativo — "
                "as cargas restantes são restauradas automaticamente na inicialização."
            )
        )

        embed.add_field(
            name="🛒 VISUAL: Loja Reformulada (!loja)",
            inline=False,
            value=(
                "A `!loja` foi redesenhada para ficar mais limpa e menos poluída. "
                "Os cargos agora aparecem em **duas colunas lado a lado**, "
                "e cada item ocupa apenas uma linha com as informações essenciais."
            )
        )

        embed.add_field(
            name="🏆 VISUAL: Ranking Reformulado (!rank)",
            inline=False,
            value=(
                "O `!rank` ganhou um novo visual com **pódio em destaque** (🥇🥈🥉 em colunas separadas), "
                "saldos abreviados (ex: `12.5K MC`, `1.2M MC`) e exibição do cargo de cada jogador. "
                "Se você estiver fora do Top 10, sua posição aparece no final."
            )
        )

        embed.add_field(
            name="🛠️ Correções",
            inline=False,
            value=(
                "• **Blackjack:** o emoji 👉 do próximo jogador agora atualiza imediatamente ao passar a vez, sem precisar de uma ação extra.\n"
            )
        )

        embed.set_footer(text="Koba: Evoluindo a sobrevivência na selva. 🌴")

        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await canal_patchnotes.send(
            content="📢 **ATUALIZAÇÃO DE SISTEMA DISPONÍVEL (v7.5)** @everyone",
            embed=embed
        )

def setup(bot):
    bot.add_cog(Patchnotes(bot))