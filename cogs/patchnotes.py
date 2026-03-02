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

        canal_id         = 1475606959247065118
        canal_patchnotes = self.bot.get_channel(canal_id)

        if not canal_patchnotes:
            return await ctx.author.send("❌ Erro: Canal de patchnotes não encontrado.")

        embed = disnake.Embed(
            title="📜 REGISTRO DE ATUALIZAÇÕES: v7.9 — LOGÍSTICA DA SELVA",
            description=(
                "A economia da selva acaba de ficar mais imprevisível! Encontre tesouros, "
                "intercepte contrabandos e use novos itens táticos para dominar o servidor."
            ),
            color=disnake.Color.dark_green()
        )

        embed.add_field(
            name="📦 NOVIDADE: Lootboxes (Caixas de Suprimentos)",
            inline=False,
            value=(
                "Agora você pode obter caixas misteriosas que contêm itens raros, consumíveis ou grandes quantias de dinheiro!\n\n"
                "• **Como obter:** Comprando na `!loja` ou com **5% de chance** ao usar o comando `!trabalhar`.\n"
                "• **Caixote de Madeira:** Comum e barato, ótimo para itens básicos.\n"
                "• **Baú do Caçador:** Raro, focado em equipamentos de ataque e defesa.\n"
                "• **Relíquia Ancestral:** Lendária e valiosa, contém os maiores tesouros da selva.\n"
                "• **Comando:** Use `!abrir <nome da caixa>` para revelar seu prêmio!"
            )
        )

        embed.add_field(
            name="✈️ EVENTO GLOBAL: Air Drops de Contrabando",
            inline=False,
            value=(
                "Aviões de carga passarão aleatoriamente pelos canais da selva! Quando um Air Drop cair, "
                "o primeiro macaco a clicar no botão **SAQUEAR** leva a caixa direto para sua mochila.\n\n"
                "💡 *Fique atento aos chats de economia, o tempo de reação é o que separa um Rei de um Lêmure!*"
            )
        )

        embed.add_field(
            name="🧪 NOVOS ITENS TÁTICOS",
            inline=False,
            value=(
                "Adicionamos itens consumíveis que podem ser encontrados nas caixas:\n\n"
                "• ⚡ **Energético Símio:** Zera instantaneamente o tempo de espera do seu `!trabalhar`.\n"
                "• 💨 **Bomba de Fumaça:** Zera o seu tempo de espera para realizar um novo `!roubar`.\n"
                "• 🧨 **Carga de C4:** Use `!c4 @user` para **explodir e destruir** o escudo de um alvo na hora!\n"
                "• 💎 **Tesouros:** Diamantes e Estátuas de Ouro que podem ser vendidos por fortunas usando `!vender`."
            )
        )

        embed.set_footer(text="Koba: A sorte favorece os audazes. 🌴")

        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await canal_patchnotes.send(
            content="📢 **NOVA CARGA DETECTADA (v7.9)** @everyone",
            embed=embed
        )

def setup(bot):
    bot.add_cog(Patchnotes(bot))