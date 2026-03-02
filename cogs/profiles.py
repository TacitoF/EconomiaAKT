import disnake
from disnake.ext import commands
import database as db
import time

ESCUDO_CARGAS = 3

def formatar_moeda(valor: float) -> str:
    """Formata para o padrão brasileiro: 1.000,00"""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

class Profiles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, use este comando no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    # emoji e cor do embed pra cada cargo
    _CARGO_INFO = {
        "Lêmure":      ("🐭", 0x7b7b7b),
        "Macaquinho":  ("🐒", 0x8B5E3C),
        "Babuíno":     ("🦍", 0x5B7FA6),
        "Chimpanzé":   ("🐵", 0x4CAF50),
        "Orangutango": ("🦧", 0xFF8C00),
        "Gorila":      ("🦾", 0x9C27B0),
        "Ancestral":   ("🌿", 0x00BCD4),
        "Rei Símio":   ("👑", 0xFFD700),
    }

    # mapeamento de slug -> nome exibido no perfil
    _MAPA_CONQUISTAS = {
        "palhaco":           "🤡 Palhaço",
        "filho_da_sorte":    "🍀 Sortudo",
        "escorregou_banana": "🍌 Desastrado",
        "pix_irritante":     "💸 Pix Irritante",
        "casca_grossa":      "🐢 Casca Grossa",
        "briga_de_bar":      "🥊 Briguento",
        "ima_desgraca":      "🧲 Imã de Desgraça",
        "veterano_coco":     "🥥 Veterano",
        "queda_livre":       "📉 Queda Livre",
        "astronauta_cipo":   "🚀 Astronauta",
        "esquadrao_suicida": "💣 Esquadrão Suicida",
        "covarde":           "🏳️ Covarde",
        "desarmador":        "🎖️ Desarmador",
        "quase_la":          "😭 Quase Lá",
        "invicto_coco":      "🔥 Mestre dos Cocos",
        "mestre_sombras":    "🥷 Mestre das Sombras",
        "proletario":        "⚒️ Proletário Padrão",
        "detetive":          "🕵️ Detetive",
    }

    @commands.command(aliases=["emblemas"])
    @commands.cooldown(1, 5, commands.BucketType.user)
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
            "• **Burguês Safado:** Acumule a fortuna de **500.000 MC**.\n"
            "• **Magnata:** Acumule um saldo de **100.000 MC** ou mais.\n"
            "• **Falência Técnica:** Tenha um saldo abaixo de **100 MC**.\n"
            "• **Passa Fome:** Zere completamente sua conta (**0 MC**)."
        ))
        embed.add_field(name="🏃 Atividade Diária", inline=False, value=(
            "• **Proletário Padrão:** Realize 10 trabalhos em um único dia.\n"
            "• **Mestre das Sombras:** Realize 5 roubos bem-sucedidos em um único dia.\n"
            "• **Invasor:** Tenha um **Pé de Cabra** no inventário."
        ))
        embed.add_field(name="🚨 Submundo", inline=False, value=(
            "• **Inimigo Público:** Recompensa de **5.000 MC** ou mais pela cabeça.\n"
            "• **Rei do Crime:** Seja o macaco mais procurado (Top 1) da selva."
        ))
        embed.add_field(name="🤫 Segredos Ocultos (Parte 1)", inline=False, value=(
            "🤡 **Palhaço:** *O espelho reflete o golpe que você mesmo desferiu.*\n"
            "🐢 **Casca Grossa:** *A carapaça ignorou a fúria de quem tentou te tocar.*\n"
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
            "🕵️ **Detetive:** *Você farejou a mentira antes que ela te engolisse.*\n"
        ))
        embed.set_footer(text="Apenas os astutos dominarão a selva. 🐒")
        await ctx.send(embed=embed)

    @conquistas.error
    async def conquistas_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Tente novamente em {error.retry_after:.1f}s.", delete_after=3)

    @commands.command(aliases=["p", "status"])
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def perfil(self, ctx, membro: disnake.Member = None):
        membro  = membro or ctx.author
        user_id = str(membro.id)
        try:
            user = db.get_user_data(user_id)
            if not user:
                return await ctx.send(f"❌ {membro.mention} não tem conta!")

            saldo = db.parse_float(user["data"][2])
            cargo = user["data"][3] if len(user["data"]) > 3 and user["data"][3] else "Lêmure"
            agora = time.time()

            ultimo_work   = db.parse_float(user["data"][4] if len(user["data"]) > 4 else None)
            ultimo_roubo  = db.parse_float(user["data"][6] if len(user["data"]) > 6 else None)
            ultimo_invest = db.parse_float(user["data"][7] if len(user["data"]) > 7 else None)

            def _cd(ultimo, cooldown):
                return "✅ Disponível" if agora - ultimo >= cooldown else f"<t:{int(ultimo + cooldown)}:R>"

            st_work   = _cd(ultimo_work,   3600)
            st_roubo  = _cd(ultimo_roubo,  7200)
            st_invest = _cd(ultimo_invest, 86400)

            inv_str  = str(user["data"][5]) if len(user["data"]) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(",") if i.strip() and i.strip().lower() != "nenhum"]
            cargas_escudo = self.bot.escudos_ativos.get(user_id, 0) if hasattr(self.bot, "escudos_ativos") else 0

            if inv_list:
                contagem = {}
                for item in inv_list:
                    contagem[item] = contagem.get(item, 0) + 1
                itens = [f"`{q}× {i}`" if q > 1 else f"`{i}`" for i, q in contagem.items()]
            else:
                itens = []
            if cargas_escudo > 0:
                itens.append(f"`🛡️ Escudo ({cargas_escudo}/{ESCUDO_CARGAS})`")
            inv_val = "  ".join(itens) if itens else "*Mochila vazia*"

            emblemas = []
            if saldo >= 500000:   emblemas.append("🤑 Burguês Safado")
            elif saldo >= 100000: emblemas.append("💎 Magnata")
            if 0 < saldo < 100:   emblemas.append("📉 Falência Técnica")
            if saldo <= 0:        emblemas.append("🦴 Passa Fome")
            if cargo == "Rei Símio":       emblemas.append("👑 Rei da Selva")
            if "Pé de Cabra" in inv_list:  emblemas.append("🕵️ Invasor")

            # busca posição no rank (pode ser lento, mas só acontece no !perfil)
            try:
                all_rows = db.sheet.get_all_values()
                if len(all_rows) > 1:
                    dados_sorted = sorted(
                        all_rows[1:],
                        key=lambda r: db.parse_float(r[2]) if len(r) > 2 else 0,
                        reverse=True,
                    )
                    for i, row in enumerate(dados_sorted):
                        if str(row[0]) == user_id:
                            if i == 0:   emblemas.append("🥇 Alfa da Selva")
                            elif i == 1: emblemas.append("🥈 Vice-Líder")
                            elif i == 2: emblemas.append("🥉 Bronze de Ouro")
                            break
            except Exception as e:
                print(f"⚠️ Rank no !perfil: {e}")

            conquistas_db = str(user["data"][9]) if len(user["data"]) > 9 else ""
            for slug in [c.strip() for c in conquistas_db.split(",") if c.strip()]:
                if slug in self._MAPA_CONQUISTAS:
                    emblemas.append(self._MAPA_CONQUISTAS[slug])

            rec = getattr(self.bot, "recompensas", {}).get(user_id, 0.0)
            recompensas_gerais = getattr(self.bot, "recompensas", {})
            valores_rec = [v for v in recompensas_gerais.values() if v > 0]
            if rec >= 5000: emblemas.append("🚨 Inimigo Público")
            if valores_rec and max(recompensas_gerais, key=recompensas_gerais.get) == user_id:
                emblemas.append("💀 Rei do Crime")

            cargo_icon, embed_color = self._CARGO_INFO.get(cargo, ("🐒", 0xFFD700))
            saldo_fmt = f"{formatar_moeda(saldo)} MC"

            sep = "─" * 34
            desc = (
                f"### {cargo_icon}  {membro.display_name}\n"
                f"{sep}\n"
                f"💼  **Cargo:** `{cargo}`\n"
                f"💰  **Saldo:** `{saldo_fmt}`"
            )
            if rec > 0:
                rec_fmt = f"{formatar_moeda(rec)} MC"
                desc += f"\n🚨  **Recompensa:** `{rec_fmt}`"

            embed = disnake.Embed(description=desc, color=embed_color)
            embed.set_author(
                name=f"🌿 Perfil · {membro.display_name}",
                icon_url=membro.display_avatar.url,
            )
            embed.set_thumbnail(url=membro.display_avatar.url)

            embed.add_field(name="🔨  Trabalho",     value=st_work,   inline=True)
            embed.add_field(name="🔫  Roubo",        value=st_roubo,  inline=True)
            embed.add_field(name="🏛️  Investimento", value=st_invest, inline=True)
            embed.add_field(name="🎒  Inventário",   value=inv_val,   inline=False)

            if emblemas:
                linhas = []
                for i in range(0, len(emblemas), 3):
                    linhas.append("  ·  ".join(emblemas[i:i+3]))
                emblemas_val = "\n".join(linhas)
            else:
                emblemas_val = "*Nenhuma conquista ainda — vá à luta!*"

            embed.add_field(
                name=f"🏆  Conquistas  ({len(emblemas)})",
                value=emblemas_val,
                inline=False,
            )
            embed.set_footer(text="🐒 Selva dos Macacoins  ·  !conquistas para ver todas")
            await ctx.send(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !perfil: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, erro ao carregar perfil. Tente novamente!")

    @perfil.error
    async def perfil_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Não faça spam, macaco! Tente novamente em {error.retry_after:.1f}s.", delete_after=5)

    @commands.command(aliases=["top", "ricos", "placar"])
    @commands.cooldown(1, 10, commands.BucketType.guild)  # cooldown por servidor pra não travar o sheets
    async def rank(self, ctx):
        try:
            try:
                all_rows = db.sheet.get_all_values()
            except Exception as e:
                print(f"❌ Erro ao acessar planilha no !rank: {e}")
                return await ctx.send("⚠️ **O banco está ocupado!** Tente novamente em 1 minuto.")

            if len(all_rows) < 2:
                return await ctx.send("❌ Sem dados suficientes.")

            cabecalho = all_rows[0]
            dados     = all_rows[1:]

            idx_id    = 0
            idx_nome  = next((i for i, c in enumerate(cabecalho) if c.lower() == "nome"),  1)
            idx_saldo = next((i for i, c in enumerate(cabecalho) if c.lower() == "saldo"), 2)
            idx_cargo = next((i for i, c in enumerate(cabecalho) if c.lower() == "cargo"), 3)

            dados_validos = [r for r in dados if len(r) > idx_saldo]
            sorted_all    = sorted(dados_validos, key=lambda r: db.parse_float(r[idx_saldo]), reverse=True)
            top           = sorted_all[:10]

            CARGO_EMOJI = {
                "Lêmure": "🐭", "Macaquinho": "🐒", "Babuíno": "🐵",
                "Chimpanzé": "🌴", "Orangutango": "🦧", "Gorila": "🦍 ",
                "Ancestral": "🗿", "Rei Símio": "👑",
            }

            def _fmt(s):
                if s >= 1_000_000: return f"{formatar_moeda(s/1_000_000)}M MC"
                if s >= 1_000:     return f"{formatar_moeda(s/1_000)}K MC"
                return f"{formatar_moeda(s)} MC"

            autor_id  = str(ctx.author.id)
            autor_pos = None
            autor_row = None
            for i, row in enumerate(sorted_all):
                if str(row[idx_id]) == autor_id:
                    autor_pos = i + 1
                    autor_row = row
                    break

            embed = disnake.Embed(
                title       = "🏆  RANKING DA SELVA",
                description = "Os macacos mais ricos de toda a selva.",
                color       = 0xFFD700,
            )

            PODIO = ["🥇  **1º Lugar**", "🥈  **2º Lugar**", "🥉  **3º Lugar**"]
            for i in range(min(3, len(top))):
                row   = top[i]
                nome  = row[idx_nome]  if len(row) > idx_nome  else "???"
                saldo = db.parse_float(row[idx_saldo])
                cargo = row[idx_cargo] if len(row) > idx_cargo else "Lêmure"
                c_em  = CARGO_EMOJI.get(cargo, "🐒")
                embed.add_field(
                    name  = PODIO[i],
                    value = f"**{nome}**\n{c_em} `{cargo}`\n💰 `{_fmt(saldo)}`",
                    inline= True,
                )

            if len(top) > 3:
                embed.add_field(name="\u200b", value="\u200b", inline=False)
                NUMS = ["4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
                linhas = []
                for i, row in enumerate(top[3:], start=3):
                    nome  = row[idx_nome]  if len(row) > idx_nome  else "???"
                    saldo = db.parse_float(row[idx_saldo])
                    cargo = row[idx_cargo] if len(row) > idx_cargo else "Lêmure"
                    c_em  = CARGO_EMOJI.get(cargo, "🐒")
                    linhas.append(f"{NUMS[i-3]}  {c_em} **{nome}** — `{_fmt(saldo)}`")
                embed.add_field(name="📊  Classificação", value="\n".join(linhas), inline=False)

            if autor_pos and autor_pos > 10 and autor_row:
                embed.add_field(
                    name  = "📍  Sua posição",
                    value = f"Você está em **#{autor_pos}** com `{_fmt(db.parse_float(autor_row[idx_saldo]))}`",
                    inline= False,
                )

            embed.set_footer(text="🌿 Use !perfil para ver seus detalhes completos")
            await ctx.send(embed=embed)
        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !rank: {e}")
            await ctx.send("⚠️ **O banco está ocupado!** Tente novamente em 1 minuto.")

    @rank.error
    async def rank_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ O painel de rank está sendo atualizado. Aguarde {error.retry_after:.1f}s.", delete_after=5)

def setup(bot):
    bot.add_cog(Profiles(bot))