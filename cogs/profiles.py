import disnake
from disnake.ext import commands
import database as db
import time

class Profiles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, 'tracker_emblemas'): bot.tracker_emblemas = {}

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, use este comando no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["emblemas"])
    async def conquistas(self, ctx):
        embed = disnake.Embed(title="🏆 Guia de Conquistas", color=disnake.Color.gold())
        embed.add_field(name="🥇 Rank", value="O Alfa da Selva (Top 1) | Vice-Líder (Top 2) | Bronze de Ouro (Top 3)", inline=False)
        embed.add_field(name="💰 Status", value="Magnata (20k C) | Rei da Selva (Cargo Gorila) | Falência Técnica (<100 C) | Passa fome (0 C)", inline=False)
        embed.add_field(name="🏃 Ação", value="Proletário Padrão (Trabalhou 5x no dia) | Mestre das Sombras (Roubou 5x no dia) | Freguês (Preso 3x seguidas) | Invasor (Tem Pé de Cabra)", inline=False)
        embed.add_field(name="🤫 Secretas", value="Existem 11 conquistas ocultas escondidas nos jogos e ações. Tente a sorte!", inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=["top", "ricos", "placar"])
    async def rank(self, ctx):
        all_data = db.sheet.get_all_records()
        if not all_data: return await ctx.send("❌ Sem dados suficientes.")
        sorted_users = sorted(all_data, key=lambda x: int(x.get('saldo', 0)), reverse=True)
        embed = disnake.Embed(title="🏆 Ranking de Conguitos", color=disnake.Color.gold())
        lista_rank = ""
        for i, user in enumerate(sorted_users[:10]):
            nome = user.get('nome', 'Desconhecido')
            saldo = user.get('saldo', 0)
            if i == 0: linha = f"🥇 **{nome}** — `{saldo} C`"
            elif i == 1: linha = f"🥈 **{nome}** — `{saldo} C`"
            elif i == 2: linha = f"🥉 **{nome}** — `{saldo} C`"
            else: linha = f"**{i+1}.** {nome} — `{saldo} C`"
            lista_rank += linha + "\n"
        embed.add_field(name="Top 10 Jogadores", value=lista_rank, inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=["p", "status"])
    async def perfil(self, ctx, membro: disnake.Member = None):
        membro = membro or ctx.author
        user_id = str(membro.id)
        user = db.get_user_data(user_id)
        if not user: return await ctx.send(f"❌ {membro.mention} não tem conta!")

        saldo = int(user['data'][2])
        cargo = user['data'][3]
        inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
        inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
        
        if not inv_list: inv_formatado = "Nenhum item"
        else:
            contagem = {}
            for item in inv_list: contagem[item] = contagem.get(item, 0) + 1
            itens_agrupados = [f"`{qtd}x {item}`" if qtd > 1 else f"`{item}`" for item, qtd in contagem.items()]
            inv_formatado = " | ".join(itens_agrupados)

        emblemas = []
        agora = time.time()
        if saldo >= 20000: emblemas.append("💎 **Magnata**")
        if cargo == "Gorila": emblemas.append("👑 **Rei da Selva**")
        if "Pé de Cabra" in inv_list: emblemas.append("🕵️ **Invasor**")
        if saldo < 100: emblemas.append("📉 **Falência Técnica**")
        if saldo == 0: emblemas.append("🦴 **Passa fome**")

        all_data = db.sheet.get_all_records()
        if all_data:
            sorted_users = sorted(all_data, key=lambda x: int(x.get('saldo', 0)), reverse=True)
            for i, u in enumerate(sorted_users):
                if str(u.get('id', u.get('id_usuario', u.get('Id', '')))) == user_id:
                    if i == 0: emblemas.append("🥇 **O Alfa da Selva**")
                    elif i == 1: emblemas.append("🥈 **Vice-Líder**")
                    elif i == 2: emblemas.append("🥉 **Bronze de Ouro**")
                    break

        if hasattr(self.bot, 'tracker_emblemas'):
            tr = self.bot.tracker_emblemas
            if len([t for t in tr.get('trabalhos', {}).get(user_id, []) if agora - t < 86400]) >= 5: emblemas.append("🐒 **Proletário Padrão**")
            if len([t for t in tr.get('roubos_sucesso', {}).get(user_id, []) if agora - t < 86400]) >= 5: emblemas.append("🥷 **Mestre das Sombras**")
            if tr.get('roubos_falha', {}).get(user_id, 0) >= 3: emblemas.append("⛓️ **Freguês**")
            if user_id in tr.get('esquadrao_suicida', set()): emblemas.append("💣 **Esquadrão Suicida**")
            if user_id in tr.get('palhaco', set()): emblemas.append("🤡 **Palhaço**")
            if user_id in tr.get('filho_da_sorte', set()): emblemas.append("🍀 **Sortudo**")
            if user_id in tr.get('escorregou_banana', set()): emblemas.append("🍌 **Desastrado**")
            if user_id in tr.get('pix_irritante', set()): emblemas.append("💸 **Pix Irritante**")
            if user_id in tr.get('casca_grossa', set()): emblemas.append("🐢 **Casca Grossa**")
            if user_id in tr.get('briga_de_bar', set()): emblemas.append("🥊 **Briguento**")
            if user_id in tr.get('ima_desgraca', set()): emblemas.append("🧲 **Imã de Desgraça**")
            if user_id in tr.get('veterano_coco', set()): emblemas.append("🥥 **Veterano**")
            if user_id in tr.get('queda_livre', set()): emblemas.append("📉 **Queda Livre**")
            if user_id in tr.get('astronauta_cipo', set()): emblemas.append("🚀 **Astronauta**")

        embed = disnake.Embed(title=f"🐒 Perfil AKTrovão", color=disnake.Color.gold())
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.add_field(name="💰 Saldo", value=f"{saldo} C", inline=True)
        embed.add_field(name="💼 Cargo", value=cargo, inline=True)
        embed.add_field(name="🎒 Inventário", value=inv_formatado, inline=False)
        embed.add_field(name="🏆 Conquistas", value=" | ".join(emblemas) if emblemas else "Nenhuma", inline=False)
        
        rec = getattr(self.bot, 'recompensas', {}).get(user_id, 0)
        if rec > 0: embed.add_field(name="🚨 PROCURADO", value=f"`{rec} C` pela sua cabeça!", inline=False)

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Profiles(bot))