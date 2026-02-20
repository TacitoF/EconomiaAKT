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
            "🏅 `!conquistas` (!emblemas) - Veja o guia de troféus e segredos.\n"
            "🏆 `!rank` (!top) - Veja os primatas mais ricos do servidor.\n"
            "🛒 `!loja` - Ver preços de itens, cargos e castigos.\n"
            "💳 `!comprar <item>` - Evoluir cargo ou comprar itens.\n"
            "💸 `!pagar @user <valor>` (!pix) - Transfira dinheiro para outro macaco."
        )
        embed.add_field(name="💵 ECONOMIA E PERFIL", value=economia_txt, inline=False)

        # Roubos, Caçadas e Sabotagem (ATUALIZADO)
        sabotagem_txt = (
            "🥷 `!roubar @user` - 40% de chance de roubar 20% do saldo do alvo.\n"
            "🚨 `!recompensa @user <valor>` - Coloque a cabeça de alguém a prêmio!\n"
            "📜 `!recompensas` (!procurados) - Veja o mural com todos os procurados.\n"
            "🍌 `!casca @user` - Faz o alvo falhar no próximo trabalho/roubo (Requer item).\n"
            "🦍 `!taxar @user` - Rouba 25% de todo o trabalho do alvo por **24 horas**! (Requer item).\n"
            "🪄 `!apelidar @user <nick>` - Muda o apelido de alguém por 30min (Requer item)."
        )
        embed.add_field(name="😈 ROUBOS, CAÇADAS E SABOTAGEM", value=sabotagem_txt, inline=False)

        # Banco & Investimentos
        banco_txt = (
            "🏛️ `!investir fixo <valor>` - Seguro! Rende **+10%** na hora (Limite 5.000 C/dia).\n"
            "📈 `!investir cripto <valor>` - Risco Alto! Rende entre **-25% a +25%** em 1 min."
        )
        embed.add_field(name="🏦 BANCO E INVESTIMENTOS", value=banco_txt, inline=False)

        # Jogos & Eventos
        jogos_txt = (
            "🚀 `!crash <valor>` - Foguetinho! Suba no cipó e digite `parar` a tempo.\n"
            "🎰 `!cassino <valor>` - Caça-níquel.\n"
            "🥥 `!coco <valor>` - Crie uma Roleta do Coco Explosivo.\n"
            "🏃 `!entrar_coco` - Entre na roda de coco antes do tempo acabar!\n"
            "🏁 `!corrida <corredor> <valor>` - Aposte entre Macaquinho, Gorila ou Orangutango.\n"
            "🪙 `!moeda <cara/coroa> <valor>` - Dobro ou nada.\n"
            "🦁 `!bicho <animal> <valor>` - Escolha Leao, Cobra, Jacare, Arara ou Elefante.\n"
            "💣 `!minas <bombas> <valor>` - Escolha entre 1 e 5 bombas.\n"
            "🥊 `!briga @user <valor>` - Desafie alguém para PvP!\n"
            "🎫 `!loteria` (!bilhete) - Compre um bilhete (500 C) para o sorteio!\n"
            "💰 `!pote` (!premio) - Veja o valor acumulado na loteria.\n"
            "🃏 `!carta @user <valor>` - Desafie alguém para um duelo de cartas!\n"
            "♠️ `!bj <valor>` (!21) - Crie uma mesa de **Blackjack MULTIPLAYER**!\n"
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
        
        await ctx.send(content=f"Aqui está sua lista completa atualizada, {ctx.author.mention}!", embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def postar_regras(self, ctx):
        """Posta e fixa as regras no canal atual (Deve ser usado no #🐒・conguitos)."""
        embed = disnake.Embed(title="🍌 Regras da Selva AKTrovão", color=disnake.Color.gold())
        embed.add_field(name="⚒️ Trabalho", value="`!trabalhar` a cada 1h no #🐒・conguitos. Evolua seu primata!", inline=False)
        embed.add_field(name="🏦 Investimentos & Pix", value="Multiplique seus conguitos no banco ou faça transferências para outros jogadores.", inline=False)
        embed.add_field(name="🥷 Roubos & Caçadas", value="Use `!roubar` e `!recompensa`. Cuidado com o Pé de Cabra, use Escudos e coloque seus inimigos a prêmio! Consulte o mural com `!recompensas`.", inline=False)
        embed.add_field(name="😈 Sabotagem", value="A loja agora vende itens sujos. Você pode fazer amigos escorregarem com `!casca`, taxar o salário deles com `!taxar` ou mudar o nome deles com `!apelidar`.", inline=False)
        embed.add_field(name="🏆 Ranking", value="Use `!rank` para ver o pódio da ostentação.", inline=False)
        embed.add_field(name="🎰 Cassino & Loteria", value="Jogos, apostas e sorteios acumulados liberados no canal #🎰・akbet.", inline=False)
        embed.add_field(name="🤐 Castigos", value="Respeite para não ser castigado. Castigos de voz custam conguitos.", inline=False)
        
        msg = await ctx.send(embed=embed)
        await msg.pin()
        await ctx.send(f"✅ Regras fixadas em {ctx.channel.mention}!")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def patchnotes(self, ctx):
        """Envia o anúncio de atualização do bot (Apenas Admin)."""
        embed = disnake.Embed(
            title="📢 ATUALIZAÇÃO DA SELVA: A Era da Sabotagem! 😈🍌 (V4.0)",
            description="A economia mudou! O Gerente Conguito abriu o mercado negro e agora a selva virou terra sem lei. Confiram as novidades de peso desta versão:",
            color=disnake.Color.brand_red()
        )

        # TEXTO ATUALIZADO AQUI TAMBÉM
        embed.add_field(
            name="😈 1. NOVOS ITENS DE SABOTAGEM", 
            value="Chegou a hora de infernizar a vida dos seus amigos (Compre na `!loja`):\n"
                  "🍌 **Casca de Banana:** Use `!casca @user` e faça o próximo trabalho ou roubo do alvo dar completamente errado!\n"
                  "🦍 **Imposto do Gorila:** Use `!taxar @user` e extorqua 25% de todo o dinheiro que a vítima ganhar trabalhando durante **24 horas** diretas!\n"
                  "🪄 **Troca de Nick:** Use `!apelidar @user <novo_nome>` para humilhar alguém mudando o apelido dele no servidor por 30 minutos.", 
            inline=False
        )

        embed.add_field(
            name="🛡️ 2. NOVO ITEM DE PROTEÇÃO: SEGURO", 
            value="Cansado de perder suas fortunas para ladrões com Pé de Cabra? Compre o **Seguro** na `!loja`. Se alguém te assaltar e você tiver o seguro no inventário, o Banco da Selva te reembolsa 60% do valor roubado automaticamente!", 
            inline=False
        )
        
        embed.add_field(
            name="📜 3. MURAL DE PROCURADOS", 
            value="O sistema de recompensas (`!recompensa`) foi atualizado. Agora, se várias pessoas colocarem recompensa na mesma pessoa, **o valor se acumula**! Você pode ver a lista de cabeças a prêmio usando o comando **`!recompensas`** (ou `!procurados`).", 
            inline=False
        )

        embed.add_field(
            name="🎒 4. INVENTÁRIO INFINITO E ACUMULATIVO", 
            value="Sua mochila cresceu! Agora você pode comprar e estocar **múltiplos itens iguais ou diferentes** ao mesmo tempo (ex: 3x Escudo, 2x Casca de Banana). Acumule seu arsenal na `!loja` e veja tudo no seu `!perfil`!", 
            inline=False
        )

        embed.add_field(
            name="♠️ 5. BLACKJACK OTIMIZADO", 
            value="O jogo de `!21` foi reconstruído do zero. A contagem de jogadores no lobby foi arrumada, o sistema de **Split (Dividir)** foi adicionado e regras de Empate Mútuo (quando ambos estouram) foram corrigidas.", 
            inline=False
        )

        embed.set_footer(text="A caça aos troféus e a sabotagem mútua começaram! Digite !ajuda para ver tudo.")
        
        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await ctx.send(content="🚨 **ATUALIZAÇÃO DE MERCADO NEGRO E SABOTAGEM LIBERADA!** 🚨\n", embed=embed)
        await ctx.message.delete()

def setup(bot):
    bot.add_cog(General(bot))