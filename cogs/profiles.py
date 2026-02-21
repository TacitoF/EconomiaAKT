import disnake
from disnake.ext import commands
import database as db
import time

class Profiles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, use este comando no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["emblemas"])
    async def conquistas(self, ctx):
        """Mostra o mural de medalhas com descrições claras e enigmas ocultos."""
        embed = disnake.Embed(
            title="🏆 MURAL DE CONQUISTAS DA SELVA", 
            description="Acumule glória e decifre o desconhecido para brilhar no seu `!perfil`!",
            color=disnake.Color.gold()
        )

        embed.add_field(
            name="🥇 Prestígio e Rank", 
            value="• **O Alfa da Selva:** Alcance o Top 1 no `!rank`.\n"
                  "• **Vice-Líder:** Alcance o Top 2 no `!rank`.\n"
                  "• **Bronze de Ouro:** Alcance o Top 3 no `!rank`.\n"
                  "• **Rei da Selva:** Possua o cargo máximo (**Gorila**).", 
            inline=False
        )

        embed.add_field(
            name="💰 Fortuna e Miséria", 
            value="• **Magnata:** Acumule um saldo de **20.000 C** ou mais.\n"
                  "• **Falência Técnica:** Tenha um saldo abaixo de **100 C**.\n"
                  "• **Passa Fome:** Zere completamente sua conta (**0 C**).", 
            inline=False
        )

        embed.add_field(
            name="🏃 Atividade Diária", 
            value="• **Proletário Padrão:** Realize 5 trabalhos em um único dia.\n"
                  "• **Mestre das Sombras:** Realize 5 roubos bem-sucedidos em um único dia.\n"
                  "• **Freguês:** Seja enviado para a prisão 3 vezes consecutivas.\n"
                  "• **Invasor:** Adquira um **Pé de Cabra** na loja.", 
            inline=False
        )

        enigmas_txt = (
            "🤡 **Palhaço:** *O espelho reflete o golpe que você mesmo desferiu.*\n"
            "🐢 **Casca Grossa:** *A carapaça ignora a fúria de quem tenta te tocar.*\n"
            "💸 **Pix Irritante:** *O menor dos tributos desperta a maior das indignações.*\n"
            "🍀 **Sortudo:** *A face tripla da fortuna sorriu no momento exato.*\n"
            "🥊 **Briguento:** *Um duelo mortal onde a recompensa é apenas poeira.*\n"
            "🍌 **Desastrado:** *Em um labirinto de zeros, você encontrou a única ruína.*\n"
            "💣 **Esquadrão Suicida:** *Onde o fim era certo, sua audácia te trouxe de volta.*\n"
            "🧲 **Imã de Desgraça:** *Entre muitos alvos, o destino te marcou primeiro.*\n"
            "🥥 **Veterano:** *O último a respirar quando a semente do caos explode.*\n"
            "📉 **Queda Livre:** *O chão te abraçou antes mesmo do salto começar.*\n"
            "🚀 **Astronauta:** *Acima das nuvens, onde o risco e o lucro não têm fim.*"
        )
        
        embed.add_field(name="🤫 Segredos Ocultos (Enigmas)", value=enigmas_txt, inline=False)
        embed.set_footer(text="Apenas os astutos dominarão a selva. 🐒")
        await ctx.send(embed=embed)

    @commands.command(aliases=["p", "status"])
    async def perfil(self, ctx, membro: disnake.Member = None):
        membro = membro or ctx.author
        user_id = str(membro.id)
        user = db.get_user_data(user_id)
        if not user: return await ctx.send(f"❌ {membro.mention} não tem conta!")

        saldo = int(user['data'][2])
        cargo = user['data'][3]
        
        # Correção do Inventário: Filtra o "Nenhum" e strings vazias
        inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
        inv_list = [i.strip() for i in inv_str.split(',') if i.strip() and i.strip().lower() != 'nenhum']
        
        if not inv_list: 
            inv_formatado = "Nenhum item"
        else:
            contagem = {}
            for item in inv_list: contagem[item] = contagem.get(item, 0) + 1
            itens_agrupados = [f"`{qtd}x {item}`" if qtd > 1 else f"`{item}`" for item, qtd in contagem.items()]
            inv_formatado = " | ".join(itens_agrupados)

        # LÓGICA DE CONQUISTAS PERSISTENTES (Coluna J / Índice 9)
        conquistas_db = str(user['data'][9]) if len(user['data']) > 9 else ""
        lista_conquistas_salvas = [c.strip() for c in conquistas_db.split(',') if c.strip()]

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
                if str(u.get('id_usuario', '')) == user_id:
                    if i == 0: emblemas.append("🥇 **O Alfa da Selva**")
                    elif i == 1: emblemas.append("🥈 **Vice-Líder**")
                    elif i == 2: emblemas.append("🥉 **Bronze de Ouro**")
                    break

        mapa_emblemas = {
            "palhaco": "🤡 **Palhaço**", "filho_da_sorte": "🍀 **Sortudo**",
            "escorregou_banana": "🍌 **Desastrado**", "pix_irritante": "💸 **Pix Irritante**",
            "casca_grossa": "🐢 **Casca Grossa**", "briga_de_bar": "🥊 **Briguento**",
            "ima_desgraca": "🧲 **Imã de Desgraça**", "veterano_coco": "🥥 **Veterano**",
            "queda_livre": "📉 **Queda Livre**", "astronauta_cipo": "🚀 **Astronauta**",
            "esquadrao_suicida": "💣 **Esquadrão Suicida**"
        }

        for slug in lista_conquistas_salvas:
            if slug in mapa_emblemas: emblemas.append(mapa_emblemas[slug])

        if hasattr(self.bot, 'tracker_emblemas'):
            tr = self.bot.tracker_emblemas
            if len([t for t in tr.get('trabalhos', {}).get(user_id, []) if agora - t < 86400]) >= 5: emblemas.append("🐒 **Proletário Padrão**")
            if len([t for t in tr.get('roubos_sucesso', {}).get(user_id, []) if agora - t < 86400]) >= 5: emblemas.append("🥷 **Mestre das Sombras**")
            if tr.get('roubos_falha', {}).get(user_id, 0) >= 3: emblemas.append("⛓️ **Freguês**")

        embed = disnake.Embed(title=f"🐒 Perfil AKTrovão", color=disnake.Color.gold())
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.add_field(name="💰 Saldo", value=f"{saldo} C", inline=True)
        embed.add_field(name="💼 Cargo", value=cargo, inline=True)
        embed.add_field(name="🎒 Inventário", value=inv_formatado, inline=False)
        embed.add_field(name="🏆 Conquistas", value=" | ".join(emblemas) if emblemas else "Nenhuma", inline=False)
        
        rec = getattr(self.bot, 'recompensas', {}).get(user_id, 0)
        if rec > 0: embed.add_field(name="🚨 PROCURADO", value=f"`{rec} C` pela sua cabeça!", inline=False)

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

def setup(bot):
    bot.add_cog(Profiles(bot))