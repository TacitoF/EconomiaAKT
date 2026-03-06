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
            "💰 **`!trabalhar`** ─ *Trabalhe a cada 1h para lucrar e achar caixas.*\n"
            "👤 **`!perfil [@user]`** ─ *Cartão público com cargo, estilo e conquistas.*\n"
            "└ *No próprio perfil: botão para ver sua conta privada.*\n"
            "└ *No perfil alheio: botão para comprar o dossiê completo (500 MC).*\n"
            "🔒 **`!conta`** ─ *Seu saldo, cooldowns e inventário (some em 60s).*\n"
            "🏆 **`!rank`** ─ *Top 10 da selva* | 🏅 **`!conquistas`** ─ *Emblemas.*\n"
            "💵 **`!salarios`** ─ *Tabela de ganhos e limites de aposta por cargo.*\n"
            "💸 **`!pagar @user <valor>`** ─ *Transfira MC para outro macaco.*"
        ))

        embed.add_field(name="📦 MERCADO E CONTRABANDO", inline=False, value=(
            "🛒 **`!loja`** ─ *Mercado negro: cargos, itens, lootboxes e cosméticos.*\n"
            "🔓 **`!abrir <caixote/baú/relíquia>`** ─ *Abra caixas do inventário.*\n"
            "📊 **`!caixas`** ─ *Porcentagens e recompensas de cada lootbox.*\n"
            "✈️ **Airdrops** ─ *Caem do nada no chat. O 1º a `SAQUEAR` leva a caixa!*"
        ))

        embed.add_field(name="😈 ROUBOS E SABOTAGEM", inline=False, value=(
            "🥷 **`!roubar @user`** ─ *Assalte alguém para roubar MC (cooldown 2h).*\n"
            "🛡️ **`!escudo`** ─ *Checa defesa* | 🧨 **`!c4 @user`** ─ *Destrói escudo.*\n"
            "🚨 **`!recompensa @user <valor>`** ─ *Coloca a cabeça do alvo a prêmio.*\n"
            "📜 **`!recompensas`** ─ *Mural de procurados da selva.*\n"
            "🍌 **`!casca @user`** ─ *Atrasa o trabalho do alvo.*\n"
            "🦍 **`!taxar @user`** ─ *Rouba 25% do próximo trabalho.*\n"
            "🪄 **`!apelidar @user <nick>`** ─ *Altera o apelido de alguém.*\n"
            "🧪 **`!energetico`** ─ *Zera CD trabalho* | 💨 **`!fumaca`** ─ *Zera CD roubo.*"
        ))

        embed.add_field(name="🏦 BANCO E INVESTIMENTO", inline=False, value=(
            "🏛️ **`!investir fixo <valor>`** ─ *+10% garantido na hora (limite 5.000 MC/dia).*\n"
            "📈 **`!investir cripto <valor>`** ─ *Alto risco! -25% a +20% após 30s.*"
        ))

        embed.add_field(name="🃏 TRUCO (neste canal)", inline=False, value=(
            "🎴 **`!truco 1v1 <aposta>`** ─ *Desafio individual. Ex: `!truco 1v1 500`*\n"
            "🎴 **`!truco 2v2 <aposta>`** ─ *Duplas. Ex: `!truco 2v2 1000` (por jogador)*\n"
            "└ *Truco Paulista completo: mão de 11, truco/seis/nove/doze, aposta livre.*\n"
            "└ *Adversários clicam **Entrar** no lobby → cartas enviadas em privado.*"
        ))

        embed.add_field(name="🎲 JOGOS E APOSTAS (Canal #🎰・akbet)", inline=False, value=(
            "🎰 **Solo:** `!crash` | `!cassino` | `!minas` | `!corrida` | `!bicho`\n"
            "⚔️ **1x1:** `!duelo` | `!cipo` | `!bang` | `!briga` | `!carta` | `!explorar`\n"
            "🎮 **Multiplayer:** `!21` | `!roleta` | `!mentira` | `!torneio` | `!coco`\n"
            "⚽ **Futebol:** `!futebol` *(apostar)* | `!pule` *(ver bilhetes e cancelar)*\n"
            "└ *Use `!jogos` no canal de apostas para ver como cada um funciona!*"
        ))

        embed.add_field(name="✨ COSMÉTICOS E PERFIL", inline=False, value=(
            "🎨 **`!visuais`** ─ *Painel privado para equipar/remover cosméticos.*\n"
            "💬 **`!bio <texto>`** ─ *Frase no perfil (máx. 60 chars). `!bio` para remover.*\n\n"
            "**Raridades:** ⚫ Comuns · 🔵 Raros · 🟣 Épicos · 🌟 Lendários *(só nas Relíquias)*"
        ))

        embed.add_field(name="🤐 CASTIGOS DE VOZ", inline=False, value=(
            "🔇 **`!castigo <mudo/surdo/surdomudo> <1/5/10> @user`**\n"
            "👟 **`!desconectar @user`**"
        ))

        embed.set_footer(text="A selva pune os fracos. Evolua o seu cargo e domine o servidor! 🦍👑")
        await ctx.send(embed=embed)

    @commands.command(aliases=["ganhos", "cargos", "limites"])
    async def salarios(self, ctx):
        embed = disnake.Embed(
            title="🍌 GUIA DE PROGRESSÃO DA SELVA",
            description=(
                "Veja o salário base por hora (`!trabalhar`), custo e limite de aposta de cada cargo.\n"
                "⚠️ **Dica:** O trabalho puro não enriquece ninguém — abra caixas, ganhe minigames, roube e invista para subir mais rápido!\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.gold()
        )

        # Atualizado para incluir os Limites Máximos de Aposta
        tabela = [
            ("🐒 Lêmure",      "40 – 80 MC",        "400 MC",         "—",            "1.200 MC"),
            ("🐵 Macaquinho",  "130 – 230 MC",      "1.500 MC",       "1.200 MC",     "5.500 MC"),
            ("🦍 Babuíno",     "320 – 530 MC",      "4.500 MC",       "5.500 MC",     "14.000 MC"),
            ("🦧 Chimpanzé",   "780 – 1.320 MC",    "12.000 MC",      "14.000 MC",    "35.000 MC"),
            ("🌴 Orangutango", "1.900 – 3.200 MC",  "30.000 MC",      "35.000 MC",    "85.000 MC"),
            ("🌋 Gorila",      "4.700 – 7.800 MC",  "80.000 MC",      "85.000 MC",    "210.000 MC"),
            ("🗿 Ancestral",   "11.500 – 19.000 MC","250.000 MC",     "210.000 MC",   "600.000 MC"),
            ("👑 Rei Símio",   "27.000 – 45.000 MC","1.500.000 MC",   "600.000 MC",   "MÁXIMO 👑"),
        ]

        for cargo, salario, limite_aposta, custo_este, custo_prox in tabela:
            embed.add_field(
                name=cargo,
                value=(
                    f"💰 Salário: **{salario}**\n"
                    f"🎰 Aposta Máx: **`{limite_aposta}`**\n"
                    f"└ *Preço: `{custo_este}`*\n"
                    f"└ *Próximo: `{custo_prox}`*"
                ),
                inline=True
            )

        embed.set_footer(text="Evolua o seu cargo na !loja para conseguir apostar valores mais altos!")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(General(bot))