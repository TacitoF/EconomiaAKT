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
        canal_id = 1476042364090060912
        canal_patchnotes = self.bot.get_channel(canal_id)

        if not canal_patchnotes:
            return await ctx.author.send("❌ Erro: Canal de patchnotes não encontrado.")

        embed = disnake.Embed(
            title="🦍 v11.0 — A Nova Era",
            description=(
                "A temporada anterior chegou ao fim. Saldos, inventários e mascotes **voltaram ao pó**.\n"
                "Todos começam do zero — mas a selva ficou muito mais interessante.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.dark_red()
        )

        embed.add_field(
            name="🆕 O QUE HÁ DE NOVO",
            inline=False,
            value=(
                "**📜 Missões Diárias** → `!missoes`\n"
                "Receba **3 tarefas** novas todo dia (trabalhar, roubar, duelar…). Complete todas e ganhe **300–900 MC** + **1 item garantido**. Reseta à meia-noite.\n\n"
                "**🚨 A Hora do Purge**\n"
                "Evento surpresa de **30 minutos** onde as leis somem: `!trabalhar` bloqueado, cooldown do `!roubar` cai pra **5 min** e roubo fracassado não gera multa. Fique esperto.\n\n"
                "**🦍 World Boss — Gorila Mutante**\n"
                "Aparece uma vez por dia entre **13h–18h** com **10.000 HP**. Ataque em grupo com Soco 👊, Pet 🐾, Pé de Cabra 🕵️ ou C4 🧨.\n"
                "› MVP leva uma `Relíquia Ancestral 🔒` · Participantes ganham `Baú do Caçador 🔒`\n"
                "› Se fugir em 1h, a selva toda paga o preço.\n\n"
                "**🔒 Itens Vinculados**\n"
                "Itens com `🔒` ficam presos à sua conta — não podem ser vendidos ou trocados. Só restam os benefícios. Use bem."
            )
        )

        embed.add_field(
            name="♻️ RESET & TEMPORADA",
            inline=False,
            value=(
                "› Todos os jogadores voltaram ao cargo inicial\n"
                "› Top 3 da Era passada recebeu **Pacotes de Fundação** exclusivos (`🔒`)\n"
                "› Preços da `!loja` foram resetados\n"
                "› A corrida para o Topo 1 recomeça agora"
            )
        )

        embed.add_field(
            name="🐛 CORREÇÃO CRÍTICA",
            inline=False,
            value=(
                "**Bug do Imposto resolvido.**\n"
                "O imposto estava confiscando valores absurdos — chegando a limpar saldos inteiros em cargos altos. "
                "Agora cada cargo tem um **teto máximo** de imposto por turno de trabalho. "
                "Rei Símio, por exemplo, nunca perde mais de **9.000 MC** por trabalho taxado."
            )
        )

        embed.add_field(
            name="⚽ REMOVIDO",
            inline=False,
            value="**Apostas Esportivas** — removidas por votação da comunidade. Obrigado a todos que participaram! 🗳️"
        )

        embed.add_field(
            name="⚠️ AVISO",
            inline=False,
            value=(
                "Tudo que foi **adicionado ou modificado** nessa atualização pode conter bugs.\n"
                "Se encontrar qualquer comportamento estranho, reporte imediatamente para a staff.\n"
                "*Quanto mais rápido o report, mais rápido o fix.* 🔧"
            )
        )

        embed.set_footer(text="v11.0 · A selva pune os lentos e recompensa os cruéis 🦍")

        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        try:
            await canal_patchnotes.send(content="@here", embed=embed)
            await ctx.author.send("✅ Patchnotes publicado com sucesso!")
        except Exception as e:
            await ctx.author.send(f"❌ Erro ao enviar as notas de atualização: {e}")

def setup(bot):
    bot.add_cog(Patchnotes(bot))