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
            title="📜 REGISTRO DE ATUALIZAÇÕES: v9.5 — A GRANDE EXPANSÃO DOS MASCOTES",
            description=(
                "A selva está mais viva do que nunca! 🐾\n"
                "Expandimos massivamente o sistema de **Mascotes**. Agora existem **12 animais diferentes** "
                "para você resgatar, cada um com estratégias únicas para ajudar a enriquecer ou destruir os seus rivais."
            ),
            color=disnake.Color.green()
        )

        embed.add_field(
            name="🐾 COMO CONSEGUIR O SEU?",
            inline=False,
            value=(
                "Trabalhe arduamente! Ao usar `!trabalhar`, existe uma chance de encontrar uma **Gaiola Misteriosa** perdida. "
                "Use `!abrir gaiola` para descobrir qual dos 12 mascotes você tirou e que raridade ele tem."
            )
        )

        embed.add_field(
            name="🟢 COMUNS E 🔵 RAROS",
            inline=False,
            value=(
                "🦦 **Capivara**: +10% de lucro no Trabalho\n"
                "🦥 **Bicho-Preguiça**: +15% no Trabalho *(mas gasta a fome mais rápido)*\n"
                "🐸 **Sapo-Boi**: +8% no Trabalho *(20% de chance de NÃO gastar fome)*\n"
                "🦜 **Papagaio**: -15% de chance de ser roubado\n"
                "🐍 **Jiboia**: -10% de chance de ser roubado *(e o Ladrão paga uma multa 50% maior se falhar)*\n"
                "🦔 **Gambá**: -20% de chance de ser roubado *(gasta muita fome ao te defender)*"
            )
        )

        embed.add_field(
            name="🟣 ÉPICOS E 🌟 LENDÁRIOS",
            inline=False,
            value=(
                "🐒 **Macaco-Prego**: +15% de chance de sucesso no Roubo\n"
                "🦅 **Harpia**: +10% Roubo *(permite saquear uma quantia maior de MC da vítima)*\n"
                "🐺 **Lobo-Guará**: +10% Trabalho **E** +10% Roubo\n"
                "🐆 **Onça Pintada**: +15% Trabalho / +15% Roubo / -15% Defesa\n"
                "🦍 **Gorila Costas-Prateadas**: +25% Trabalho / +20% Roubo *(O brutamontes do dinheiro)*\n"
                "🐉 **Dragão-de-Komodo**: +25% Roubo / -25% Defesa *(O rei absoluto do submundo)*"
            )
        )

        embed.add_field(
            name="🍗 CUIDADOS BÁSICOS",
            inline=False,
            value=(
                "Os seus mascotes gastam energia ao trabalhar ou ao ajudá-lo/defendê-lo em roubos. "
                "Se a **Fome chegar a 0%**, eles dormem e os bônus desligam! Compre **Ração Símia** na `!loja` "
                "e use `!alimentar` para mantê-los ativos. Se quiser tentar a sorte noutro animal, use `!libertar` primeiro."
            )
        )

        embed.set_footer(text="Koba: Escolha bem o seu parceiro. A selva não perdoa fracos. 🦍")

        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await canal_patchnotes.send(embed=embed)
        await ctx.author.send("✅ Patchnotes v9.5 enviado com sucesso!")

def setup(bot):
    bot.add_cog(Patchnotes(bot))