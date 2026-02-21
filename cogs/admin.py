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
            title="📢 ATUALIZAÇÃO DA SELVA (V4.1): A Era do Cassino! 🎰🐒",
            description="O Gerente Conguito reformou o cassino, atualizou os servidores e trouxe novidades quentes! Confira os detalhes:",
            color=disnake.Color.blue()
        )

        embed.add_field(
            name="💾 1. CONQUISTAS PERSISTENTES & ENIGMAS", 
            value="Suas medalhas agora são **salvas permanentemente na planilha** (não somem mais ao reiniciar). Além disso, o comando `!conquistas` virou um **Mural de Enigmas** para você decifrar os segredos da selva!", 
            inline=False
        )

        embed.add_field(
            name="🎰 2. NOVA ROLETA MULTIPLAYER", 
            value="O novo comando `!roleta` chegou! A mesa abre por 30 segundos e todos os macacos podem usar `!apostar` ao mesmo tempo. Aposte em cores (paga 2x) ou arrisque num número em cheio para ganhar **36x** o valor! 🎯", 
            inline=False
        )

        embed.add_field(
            name="🎰 3. REFORMA NO CASSINO (SLOTS)", 
            value="A máquina de caça-níqueis (`!cassino`) foi balanceada matematicamente! Agora jogamos com **8 emojis** na roleta, deixando a máquina mais justa e aumentando suas chances de forrar com duplas e jackpots!", 
            inline=False
        )

        embed.add_field(
            name="🪙 4. ADEUS, CARA OU COROA", 
            value="Para dar espaço às novas mesas de luxo e modernizar a nossa economia, o velho e enferrujado jogo de Cara ou Coroa (`!moeda`) foi oficialmente aposentado da selva.", 
            inline=False
        )

        embed.add_field(
            name="🦍 5. ECONOMIA ESTÁVEL & IMPOSTOS", 
            value="Os preços da `!loja` foram reduzidos para facilitar o caos. Mas cuidado: o **Imposto do Gorila** ficou cruel e agora dura 24 horas seguidas travando o seu trabalho!", 
            inline=False
        )

        embed.set_footer(text="A selva nunca esquece. Digite !jogos para ver a nova lista! 🍌")
        
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