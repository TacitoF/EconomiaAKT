import disnake
from disnake.ext import commands
import database as db
import time

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = 757752617722970243

    @commands.command()
    async def setar(self, ctx, membro: disnake.Member, valor: int):
        if ctx.author.id != self.owner_id: return await ctx.send("❌ Sem permissão!")
        u = db.get_user_data(str(membro.id))
        if not u: return await ctx.send("❌ Usuário não encontrado!")
        db.update_value(u['row'], 3, valor)
        await ctx.send(f"✅ Saldo de {membro.mention} setado para **{valor} C**.")

    @commands.command()
    async def dar_conquista(self, ctx, membro: disnake.Member, slug: str):
        """
        Adiciona manualmente uma conquista ao rastreador do bot.
        Slugs: palhaco, filho_da_sorte, escorregou_banana, pix_irritante, 
               casca_grossa, briga_de_bar, ima_desgraca, veterano_coco, 
               queda_livre, astronauta_cipo, esquadrao_suicida
        """
        if ctx.author.id != self.owner_id: 
            return await ctx.send("❌ Sem permissão!")

        if not hasattr(self.bot, 'tracker_emblemas'):
            return await ctx.send("❌ O sistema de rastreio de conquistas não está carregado.")

        tr = self.bot.tracker_emblemas
        user_id = str(membro.id)

        # Trata conquistas baseadas em SET (maioria das secretas/ações)
        if slug in tr and isinstance(tr[slug], set):
            tr[slug].add(user_id)
            await ctx.send(f"🏆 Conquista `{slug}` concedida a {membro.mention}!")
        
        # Trata progressos baseados em DICIONÁRIOS (trabalhos e roubos)
        elif slug in tr and isinstance(tr[slug], dict):
            if user_id not in tr[slug]: tr[slug][user_id] = []
            # Adiciona 5 registros para garantir o desbloqueio imediato no perfil
            agora = time.time()
            for _ in range(5):
                tr[slug][user_id].append(agora)
            await ctx.send(f"📈 Progresso de `{slug}` finalizado para {membro.mention}!")
        
        else:
            await ctx.send(f"❌ Slug `{slug}` inválido! Verifique a lista de nomes.")

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
        embed = disnake.Embed(title="📢 ATUALIZAÇÃO DA SELVA: A Era da Sabotagem! 😈🍌 (V4.0)", color=disnake.Color.brand_red())
        embed.add_field(name="😈 1. SABOTAGEM", value="🍌 **Casca:** `!casca @user` (Alvo falha trabalho/roubo)\n🦍 **Imposto:** `!taxar @user` (Rouba 25% dos trabalhos por 24h)\n🪄 **Nick:** `!apelidar @user <nick>` (Muda nick por 30min)", inline=False)
        embed.add_field(name="🛡️ 2. SEGURO", value="Compre Seguro na loja. Se for roubado, banco devolve 60%!", inline=False)
        embed.add_field(name="📜 3. CAÇADAS", value="Recompensas (`!recompensa`) agora acumulam valores! Veja em `!recompensas`.", inline=False)
        embed.add_field(name="🎒 4. INVENTÁRIO INFINITO", value="Acumule múltiplos itens repetidos (ex: 3x Escudo)!", inline=False)
        embed.set_footer(text="Digite !ajuda para ver tudo.")
        await ctx.send(content="🚨 **ATUALIZAÇÃO DE MERCADO NEGRO E SABOTAGEM LIBERADA!** 🚨\n", embed=embed)
        await ctx.message.delete()

def setup(bot):
    bot.add_cog(Admin(bot))