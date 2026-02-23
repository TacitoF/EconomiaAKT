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
            return # Silêncio total para não-admins

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
            value="`!ligar` / `!desligar` - Trava global de manutenção\n`!postar_regras` - Envia e fixa as regras\n`!patchnotes` - Envia log da versão 4.4", 
            inline=False
        )

        embed.add_field(
            name="💰 loteria", 
            value="`!sortear_loteria` - Sorteia o pote atual da loteria e premia o vencedor", 
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def darconquista(self, ctx, membro: disnake.Member = None, slug: str = None):
        if ctx.author.id != OWNER_ID: return 
        if membro is None or slug is None:
            return await ctx.send("⚠️ Use: `!dar_conquista @membro slug_da_conquista`")

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
            print(f"❌ Erro no !dar_conquista: {e}")

    @commands.command()
    async def removerconquista(self, ctx, membro: disnake.Member = None, slug: str = None):
        if ctx.author.id != OWNER_ID: return 
        if membro is None or slug is None:
            return await ctx.send("⚠️ Use: `!remover_conquista @membro slug_da_conquista`")

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
            print(f"❌ Erro no !remover_conquista: {e}")

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
            # Convertendo saldo atual com replace para evitar erro de vírgula
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
            title="📢 ATUALIZAÇÃO DA SELVA (V4.4): A Era de Ouro! 🦍👑",
            description="A selva evoluiu! A economia mudou, os impostos caíram e o crime tem consequências sérias.",
            color=disnake.Color.dark_red()
        )
        embed.add_field(name="🪙 1. Economia de Centavos & Novos Cargos", inline=False, value=(
            "• Agora aceitamos **centavos**! Use valores quebrados (ex: `150.50`) em todos os comandos.\n"
            "• A `!loja` possui **8 cargos** de progressão (do *Lêmure* ao *Rei Símio*).\n"
            "• O `!perfil` mostra cronômetro ao vivo para trabalho e roubo."
        ))
        embed.add_field(name="🚫 2. Fim dos Impostos nos Jogos", inline=False, value=(
            "A taxa de 15% foi **REMOVIDA** dos minigames. O lucro vai **100% para o seu bolso**!"
        ))
        embed.add_field(name="🥷 3. Novo Submundo (Roubos Dinâmicos)", inline=False, value=(
            "• `!roubar` rouba entre **5% a 12%** do alvo.\n"
            "• 🚨 Roubos bem-sucedidos injetam **recompensa automática** na sua cabeça!"
        ))
        embed.add_field(name="🏆 4. Novas Conquistas", inline=False, value=(
            "Novas medalhas para os mais perigosos e ricos! Tente platinar o `!perfil`."
        ))
        embed.set_footer(text="A corrida para se tornar o Rei Símio começou! Boa sorte! 👑")
        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.send(content="🚨 **A VERSÃO 4.4 ESTÁ NO AR!** 🚨\n", embed=embed)
        try: await ctx.message.delete()
        except: pass

def setup(bot):
    bot.add_cog(Admin(bot))