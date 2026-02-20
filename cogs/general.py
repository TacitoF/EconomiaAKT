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
            "👤 `!perfil [@user]` - Ver saldo, cargo, inventário e **🏅 Badges**.\n"
            "🏆 `!rank` (!top) - Veja os primatas mais ricos do servidor.\n"
            "🛒 `!loja` - Ver preços de itens (Pé de Cabra, Escudo), cargos e castigos.\n"
            "💳 `!comprar <item>` - Evoluir cargo ou comprar itens de proteção/ação.\n"
            "🥷 `!roubar @user` - Rouba 20% do saldo (Anti-foco: máx 2 roubos a cada 2h).\n"
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
            "🎰 `!cassino <valor>` - Caça-níquel.\n"
            "🏁 `!corrida <corredor> <valor>` - Aposte entre \"Macaquinho\", \"Gorila\" ou \"Orangutango\".\n"
            "🪙 `!moeda <cara/coroa> <valor>` - Dobro ou nada.\n"
            "🦁 `!bicho <animal> <valor>` - Escolha entre \"Leao\", \"Cobra\", \"Jacare\", \"Arara\" ou \"Elefante\".\n"
            "💣 `!minas <bombas> <valor>` - Escolha entre 1 e 5 bombas.\n"
            "🥊 `!briga @user <valor>` - Desafie alguém para PvP!\n"
            "🎫 `!loteria` (!bilhete) - Compre um bilhete (500 C) para o sorteio acumulado!\n"
            "💰 `!pote` (!premio) - Veja o valor total acumulado na loteria.\n"
            "💡 *Use os jogos no canal #🎰・akbet (Loteria também funciona no banco)*"
        )
        embed.add_field(name="🎲 AK-BET JOGOS & EVENTOS", value=jogos_txt, inline=False)

        # Castigos
        castigos_txt = (
            "🔇 `!castigo mudo <tempo> @user` - Silencia alguém.\n"
            "🎧 `!castigo surdo <tempo> @user` - Ensurdece alguém.\n"
            "🤐 `!castigo surdomudo <tempo> @user` - Combo Total.\n"
            "⏱️ *Tempos: 1, 5 ou 10 minutos.*\n"
            "👟 `!desconectar` (@kick) - Chuta o usuário da call."
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
            title="📢 GRANDE ATUALIZAÇÃO DA SELVA: A Era do Caos! (V2.0) 🍌🦍",
            description="O Gerente Conguito recebeu um pacote gigante de novidades! A economia mudou, o submundo cresceu e o cassino expandiu. Confiram as novidades:",
            color=disnake.Color.brand_red()
        )

        embed.add_field(name="📉 1. DEFLAÇÃO TOTAL", value="Tudo ficou mais barato! Os preços da `!loja` e dos castigos de voz despencaram.", inline=False)
        
        embed.add_field(name="🏅 2. BADGES DE PERFIL", value="O `!perfil` agora exibe suas conquistas automáticas (💎 Magnata, 👑 Rei da Selva, 🕵️ Invasor e 🦴 Passando Fome).", inline=False)
        
        embed.add_field(name="💸 3. PIX DO MACACO", value="Agora você pode transferir conguitos! Use `!pagar @usuario <valor>`. Façam alianças ou ajudem os falidos.", inline=False)
        
        embed.add_field(name="🚨 4. CAÇADORES DE RECOMPENSA (Mercenários)", value="Alguém te irritou? Coloque a cabeça dele a prêmio com `!recompensa @usuario <valor>`. O primeiro que conseguir roubar essa vítima com sucesso leva o roubo E a recompensa!", inline=False)
        
        embed.add_field(name="🕵️ 5. NOVO ITEM: PÉ DE CABRA", value="Vendido na `!loja` por 1.200 C. Ele aumenta a chance de sucesso no seu próximo roubo para **70%**! *(Quebra após o uso)*.", inline=False)
        
        embed.add_field(name="🏦 6. SISTEMA BANCÁRIO", value="`!investir fixo <valor>`: Rende +10% garantido na hora (Máx 5k por dia).\n`!investir cripto <valor>`: Volátil! Risco de perder até -25% ou ganhar até +25% em 1 min.", inline=False)
        
        embed.add_field(name="🎫 7. LOTERIA ACUMULADA", value="Compre um `!bilhete` por 500 C. O dinheiro vai para um pote. Use **`!pote`** para ver o prêmio acumulado. Quando a administração realizar o sorteio, **UM ÚNICO SORTUDO** leva tudo!", inline=False)

        embed.set_footer(text="Digite !ajuda para ver o manual completo atualizado.")
        
        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await ctx.send(content="@everyone Atualização fresquinha!", embed=embed)
        
        # Apaga o seu comando '!patchnotes' do chat para ficar limpo
        await ctx.message.delete()

def setup(bot):
    bot.add_cog(General(bot))