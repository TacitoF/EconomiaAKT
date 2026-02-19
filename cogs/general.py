import disnake
from disnake.ext import commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        """Restringe os comandos gerais ao canal #🐒・conguitos."""
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, o guia de comandos e regras só podem ser consultados no canal {mencao}!")
            raise commands.CommandError("Canal incorreto para comandos gerais.")

    @commands.command(name="ajuda", aliases=["comandos", "info"])
    async def ajuda_comando(self, ctx):
        """Mostra todos os comandos disponíveis."""
        
        embed = disnake.Embed(
            title="📖 Guia do Gerente Conguito", 
            description=f"Olá {ctx.author.mention}, aqui está o manual de sobrevivência da selva **AKTrovão**!",
            color=disnake.Color.green()
        )

        # Economia & Interação (Incluindo Roubo aqui)
        economia_txt = (
            "💰 `!trabalhar` - Ganhe conguitos (1h cooldown).\n"
            "👤 `!perfil [@user]` - Ver saldo, cargo e inventário.\n"
            "🛒 `!loja` - Ver preços de itens, cargos e castigos.\n"
            "💳 `!comprar <item>` - Evoluir cargo ou comprar Escudo.\n"
            "🥷 `!roubar @user` - Tenta roubar 20% do saldo (40% chance)."
        )
        embed.add_field(name="💵 ECONOMIA & ROUBOS", value=economia_txt, inline=False)

        # Jogos (Apenas jogos de aposta pura)
        jogos_txt = (
            "🎰 `!cassino <valor>` - Caça-níquel.\n"
            "🏁 `!corrida <corredor> <valor>` - Aposte entre ""Macaquinho"", ""Gorila"" ou ""Orangutango"".\n"
            "🪙 `!moeda <cara/coroa> <valor>` - Dobro ou nada.\n"
            "🦁 `!bicho <animal> <valor>` - escolha entre ""Leao"", ""Cobra"", ""Jacare"", ""Arara"" ou ""Elefante"".\n"
            "💣 `!minas <bombas> <valor>` - escolha entre 1 e 5 bombas.\n"
            "🥊 `!briga @user <valor>` - Desafie alguém para PvP!\n"
            "💡 *Use estes no canal #🎰・akbet*"
        )
        embed.add_field(name="🎲 AK-BET JOGOS", value=jogos_txt, inline=False)

        # Castigos
        castigos_txt = (
            "🔇 `!castigo mudo <tempo> @user` - Silencia alguém.\n"
            "🎧 `!castigo surdo <tempo> @user` - Ensurdece alguém.\n"
            "🤐 `!castigo surdomudo <tempo> @user` - Combo Total.\n"
            "⏱️ *Tempos: 1, 5 ou 10 minutos.*\n"
            "👟 `!desconectar(!kick - !tchau) @user` - Chuta o usuário da call."
        )
        embed.add_field(name="🤐 CASTIGOS DE VOZ", value=castigos_txt, inline=False)

        embed.set_footer(text="Dúvidas? Procure Administração! 🐒")
        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        await ctx.send(content=f"Aqui está sua lista, {ctx.author.mention}!", embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def postar_regras(self, ctx):
        """Posta e fixa as regras no canal atual (Deve ser usado no #🐒・conguitos)."""
        embed = disnake.Embed(title="🍌 Regras da Selva AKTrovão", color=disnake.Color.gold())
        embed.add_field(name="⚒️ Trabalho", value="`!trabalhar` a cada 1h no #🐒・conguitos. Evolua seu primata!", inline=False)
        embed.add_field(name="🥷 Roubos", value="Comando `!roubar` liberado no #🐒・conguitos. Use Escudo para se proteger!", inline=False)
        embed.add_field(name="🎰 Cassino", value="Jogos e apostas liberados apenas no canal #🎰・akbet.", inline=False)
        embed.add_field(name="🤐 Castigos", value="Respeite para não ser castigado. Castigos custam conguitos.", inline=False)
        
        msg = await ctx.send(embed=embed)
        await msg.pin()
        await ctx.send(f"✅ Regras fixadas em {ctx.channel.mention}!")

def setup(bot):
    bot.add_cog(General(bot))