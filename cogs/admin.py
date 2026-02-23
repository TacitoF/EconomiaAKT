import disnake
from disnake.ext import commands
import database as db

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = 757752617722970243

    @commands.command()
    async def dar_conquista(self, ctx, membro: disnake.Member = None, slug: str = None):
        if ctx.author.id != self.owner_id: return await ctx.send("❌ Sem permissão!")
        if membro is None or slug is None:
            return await ctx.send("⚠️ Use: `!dar_conquista @membro slug_da_conquista`")

        u = db.get_user_data(str(membro.id))
        if not u: return await ctx.send("❌ Usuário não encontrado!")

        conquistas_atuais = str(u['data'][9]) if len(u['data']) > 9 else ""
        lista = [c.strip() for c in conquistas_atuais.split(',') if c.strip()]

        if slug in lista: return await ctx.send(f"⚠️ {membro.display_name} já possui esta conquista!")

        lista.append(slug)
        db.update_value(u['row'], 10, ", ".join(lista))
        await ctx.send(f"🏆 Conquista `{slug}` gravada para {membro.mention}!")

    @commands.command()
    async def remover_conquista(self, ctx, membro: disnake.Member = None, slug: str = None):
        if ctx.author.id != self.owner_id: return await ctx.send("❌ Sem permissão!")
        if membro is None or slug is None:
            return await ctx.send("⚠️ Use: `!remover_conquista @membro slug_da_conquista`")

        u = db.get_user_data(str(membro.id))
        if not u: return await ctx.send("❌ Usuário não encontrado!")

        conquistas_atuais = str(u['data'][9]) if len(u['data']) > 9 else ""
        lista = [c.strip() for c in conquistas_atuais.split(',') if c.strip()]

        if slug not in lista: return await ctx.send(f"❌ {membro.display_name} não possui essa conquista.")

        lista.remove(slug)
        db.update_value(u['row'], 10, ", ".join(lista))
        await ctx.send(f"🧹 Conquista `{slug}` removida de {membro.mention}!")

    @commands.command()
    async def setar(self, ctx, membro: disnake.Member = None, valor: float = None):
        if ctx.author.id != self.owner_id: return await ctx.send("❌ Sem permissão!")
        if membro is None or valor is None:
            return await ctx.send("⚠️ Use: `!setar @membro <valor>`")

        u = db.get_user_data(str(membro.id))
        if not u: return await ctx.send("❌ Usuário não encontrado!")
        
        valor = round(valor, 2)
        db.update_value(u['row'], 3, valor)
        await ctx.send(f"✅ Saldo de {membro.mention} cravado em **{valor:.2f} C**.")

    @commands.command(aliases=["add", "dar"])
    async def adicionar(self, ctx, membro: disnake.Member = None, valor: float = None):
        """Soma um valor ao saldo atual do usuário (Apenas Dono)"""
        if ctx.author.id != self.owner_id: return await ctx.send("❌ Sem permissão!")
        if membro is None or valor is None:
            return await ctx.send("⚠️ Use: `!adicionar @membro <valor>`")

        u = db.get_user_data(str(membro.id))
        if not u: return await ctx.send("❌ Usuário não encontrado!")
        
        saldo_atual = float(u['data'][2])
        novo_saldo = round(saldo_atual + valor, 2)
        
        db.update_value(u['row'], 3, novo_saldo)
        await ctx.send(f"📈 Foram adicionados **{valor:.2f} C** ao bolso de {membro.mention}. (Novo Saldo: `{novo_saldo:.2f} C`)")

    @commands.command(aliases=["tirar", "subtrair"])
    async def remover(self, ctx, membro: disnake.Member = None, valor: float = None):
        """Subtrai um valor do saldo atual do usuário (Apenas Dono)"""
        if ctx.author.id != self.owner_id: return await ctx.send("❌ Sem permissão!")
        if membro is None or valor is None:
            return await ctx.send("⚠️ Use: `!remover @membro <valor>`")

        u = db.get_user_data(str(membro.id))
        if not u: return await ctx.send("❌ Usuário não encontrado!")
        
        saldo_atual = float(u['data'][2])
        novo_saldo = round(saldo_atual - valor, 2)
        if novo_saldo < 0: novo_saldo = 0.0 # Não deixa o saldo ficar negativo
        
        db.update_value(u['row'], 3, novo_saldo)
        await ctx.send(f"📉 Foram removidos **{valor:.2f} C** do bolso de {membro.mention}. (Novo Saldo: `{novo_saldo:.2f} C`)")

    @commands.command()
    async def wipe(self, ctx):
        if ctx.author.id != self.owner_id: return await ctx.send("❌ Sem permissão!")
        await ctx.send("🧹 Resetando toda a economia da selva...")
        try:
            db.wipe_database() 
            await ctx.send("✅ **WIPE CONCLUÍDO!** Todos os macacos voltaram ao zero.")
        except Exception as e: await ctx.send(f"⚠️ Erro ao realizar wipe: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def postar_regras(self, ctx):
        embed = disnake.Embed(title="🍌 Regras da Selva AKTrovão", color=disnake.Color.gold())
        embed.add_field(name="⚒️ Trabalho", value="`!trabalhar` a cada 1h no #🐒・conguitos.", inline=False)
        embed.add_field(name="🏦 Banco & Pix", value="Multiplique conguitos no banco ou faça Pix.", inline=False)
        embed.add_field(name="🥷 Roubos & Caçadas", value="Use `!roubar` e `!recompensa`. Consulte `!perfil`.", inline=False)
        embed.add_field(name="😈 Sabotagem", value="Itens para sabotar: `!casca`, `!taxar`, `!apelidar`, `!amaldicoar`.", inline=False)
        embed.add_field(name="🎰 Cassino & Jogos", value="Jogos e loteria no canal #🎰・akbet.", inline=False)
        msg = await ctx.send(embed=embed)
        await msg.pin()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def patchnotes(self, ctx):
        """Envia o anúncio de atualização final v4.4 focado nos jogadores."""
        embed = disnake.Embed(
            title="📢 ATUALIZAÇÃO DA SELVA (V4.4): A Era de Ouro! 🦍👑",
            description="A selva evoluiu! A economia mudou, os impostos caíram e o crime agora tem consequências sérias. Confira as novidades:",
            color=disnake.Color.dark_red()
        )

        embed.add_field(
            name="🪙 1. Economia de Centavos & Novos Cargos", 
            value="• Agora aceitamos **centavos**! Use valores quebrados (ex: `150.50`) em apostas e transferências.\n• A `!loja` possui **8 novos cargos** de progressão (do *Lêmure* ao bilionário *Rei Símio*).\n• O seu `!perfil` agora mostra o tempo exato (com cronômetro ao vivo) para você poder trabalhar e roubar de novo.", 
            inline=False
        )

        embed.add_field(
            name="🚫 2. O FIM DOS IMPOSTOS NOS JOGOS", 
            value="O leão da receita foi domado! A taxa de 15% foi **REMOVIDA** dos minigames. O lucro que você tira no `!minas`, `!21`, `!roleta`, `!crash`, `!cassino`, `!bicho` e nos `PvP` agora vai **100% para o seu bolso**!", 
            inline=False
        )

        embed.add_field(
            name="🥷 3. O Novo Submundo (Roubos Dinâmicos)", 
            value="• O `!roubar` está mais justo: agora rouba entre **5% a 12%** do alvo (mas você precisa de pelo menos 50 C na conta para tentar).\n• 🚨 **A Polícia está de olho:** Roubos bem-sucedidos agora injetam uma **recompensa automática** na sua cabeça no mural de procurados!", 
            inline=False
        )

        embed.add_field(
            name="🏆 4. Novas Conquistas", 
            value="Novas medalhas para os mais perigosos e ricos da selva! Tente platinar seu `!perfil` descobrindo como pegar as novas: *Inimigo Público*, *Rei do Crime* e *Burguês Safado*.", 
            inline=False
        )

        embed.set_footer(text="A corrida para se tornar o Rei Símio começou! Boa sorte! 👑")
        
        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await ctx.send(content="🚨 **BEEP BOOP! A VERSÃO 4.4 ESTÁ NO AR!** 🚨\n", embed=embed)
        try: await ctx.message.delete()
        except: pass
        
def setup(bot):
    bot.add_cog(Admin(bot))