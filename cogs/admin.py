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
        """Envia o anúncio de atualização do bot para a v4.1."""
        embed = disnake.Embed(
            title="📢 ATUALIZAÇÃO DA SELVA: Memória Eterna e Enigmas! 🐒💾 (V4.1)",
            description="O Gerente Conguito instalou novos servidores! Suas glórias agora são imortais. Confira os detalhes:",
            color=disnake.Color.blue()
        )

        embed.add_field(
            name="💾 1. CONQUISTAS PERSISTENTES", 
            value="Chega de perder medalhas! Todas as suas conquistas secretas e de ação agora são **salvas permanentemente na planilha**. Mesmo que o bot reinicie, seu legado continua no seu `!perfil`.", 
            inline=False
        )

        embed.add_field(
            name="🌑 2. MURAL DE ENIGMAS", 
            value="O comando `!conquistas` foi reformulado. As medalhas comuns continuam claras, mas os segredos foram selados com **charadas enigmáticas**. Você consegue decifrar como ganhar cada uma?", 
            inline=False
        )

        embed.add_field(
            name="🦍 3. REFORMA TRIBUTÁRIA", 
            value="O **Imposto do Gorila** ficou mais cruel! Agora, ao taxar alguém, o efeito dura **24 horas seguidas**. O alvo verá quanto tempo de 'escravidão' ainda resta toda vez que tentar trabalhar.", 
            inline=False
        )

        embed.add_field(
            name="📉 4. ECONOMIA ESTÁVEL", 
            value="Os preços da `!loja` foram reduzidos para facilitar o caos e a diversão. Além disso, corrigimos o bug que permitia criar mesas duplicadas de Blackjack.", 
            inline=False
        )

        embed.set_footer(text="A selva nunca esquece. Digite !ajuda para ver as novidades! 🍌")
        
        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await ctx.send(content="🚨 **BEEP BOOP! NOVA ATUALIZAÇÃO DISPONÍVEL!** 🚨\n", embed=embed)
        await ctx.message.delete()

def setup(bot):
    bot.add_cog(Admin(bot))