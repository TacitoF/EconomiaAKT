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
        embed = disnake.Embed(
            title="🏆 MURAL DE CONQUISTAS DA SELVA",
            description="Acumule glória e decifre o desconhecido para brilhar no seu `!perfil`!",
            color=disnake.Color.gold()
        )
        embed.add_field(name="🥇 Prestígio e Rank", inline=False, value=(
            "• **O Alfa da Selva:** Alcance o Top 1 no `!rank`.\n"
            "• **Vice-Líder:** Alcance o Top 2 no `!rank`.\n"
            "• **Bronze de Ouro:** Alcance o Top 3 no `!rank`.\n"
            "• **Rei da Selva:** Possua o cargo máximo (**Rei Símio**)."
        ))
        embed.add_field(name="💰 Fortuna e Miséria", inline=False, value=(
            "• **Burguês Safado:** Acumule a fortuna de **500.000 C**.\n"
            "• **Magnata:** Acumule um saldo de **100.000 C** ou mais.\n"
            "• **Falência Técnica:** Tenha um saldo abaixo de **100 C**.\n"
            "• **Passa Fome:** Zere completamente sua conta (**0 C**)."
        ))
        embed.add_field(name="🏃 Atividade Diária", inline=False, value=(
            "• **Proletário Padrão:** Realize 5 trabalhos em um único dia.\n"
            "• **Mestre das Sombras:** Realize 5 roubos bem-sucedidos em um único dia.\n"
            "• **Freguês:** Seja enviado para a prisão 3 vezes consecutivas.\n"
            "• **Invasor:** Adquira um **Pé de Cabra** na loja."
        ))
        embed.add_field(name="🚨 Submundo", inline=False, value=(
            "• **Inimigo Público:** Recompensa de **5.000 C** ou mais pela cabeça.\n"
            "• **Rei do Crime:** Seja o macaco mais procurado (Top 1) da selva."
        ))
        
        # O campo de segredos foi dividido em dois para não estourar o limite de 1024 caracteres do Discord
        embed.add_field(name="🤫 Segredos Ocultos (Parte 1)", inline=False, value=(
            "🤡 **Palhaço:** *O espelho reflete o golpe que você mesmo desferiu.*\n"
            "🐢 **Casca Grossa:** *A carapaça ignora a fúria de quem tenta te tocar.*\n"
            "💸 **Pix Irritante:** *O menor dos tributos desperta a maior das indignações.*\n"
            "🍀 **Sortudo:** *A face tripla da fortuna sorriu no momento exato.*\n"
            "🥊 **Briguento:** *Um duelo mortal onde a recompensa é apenas poeira.*\n"
            "🍌 **Desastrado:** *Em um labirinto de zeros, você encontrou a única ruína.*\n"
            "💣 **Esquadrão Suicida:** *Onde o fim era certo, sua audácia te trouxe de volta.*"
        ))
        embed.add_field(name="🤫 Segredos Ocultos (Parte 2)", inline=False, value=(
            "🧲 **Imã de Desgraça:** *Entre muitos alvos, o destino te marcou primeiro.*\n"
            "🥥 **Veterano:** *O último a respirar quando a semente do caos explode.*\n"
            "📉 **Queda Livre:** *O chão te abraçou antes mesmo do salto começar.*\n"
            "🚀 **Astronauta:** *Acima das nuvens, onde o risco e o lucro não têm fim.*\n"
            "🏳️ **Covarde:** *A primeira luz foi suficiente para apagar sua coragem.*\n"
            "🎖️ **Desarmador:** *Você caminhou pelo inferno e saiu sem um arranhão.*\n"
            "😭 **Quase Lá:** *A vitória estava ao alcance, mas o destino tinha outros planos.*\n"
            "🔥 **Mestre dos Cocos:** *A bomba beijou sua mão três vezes e recuou com medo.*\n"
        ))
        
        embed.set_footer(text="Apenas os astutos dominarão a selva. 🐒")
        await ctx.send(embed=embed)

    @commands.command(aliases=["p", "status"])
    async def perfil(self, ctx, membro: disnake.Member = None):
        membro = membro or ctx.author
        user_id = str(membro.id)
        try:
            user = db.get_user_data(user_id)
            if not user:
                return await ctx.send(f"❌ {membro.mention} não tem conta!")

            saldo = db.parse_float(user['data'][2])
            cargo = user['data'][3] if len(user['data']) > 3 and user['data'][3] else "Lêmure"
            agora = time.time()

            ultimo_work  = db.parse_float(user['data'][4] if len(user['data']) > 4 else None)
            ultimo_roubo = db.parse_float(user['data'][6] if len(user['data']) > 6 else None)

            status_work  = "Disponível ✅" if agora - ultimo_work  >= 3600 else f"<t:{int(ultimo_work  + 3600)}:R>"
            status_roubo = "Disponível ✅" if agora - ultimo_roubo >= 7200 else f"<t:{int(ultimo_roubo + 7200)}:R>"

            inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip() and i.strip().lower() != 'nenhum']
            if not inv_list:
                inv_formatado = "Nenhum item"
            else:
                contagem = {}
                for item in inv_list: contagem[item] = contagem.get(item, 0) + 1
                inv_formatado = " | ".join([f"`{q}x {i}`" if q > 1 else f"`{i}`" for i, q in contagem.items()])

            emblemas = []
            if saldo >= 500000: emblemas.append("🤑 **Burguês Safado**")
            elif saldo >= 100000: emblemas.append("💎 **Magnata**")
            if cargo == "Rei Símio": emblemas.append("👑 **Rei da Selva**")
            if "Pé de Cabra" in inv_list: emblemas.append("🕵️ **Invasor**")
            if 0 < saldo < 100: emblemas.append("📉 **Falência Técnica**")
            if saldo <= 0: emblemas.append("🦴 **Passa fome**")

            try:
                all_rows = db.sheet.get_all_values()
                if len(all_rows) > 1:
                    dados_sorted = sorted(all_rows[1:], key=lambda r: db.parse_float(r[2]) if len(r) > 2 else 0, reverse=True)
                    for i, row in enumerate(dados_sorted):
                        if str(row[0]) == user_id:
                            if i == 0: emblemas.append("🥇 **O Alfa da Selva**")
                            elif i == 1: emblemas.append("🥈 **Vice-Líder**")
                            elif i == 2: emblemas.append("🥉 **Bronze de Ouro**")
                            break
            except:
                pass

            # Mapa de todas as conquistas incluindo as novas do minas
            mapa_conquistas = {
                "palhaco":           "🤡 **Palhaço**",
                "filho_da_sorte":    "🍀 **Sortudo**",
                "escorregou_banana": "🍌 **Desastrado**",
                "pix_irritante":     "💸 **Pix Irritante**",
                "casca_grossa":      "🐢 **Casca Grossa**",
                "briga_de_bar":      "🥊 **Briguento**",
                "ima_desgraca":      "🧲 **Imã de Desgraça**",
                "veterano_coco":     "🥥 **Veterano**",
                "queda_livre":       "📉 **Queda Livre**",
                "astronauta_cipo":   "🚀 **Astronauta**",
                "esquadrao_suicida": "💣 **Esquadrão Suicida**",
                "covarde":           "🏳️ **Covarde**",
                "desarmador":        "🎖️ **Desarmador**",
                "quase_la":          "😭 **Quase Lá**",
                "invicto_coco":      "🔥 **Mestre dos Cocos**",
            }

            conquistas_db = str(user['data'][9]) if len(user['data']) > 9 else ""
            for slug in [c.strip() for c in conquistas_db.split(',') if c.strip()]:
                if slug in mapa_conquistas:
                    emblemas.append(mapa_conquistas[slug])

            rec = getattr(self.bot, 'recompensas', {}).get(user_id, 0.0)
            if rec >= 5000: emblemas.append("🚨 **Inimigo Público**")
            recompensas_gerais = getattr(self.bot, 'recompensas', {})
            valores_rec = [v for v in recompensas_gerais.values() if v > 0]
            if valores_rec and max(recompensas_gerais, key=recompensas_gerais.get) == user_id:
                emblemas.append("👑 **Rei do Crime**")

            embed = disnake.Embed(title=f"🐒 Perfil de {membro.display_name}", color=disnake.Color.gold())
            embed.set_thumbnail(url=membro.display_avatar.url)
            embed.add_field(name="💰 Saldo",     value=f"`{saldo:.2f} C`", inline=True)
            embed.add_field(name="💼 Cargo",     value=f"`{cargo}`",       inline=True)
            embed.add_field(name="🔨 Trabalho",  value=status_work,        inline=True)
            embed.add_field(name="🔫 Roubo",     value=status_roubo,       inline=True)
            embed.add_field(name="🎒 Inventário",value=inv_formatado,       inline=False)
            embed.add_field(name="🏆 Conquistas",value=" | ".join(emblemas) if emblemas else "Nenhuma", inline=False)
            if rec > 0:
                embed.add_field(name="🚨 PROCURADO", value=f"`{rec:.2f} C` pela sua cabeça!", inline=False)
            await ctx.send(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !perfil: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, erro ao carregar perfil. Tente novamente!")

    @commands.command(aliases=["top", "ricos", "placar"])
    async def rank(self, ctx):
        try:
            all_rows = db.sheet.get_all_values()
            if len(all_rows) < 2:
                return await ctx.send("❌ Sem dados suficientes.")

            cabecalho = all_rows[0]
            dados     = all_rows[1:]

            idx_nome  = next((i for i, c in enumerate(cabecalho) if c.lower() == 'nome'),  1)
            idx_saldo = next((i for i, c in enumerate(cabecalho) if c.lower() == 'saldo'), 2)

            dados_validos = [r for r in dados if len(r) > idx_saldo]
            sorted_users  = sorted(dados_validos, key=lambda r: db.parse_float(r[idx_saldo]), reverse=True)

            embed = disnake.Embed(title="🏆 Ranking de Conguitos", color=disnake.Color.gold())
            lista_rank = ""
            for i, row in enumerate(sorted_users[:10]):
                nome  = row[idx_nome] if len(row) > idx_nome else "Desconhecido"
                saldo = db.parse_float(row[idx_saldo])
                if i == 0:   linha = f"🥇 **{nome}** — `{saldo:.2f} C`"
                elif i == 1: linha = f"🥈 **{nome}** — `{saldo:.2f} C`"
                elif i == 2: linha = f"🥉 **{nome}** — `{saldo:.2f} C`"
                else:        linha = f"**{i+1}.** {nome} — `{saldo:.2f} C`"
                lista_rank += linha + "\n"

            embed.add_field(name="Top 10 Jogadores", value=lista_rank, inline=False)
            await ctx.send(embed=embed)
        except Exception as e:
            print(f"❌ Erro no !rank: {e}")
            await ctx.send("⚠️ **O banco está ocupado!** Tente novamente em 1 minuto.")

def setup(bot):
    bot.add_cog(Profiles(bot))