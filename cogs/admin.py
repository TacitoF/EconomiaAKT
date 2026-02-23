import disnake
from disnake.ext import commands
import database as db

OWNER_ID = 757752617722970243

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ajudaadm(self, ctx):
        if ctx.author.id != OWNER_ID: 
            return

        embed = disnake.Embed(
            title="🛠️ Painel de Controle Administrativo",
            description="Comandos exclusivos para a gerência da selva.",
            color=disnake.Color.dark_grey()
        )
        embed.add_field(
            name="🏆 Conquistas", 
            value="`!darconquista @membro slug` - Grava conquista\n`!removerconquista @membro slug` - Remove conquista", 
            inline=False
        )
        embed.add_field(
            name="💰 Economia", 
            value="`!setar @membro valor` - Define saldo exato\n`!adicionar @membro valor` - Soma ao saldo\n`!remover @membro valor` - Subtrai do saldo\n`!wipe` - Reseta toda a planilha", 
            inline=False
        )
        embed.add_field(
            name="⚙️ Sistema & Avisos", 
            value="`!ligar` / `!desligar` - Trava global de manutenção\n`!postar_regras` - Envia e fixa as regras\n`!patchnotes` - Envia as notas da versão atual", 
            inline=False
        )
        embed.add_field(
            name="🎰 Loteria", 
            value="`!sortear_loteria` - Sorteia o pote atual da loteria e premia o vencedor", 
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def darconquista(self, ctx, membro: disnake.Member = None, slug: str = None):
        if ctx.author.id != OWNER_ID: return 
        if membro is None or slug is None:
            return await ctx.send("⚠️ Use: `!darconquista @membro slug_da_conquista`")
        try:
            u = db.get_user_data(str(membro.id))
            if not u: return await ctx.send("❌ Usuário não encontrado!")
            conquistas = str(u['data'][9]) if len(u['data']) > 9 else ""
            lista = [c.strip() for c in conquistas.split(',') if c.strip()]
            if slug in lista: return await ctx.send(f"⚠️ {membro.display_name} já possui esta conquista!")
            lista.append(slug)
            db.update_value(u['row'], 10, ", ".join(lista))
            await ctx.send(f"🏆 Conquista `{slug}` gravada para {membro.mention}!")
        except Exception as e:
            print(f"❌ Erro no !darconquista: {e}")

    @commands.command()
    async def removerconquista(self, ctx, membro: disnake.Member = None, slug: str = None):
        if ctx.author.id != OWNER_ID: return 
        if membro is None or slug is None:
            return await ctx.send("⚠️ Use: `!removerconquista @membro slug_da_conquista`")
        try:
            u = db.get_user_data(str(membro.id))
            if not u: return await ctx.send("❌ Usuário não encontrado!")
            conquistas = str(u['data'][9]) if len(u['data']) > 9 else ""
            lista = [c.strip() for c in conquistas.split(',') if c.strip()]
            if slug not in lista: return await ctx.send(f"❌ {membro.display_name} não possui essa conquista.")
            lista.remove(slug)
            db.update_value(u['row'], 10, ", ".join(lista))
            await ctx.send(f"🧹 Conquista `{slug}` removida de {membro.mention}!")
        except Exception as e:
            print(f"❌ Erro no !removerconquista: {e}")

    @commands.command()
    async def setar(self, ctx, membro: disnake.Member = None, valor: float = None):
        if ctx.author.id != OWNER_ID: return 
        if membro is None or valor is None:
            return await ctx.send("⚠️ Use: `!setar @membro <valor>`")
        try:
            u = db.get_user_data(str(membro.id))
            if not u: return await ctx.send("❌ Usuário não encontrado!")
            valor = round(valor, 2)
            db.update_value(u['row'], 3, valor)
            await ctx.send(f"✅ Saldo de {membro.mention} definido em **{valor:.2f} C**.")
        except Exception as e:
            print(f"❌ Erro no !setar: {e}")

    @commands.command(aliases=["add", "dar"])
    async def adicionar(self, ctx, membro: disnake.Member = None, valor: float = None):
        if ctx.author.id != OWNER_ID: return 
        if membro is None or valor is None:
            return await ctx.send("⚠️ Use: `!adicionar @membro <valor>`")
        try:
            u = db.get_user_data(str(membro.id))
            if not u: return await ctx.send("❌ Usuário não encontrado!")
            saldo_atual = float(str(u['data'][2]).replace(',', '.'))
            novo_saldo = round(saldo_atual + valor, 2)
            db.update_value(u['row'], 3, novo_saldo)
            await ctx.send(f"📈 **+{valor:.2f} C** adicionados para {membro.mention}. (Saldo: `{novo_saldo:.2f} C`)")
        except Exception as e:
            print(f"❌ Erro no !adicionar: {e}")

    @commands.command(aliases=["tirar", "subtrair"])
    async def remover(self, ctx, membro: disnake.Member = None, valor: float = None):
        if ctx.author.id != OWNER_ID: return 
        if membro is None or valor is None:
            return await ctx.send("⚠️ Use: `!remover @membro <valor>`")
        try:
            u = db.get_user_data(str(membro.id))
            if not u: return await ctx.send("❌ Usuário não encontrado!")
            saldo_atual = float(str(u['data'][2]).replace(',', '.'))
            novo_saldo = max(round(saldo_atual - valor, 2), 0.0)
            db.update_value(u['row'], 3, novo_saldo)
            await ctx.send(f"📉 **-{valor:.2f} C** removidos de {membro.mention}. (Saldo: `{novo_saldo:.2f} C`)")
        except Exception as e:
            print(f"❌ Erro no !remover: {e}")

    @commands.command()
    async def wipe(self, ctx):
        if ctx.author.id != OWNER_ID: return 
        await ctx.send("🧹 Resetando toda a economia da selva...")
        try:
            db.wipe_database()
            await ctx.send("✅ **WIPE CONCLUÍDO!** Todos os macacos voltaram ao zero.")
        except Exception as e:
            await ctx.send(f"⚠️ Erro ao realizar wipe: {e}")

    @commands.command()
    async def postar_regras(self, ctx):
        if ctx.author.id != OWNER_ID: return 
        embed = disnake.Embed(title="🍌 Regras da Selva AKTrovão", color=disnake.Color.gold())
        embed.add_field(name="⚒️ Trabalho", value="`!trabalhar` a cada 1h no #🐒・conguitos.", inline=False)
        embed.add_field(name="🏦 Banco & Pix", value="Multiplique conguitos no banco ou faça Pix.", inline=False)
        embed.add_field(name="🥷 Roubos & Caçadas", value="Use `!roubar` e `!recompensa`. Consulte `!perfil`.", inline=False)
        embed.add_field(name="😈 Sabotagem", value="Itens para sabotar: `!casca`, `!taxar`, `!apelidar`, `!amaldicoar`.", inline=False)
        embed.add_field(name="🎰 Cassino & Jogos", value="Jogos e loteria no canal #🎰・akbet.", inline=False)
        msg = await ctx.send(embed=embed)
        await msg.pin()

    @commands.command()
    async def patchnotes(self, ctx):
        if ctx.author.id != OWNER_ID: return

        embed = disnake.Embed(
            title="🌿 ATUALIZAÇÃO DA SELVA — Rebalanceamento Econômico",
            description="A economia foi reformulada. Chegar ao topo agora exige mais do que só trabalhar — **os jogos fazem parte da progressão**.",
            color=disnake.Color.dark_green()
        )

        embed.add_field(
            name="💰 Salários reduzidos",
            value="Os ganhos do `!trabalhar` foram diminuídos em todos os cargos, com cortes maiores nos ranks avançados.",
            inline=False
        )

        embed.add_field(
            name="🛒 Cargos mais caros",
            value=(
                "🐒 Macaquinho: **1.200 C** | 🐒 Babuíno: **5.500 C**\n"
                "🦧 Chimpanzé: **14.000 C** | 🦧 Orangutango: **35.000 C**\n"
                "🦍 Gorila: **85.000 C** | 🗿 Ancestral: **210.000 C**\n"
                "👑 Rei Símio: **600.000 C**"
            ),
            inline=False
        )

        embed.add_field(
            name="🥷 Roubo mais arriscado",
            value="Chance de sucesso menor, multa por falha maior. Vale a pena — mas com cuidado.",
            inline=False
        )

        embed.add_field(
            name="💣 Campo Minado renovado",
            value=(
                "O `!minas` ganhou uma grade **4×4 interativa**! Clique nas casas para revelar e use o botão "
                "**💰 Sacar** a qualquer momento para garantir seus ganhos.\n"
                "Quanto mais bombas e mais casas revelar sem explodir, maior o multiplicador."
            ),
            inline=False
        )

        embed.add_field(
            name="💡 Como progredir agora",
            value="O trabalho cobre só parte da jornada. Use os jogos no `#🎰・akbet`, invista no banco e arrisque roubos para avançar mais rápido. Use `!salarios` para ver a tabela completa.",
            inline=False
        )

        embed.set_footer(text="👑 Rei Símio agora é uma conquista de verdade. Boa sorte!")

        await ctx.send(content="🚨 **ATUALIZAÇÃO DA SELVA** 🚨", embed=embed)
        try:
            await ctx.message.delete()
        except:
            pass

def setup(bot):
    bot.add_cog(Admin(bot))