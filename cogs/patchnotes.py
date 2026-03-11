import disnake
from disnake.ext import commands

OWNER_ID = 757752617722970243

class Patchnotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def patchnotes(self, ctx):
        try:
            await ctx.message.delete()
        except:
            pass

        if ctx.author.id != OWNER_ID:
            return

        # Canal onde o anúncio será postado
        canal_id = 1475606959247065118
        canal_patchnotes = self.bot.get_channel(canal_id)

        if not canal_patchnotes:
            return await ctx.author.send("❌ Erro: Canal de patchnotes não encontrado.")

        embed = disnake.Embed(
            title="📜 REGISTRO DE ATUALIZAÇÕES: v10.0 — O MERCADO VIVO",
            description=(
                "A economia da selva nunca mais será a mesma. 💹\n"
                "Esta atualização transforma o mercado em um sistema **vivo e dinâmico**, "
                "onde os preços flutuam com a demanda e os jogadores podem negociar diretamente entre si."
            ),
            color=0x00C853
        )

        embed.add_field(
            name="💹 PREÇOS DINÂMICOS NO MERCADO",
            inline=False,
            value=(
                "Os itens de poder agora têm **preço variável** — a oferta e a demanda mandam!\n\n"
                "📈 **Alta demanda:** Cada compra empurra o preço **+3%** para cima (teto: **+80%**)\n"
                "📉 **Baixa demanda:** Se ninguém comprar, o preço cai gradualmente (piso: **-40%**)\n"
                "🔄 O contador de compras **reseta todo dia**, então os preços oscilam diariamente\n\n"
                "A loja exibe o indicador de tendência ao lado de cada item:\n"
                "`🔥 Alta demanda` · `📈 Em alta` · `📉 Pouca procura`"
            )
        )

        embed.add_field(
            name="⚖️ IMPOSTO PROGRESSIVO POR CARGO",
            inline=False,
            value=(
                "Rico paga mais, pobre paga menos — simples assim.\n\n"
                "🐭 **Lêmure** → preço base (100%)\n"
                "🐒 **Macaquinho** → +10%\n"
                "🦍 **Babuíno** → +22%\n"
                "🐵 **Chimpanzé** → +38%\n"
                "🦧 **Orangutango** → +58%\n"
                "🦾 **Gorila** → +82%\n"
                "🗿 **Ancestral** → +110%\n"
                "👑 **Rei Símio** → +145%\n\n"
                "*Cosméticos e upgrades de cargo sempre têm preço fixo.*"
            )
        )

        embed.add_field(
            name="🤝 COMÉRCIO ENTRE JOGADORES",
            inline=False,
            value=(
                "Agora é possível **vender itens do inventário** diretamente para outros jogadores!\n\n"
                "🛒 `!vender @usuario <item> <preço>` — Cria uma proposta de venda\n"
                "✅ O comprador recebe uma notificação e tem **60 segundos** para aceitar ou recusar\n"
                "🔒 O bot revalida o item e o saldo no momento do aceite — sem golpes possíveis\n\n"
                "**Itens intransferíveis** (têm lógica de estado ativo):\n"
                "`Escudo` · `Pé de Cabra` · `Seguro`"
            )
        )

        embed.add_field(
            name="🎒 NOVO COMANDO: !inventario",
            inline=False,
            value=(
                "`!inventario` — Mostra seus itens vendíveis de forma organizada\n"
                "✅ Indica quais podem ser negociados e quais são intransferíveis\n"
                "🔒 O inventário de outros jogadores continua sendo **dado privado** — "
                "use `!perfil @usuario` para espionar (500 MC)"
            )
        )

        embed.add_field(
            name="⚠️ O QUE NÃO MUDOU",
            inline=False,
            value=(
                "• Preços de **cargos** e **cosméticos** continuam fixos\n"
                "• Jogadores com cargos baixos **nunca são prejudicados** pela inflação\n"
                "• Toda a lógica de roubos, escudo e imposto continua igual"
            )
        )

        embed.set_footer(text="Koba: O mercado pune os ingênuos e recompensa os espertos. 🦍")

        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await canal_patchnotes.send(content="@everyone", embed=embed)
        await ctx.author.send("✅ Patchnotes v10.0 enviado com sucesso!")

def setup(bot):
    bot.add_cog(Patchnotes(bot))