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
            title="🛡️ ATUALIZAÇÃO DA SELVA: v7.1 — O ESCUDO GANHOU DENTES 🛡️",
            description=(
                "O sistema de proteção contra roubos foi reformulado para ser mais justo e estratégico. "
                "O Escudo deixou de ser um item descartável de uso único e agora oferece **proteção real por tempo determinado**.\n\n"
                "⚠️ **Aviso:** Escudos já existentes nos inventários continuam funcionando normalmente com as novas regras."
            ),
            color=disnake.Color.blue()
        )

        embed.add_field(
            name="🛡️ Escudo — Nova Mecânica de Duração",
            inline=False,
            value=(
                "**Antes:** O Escudo bloqueava apenas **1 roubo** e era consumido na hora.\n"
                "**Agora:** O Escudo oferece **6 horas de proteção contínua** a partir da ativação.\n\n"
                "• **Ativação automática:** Ao receber o primeiro ataque de roubo, o Escudo sai do inventário e começa a contar as 6 horas.\n"
                "• **Ativação manual:** Use `!escudo` para ativar a proteção imediatamente, sem precisar esperar ser atacado.\n"
                "• **Transparência:** Quando um roubo é bloqueado, o atacante vê exatamente quando sua proteção vai expirar.\n"
                "• **Consulta:** Use `!escudo` a qualquer momento para ver quanto tempo de proteção ainda resta."
            )
        )

        embed.add_field(
            name="⚖️ Por que essa mudança?",
            inline=False,
            value=(
                "Com a taxa de sucesso de roubo em **45%**, o antigo Escudo de uso único era muito fraco para seu custo de **700 MC** — "
                "havia uma chance enorme de o ladrão simplesmente falhar naturalmente, desperdiçando sua proteção. "
                "O novo sistema garante que o Escudo valha o investimento, cobrindo múltiplos ataques durante uma janela de tempo estratégica."
            )
        )

        embed.add_field(
            name="📋 Resumo Rápido",
            inline=False,
            value=(
                "🛒 **Custo:** 700 MC (sem alteração)\n"
                "⏱️ **Duração:** 6 horas por uso\n"
                "🔒 **Proteção:** Todos os roubos durante o período são bloqueados\n"
                "⚡ **Ativação:** Automática no primeiro ataque **ou** manual com `!escudo`\n"
                "🔍 **Consulta:** `!escudo` mostra o tempo restante de proteção"
            )
        )

        embed.set_footer(text="Koba: Proteção é poder. Use com sabedoria. 🌴")

        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await canal_patchnotes.send(
            content="🚨 **ATUALIZAÇÃO DO SISTEMA DE PROTEÇÃO!** @everyone 🚨\n",
            embed=embed
        )


def setup(bot):
    bot.add_cog(Patchnotes(bot))