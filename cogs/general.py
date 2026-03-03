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

    @commands.command(name="ajuda", aliases=["comandos", "info", "help"])
    async def ajuda_comando(self, ctx):
        embed = disnake.Embed(
            title="📖 Guia de Sobrevivência na Selva",
            description=(
                f"Olá {ctx.author.mention}, este é o seu manual de sobrevivência.\n"
                "Para começar a enriquecer, use **`!trabalhar`** e tente a sorte!\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.green()
        )

        embed.add_field(name="💵 BÁSICO E ECONOMIA", inline=False, value=(
            "💰 **`!trabalhar`**\n"
            "└ *Trabalhe a cada 1h para lucrar e ter chance de achar caixas.*\n"
            "👤 **`!perfil [@user]`** ─ *Verifica saldo, cargo, inventário e cosméticos equipados.*\n"
            "🏆 **`!rank`** ─ *Top 10* | 🏅 **`!conquistas`** ─ *Emblemas.*\n"
            "💵 **`!salarios`** ─ *Tabela de ganhos e custos de cada cargo.*\n"
            "💸 **`!pagar @user <valor>`** ─ *Transfira MC para outro macaco.*"
        ))

        embed.add_field(name="📦 MERCADO E CONTRABANDO", inline=False, value=(
            "🛒 **`!loja`**\n"
            "└ *Acesse o mercado negro para comprar cargos, itens e cosméticos.*\n"
            "💳 **`!comprar <item>`** ─ *Ex: `!comprar Pé de Cabra` ou `!comprar Cor Roxo Místico`.*\n"
            "💎 **`!vender <item>`** ─ *Venda tesouros ganhos nas caixas por MC.*\n"
            "🔓 **`!abrir <caixa>`**\n"
            "└ *Abra Caixote, Baú ou Relíquia do seu inventário.*\n"
            "✈️ **Airdrops:** *Caem do nada no chat. O 1º a `SAQUEAR` leva a caixa!*"
        ))

        embed.add_field(name="😈 ROUBOS E SABOTAGEM", inline=False, value=(
            "🥷 **`!roubar @user`**\n"
            "└ *Tente assaltar alguém para roubar MC (cooldown 2h).*\n"
            "🛡️ **`!escudo`** ─ *Checa defesa* | 🧨 **`!c4 @user`** ─ *Destrói escudo.*\n"
            "🚨 **`!recompensa @user <valor>`** ─ *Coloca a cabeça do alvo a prêmio.*\n"
            "📜 **`!recompensas`** ─ *Mostra o mural de procurados da selva.*\n"
            "🍌 **`!casca @user`** ─ *Atrasa o trabalho do alvo.*\n"
            "🦍 **`!taxar @user`** ─ *Rouba 25% do próximo trabalho.*\n"
            "🪄 **`!apelidar @user <nick>`** ─ *Altera o nome de alguém no server.*\n"
            "🧪 **`!energetico`** ─ *Zera CD trabalho* | 💨 **`!fumaca`** ─ *Zera CD roubo.*"
        ))

        embed.add_field(name="🏦 BANCO E INVESTIMENTO", inline=False, value=(
            "🏛️ **`!investir fixo <valor>`**\n"
            "└ *Retorno 100% seguro de +10% na hora (Limite 5.000 MC/dia).*\n"
            "📈 **`!investir cripto <valor>`**\n"
            "└ *Alto risco! Retorno entre -25% e +20% após 30 segundos.*"
        ))

        embed.add_field(name="🎲 JOGOS E APOSTAS (Canal #🎰・akbet)", inline=False, value=(
            "🎰 **Solo:** `!crash` | `!cassino` | `!minas`| `!corrida` | `!bicho`\n"
            "⚔️ **1x1:**  `!duelo` | `!cipo` | `!bang` | `!briga` | `!carta` | `!explorar`\n"
            "🎮 **Multiplayer:** `!21` | `!roleta` | `!mentira` | `!torneio` | `!coco` \n"
            "⚽ **Futebol:** `!futebol` *(apostar)* | `!pule` *(ver bilhetes)*\n"
            "└ *Use `!jogos` lá no canal de apostas para ver como cada um funciona!*"
        ))

        embed.add_field(name="✨ COSMÉTICOS E PERFIL", inline=False, value=(
            "🎨 **`!visuais`**\n"
            "└ *Veja seus cosméticos no inventário e o que está equipado.*\n"
            "🖼️ **`!visuais <slug>`** ─ *Equipa um cosmético. Ex: `!visuais cor:roxo`*\n"
            "└ *O perfil muda de cor, exibe moldura e título automaticamente.*\n"
            "💬 **`!bio <texto>`** ─ *Define uma frase no perfil (máx. 60 chars). Grátis!*\n"
            "└ *Use `!bio` sem texto para remover.*\n\n"
            "**Raridades disponíveis:**\n"
            "⚫ **Comuns** ─ Cores e títulos básicos (`500–1.500 MC` na `!loja`)\n"
            "🟣 **Raros** ─ Cores, molduras e títulos táticos (`2.000–2.500 MC` na `!loja`)\n"
            "🟡 **Épicos** ─ Cores vibrantes, molduras e títulos premium (`6.000–8.000 MC` na `!loja`)\n"
            "🌟 **Lendários** ─ *Moldura Estrela Cadente, Lenda da Selva e mais — só nas Relíquias!*\n\n"
            "📦 *Cosméticos também saem nas lootboxes:*\n"
            "└ 🪵 Caixote: **15%** comum | 🪙 Baú: **30%** raro | 🏺 Relíquia: **55%** épico/lendário\n"
            "└ *Cosmético duplicado vira MC de consolação automaticamente.*"
        ))

        embed.add_field(name="🤐 CASTIGOS DE VOZ", inline=False, value=(
            "🔇 **`!castigo <mudo/surdo/surdomudo> <1/5/10> @user`**\n"
            "👟 **`!desconectar @user`**"
        ))

        embed.set_footer(text="A selva pune os fracos. Evolua o seu cargo e domine o servidor! 🦍👑")
        await ctx.send(embed=embed)

    @commands.command(aliases=["ganhos", "cargos"])
    async def salarios(self, ctx):
        embed = disnake.Embed(
            title="🍌 GUIA DE PROGRESSÃO DA SELVA",
            description=(
                "Salário base por hora (`!trabalhar`) e custo de cada cargo.\n"
                "⚠️ **Dica:** O trabalho puro não enriquece ninguém — abra caixas, ganhe minigames, roube e invista para subir mais rápido!\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.gold()
        )

        tabela = [
            ("🐒 Lêmure",      "40 – 80 MC",        "—",            "1.200 MC"),
            ("🐵 Macaquinho",  "130 – 230 MC",      "1.200 MC",     "5.500 MC"),
            ("🦍 Babuíno",     "320 – 530 MC",      "5.500 MC",     "14.000 MC"),
            ("🦧 Chimpanzé",   "780 – 1.320 MC",    "14.000 MC",    "35.000 MC"),
            ("🌴 Orangutango", "1.900 – 3.200 MC",  "35.000 MC",    "85.000 MC"),
            ("🌋 Gorila",      "4.700 – 7.800 MC",  "85.000 MC",    "210.000 MC"),
            ("🗿 Ancestral",   "11.500 – 19.000 MC","210.000 MC",   "600.000 MC"),
            ("👑 Rei Símio",   "27.000 – 45.000 MC","600.000 MC",   "MÁXIMO 👑"),
        ]

        for cargo, salario, custo_este, custo_prox in tabela:
            embed.add_field(
                name=cargo,
                value=(
                    f"💰 Salário: **{salario}**\n"
                    f"└ *Preço: `{custo_este}`*\n"
                    f"└ *Próximo: `{custo_prox}`*"
                ),
                inline=True
            )

        embed.set_footer(text="Limites de aposta aumentam a cada cargo — arrisque mais para ganhar mais!")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(General(bot))