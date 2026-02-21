import disnake
from disnake.ext import commands
import database as db

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = 757752617722970243

    @commands.command()
    async def dar_conquista(self, ctx, membro: disnake.Member, slug: str):
        if ctx.author.id != self.owner_id: return await ctx.send("❌ Sem permissão!")
        u = db.get_user_data(str(membro.id))
        if not u: return await ctx.send("❌ Usuário não encontrado!")

        conquistas_atuais = str(u['data'][9]) if len(u['data']) > 9 else ""
        lista = [c.strip() for c in conquistas_atuais.split(',') if c.strip()]

        if slug in lista: return await ctx.send(f"⚠️ {membro.display_name} já possui esta conquista!")

        lista.append(slug)
        db.update_value(u['row'], 10, ", ".join(lista))
        await ctx.send(f"🏆 Conquista `{slug}` gravada na planilha para {membro.mention}!")

    @commands.command()
    async def remover_conquista(self, ctx, membro: disnake.Member, slug: str):
        if ctx.author.id != self.owner_id: return await ctx.send("❌ Sem permissão!")
        u = db.get_user_data(str(membro.id))
        if not u: return await ctx.send("❌ Usuário não encontrado!")

        conquistas_atuais = str(u['data'][9]) if len(u['data']) > 9 else ""
        lista = [c.strip() for c in conquistas_atuais.split(',') if c.strip()]

        if slug not in lista: return await ctx.send(f"❌ {membro.display_name} não possui essa conquista.")

        lista.remove(slug)
        db.update_value(u['row'], 10, ", ".join(lista))
        await ctx.send(f"🧹 Conquista `{slug}` removida de {membro.mention}!")

    @commands.command()
    async def setar(self, ctx, membro: disnake.Member, valor: int):
        if ctx.author.id != self.owner_id: return await ctx.send("❌ Sem permissão!")
        u = db.get_user_data(str(membro.id))
        if not u: return await ctx.send("❌ Usuário não encontrado!")
        db.update_value(u['row'], 3, valor)
        await ctx.send(f"✅ Saldo de {membro.mention} setado para **{valor} C**.")

    @commands.command()
    async def wipe(self, ctx):
        if ctx.author.id != self.owner_id: return await ctx.send("❌ Sem permissão!")
        await ctx.send("🧹 Resetando economia...")
        try:
            db.wipe_database() 
            await ctx.send("✅ **WIPE CONCLUÍDO!**")
        except Exception as e: await ctx.send(f"⚠️ Erro: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def postar_regras(self, ctx):
        embed = disnake.Embed(title="🍌 Regras da Selva AKTrovão", color=disnake.Color.gold())
        embed.add_field(name="⚒️ Trabalho", value="`!trabalhar` a cada 1h no #🐒・conguitos.", inline=False)
        embed.add_field(name="🏦 Banco & Pix", value="Multiplique conguitos no banco ou faça Pix.", inline=False)
        embed.add_field(name="🥷 Roubos & Caçadas", value="Use `!roubar` e `!recompensa`. Consulte mural com `!recompensas`.", inline=False)
        embed.add_field(name="😈 Sabotagem", value="Loja tem itens para fazer amigos escorregarem (`!casca`), taxar salários (`!taxar`) ou mudar nicks (`!apelidar`).", inline=False)
        embed.add_field(name="🎰 Cassino & Jogos", value="Jogos e loteria no canal #🎰・akbet.", inline=False)
        msg = await ctx.send(embed=embed)
        await msg.pin()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def patchnotes(self, ctx):
        """Envia o anúncio de atualização do bot para a v4.4."""
        embed = disnake.Embed(
            title="📢 ATUALIZAÇÃO DA SELVA (V4.4): A Escada da Evolução! 🦍👑",
            description="O sistema econômico da selva expandiu! Agora temos uma nova jornada de progressão e novas formas de atormentar seus amigos.",
            color=disnake.Color.dark_red()
        )

        embed.add_field(
            name="🪜 1. A NOVA HIERARQUIA (8 CARGOS)", 
            value="A `!loja` foi atualizada com uma nova escada social! Comece como um humilde **Lêmure** e evolua até se tornar o lendário **Rei Símio**!", 
            inline=False
        )

        embed.add_field(
            name="💼 2. SALÁRIOS E LIMITES END-GAME", 
            value="Cada novo cargo aumenta consideravelmente seu limite de apostas no Cassino e seus ganhos no `!trabalhar`. O Rei Símio tem um limite de aposta de impressionantes **1.000.000 C** e pode faturar até **70.000 C** por hora de trabalho!", 
            inline=False
        )

        embed.add_field(
            name="⚡ 3. SABOTAGENS INSTANTÂNEAS", 
            value="A **Maldição Símia** (`!amaldicoar`) e o **Impostor** (`!impostor`) agora são comandos diretos! Custam **500 C** e cobram na hora direto do seu saldo, sem precisar comprar e guardar no inventário antes. Pagou, usou!", 
            inline=False
        )

        embed.add_field(
            name="💣 4. CAMPO MINADO RECALIBRADO", 
            value="O `!minas` agora tem um risco/recompensa inteligente! Jogar com 1 bomba é super seguro e dá um lucro de formiguinha (1.1x), mas se você tiver coragem de colocar 5 bombas... o multiplicador sobe e a selva pega fogo! (Lembrando: a taxa de 15% do Cassino só morde o seu lucro).", 
            inline=False
        )

        embed.set_footer(text="A corrida para se tornar o primeiro Rei Símio começou! Boa sorte! 👑")
        
        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await ctx.send(content="🚨 **BEEP BOOP! NOVA ATUALIZAÇÃO DISPONÍVEL!** 🚨\n", embed=embed)
        
        # Tenta apagar a mensagem original de quem chamou o comando
        try:
            await ctx.message.delete()
        except disnake.Forbidden:
            pass
        
def setup(bot):
    bot.add_cog(Admin(bot))