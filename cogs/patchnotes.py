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
            title="📜 REGISTRO DE ATUALIZAÇÕES: v7.8 — JUSTIÇA E CAOS PVP",
            description=(
                "A selva passou por uma limpeza pesada contra trapaças e, para compensar, "
                "trouxemos a maior atualização de jogos PvP até agora! Preparem seus Macacoins."
            ),
            color=disnake.Color.dark_green()
        )

        embed.add_field(
            name="⚖️ CORREÇÃO E PUNIÇÕES: Apostas Esportivas",
            inline=False,
            value=(
                "Identificamos e corrigimos uma falha crítica na agência de apostas (`!futebol`) que "
                "permitia aos jogadores fazerem palpites em jogos que já tinham acabado.\n\n"
                "🚨 **Aviso aos espertinhos:** Todos os usuários que abusaram desse bug para lucrar tiveram "
                "suas **apostas canceladas** e sofreram um **rollback (rebaixamento) nos cargos**. "
                "A regra é clara: joguem limpo, ou a selva cobra o preço."
            )
        )

        embed.add_field(
            name="⚔️ NOVIDADE: O Arsenal PvP foi Expandido!",
            inline=False,
            value=(
                "Chegou a hora de arrancar o dinheiro dos seus amigos! Adicionamos **4 novos jogos** "
                "totalmente interativos para você desafiar qualquer um no servidor:\n\n"
                "✂️ **Duelo de Jokenpô** (`!duelo @user <valor>`)\n"
                "Gorila amassa Caçador, Caçador atira na Casca, Casca derruba o Gorila. Um clássico de escolhas secretas!\n\n"
                "🌿 **Salto do Cipó Podre** (`!cipo @user <valor>`)\n"
                "Uma roleta russa nas alturas! De 6 cipós na tela, 1 está podre. Revezem os saltos até alguém cair no penhasco.\n\n"
                "🗺️ **Caça ao Tesouro** (`!explorar @user <valor>`)\n"
                "Um mini campo minado 5x5! Revezem clicando nos botões para achar Bananas (+1 ponto e joga de novo). Só evitem as Cobras!\n\n"
                "🔫 **Duelo de Reflexos** (`!bang @user <valor>`)\n"
                "Teste o seu tempo de reação! O primeiro que clicar em ATIRAR ganha o dinheiro. Mas se clicar antes da hora... sua arma trava e você perde!"
            )
        )

        embed.set_footer(text="Koba: Evoluindo a sobrevivência na selva. 🌴")

        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await canal_patchnotes.send(
            content="📢 **ATUALIZAÇÃO DE SISTEMA DISPONÍVEL (v7.8)** @everyone",
            embed=embed
        )

def setup(bot):
    bot.add_cog(Patchnotes(bot))