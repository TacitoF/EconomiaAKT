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

        # Economia & Interação
        economia_txt = (
            "💰 `!trabalhar` - Ganhe conguitos (1h cooldown).\n"
            "👤 `!perfil [@user]` - Ver saldo, cargo, inventário e **🏆 Conquistas**.\n"
            "🏅 `!conquistas` (!emblemas) - Veja o guia completo de troféus e segredos da selva.\n"
            "🏆 `!rank` (!top) - Veja os primatas mais ricos do servidor.\n"
            "🛒 `!loja` - Ver preços de itens (Pé de Cabra, Escudo), cargos e castigos.\n"
            "💳 `!comprar <item>` - Evoluir cargo ou comprar itens de proteção/ação.\n"
            "🥷 `!roubar @user` - 40% de chance de roubar 20% do saldo do alvo.\n"
            "💸 `!pagar @user <valor>` (!pix) - Transfira dinheiro para outro macaco.\n"
            "🚨 `!recompensa @user <valor>` - Coloque a cabeça de um macaco a prêmio!"
        )
        embed.add_field(name="💵 ECONOMIA, ROUBOS & RECOMPENSAS", value=economia_txt, inline=False)

        # Banco & Investimentos
        banco_txt = (
            "🏛️ `!investir fixo <valor>` - Seguro! Rende **+10%** na hora (Limite 5.000 C/dia).\n"
            "📈 `!investir cripto <valor>` - Risco Alto! Rende entre **-25% a +25%** em 1 min (Sem limites)."
        )
        embed.add_field(name="🏦 BANCO E INVESTIMENTOS", value=banco_txt, inline=False)

        # Jogos & Eventos
        jogos_txt = (
            "🚀 `!crash <valor>` - Foguetinho! Suba no cipó e digite `parar` a tempo.\n"
            "🎰 `!cassino <valor>` - Caça-níquel.\n"
            "🥥 `!coco <valor>` - Crie uma Roleta do Coco Explosivo.\n"
            "🏃 `!entrar_coco` - Entre na roda de coco antes do tempo acabar!\n"
            "🏁 `!corrida <corredor> <valor>` - Aposte entre \"Macaquinho\", \"Gorila\" ou \"Orangutango\".\n"
            "🪙 `!moeda <cara/coroa> <valor>` - Dobro ou nada.\n"
            "🦁 `!bicho <animal> <valor>` - Escolha entre \"Leao\", \"Cobra\", \"Jacare\", \"Arara\" ou \"Elefante\".\n"
            "💣 `!minas <bombas> <valor>` - Escolha entre 1 e 5 bombas.\n"
            "🥊 `!briga @user <valor>` - Desafie alguém para PvP!\n"
            "🎫 `!loteria` (!bilhete) - Compre um bilhete (500 C) para o sorteio acumulado!\n"
            "💰 `!pote` (!premio) - Veja o valor total acumulado na loteria.\n"
            "🃏 `!carta @user <valor>` - Desafie alguém para um duelo de cartas!\n"
            "♠️ `!21 <valor>` - Jogue contra o dealer e tente chegar mais perto de 21!\n"
            "💡 *Use os jogos no canal #🎰・akbet*"
        )
        embed.add_field(name="🎲 AK-BET JOGOS & EVENTOS", value=jogos_txt, inline=False)

        # Castigos
        castigos_txt = (
            "🔇 `!castigo mudo <tempo> @user` - Silencia alguém.\n"
            "🎧 `!castigo surdo <tempo> @user` - Ensurdece alguém.\n"
            "🤐 `!castigo surdomudo <tempo> @user` - Combo Total.\n"
            "⏱️ *Tempos: 1, 5 ou 10 minutos.*\n"
            "👟 `!desconectar` (!kick) - Chuta o usuário da call."
        )
        embed.add_field(name="🤐 CASTIGOS DE VOZ", value=castigos_txt, inline=False)

        embed.set_footer(text="Dúvidas? Procure a Administração! 🐒")
        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        await ctx.send(content=f"Aqui está sua lista, {ctx.author.mention}!", embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def postar_regras(self, ctx):
        """Posta e fixa as regras no canal atual (Deve ser usado no #🐒・conguitos)."""
        embed = disnake.Embed(title="🍌 Regras da Selva AKTrovão", color=disnake.Color.gold())
        embed.add_field(name="⚒️ Trabalho", value="`!trabalhar` a cada 1h no #🐒・conguitos. Evolua seu primata!", inline=False)
        embed.add_field(name="🏦 Investimentos & Pix", value="Multiplique seus conguitos no banco ou faça transferências para outros jogadores.", inline=False)
        embed.add_field(name="🥷 Roubos & Recompensas", value="Use `!roubar` e `!recompensa` no #🐒・conguitos. Cuidado com o Pé de Cabra, use Escudos e coloque inimigos a prêmio!", inline=False)
        embed.add_field(name="🏆 Ranking", value="Use `!rank` para ver o pódio da ostentação.", inline=False)
        embed.add_field(name="🎰 Cassino & Loteria", value="Jogos, apostas e sorteios acumulados liberados no canal #🎰・akbet.", inline=False)
        embed.add_field(name="🤐 Castigos", value="Respeite para não ser castigado. Castigos custam conguitos.", inline=False)
        
        msg = await ctx.send(embed=embed)
        await msg.pin()
        await ctx.send(f"✅ Regras fixadas em {ctx.channel.mention}!")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def patchnotes(self, ctx):
        """Envia o anúncio de atualização do bot (Apenas Admin)."""
        embed = disnake.Embed(
            title="📢 ATUALIZAÇÃO DA SELVA: Novos Jogos & Conquistas! 🏆🎰 (V3.2)",
            description="O Gerente Conguito trouxe novos vícios para a selva e instalou um sistema de troféus para separar os verdadeiros reis dos macacos de imitação! Confiram as novidades:",
            color=disnake.Color.brand_red()
        )

        embed.add_field(
            name="📜 1. NOVO COMANDO: `!conquistas`", 
            value="Use este comando (ou `!emblemas`) para abrir o Guia Oficial. Lá você verá o que precisa fazer para desbloquear emblemas baseados no seu Rank, Riqueza e Atividades diárias.", 
            inline=False
        )

        embed.add_field(
            name="🏅 2. NOVO `!perfil`", 
            value="Suas vitórias (e fracassos) agora ficam cravadas no seu perfil para todos verem! **Atenção:** Algumas conquistas como *Proletário Padrão* e *Mestre das Sombras* resetam diariamente. Mantenha o ritmo para não perder o status!", 
            inline=False
        )
        
        embed.add_field(
            name="🤫 3. SEGREDOS DA SELVA", 
            value="O guia possui uma área de Conquistas Secretas (???). Elas são desbloqueadas através de azar absurdo ou sorte extrema. Testem os limites dos comandos e descubram!", 
            inline=False
        )

        embed.add_field(
            name="🎰 4. VISUAL DO CASSINO & JACKPOT", 
            value="O comando `!cassino` ganhou uma interface de caça-níquel real. Quem conseguir a proeza de tirar 3 emojis iguais vai estourar um **JACKPOT** de 10x o valor apostado.", 
            inline=False
        )

        embed.add_field(
            name="🚀 5. NOVO JOGO: CRASH DO CIPÓ", 
            value="O foguetinho chegou na selva! Use `!crash <valor>`. O macaco vai subir e o multiplicador de dinheiro vai aumentar. Digite **`parar`** no chat antes que o cipó arrebente para garantir seu lucro!", 
            inline=False
        )

        embed.add_field(
            name="🥥 6. NOVO JOGO: COCO EXPLOSIVO", 
            value="Roleta mortal multiplayer! Inicie com `!coco <valor>`. Os outros macacos têm 1 minuto para entrar usando `!entrar_coco`. O coco vai passar de mão em mão até explodir. O último que sobreviver leva o dinheiro de todo mundo!", 
            inline=False
        )

        embed.add_field(
            name="🃏 7. NOVO JOGO: DUELO DE CARTAS", 
            value="Desafie alguém para um duelo de cartas! Use `!carta <usuário> <valor>`. Quem tirar a carta maior vence o pote!", 
            inline=False
        )

        embed.add_field(
            name="♠️ 8. NOVO JOGO: BLACK JACK (21) BETA", 
            value="Teste sua sorte contra o dealer! Use `!21 <valor>`. Tente chegar o mais próximo possível de 21 sem passar. Se vencer, ganha o dobro do valor apostado!", 
            inline=False
        )

        embed.set_footer(text="A caça aos troféus (e o vício) começou! Digite !ajuda para ver tudo.")
        
        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await ctx.send(content="🚨 **ATUALIZAÇÃO DE JOGOS E CONQUISTAS LIBERADA!** 🚨\n", embed=embed)
        
        # Apaga o seu comando '!patchnotes' do chat para ficar limpo
        await ctx.message.delete()

def setup(bot):
    bot.add_cog(General(bot))