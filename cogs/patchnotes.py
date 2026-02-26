import disnake
from disnake.ext import commands

OWNER_ID = 757752617722970243

class Patchnotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def patchnotes(self, ctx):
        """Publica as notas de atualização v7.4 no canal oficial."""
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
            title="📜 REGISTRO DE ATUALIZAÇÕES: v7.4 — EVOLUÇÃO TÁTICA",
            description=(
                "Implementamos uma série de novos sistemas e otimizações para aprimorar a estabilidade da economia e a experiência de jogo no Koba."
            ),
            color=disnake.Color.dark_green()
        )

        embed.add_field(
            name="🎲 NOVIDADE: Blefe de Dados (!mentira)",
            inline=False,
            value=(
                "Um novo jogo multiplayer focado em estratégia e blefe foi adicionado. "
                "Desafie seus amigos em uma mesa de 2 a 6 jogadores e use sua astúcia para levar o pote total."
            )
        )

        embed.add_field(
            name="🎰 REFORMULADO: Roleta Interativa (!roleta)",
            inline=False,
            value=(
                "A Roleta agora funciona totalmente via **botões e janelas (Modals)**. "
                "O comando `!apostar` foi removido para tornar o chat mais limpo e a jogabilidade mais rápida."
            )
        )

        embed.add_field(
            name="🎫 NOVIDADE: Raspadinha da Selva (!raspadinha)",
            inline=False,
            value=(
                "Substituindo o antigo sistema de loteria, a Raspadinha agora conta com uma mecânica visual de revelação acelerada e suspense aprimorado."
            )
        )

        embed.add_field(
            name="🛡️ AJUSTE: Escudo vs Pé de Cabra",
            inline=False,
            value=(
                "O sistema de defesa foi recalibrado. Agora, o **Pé de Cabra** perfura a proteção mas **consome 1 carga** do escudo do alvo no processo. "
                "A vítima perde a carga, mas o roubo não é bloqueado."
            )
        )

        embed.add_field(
            name="♻️ Comunicado: Remoção do 'Coqueiro'",
            inline=False,
            value=(
                "Após a fase de testes, decidimos remover o jogo Coqueiro permanentemente devido a falhas de renderização na interface do Discord que comprometiam a experiência."
            )
        )

        embed.add_field(
            name="🛠️ Melhorias Gerais",
            inline=False,
            value=(
                "• **Estabilidade:** Correção de bug crítico de reembolso duplo em jogos multiplayer.\n"
                "• **Performance:** Ajuste fino nos tempos de animação e suspenses de todos os minigames solo.\n"
                "• **Menus:** Comandos `!ajuda` e `!jogos` totalmente atualizados com os novos sistemas."
            )
        )

        embed.set_footer(text="Koba: Evoluindo a sobrevivência na selva. 🌴")

        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await canal_patchnotes.send(
            content="📢 **ATUALIZAÇÃO DE SISTEMA DISPONÍVEL (v7.4)** @everyone",
            embed=embed
        )

def setup(bot):
    bot.add_cog(Patchnotes(bot))