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
            title="📜 ATUALIZAÇÃO v11.0: A NOVA ERA & O CAOS 💀",
            description=(
                "A temporada passada chegou ao fim e a poeira baixou. "
                "Saldos, inventários e mascotes **voltaram ao pó**.\n\n"
                "Iniciamos agora uma **Nova Era** na selva! Todos começam do zero, "
                "mas trouxemos grandes novidades para recompensar os macacos mais ativos "
                "e aterrorizar os mais ricos."
            ),
            color=disnake.Color.dark_red()
        )

        embed.add_field(
            name="📜 NOVO SISTEMA: Missões Diárias",
            inline=False,
            value=(
                "Ganhar dinheiro só trabalhando ficou no passado! Use o comando **`!missoes`**.\n"
                "• Todo dia, o bot sorteará **3 tarefas aleatórias** para você (trabalhar, assaltar, jogar cassino, duelar, etc.).\n"
                "• Ao completar as 3 missões, você ganha de **300 a 900 MC** e um **Item Aleatório** garantido (Caixas, Gaiolas, Rações ou até Relíquias Lendárias!).\n"
                "• O quadro de missões é resetado todos os dias à meia-noite."
            )
        )

        embed.add_field(
            name="🚨 NOVO EVENTO: A Hora do Purge",
            inline=False,
            value=(
                "De tempos em tempos, a sirene vai tocar e as leis da selva serão suspensas por **30 minutos** de anarquia pura!\n"
                "🔨 **Trabalho inútil:** O comando `!trabalhar` é bloqueado.\n"
                "🥷 **Assaltos frenéticos:** O cooldown do `!roubar` cai de 2 horas para apenas **5 minutos**.\n"
                "💀 **Sem leis:** Se você falhar em um roubo, a multa é **ZERADA**. Não há punições.\n"
                "*Preparem seus escudos, estoquem C4 e protejam as carteiras!*"
            )
        )

        embed.add_field(
            name="🔒 NOVA MECÂNICA: Itens Vinculados",
            inline=False,
            value=(
                "Para manter a economia do Dia 1 justa e competitiva, introduzimos os itens vinculados.\n"
                "• Se um item no seu inventário possuir um cadeado (`🔒`), significa que ele está **preso à sua conta**.\n"
                "• **Efeito:** Você **não pode** vender para o sistema, e nem trocar ou vender para outros jogadores. Você é obrigado a usar o item e aproveitar seus benefícios para dominar a selva!"
            )
        )

        embed.add_field(
            name="♻️ O Grande Reset",
            inline=False,
            value=(
                "• A economia foi nivelada. Todos os jogadores voltaram ao cargo inicial.\n"
                "• Os campeões do Top 3 da Era passada receberam seus Pacotes de Fundação com itens exclusivos (que estão vinculados com `🔒`).\n"
                "• Os preços da `!loja` foram resetados.\n"
                "Que a corrida para o Top 1 recomece!"
            )
        )

        embed.set_footer(text="A selva pune os lentos e recompensa os cruéis. Boa sorte! 🦍")

        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        try:
            await canal_patchnotes.send(content="@everyone", embed=embed)
            await ctx.author.send("✅ Patchnotes publicado com sucesso!")
        except Exception as e:
            await ctx.author.send(f"❌ Erro ao enviar as notas de atualização: {e}")

def setup(bot):
    bot.add_cog(Patchnotes(bot))