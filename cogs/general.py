import disnake
from disnake.ext import commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, comandos gerais no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(name="ajuda", aliases=["comandos", "info"])
    async def ajuda_comando(self, ctx):
        embed = disnake.Embed(
            title="📖 Guia do Gerente Conguito",
            description=(
                f"Olá {ctx.author.mention}, este é o seu manual de sobrevivência na selva!\n\n"
                "🪙 **DICA:** A economia suporta **centavos**! Use valores como `150.50` em todos os comandos."
            ),
            color=disnake.Color.green()
        )
        embed.add_field(name="💵 ECONOMIA E PERFIL", inline=False, value=(
            "💰 `!trabalhar` — Ganhe conguitos a cada 1h\n"
            "👤 `!perfil [@user]` — Veja seu status\n"
            "🏅 `!conquistas` — Lista de conquistas\n"
            "🏆 `!rank` — Top 10 da selva\n"
            "🛒 `!loja` — Loja de itens e cargos\n"
            "💳 `!comprar <item>` — Compre um item\n"
            "💸 `!pagar @user <valor>` — Faça um Pix\n"
            "💵 `!salarios` — Veja os salários e progressão"
        ))
        embed.add_field(name="😈 ROUBOS, CAÇADAS E SABOTAGEM", inline=False, value=(
            "🥷 `!roubar @user` — Tente roubar alguém (cooldown 2h)\n"
            "🚨 `!recompensa @user <valor>` — Coloque cabeça a prêmio\n"
            "📜 `!recompensas` — Lista de procurados\n"
            "🍌 `!casca @user` — Usa Casca de Banana\n"
            "🦍 `!taxar @user` — Usa Imposto do Gorila\n"
            "🪄 `!apelidar @user <nick>` — Usa Troca de Nick\n"
            "🐒 `!amaldicoar @user` — Maldição Símia (500 C)\n"
            "🎭 `!impostor @user <msg>` — Impostor (500 C)"
        ))
        embed.add_field(name="🏦 BANCO E INVESTIMENTOS", inline=False, value=(
            "🏛️ `!investir fixo <valor>` — +10% na hora (limite 5.000 C/dia)\n"
            "📈 `!investir cripto <valor>` — -25% a +25% em 1 minuto"
        ))
        embed.add_field(name="🎲 JOGOS (Canal #🎰・akbet)", inline=False, value=(
            "🚀 `!crash` | 🎰 `!cassino` | 🎰 `!roleta` | 🥥 `!coco` | 🏁 `!corrida`\n"
            "🦁 `!bicho` | 🥊 `!briga` | 🎫 `!loteria` | 💰 `!pote` | 🃏 `!carta`\n"
            "💣 `!minas` | ♠️ `!21`\n"
            "*Use `!jogos` no canal de apostas para ver detalhes*"
        ))
        embed.add_field(name="🤐 CASTIGOS DE VOZ", inline=False, value=(
            "🔇 `!castigo mudo <1/5/10> @user`\n"
            "🎧 `!castigo surdo <1/5/10> @user`\n"
            "🤐 `!castigo surdomudo <1/5/10> @user`\n"
            "👟 `!desconectar @user`"
        ))
        embed.set_footer(text="Use !salarios para ver a progressão completa. 🦍👑")
        await ctx.send(embed=embed)

    @commands.command(aliases=["ganhos"])
    async def salarios(self, ctx):
        embed = disnake.Embed(
            title="🍌 GUIA DE PROGRESSÃO DA SELVA",
            description=(
                "Salário por hora (`!trabalhar`) e custo de cada cargo.\n"
                "⚠️ **Trabalho puro não é suficiente — use jogos, roubos e investimentos para avançar!**"
            ),
            color=disnake.Color.gold()
        )

        tabela = [
            ("🐒 Lêmure",      "40 – 80 C",            "1.200 C",    "—"),
            ("🐵 Macaquinho",  "130 – 230 C",          "5.500 C",    "1.200 C"),
            ("🦍 Babuíno",     "320 – 530 C",          "14.000 C",   "5.500 C"),
            ("🦧 Chimpanzé",   "780 – 1.320 C",        "35.000 C",   "14.000 C"),
            ("🌴 Orangutango", "1.900 – 3.200 C",      "85.000 C",   "35.000 C"),
            ("🌋 Gorila",      "4.700 – 7.800 C",      "210.000 C",  "85.000 C"),
            ("🗿 Ancestral",   "11.500 – 19.000 C",    "600.000 C",  "210.000 C"),
            ("👑 Rei Símio",   "27.000 – 45.000 C",    "MÁXIMO 👑",  "600.000 C"),
        ]

        for cargo, salario, prox_custo, custo_atual in tabela:
            embed.add_field(
                name=cargo,
                value=(
                    f"💰 **{salario}** /h\n"
                    f"🏪 Custo: `{custo_atual}`\n"
                    f"➡️ Próximo: `{prox_custo}`"
                ),
                inline=True
            )

        embed.add_field(
            name="⏱️ Estimativa (só trabalho, 8h/dia)",
            value=(
                "Lêmure → Macaquinho: **~2 dias**\n"
                "Macaquinho → Babuíno: **~4 dias**\n"
                "Babuíno → Chimpanzé: **~5 dias**\n"
                "Chimpanzé → Orangutango: **~7 dias**\n"
                "Orangutango → Gorila: **~9 dias**\n"
                "Gorila → Ancestral: **~11 dias**\n"
                "Ancestral → Rei Símio: **~17 dias**\n"
                "⚡ *Com jogos e roubos: ~2–3× mais rápido!*"
            ),
            inline=False
        )

        embed.set_footer(text="Limites de aposta aumentam a cada cargo — arrisque mais para ganhar mais!")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(General(bot))