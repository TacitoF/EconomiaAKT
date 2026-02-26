import disnake
from disnake.ext import commands

OWNER_ID = 757752617722970243

class Patchnotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def patchnotes(self, ctx):
        """Publica as notas de atualização v7.3 no canal oficial."""
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
            title="🎖️ ATUALIZAÇÃO DA SELVA: v7.3 — RESISTÊNCIA TOTAL 🎖️",
            description=(
                "A v7.3 chegou focada em durabilidade e visual! "
                "Reformulamos a defesa dos seus Conguitos e a estética de um dos clássicos da selva."
            ),
            color=disnake.Color.green()
        )

        embed.add_field(
            name="🛡️ Escudo 2.0: Agora por Cargas",
            inline=False,
            value=(
                "**Antes:** Proteção por 6 horas (podia expirar sem você ser atacado).\n"
                "**Agora:** O Escudo protege você contra **3 tentativas de roubo**!\n\n"
                "• **Sem Tempo Limite:** O escudo não some mais com o passar das horas. Ele fica ativo até que 3 ladrões tentem te roubar.\n"
                "• **Consumo por Uso:** Cada vez que um ladrão (sem pé de cabra) for bloqueado por você, o escudo perde 1 carga.\n"
                "• **Estratégia:** Agora você tem a certeza de que seu investimento de 700 MC vai bloquear exatamente 3 ataques."
            )
        )

        embed.add_field(
            name="🦅 Jogo do Bicho: Cara Nova",
            inline=False,
            value=(
                "• **Nova Interface:** O comando `!bicho` recebeu uma renovação visual completa.\n"
                "• **Mais Clareza:** Agora ficou muito mais fácil identificar seus palpites, os bichos sorteados e os seus ganhos."
            )
        )

        embed.add_field(
            name="🛠️ Lembrete: Pé de Cabra",
            inline=False,
            value=(
                "• O Pé de Cabra continua sendo a única ferramenta capaz de ignorar o Escudo, "
                "mas atenção: ele agora consome **1 carga** do escudo do alvo ao passar pela defesa!"
            )
        )

        embed.set_footer(text="Koba: Resistência é a chave da sobrevivência. 🌴")

        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await canal_patchnotes.send(
            content="🚨 **NOVA VERSÃO DISPONÍVEL! v7.3** @everyone 🚨\n",
            embed=embed
        )

def setup(bot):
    bot.add_cog(Patchnotes(bot))