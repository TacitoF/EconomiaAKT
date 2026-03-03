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
            title="📜 REGISTRO DE ATUALIZAÇÕES: v8.0 — PRIVACIDADE E LUXO",
            description=(
                "A selva evoluiu! Agora, suas informações são sagradas e o mercado negro "
                "está mais sofisticado do que nunca. Confira as mudanças de hoje:"
            ),
            color=disnake.Color.dark_purple()
        )

        embed.add_field(
            name="👤 PERFIL PRIVADO (Modo Ephemeral)",
            inline=False,
            value=(
                "Agora, ao digitar `!perfil`, as informações da sua conta aparecem apenas para você! "
                "Ninguém mais verá seu saldo, suas conquistas ou seus itens no chat público, "
                "mantendo seus segredos protegidos de olhos invejosos."
            )
        )

        embed.add_field(
            name="🕵️ TAXA DE ESPIONAGEM",
            inline=False,
            value=(
                "Quer saber o quanto o seu rival tem no banco? Agora isso custa caro! "
                "Para visualizar o perfil de outro usuário, você deve pagar uma **taxa de 500 MC** "
                "para os informantes da selva. Se o alvo tiver um **Escudo**, você perderá o dinheiro e não verá nada!"
            )
        )

        embed.add_field(
            name="🛍️ NOVA INTERFACE DA LOJA",
            inline=False,
            value=(
                "A `!loja` foi totalmente remodelada para uma interface moderna baseada em botões. "
                "Chega de comandos complicados! Agora você navega entre as categorias "
                "(Cargos, Utilidades, Cosméticos) com um clique e compra tudo de forma muito mais rápida."
            )
        )

        embed.add_field(
            name="🎨 PAINEL DE VISUAIS",
            inline=False,
            value=(
                "Implementamos o novo comando `!visuais`. Lá você gerencia suas cores, molduras e títulos "
                "em um menu interativo e privado. Personalize seu perfil sem poluir o chat geral!"
            )
        )

        embed.set_footer(text="Koba: O conhecimento tem um preço, e o silêncio é ouro. 🦍")

        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await canal_patchnotes.send(embed=embed)
        await ctx.author.send("✅ Patchnotes v8.0 enviado com sucesso!")

def setup(bot):
    bot.add_cog(Patchnotes(bot))