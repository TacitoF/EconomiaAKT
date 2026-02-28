import disnake
from disnake.ext import commands

OWNER_ID = 757752617722970243

class Patchnotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def patchnotes(self, ctx):
        """Publica as notas de atualização v7.6 no canal oficial."""
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
            title="📜 REGISTRO DE ATUALIZAÇÕES: v7.6 — ECONOMIA DINÂMICA",
            description=(
                "Implementamos novos sistemas de inflação defensiva e imunidade tributária "
                "para equilibrar o mercado e evitar abusos na selva."
            ),
            color=disnake.Color.dark_green()
        )

        embed.add_field(
            name="🛡️ REFORMULADO: Escudo Inflacionário",
            inline=False,
            value=(
                "O custo do **Escudo** agora é dinâmico e focado em evitar o acúmulo infinito de defesas!\n\n"
                "• **Preço base:** `1.000 MC`\n"
                "• **Inflação:** A cada compra realizada, o valor **sobe 50%** exclusivamente para você durante a semana (1.000 → 1.500 → 2.250 → 3.375...).\n"
                "• **Reset:** O seu contador de inflação reseta automaticamente para o preço base após **7 dias**.\n"
                "• O comando `!escudo` e a compra sempre informarão o seu preço personalizado atual."
            )
        )

        embed.add_field(
            name="🦍 BALANCEAMENTO: Imunidade Tributária",
            inline=False,
            value=(
                "Para evitar perseguições constantes com o **Imposto do Gorila**, adicionamos uma janela de respiro.\n\n"
                "• **Imunidade:** Assim que as 5 cargas de imposto sobre você terminarem, você ganha **48 horas de proteção** contra novas taxas.\n"
                "• Ao se livrar do imposto, o bot informará exatamente quando a sua imunidade expira.\n"
                "• O comando `!taxar` passa a bloquear tentativas contra jogadores imunes."
            )
        )

        embed.add_field(
            name="🛠️ Melhorias Gerais de Interface",
            inline=False,
            value=(
                "• A `!loja` agora exibe corretamente a informação de inflação semanal do Escudo.\n"
                "• O rastreio de pagamentos de apostas esportivas pendentes recebeu atualizações de estabilidade."
            )
        )

        embed.set_footer(text="Koba: Evoluindo a sobrevivência na selva. 🌴")

        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await canal_patchnotes.send(
            content="📢 **ATUALIZAÇÃO DE SISTEMA DISPONÍVEL (v7.6)** @everyone",
            embed=embed
        )

def setup(bot):
    bot.add_cog(Patchnotes(bot))