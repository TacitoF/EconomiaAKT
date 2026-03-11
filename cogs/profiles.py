import disnake
from disnake.ext import commands
import database as db
import time

ESCUDO_CARGAS = 3

def formatar_moeda(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS DE COSMÉTICOS
# ══════════════════════════════════════════════════════════════════════════════

TIPO_EMOJI      = {"cor": "🎨", "moldura": "🖼️", "titulo": "🏷️"}
TIPO_LABEL      = {"cor": "Cor",  "moldura": "Moldura", "titulo": "Título"}
TIPO_LABEL_ICON = {"cor": "🎨 Cor", "moldura": "🖼️ Moldura", "titulo": "🏷️ Título"}

def _parse_slug(slug: str):
    if slug.startswith("cor:"):     return "cor",     slug[4:]
    if slug.startswith("moldura:"): return "moldura", slug[8:]
    if slug.startswith("titulo:"):  return "titulo",  slug[7:]
    return "desconhecido", slug

def _montar_inv_str(inv_list: list) -> str:
    return ", ".join(inv_list) if inv_list else "Nenhum"

def _parse_inv(user: dict) -> list:
    raw = str(user["data"][5]) if len(user["data"]) > 5 else ""
    return [i.strip() for i in raw.split(",") if i.strip() and i.strip().lower() != "nenhum"]

def _parse_cosm_str(user: dict) -> dict:
    raw = str(user["data"][12]) if len(user["data"]) > 12 else ""
    result = {}
    for parte in raw.strip().split("|"):
        parte = parte.strip()
        if ":" in parte:
            chave, _, valor = parte.partition(":")
            result[chave.strip()] = valor.strip()
    return result

def _serializar_cosm(cosm: dict) -> str:
    return "|".join(f"{k}:{v}" for k, v in cosm.items() if v)

def _build_embed_visuais(autor: disnake.Member, cosm_inv: list, cosm_atual: dict) -> disnake.Embed:
    embed = disnake.Embed(title="✨ PAINEL DE COSMÉTICOS", color=disnake.Color.purple())
    embed.set_author(name=autor.display_name, icon_url=autor.display_avatar.url)

    if cosm_inv:
        linhas = []
        for item in cosm_inv:
            slug = item.split(":", 1)[1]
            tipo_slug, valor = _parse_slug(slug)
            marca = " ✅" if cosm_atual.get(tipo_slug) == valor else ""
            linhas.append(f"{TIPO_EMOJI.get(tipo_slug, '✨')} `{slug}`{marca}")
        embed.add_field(name=f"🎒 No inventário ({len(cosm_inv)})", value="\n".join(linhas), inline=False)
    else:
        embed.add_field(name="🎒 No inventário", value="*Vazio — compre na `!loja` ou encontre nas lootboxes!*", inline=False)

    equipados_txt = []
    if cosm_atual.get("cor"):     equipados_txt.append(f"🎨 Cor: `{cosm_atual['cor']}`")
    if cosm_atual.get("moldura"): equipados_txt.append(f"🖼️ Moldura: `{cosm_atual['moldura']}`")
    if cosm_atual.get("titulo"):  equipados_txt.append(f"🏷️ Título: `{cosm_atual['titulo']}`")
    embed.add_field(
        name="✅ Equipados agora",
        value="\n".join(equipados_txt) if equipados_txt else "*Nenhum*",
        inline=False,
    )
    embed.set_footer(text="Use o menu abaixo para equipar  ·  Botões para remover o que está equipado")
    return embed


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW: PAINEL DE COSMÉTICOS
# ══════════════════════════════════════════════════════════════════════════════

class ViewVisuais(disnake.ui.View):
    def __init__(self, autor: disnake.Member, row: int, itens_normais: list, cosm_inv: list, cosm_atual: dict):
        super().__init__(timeout=120)
        self.autor         = autor
        self.row           = row
        self.itens_normais = list(itens_normais)
        self.cosm_inv      = list(cosm_inv)
        self.cosm_atual    = dict(cosm_atual)
        self._rebuild_select()

    def _rebuild_select(self):
        self.children = [c for c in self.children if not isinstance(c, disnake.ui.StringSelect)]
        if self.cosm_inv:
            options = []
            for item in self.cosm_inv:
                slug = item.split(":", 1)[1]
                tipo_slug, valor = _parse_slug(slug)
                equipado = self.cosm_atual.get(tipo_slug) == valor
                options.append(disnake.SelectOption(
                    label       = f"{TIPO_LABEL.get(tipo_slug, tipo_slug.capitalize())}: {valor}"[:100],
                    description = "✅ Equipado atualmente" if equipado else "Clique para equipar",
                    value       = slug,
                    emoji       = TIPO_EMOJI.get(tipo_slug, "✨"),
                ))
            select = disnake.ui.StringSelect(
                placeholder = "🎨 Escolha um cosmético para equipar...",
                options     = options,
                min_values  = 1,
                max_values  = 1,
                row         = 0,
            )
            select.callback = self._on_equipar
            self.add_item(select)

    async def _salvar(self):
        inv_completo = self.itens_normais + self.cosm_inv
        inv_str  = _montar_inv_str(inv_completo)
        cosm_str = _serializar_cosm(self.cosm_atual)
        try:
            db.sheet.batch_update([
                {"range": f"F{self.row}", "values": [[inv_str]]},
                {"range": f"M{self.row}", "values": [[cosm_str]]},
            ])
        except Exception as e:
            db.handle_db_error(e)

    async def _refresh(self, inter: disnake.MessageInteraction, msg: str):
        self._rebuild_select()
        embed = _build_embed_visuais(self.autor, self.cosm_inv, self.cosm_atual)
        await inter.edit_original_response(content=msg, embed=embed, view=self)

    async def _on_equipar(self, inter: disnake.MessageInteraction):
        await inter.response.defer(ephemeral=True)
        slug             = inter.data["values"][0]
        tipo_slug, valor = _parse_slug(slug)

        chave_lower = f"cosmético:{slug}".lower()
        item_real   = next((i for i in self.cosm_inv if i.lower() == chave_lower), None)
        if not item_real:
            return await inter.edit_original_response(content=f"❌ `{slug}` não está mais no seu inventário!")

        equipado_atual = self.cosm_atual.get(tipo_slug)
        if equipado_atual and equipado_atual != valor:
            self.cosm_inv.append(f"cosmético:{tipo_slug}:{equipado_atual}")

        self.cosm_inv.remove(item_real)
        self.cosm_atual[tipo_slug] = valor

        await self._salvar()
        await self._refresh(inter, f"✨ **{TIPO_LABEL_ICON.get(tipo_slug, tipo_slug)}: `{valor}`** equipado!")

    async def _remover(self, inter: disnake.MessageInteraction, tipo: str):
        await inter.response.defer(ephemeral=True)
        valor_equipado = self.cosm_atual.get(tipo)
        if not valor_equipado:
            return await inter.edit_original_response(
                content=f"⚠️ Você não tem nenhum(a) **{TIPO_LABEL.get(tipo, tipo)}** equipado(a)."
            )
        self.cosm_inv.append(f"cosmético:{tipo}:{valor_equipado}")
        self.cosm_atual.pop(tipo, None)
        await self._salvar()
        await self._refresh(inter, f"🗑️ **{TIPO_LABEL_ICON.get(tipo, tipo)}: `{valor_equipado}`** devolvido ao inventário!")

    @disnake.ui.button(label="🗑️ Remover Cor",     style=disnake.ButtonStyle.danger,    row=1)
    async def btn_rm_cor(self, button, inter):     await self._remover(inter, "cor")

    @disnake.ui.button(label="🗑️ Remover Moldura", style=disnake.ButtonStyle.danger,    row=1)
    async def btn_rm_moldura(self, button, inter): await self._remover(inter, "moldura")

    @disnake.ui.button(label="🗑️ Remover Título",  style=disnake.ButtonStyle.danger,    row=1)
    async def btn_rm_titulo(self, button, inter):  await self._remover(inter, "titulo")

    @disnake.ui.button(label="❌ Fechar",           style=disnake.ButtonStyle.secondary, row=2)
    async def btn_fechar(self, button, inter):
        await inter.response.defer()
        await inter.delete_original_response()

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        if inter.author.id != self.autor.id:
            await inter.response.send_message(
                "❌ Este painel é só seu! Use `!visuais` para abrir o seu.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════════════════════════════════════

class Profiles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, use este comando no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

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

    _CORES = {
        "verde":    0x4CAF50,
        "azul":     0x5B7FA6,
        "cinza":    0x7b7b7b,
        "roxo":     0x9C27B0,
        "laranja":  0xFF8C00,
        "ciano":    0x00BCD4,
        "gold":     0xFFD700,
        "vermelho": 0xE53935,
        "rosa":     0xFF69B4,
    }

    # ── !conquistas ───────────────────────────────────────────────────────────

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

    # ── helpers de embed unificado ────────────────────────────────────────────

    def _build_embed_perfil(self, membro: disnake.Member, user: dict, user_id: str) -> disnake.Embed:
        saldo = db.parse_float(user["data"][2])
        cargo = user["data"][3] if len(user["data"]) > 3 and user["data"][3] else "Lêmure"
        agora = time.time()

        # Cooldowns
        ultimo_work   = db.parse_float(user["data"][4] if len(user["data"]) > 4 else None)
        ultimo_roubo  = db.parse_float(user["data"][6] if len(user["data"]) > 6 else None)
        ultimo_invest = db.parse_float(user["data"][7] if len(user["data"]) > 7 else None)

        def _cd(ultimo, cooldown):
            return "✅ Disponível" if agora - ultimo >= cooldown else f"<t:{int(ultimo + cooldown)}:R>"

        # Inventário e Escudos
        inv_str  = str(user["data"][5]) if len(user["data"]) > 5 else ""
        inv_list = [i.strip() for i in inv_str.split(",") if i.strip() and i.strip().lower() != "nenhum"]
        cargas_escudo = self.bot.escudos_ativos.get(user_id, 0) if hasattr(self.bot, "escudos_ativos") else 0

        if inv_list:
            contagem = {}
            for item in inv_list:
                # Ocultar as chaves de cosmético na exibição de mochila
                if not item.startswith("cosmético:") and not item.startswith("cosmetico:"):
                    contagem[item] = contagem.get(item, 0) + 1
            itens = [f"`{q}× {i}`" if q > 1 else f"`{i}`" for i, q in contagem.items()]
        else:
            itens = []
        if cargas_escudo > 0:
            itens.append(f"`🛡️ Escudo ({cargas_escudo}/{ESCUDO_CARGAS})`")
        inv_val = "  ".join(itens) if itens else "*Mochila vazia*"

        # Cosméticos
        cosm    = _parse_cosm_str(user)
        cor_str = cosm.get("cor", "")
        moldura = cosm.get("moldura", "")
        titulo  = cosm.get("titulo", "")
        bio     = cosm.get("bio", "")

        cargo_icon, cor_cargo = self._CARGO_INFO.get(cargo, ("🐒", 0xFFD700))
        embed_color = self._CORES.get(cor_str, cor_cargo)

        nome_display = membro.display_name
        if moldura: nome_display = f"{moldura} {nome_display}"
        if titulo:  nome_display = f"{nome_display}  ·  *{titulo}*"

        # Posição no Rank
        pos_rank = "—"
        try:
            all_rows = db.sheet.get_all_values()
            if len(all_rows) > 0:
                primeira = all_rows[0]
                tem_cabecalho = any(c.lower() in ("nome", "saldo", "cargo", "user_id") for c in primeira)
                dados = all_rows[1:] if tem_cabecalho else all_rows
                dados_sorted = sorted(dados, key=lambda r: db.parse_float(r[2]) if len(r) > 2 else 0, reverse=True)
                for i, row in enumerate(dados_sorted):
                    if str(row[0]) == user_id:
                        pos_rank = f"#{i+1} de {len(dados_sorted)}"
                        break
        except Exception:
            pass

        # Emblemas e Conquistas
        emblemas = []
        if saldo >= 500000:      emblemas.append("🤑 Burguês Safado")
        elif saldo >= 100000:    emblemas.append("💎 Magnata")
        if 0 < saldo < 100:      emblemas.append("📉 Falência Técnica")
        if saldo <= 0:           emblemas.append("🦴 Passa Fome")
        if cargo == "Rei Símio": emblemas.append("👑 Rei da Selva")
        if "Pé de Cabra" in inv_list: emblemas.append("🕵️ Invasor")

        if pos_rank.startswith("#1 "): emblemas.append("🥇 Alfa da Selva")
        elif pos_rank.startswith("#2 "): emblemas.append("🥈 Vice-Líder")
        elif pos_rank.startswith("#3 "): emblemas.append("🥉 Bronze de Ouro")

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

        # Construção da Descrição
        sep  = "─" * 34
        desc = f"### {cargo_icon}  {nome_display}\n{sep}\n"
        if bio: desc += f"💬 *\"{bio}\"*\n\n"
        desc += f"💰 **Saldo:** `{formatar_moeda(saldo)} MC`\n"
        desc += f"💼 **Cargo:** `{cargo}`\n"
        desc += f"📊 **Rank:** `{pos_rank}`"
        if rec > 0: desc += f"\n🚨 **Recompensa:** `{formatar_moeda(rec)} MC`"

        # Montagem do Embed
        embed = disnake.Embed(description=desc, color=embed_color)
        embed.set_author(name=f"🌿 Perfil · {membro.display_name}", icon_url=membro.display_avatar.url)
        embed.set_thumbnail(url=membro.display_avatar.url)

        embed.add_field(name="🔨 Trabalho",     value=_cd(ultimo_work,   3600),  inline=True)
        embed.add_field(name="🔫 Roubo",        value=_cd(ultimo_roubo,  7200),  inline=True)
        embed.add_field(name="🏛️ Investimento", value=_cd(ultimo_invest, 86400), inline=True)
        
        embed.add_field(name="🎒 Inventário",   value=inv_val, inline=False)

        cosm_equipados = []
        if cor_str: cosm_equipados.append(f"🎨 `{cor_str}`")
        if moldura:  cosm_equipados.append(f"🖼️ `{moldura}`")
        if titulo:   cosm_equipados.append(f"🏷️ `{titulo}`")
        if cosm_equipados:
            embed.add_field(name="✨ Estilo", value="  ·  ".join(cosm_equipados), inline=False)

        if emblemas:
            linhas = []
            for i in range(0, len(emblemas), 3):
                linhas.append("  ·  ".join(emblemas[i:i+3]))
            emblemas_val = "\n".join(linhas)
        else:
            emblemas_val = "*Nenhuma conquista ainda — vá à luta!*"
        embed.add_field(name=f"🏆 Conquistas ({len(emblemas)})", value=emblemas_val, inline=False)

        embed.set_footer(text="🐒 Selva dos Macacoins  ·  !visuais para personalizar")
        return embed

    # ── !perfil (Agora unificado, público e completo) ─────────────────────────

    @commands.command(aliases=["p", "status", "conta", "carteira", "saldo", "stats", "dados", "espionar"])
    @commands.cooldown(1, 4, commands.BucketType.user)
    async def perfil(self, ctx, membro: disnake.Member = None):
        membro  = membro or ctx.author
        user_id = str(membro.id)
        try:
            user = db.get_user_data(user_id)
            if not user:
                nome = "você" if membro.id == ctx.author.id else membro.mention
                return await ctx.send(f"❌ {nome} não tem conta! Use `!trabalhar` para se registrar.")

            embed = self._build_embed_perfil(membro, user, user_id)
            
            try: await ctx.message.delete()
            except: pass

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
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(f"❌ Jogador não encontrado! Use `!perfil @usuario`.", delete_after=8)


    # ── !bio ──────────────────────────────────────────────────────────────────

    @commands.command()
    async def bio(self, ctx, *, texto: str = None):
        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Use `!trabalhar` primeiro para se registrar!")

            if texto is None:
                db.set_cosmetico(user["row"], user, "bio", "")
                return await ctx.send(f"🗑️ {ctx.author.mention}, sua bio foi removida.")

            texto = texto.strip()[:60]
            db.set_cosmetico(user["row"], user, "bio", texto)
            await ctx.send(f"✅ {ctx.author.mention}, bio atualizada: *\"{texto}\"*")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !bio: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ── !visuais ──────────────────────────────────────────────────────────────

    @commands.command(aliases=["visual", "cosmetico", "skin"])
    async def visuais(self, ctx):
        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Use `!trabalhar` primeiro!")

            inv_list   = _parse_inv(user)
            cosm_inv   = [i for i in inv_list if i.startswith("cosmético:") or i.startswith("cosmetico:")]
            itens_normais = [i for i in inv_list if not (i.startswith("cosmético:") or i.startswith("cosmetico:"))]
            cosm_atual = _parse_cosm_str(user)

            embed = _build_embed_visuais(ctx.author, cosm_inv, cosm_atual)
            view  = ViewVisuais(ctx.author, user["row"], itens_normais, cosm_inv, cosm_atual)

            try: await ctx.message.delete()
            except: pass
            await ctx.send(embed=embed, view=view)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !visuais: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ── !rank ─────────────────────────────────────────────────────────────────

    @commands.command(aliases=["top", "ricos", "placar"])
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def rank(self, ctx):
        try:
            try:
                all_rows = db.sheet.get_all_values()
            except Exception as e:
                print(f"❌ Erro ao acessar planilha no !rank: {e}")
                return await ctx.send("⚠️ **O banco está ocupado!** Tente novamente em 1 minuto.")

            if len(all_rows) < 2:
                return await ctx.send("❌ Sem dados suficientes.")

            primeira = all_rows[0]
            tem_cabecalho = any(c.lower() in ("nome", "saldo", "cargo", "user_id") for c in primeira)

            if tem_cabecalho:
                cabecalho = primeira
                dados     = all_rows[1:]
            else:
                cabecalho = ["user_id", "nome", "saldo", "cargo"]
                dados     = all_rows

            idx_id    = 0
            idx_nome  = next((i for i, c in enumerate(cabecalho) if c.lower() == "nome"),  1)
            idx_saldo = next((i for i, c in enumerate(cabecalho) if c.lower() == "saldo"), 2)
            idx_cargo = next((i for i, c in enumerate(cabecalho) if c.lower() == "cargo"), 3)

            dados_validos = [r for r in dados if len(r) > idx_saldo]
            sorted_all    = sorted(dados_validos, key=lambda r: db.parse_float(r[idx_saldo]), reverse=True)
            top           = sorted_all[:10]

            CARGO_EMOJI = {
                "Lêmure": "🐭", "Macaquinho": "🐒", "Babuíno": "🐵",
                "Chimpanzé": "🌴", "Orangutango": "🦧", "Gorila": "🦍",
                "Ancestral": "🗿", "Rei Símio": "👑",
            }

            def _fmt(s):
                if s >= 1_000_000: return f"{formatar_moeda(s/1_000_000)}M MC"
                if s >= 1_000:     return f"{formatar_moeda(s/1_000)}K MC"
                return f"{formatar_moeda(s)} MC"

            autor_id  = str(ctx.author.id)
            autor_pos = None
            for i, row in enumerate(sorted_all):
                if str(row[idx_id]) == autor_id:
                    autor_pos = i + 1
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
                    # AGORA MOSTRA O VALOR EXATO PARA AS POSIÇÕES 4 AO 10!
                    linhas.append(f"{NUMS[i-3]}  {c_em} **{nome}** — `{formatar_moeda(saldo)} MC`")
                embed.add_field(name="📊  Classificação", value="\n".join(linhas), inline=False)

            if autor_pos:
                embed.add_field(
                    name  = "📍  Sua posição",
                    value = f"{ctx.author.mention} está em **#{autor_pos}** no ranking!",
                    inline= False,
                )

            embed.set_footer(text="!perfil @user para ver os detalhes completos de qualquer jogador")
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