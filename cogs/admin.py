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
        """Envia o anúncio de atualização do bot para a v4.3."""
        embed = disnake.Embed(
            title="📢 ATUALIZAÇÃO DA SELVA (V4.3): A Grande Reforma! 📉🦍",
            description="O Banco Central da Selva interveio! A inflação foi controlada e os cargos de respeito agora importam mais do que nunca.",
            color=disnake.Color.dark_red()
        )

        embed.add_field(
            name="💼 1. NOVOS SALÁRIOS (!trabalhar)", 
            value="Os ganhos foram reajustados para valorizar a hierarquia. Macaquinhos iniciantes ganham o básico para sobreviver (50 a 150 C), enquanto os Gorilas dominam o mercado ganhando até 2.500 C por hora!", 
            inline=False
        )

        embed.add_field(
            name="🚫 2. LIMITES DE APOSTA", 
            value="Chega de novatos quebrarem a banca com sorte! O seu Cargo da `!loja` agora dita o limite de quanto você pode apostar nos jogos do cassino. (Ex: Macaquinho = 500 C | Gorila = 50.000 C).", 
            inline=False
        )

        embed.add_field(
            name="🏦 3. A TAXA DA SELVA (15%)", 
            value="A casa sempre ganha! Para manter o equilíbrio da economia, o cassino agora retém **15% de imposto apenas sobre o seu LUCRO** em qualquer aposta ganha. Parte do dinheiro volta para o servidor.", 
            inline=False
        )

        embed.set_footer(text="Quer lucrar alto? Trabalhe e compre o cargo de Gorila na !loja! 📈")
        
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