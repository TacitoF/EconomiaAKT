import disnake
from disnake.ext import commands
import database as db
import time
import random

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = 757752617722970243

    async def cog_before_invoke(self, ctx):
        """Restringe comandos de economia ao canal #🐒・conguitos, exceto o comando !jogos."""
        if ctx.command.name == 'jogos':
            return

        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, assuntos de dinheiro e perfil são apenas no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command()
    async def jogos(self, ctx):
        """Lista os jogos disponíveis. Restrito ao canal #🎰・akbet."""
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            return await ctx.send(f"⚠️ {ctx.author.mention}, apostas e jogos são permitidos apenas no canal {mencao}!")

        embed = disnake.Embed(
            title="🎰 AK-BET JOGOS",
            description="Transforme seus conguitos em fortuna!",
            color=disnake.Color.purple()
        )

        embed.add_field(
            name="🎮 Comandos Disponíveis",
            value=(
                "🎰 **!cassino <valor>** - Caça-níquel.\n"
                "🐒 **!corrida <animal> <valor>** - Aposte entre ""Macaquinho"", ""Gorila"" ou ""Orangutango"".\n"
                "🪙 **!moeda <cara/coroa> <valor>** - Dobro ou nada.\n"
                "🦁 **!bicho <animal> <valor>** - escolha entre ""Leao"", ""Cobra"", ""Jacare"", ""Arara"", ""Elefante"".\n"
                "💣 **!minas <bombas> <valor>** - escolha entre 1 e 5 bombas.\n"
                "⚔️ **!briga @user <valor>** - Desafie alguém para PvP!"
            ),
            inline=False
        )

        embed.set_footer(text="Lembre-se: A casa sempre ganha! 🐒")
        await ctx.send(embed=embed)

    @commands.command()
    async def trabalhar(self, ctx):
        user_id = str(ctx.author.id)
        user = db.get_user_data(user_id)
        
        if not user:
            db.create_user(user_id, ctx.author.name)
            user = db.get_user_data(user_id)

        agora = time.time()
        ultimo_work = float(user['data'][4]) if len(user['data']) > 4 and user['data'][4] else 0

        if agora - ultimo_work < 3600:
            restante = int((3600 - (agora - ultimo_work)) / 60)
            return await ctx.send(f"⏳ {ctx.author.mention}, você está exausto! Volte em **{restante} minutos**.")

        cargo = user['data'][3]
        mults = {"Macaquinho": 1.0, "Chimpanzé": 1.5, "Orangutango": 2.5, "Gorila": 4.0}
        ganho = int(random.randint(100, 300) * mults.get(cargo, 1.0))
        
        db.update_value(user['row'], 3, int(user['data'][2]) + ganho)
        db.update_value(user['row'], 5, agora)
        
        await ctx.send(f"✅ {ctx.author.mention}, como **{cargo}**, você ganhou **{ganho} conguitos**!")

    @commands.command()
    async def perfil(self, ctx, membro: disnake.Member = None):
        membro = membro or ctx.author
        user_id = str(membro.id)
        user = db.get_user_data(user_id)
        if not user: return await ctx.send(f"❌ {membro.mention} não tem conta!")

        saldo = user['data'][2]
        cargo = user['data'][3]
        inventario = user['data'][5] if len(user['data']) > 5 and user['data'][5] != "" else "Nenhum"

        embed = disnake.Embed(title=f"🐒 Perfil AKTrovão", color=disnake.Color.gold())
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.add_field(name="💰 Saldo", value=f"{saldo} C", inline=True)
        embed.add_field(name="💼 Cargo", value=cargo, inline=True)
        embed.add_field(name="🎒 Inventário", value=f"`{inventario}`", inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def loja(self, ctx):
        """Lista os itens e serviços disponíveis conforme a imagem solicitada."""
        embed = disnake.Embed(
            title="🛒 Loja de Itens e Maldades AKTrovão",
            description="Use seu saldo para evoluir ou se proteger!",
            color=disnake.Color.blue()
        )

        embed.add_field(
            name="📈 EVOLUÇÃO (Cargos)",
            value=(
                "🐒 **Chimpanzé**: 5.000 C (1.5x)\n"
                "🦧 **Orangutango**: 15.000 C (2.5x)\n"
                "🦍 **Gorila**: 50.000 C (4.0x)\n"
                "------------------------------------------------------------------"
            ),
            inline=False
        )

        embed.add_field(
            name="🛡️ PROTEÇÃO",
            value=(
                "🛡️ **Escudo**: 2.000 C\n"
                "*(Evita 1 roubo. O item quebra após o uso!)*\n"
                "------------------------------------------------------------------"
            ),
            inline=False
        )

        embed.add_field(
            name="🥷 INTERAÇÃO (Roubos)",
            value=(
                "💰 **Comando**: `!roubar @user`\n"
                "⚠️ **Risco**: 40% de sucesso. Se falhar, paga multa para o alvo.\n"
                "⏱️ **Atenção**: Cooldown de 2 horas (mesmo se falhar).\n"
                "------------------------------------------------------------------"
            ),
            inline=False
        )

        embed.add_field(
            name="😬 SERVIÇOS (Castigos)",
            value=(
                "🔇 **Mudo/Surdo**: 1.5k - 7.5k - 15k C\n"
                "😬 **Surdomudo**: 3k - 15k - 30k C\n"
                "⏱️ Tempos: 1, 5 ou 10 minutos.\n"
                "👟 **Desconectar**: 5k C\n"
                "------------------------------------------------------------------"
            ),
            inline=False
        )

        embed.add_field(
            name="📝 Como usar?",
            value=(
                "• Para comprar: `!comprar <nome_do_item>`\n"
                "• Para roubar: `!roubar @user`\n"
                "• Para castigar: `!castigo <tipo> <tempo> @user`\n"
                "• Para desconectar: `!desconectar @user`"
            ),
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def comprar(self, ctx, *, item: str):
        user_id = str(ctx.author.id)
        user = db.get_user_data(user_id)
        if not user: return await ctx.send("❌ Use `!trabalhar` primeiro!")

        loja = {
            "chimpanzé": {"nome": "Chimpanzé", "preco": 5000, "tipo": "cargo"},
            "chimpanze": {"nome": "Chimpanzé", "preco": 5000, "tipo": "cargo"},
            "orangutango": {"nome": "Orangutango", "preco": 15000, "tipo": "cargo"},
            "gorila": {"nome": "Gorila", "preco": 50000, "tipo": "cargo"},
            "escudo": {"nome": "Escudo", "preco": 2000, "tipo": "item"}
        }

        escolha = item.lower()
        if escolha not in loja: return await ctx.send("❌ Item inválido!")
        
        if escolha == "escudo" and "Escudo" in user['data'][5]:
            return await ctx.send(f"🛡️ {ctx.author.mention}, você já tem um escudo ativo!")

        item_data = loja[escolha]
        saldo = int(user['data'][2])

        if saldo < item_data["preco"]: return await ctx.send("❌ Saldo insuficiente!")

        db.update_value(user['row'], 3, saldo - item_data["preco"])
        coluna = 4 if item_data["tipo"] == "cargo" else 6
        db.update_value(user['row'], coluna, item_data["nome"])
        await ctx.send(f"✅ {ctx.author.mention} comprou **{item_data['nome']}**!")

    @commands.command()
    async def roubar(self, ctx, vitima: disnake.Member):
        if vitima.id == ctx.author.id: return await ctx.send("🐒 Não pode roubar de si mesmo!")
        
        ladrao = db.get_user_data(str(ctx.author.id))
        alvo = db.get_user_data(str(vitima.id))
        if not ladrao or not alvo: return await ctx.send("❌ Conta não encontrada!")

        agora = time.time()
        ultimo_roubo = float(ladrao['data'][6]) if len(ladrao['data']) > 6 and ladrao['data'][6] else 0

        if agora - ultimo_roubo < 7200:
            restante = int((7200 - (agora - ultimo_roubo)) / 60)
            return await ctx.send(f"👮 Espere **{restante} minutos** para roubar novamente.")

        if "Escudo" in alvo['data'][5]:
            db.update_value(alvo['row'], 6, "")
            db.update_value(ladrao['row'], 7, agora)
            return await ctx.send(f"🛡️ {vitima.mention} estava protegido por um Escudo!")

        if random.randint(1, 100) <= 40:
            valor = int(int(alvo['data'][2]) * 0.2)
            db.update_value(ladrao['row'], 3, int(ladrao['data'][2]) + valor)
            db.update_value(alvo['row'], 3, int(alvo['data'][2]) - valor)
            db.update_value(ladrao['row'], 7, agora)
            await ctx.send(f"🥷 **SUCESSO!** Roubou **{valor} C** de {vitima.mention}!")
        else:
            multa = int(int(ladrao['data'][2]) * 0.15)
            db.update_value(ladrao['row'], 3, int(ladrao['data'][2]) - multa)
            db.update_value(alvo['row'], 3, int(alvo['data'][2]) + multa)
            db.update_value(ladrao['row'], 7, agora)
            await ctx.send(f"👮 **PRESO!** Pagou **{multa} C** de multa.")

    @commands.command()
    async def setar(self, ctx, membro: disnake.Member, valor: int):
        """Modifica a quantidade de conguitos de um usuário. Apenas para o dono."""
        if ctx.author.id != self.owner_id:
            return await ctx.send(f"❌ {ctx.author.mention}, você não tem permissão para usar este comando!")

        user = db.get_user_data(str(membro.id))
        if not user:
            return await ctx.send("❌ Usuário não encontrado no banco de dados!")

        try:
            db.update_value(user['row'], 3, valor)
            await ctx.send(f"✅ O saldo de {membro.mention} foi definido para **{valor} C** por {ctx.author.mention}!")
        except Exception as e:
            await ctx.send(f"⚠️ Erro ao atualizar: {e}")

    @commands.command()
    async def wipe(self, ctx):
        """Reseta toda a economia. Comando exclusivo do dono."""
        if ctx.author.id != self.owner_id:
            return await ctx.send(f"❌ {ctx.author.mention}, você não tem permissão para usar este comando!")

        await ctx.send("🧹 Iniciando a limpeza total da planilha de economia...")
        try:
            db.wipe_database() 
            await ctx.send("✅ **WIPE CONCLUÍDO!** Todos os saldos, cargos e inventários foram resetados.")
        except Exception as e:
            await ctx.send(f"⚠️ Ocorreu um erro ao tentar limpar a planilha: {e}")

def setup(bot):
    bot.add_cog(Economy(bot))