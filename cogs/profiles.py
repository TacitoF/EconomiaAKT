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

TIPO_EMOJI = {"cor": "🎨", "moldura": "🖼️", "titulo": "🏷️"}
TIPO_LABEL = {"cor": "Cor",  "moldura": "Moldura", "titulo": "Título"}
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
    """Lê cosméticos diretamente do campo 12 sem chamar o Sheets de novo."""
    raw = str(user["data"][11]) if len(user["data"]) > 11 else ""
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
    """Monta o embed do painel sem tocar no Sheets."""
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
#  VIEW: PAINEL DE COSMÉTICOS (ephemeral — só o dono vê)
# ══════════════════════════════════════════════════════════════════════════════

class ViewVisuais(disnake.ui.View):
    """
    Painel de cosméticos com estado em memória.
    Após equipar/remover faz apenas 1 batch_update no Sheets e reconstrói
    o embed localmente — zero leituras extras.
    """

    def __init__(self, autor: disnake.Member, row: int, cosm_inv: list, cosm_atual: dict):
        super().__init__(timeout=120)
        self.autor      = autor
        self.row        = row          # linha do usuário na planilha
        self.cosm_inv   = list(cosm_inv)    # cópia local do inventário de cosméticos
        self.cosm_atual = dict(cosm_atual)  # cópia local dos cosméticos equipados

        self._rebuild_select()

    # ── garante que o select sempre reflita o estado local ───────────────────
    def _rebuild_select(self):
        # Remove selects antigos
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
        """1 chamada batch ao Sheets: inventário (col 6) + cosméticos (col 12)."""
        inv_str  = _montar_inv_str(self._inv_completo_com_cosm())
        cosm_str = _serializar_cosm(self.cosm_atual)
        try:
            db.sheet.batch_update([
                {"range": f"F{self.row}", "values": [[inv_str]]},
                {"range": f"L{self.row}", "values": [[cosm_str]]},
            ])
        except Exception as e:
            db.handle_db_error(e)

    def _inv_completo_com_cosm(self) -> list:
        """Retorna cosm_inv formatado como itens de inventário ('cosmético:slug')."""
        return [f"cosmético:{item.split(':',1)[1]}" if not item.startswith("cosmético:") else item
                for item in self.cosm_inv]

    async def _refresh(self, inter: disnake.MessageInteraction, msg: str):
        """Reconstrói embed+select localmente e edita a mensagem — sem ler o Sheets."""
        self._rebuild_select()
        embed = _build_embed_visuais(self.autor, self.cosm_inv, self.cosm_atual)
        await inter.edit_original_response(content=msg, embed=embed, view=self)

    # ── equipar (callback do select) ─────────────────────────────────────────
    async def _on_equipar(self, inter: disnake.MessageInteraction):
        await inter.response.defer(ephemeral=True)
        slug      = inter.data["values"][0]
        tipo_slug, valor = _parse_slug(slug)

        # Verifica se ainda está no inventário local
        chave_lower = f"cosmético:{slug}".lower()
        item_real   = next((i for i in self.cosm_inv if i.lower() == chave_lower), None)
        if not item_real:
            return await inter.edit_original_response(content=f"❌ `{slug}` não está mais no seu inventário!")

        # Devolve o item anterior do mesmo tipo ao inventário (se houver)
        equipado_atual = self.cosm_atual.get(tipo_slug)
        if equipado_atual and equipado_atual != valor:
            self.cosm_inv.append(f"cosmético:{tipo_slug}:{equipado_atual}")

        # Equipa o novo item
        self.cosm_inv.remove(item_real)
        self.cosm_atual[tipo_slug] = valor

        await self._salvar()
        await self._refresh(inter, f"✨ **{TIPO_LABEL_ICON.get(tipo_slug, tipo_slug)}: `{valor}`** equipado!")

    # ── remover ──────────────────────────────────────────────────────────────
    async def _remover(self, inter: disnake.MessageInteraction, tipo: str):
        await inter.response.defer(ephemeral=True)
        valor_equipado = self.cosm_atual.get(tipo)
        if not valor_equipado:
            return await inter.edit_original_response(
                content=f"⚠️ Você não tem nenhum(a) **{TIPO_LABEL.get(tipo, tipo)}** equipado(a)."
            )

        # Devolve ao inventário local e limpa slot
        self.cosm_inv.append(f"cosmético:{tipo}:{valor_equipado}")
        self.cosm_atual.pop(tipo, None)

        await self._salvar()
        await self._refresh(inter, f"🗑️ **{TIPO_LABEL_ICON.get(tipo, tipo)}: `{valor_equipado}`** devolvido ao inventário!")

    @disnake.ui.button(label="🗑️ Remover Cor",    style=disnake.ButtonStyle.danger,     row=1)
    async def btn_rm_cor(self, button, inter):     await self._remover(inter, "cor")

    @disnake.ui.button(label="🗑️ Remover Moldura", style=disnake.ButtonStyle.danger,     row=1)
    async def btn_rm_moldura(self, button, inter): await self._remover(inter, "moldura")

    @disnake.ui.button(label="🗑️ Remover Título",  style=disnake.ButtonStyle.danger,     row=1)
    async def btn_rm_titulo(self, button, inter):  await self._remover(inter, "titulo")

    @disnake.ui.button(label="❌ Fechar",           style=disnake.ButtonStyle.secondary,  row=2)
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
        pass  # ephemeral some sozinha


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW: PORTAL MEU PERFIL — prévia privada + opção de publicar
# ══════════════════════════════════════════════════════════════════════════════

class ViewPortalPerfil(disnake.ui.View):
    """Prévia privada do cartão de perfil com opção de publicar no canal."""

    def __init__(self, author_id: int, cog, embed_publico: disnake.Embed):
        super().__init__(timeout=90)
        self.author_id     = author_id
        self.cog           = cog
        self.embed_publico = embed_publico

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        if inter.author.id != self.author_id:
            await inter.response.send_message("❌ Este painel não é seu!", ephemeral=True)
            return False
        return True

    @disnake.ui.button(label="📢 Mostrar perfil no canal", style=disnake.ButtonStyle.success)
    async def btn_publicar(self, button, inter: disnake.MessageInteraction):
        """Posta o cartão visual público para todo mundo ver."""
        await inter.response.send_message(embed=self.embed_publico)
        try:
            await inter.message.delete()
        except Exception:
            pass

    @disnake.ui.button(label="🔒 Ver minha conta", style=disnake.ButtonStyle.primary)
    async def btn_conta(self, button, inter: disnake.MessageInteraction):
        """Abre o painel financeiro privado sem sair do !perfil."""
        user = db.get_user_data(str(self.author_id))
        if not user:
            return await inter.response.send_message("❌ Conta não encontrada!", ephemeral=True)
        embed = self.cog._build_embed_conta(inter.author, user, str(self.author_id))
        await inter.response.send_message(embed=embed, ephemeral=True)

    @disnake.ui.button(label="❌ Fechar", style=disnake.ButtonStyle.secondary)
    async def btn_fechar(self, button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        try:
            await inter.message.delete()
        except Exception:
            pass

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(
                content="⏳ Portal expirado. Digite `!perfil` novamente.", view=self
            )
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW: CONFIRMAÇÃO DE INTELIGÊNCIA — !dados @usuario
# ══════════════════════════════════════════════════════════════════════════════

class ViewConfirmarEspionagem(disnake.ui.View):
    """Confirmação ephemeral antes de cobrar MC para ver os dados financeiros do alvo."""

    def __init__(self, author_id: int, alvo: disnake.Member, cog):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.alvo      = alvo
        self.cog       = cog

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        if inter.author.id != self.author_id:
            await inter.response.send_message("❌ Esta confirmação não é sua!", ephemeral=True)
            return False
        return True

    @disnake.ui.button(label="✅ Confirmar — pagar 500 MC", style=disnake.ButtonStyle.success)
    async def btn_confirmar(self, button, inter: disnake.MessageInteraction):
        espiao = db.get_user_data(str(inter.author.id))
        if not espiao:
            return await inter.response.send_message("❌ Conta não encontrada!", ephemeral=True)

        saldo_espiao = db.parse_float(espiao["data"][2])
        custo        = self.cog.CUSTO_ESPIONAR

        if saldo_espiao < custo:
            faltam = round(custo - saldo_espiao, 2)
            return await inter.response.send_message(
                content=(
                    f"❌ Saldo insuficiente!\n"
                    f"Você precisa de **`{int(custo)} MC`** — faltam `{formatar_moeda(faltam)} MC`."
                ), ephemeral=True
            )

        alvo_data = db.get_user_data(str(self.alvo.id))
        if not alvo_data:
            return await inter.response.send_message(
                content=f"❌ {self.alvo.mention} não tem conta!", ephemeral=True
            )

        db.update_value(espiao["row"], 3, round(saldo_espiao - custo, 2))
        # !dados mostra o relatório financeiro completo do alvo
        embed = self.cog._build_embed_dados(self.alvo, alvo_data, str(self.alvo.id))
        embed.set_footer(text=f"🕵️ Relatório confidencial — custou {int(custo)} MC  ·  só você está vendo isso")

        await inter.response.send_message(
            content=f"🕵️ Informante pago! Relatório de **{self.alvo.display_name}**:",
            embed=embed,
            ephemeral=True
        )

        try:
            await inter.message.delete()
        except Exception:
            pass

    @disnake.ui.button(label="❌ Cancelar", style=disnake.ButtonStyle.danger)
    async def btn_cancelar(self, button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        try:
            await inter.message.delete()
        except Exception:
            pass

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(content="⏳ O tempo para espionar esgotou.", view=self)
        except Exception:
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

    # ── !perfil ───────────────────────────────────────────────────────────────

    CUSTO_ESPIONAR = 500.0

    def _build_embed_perfil(self, membro: disnake.Member, user: dict, user_id: str) -> disnake.Embed:
        """Cartão VISUAL público — sem dados financeiros sensíveis."""
        saldo = db.parse_float(user["data"][2])
        cargo = user["data"][3] if len(user["data"]) > 3 and user["data"][3] else "Lêmure"

        cosm    = _parse_cosm_str(user)
        cor_str = cosm.get("cor", "")
        moldura = cosm.get("moldura", "")
        titulo  = cosm.get("titulo", "")
        bio     = cosm.get("bio", "")

        cargo_icon, cor_cargo = self._CARGO_INFO.get(cargo, ("🐒", 0xFFD700))
        embed_color = self._CORES.get(cor_str, cor_cargo)

        # ── Nome decorado com moldura + título ───────────────────────────────
        nome_display = membro.display_name
        if moldura:
            nome_display = f"{moldura} {nome_display}"
        if titulo:
            nome_display = f"{nome_display}  ·  *{titulo}*"

        # ── Emblemas de conquistas (público — é prestígio) ───────────────────
        emblemas = []
        if saldo >= 500000:   emblemas.append("🤑 Burguês Safado")
        elif saldo >= 100000: emblemas.append("💎 Magnata")
        if 0 < saldo < 100:   emblemas.append("📉 Falência Técnica")
        if saldo <= 0:        emblemas.append("🦴 Passa Fome")
        if cargo == "Rei Símio": emblemas.append("👑 Rei da Selva")

        inv_str  = str(user["data"][5]) if len(user["data"]) > 5 else ""
        inv_list = [i.strip() for i in inv_str.split(",") if i.strip() and i.strip().lower() != "nenhum"]
        if "Pé de Cabra" in inv_list: emblemas.append("🕵️ Invasor")

        try:
            all_rows = db.sheet.get_all_values()
            if len(all_rows) > 1:
                dados_sorted = sorted(all_rows[1:], key=lambda r: db.parse_float(r[2]) if len(r) > 2 else 0, reverse=True)
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

        sep = "─" * 34
        desc = f"### {cargo_icon}  {nome_display}\n{sep}\n💼  **Cargo:** `{cargo}`"
        if bio:
            desc += f"\n💬  *\"{bio}\"*"
        if rec > 0:
            desc += f"\n🚨  **Recompensa:** `{formatar_moeda(rec)} MC`"

        embed = disnake.Embed(description=desc, color=embed_color)
        embed.set_author(name=f"🌿 Perfil · {membro.display_name}", icon_url=membro.display_avatar.url)
        embed.set_thumbnail(url=membro.display_avatar.url)

        # ── Cosméticos equipados (orgulho de exibir) ─────────────────────────
        cosm_equipados = []
        if cor_str: cosm_equipados.append(f"🎨 `{cor_str}`")
        if moldura:  cosm_equipados.append(f"🖼️ `{moldura}`")
        if titulo:   cosm_equipados.append(f"🏷️ `{titulo}`")
        if cosm_equipados:
            embed.add_field(name="✨  Estilo", value="  ·  ".join(cosm_equipados), inline=False)

        # ── Conquistas ────────────────────────────────────────────────────────
        if emblemas:
            linhas = []
            for i in range(0, len(emblemas), 3):
                linhas.append("  ·  ".join(emblemas[i:i+3]))
            emblemas_val = "\n".join(linhas)
        else:
            emblemas_val = "*Nenhuma conquista ainda — vá à luta!*"
        embed.add_field(name=f"🏆  Conquistas  ({len(emblemas)})", value=emblemas_val, inline=False)

        embed.set_footer(text="🐒 Selva dos Macacoins  ·  !visuais para personalizar  ·  !conta para ver seus dados")
        return embed

    def _build_embed_conta(self, membro: disnake.Member, user: dict, user_id: str) -> disnake.Embed:
        """Painel PRIVADO com todos os dados financeiros e cooldowns do próprio usuário."""
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

        cargo_icon, cor_cargo = self._CARGO_INFO.get(cargo, ("🐒", 0xFFD700))

        # Posição no rank
        pos_rank = "—"
        try:
            all_rows = db.sheet.get_all_values()
            if len(all_rows) > 1:
                dados_sorted = sorted(all_rows[1:], key=lambda r: db.parse_float(r[2]) if len(r) > 2 else 0, reverse=True)
                for i, row in enumerate(dados_sorted):
                    if str(row[0]) == user_id:
                        pos_rank = f"#{i+1} de {len(dados_sorted)}"
                        break
        except Exception:
            pass

        rec = getattr(self.bot, "recompensas", {}).get(user_id, 0.0)

        sep = "─" * 34
        desc = (
            f"### 🔒  Painel Privado — {membro.display_name}\n"
            f"{sep}\n"
            f"💰  **Saldo:** `{formatar_moeda(saldo)} MC`\n"
            f"💼  **Cargo:** `{cargo_icon} {cargo}`\n"
            f"📊  **Posição no Rank:** `{pos_rank}`"
        )
        if rec > 0:
            desc += f"\n🚨  **Recompensa na sua cabeça:** `{formatar_moeda(rec)} MC`"

        embed = disnake.Embed(description=desc, color=cor_cargo)
        embed.set_author(name=f"🔐 Minha Conta · {membro.display_name}", icon_url=membro.display_avatar.url)
        embed.set_thumbnail(url=membro.display_avatar.url)

        embed.add_field(name="🔨  Trabalho",     value=st_work,   inline=True)
        embed.add_field(name="🔫  Roubo",        value=st_roubo,  inline=True)
        embed.add_field(name="🏛️  Investimento", value=st_invest, inline=True)
        embed.add_field(name="🎒  Inventário",   value=inv_val,   inline=False)

        embed.set_footer(text="🔒 Só você está vendo isso  ·  !perfil para ver seu cartão  ·  !visuais para personalizar")
        return embed

    def _build_embed_dados(self, membro: disnake.Member, user: dict, user_id: str) -> disnake.Embed:
        """Relatório de INTELIGÊNCIA sobre outro jogador — exibido via !dados @alvo (custa MC)."""
        saldo = db.parse_float(user["data"][2])
        cargo = user["data"][3] if len(user["data"]) > 3 and user["data"][3] else "Lêmure"
        agora = time.time()

        ultimo_work   = db.parse_float(user["data"][4] if len(user["data"]) > 4 else None)
        ultimo_roubo  = db.parse_float(user["data"][6] if len(user["data"]) > 6 else None)
        ultimo_invest = db.parse_float(user["data"][7] if len(user["data"]) > 7 else None)

        def _cd_label(ultimo, cooldown):
            if agora - ultimo >= cooldown:
                return "✅ Disponível agora"
            restante = int((ultimo + cooldown) - agora)
            mins = restante // 60
            return f"⏳ ~{mins} min restantes"

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

        cargo_icon, _ = self._CARGO_INFO.get(cargo, ("🐒", 0xFFD700))

        # Posição no rank do alvo
        pos_rank = "—"
        try:
            all_rows = db.sheet.get_all_values()
            if len(all_rows) > 1:
                dados_sorted = sorted(all_rows[1:], key=lambda r: db.parse_float(r[2]) if len(r) > 2 else 0, reverse=True)
                for i, row in enumerate(dados_sorted):
                    if str(row[0]) == user_id:
                        pos_rank = f"#{i+1} de {len(dados_sorted)}"
                        break
        except Exception:
            pass

        rec = getattr(self.bot, "recompensas", {}).get(user_id, 0.0)

        sep = "─" * 34
        desc = (
            f"### 🕵️  Relatório de Inteligência\n"
            f"{sep}\n"
            f"🎯  **Alvo:** {membro.mention}\n"
            f"💼  **Cargo:** `{cargo_icon} {cargo}`\n"
            f"💰  **Saldo estimado:** `{formatar_moeda(saldo)} MC`\n"
            f"📊  **Posição no Rank:** `{pos_rank}`"
        )
        if rec > 0:
            desc += f"\n🚨  **Recompensa:** `{formatar_moeda(rec)} MC`"

        embed = disnake.Embed(description=desc, color=0x2C2F33)
        embed.set_author(name=f"🕵️ Dossiê · {membro.display_name}", icon_url=membro.display_avatar.url)
        embed.set_thumbnail(url=membro.display_avatar.url)

        embed.add_field(name="🔨  Trabalho",     value=_cd_label(ultimo_work,   3600),  inline=True)
        embed.add_field(name="🔫  Roubo",        value=_cd_label(ultimo_roubo,  7200),  inline=True)
        embed.add_field(name="🏛️  Investimento", value=_cd_label(ultimo_invest, 86400), inline=True)
        embed.add_field(name="🎒  Inventário",   value=inv_val,                         inline=False)

        return embed



    @commands.command(aliases=["p", "status"])
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def perfil(self, ctx, membro: disnake.Member = None):
        """Cartão visual público. Sem @membro = exibe o seu próprio (com opção de publicar)."""
        membro  = membro or ctx.author
        user_id = str(membro.id)
        try:
            user = db.get_user_data(user_id)
            if not user:
                nome = "você" if membro.id == ctx.author.id else membro.mention
                return await ctx.send(f"❌ {nome} não tem conta! Use `!trabalhar` para se registrar.")

            embed_pub = self._build_embed_perfil(membro, user, user_id)

            # Próprio perfil — mostra prévia privada + botões
            if membro.id == ctx.author.id:
                try: await ctx.message.delete()
                except: pass
                view = ViewPortalPerfil(ctx.author.id, self, embed_pub)
                view.message = await ctx.send(
                    content=(
                        f"👤 {ctx.author.mention}, aqui está a prévia do seu cartão!\n"
                        f"📢 **Mostrar no canal** — todos verão.\n"
                        f"🔒 **Ver minha conta** — seus dados privados (só você vê)."
                    ),
                    embed=embed_pub,
                    view=view,
                )
                return

            # Perfil alheio — apenas o cartão visual, sem dados sensíveis (gratuito)
            try: await ctx.message.delete()
            except: pass
            embed_pub.set_footer(text=f"🐒 Selva dos Macacoins  ·  Use !dados @{membro.display_name} para ver dados detalhados (custa MC)")
            await ctx.send(embed=embed_pub)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !perfil: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, erro ao carregar perfil. Tente novamente!")

    @perfil.error
    async def perfil_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Não faça spam, macaco! Tente novamente em {error.retry_after:.1f}s.", delete_after=5)

    @commands.command(aliases=["carteira", "saldo", "stats"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def conta(self, ctx):
        """Painel privado com seus dados financeiros completos. Só você vê."""
        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Você não tem conta! Use `!trabalhar` primeiro.")
            try: await ctx.message.delete()
            except: pass
            embed = self._build_embed_conta(ctx.author, user, str(ctx.author.id))
            await ctx.send(embed=embed, ephemeral=True)
        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !conta: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, erro ao carregar conta. Tente novamente!")

    @conta.error
    async def conta_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Aguarde {error.retry_after:.1f}s.", delete_after=5)

    @commands.command(aliases=["espionar", "dossie", "investigar"])
    @commands.cooldown(1, 8, commands.BucketType.user)
    async def dados(self, ctx, alvo: disnake.Member = None):
        """Paga MC para ver o dossiê financeiro completo de outro jogador."""
        if not alvo:
            return await ctx.send(
                f"❌ {ctx.author.mention}, mencione um jogador! Ex: `!dados @usuario`", delete_after=8
            )
        if alvo.id == ctx.author.id:
            return await ctx.send(
                f"🤦 {ctx.author.mention}, use `!conta` para ver seus próprios dados — de graça!", delete_after=8
            )
        if alvo.bot:
            return await ctx.send(f"🤖 Bots não têm carteira na selva!", delete_after=6)

        try:
            espiao = db.get_user_data(str(ctx.author.id))
            if not espiao:
                return await ctx.send("❌ Você não tem conta! Use `!trabalhar` primeiro.")

            saldo_espiao = db.parse_float(espiao["data"][2])
            custo        = self.CUSTO_ESPIONAR

            if saldo_espiao < custo:
                faltam = round(custo - saldo_espiao, 2)
                try: await ctx.message.delete()
                except: pass
                return await ctx.send(
                    f"🕵️ {ctx.author.mention}, contratar um informante custa **`{int(custo)} MC`**!\n"
                    f"Você tem `{formatar_moeda(saldo_espiao)} MC` — faltam `{formatar_moeda(faltam)} MC`.",
                    delete_after=10
                )

            try: await ctx.message.delete()
            except: pass

            embed_conf = disnake.Embed(
                title="🕵️ Contratar Informante?",
                description=(
                    f"Você quer pagar **`{int(custo)} MC`** para obter o dossiê completo de {alvo.mention}.\n\n"
                    f"💰 Seu saldo: `{formatar_moeda(saldo_espiao)} MC`\n"
                    f"💸 Após pagar: `{formatar_moeda(saldo_espiao - custo)} MC`\n\n"
                    f"📋 **O dossiê inclui:** saldo, cargo, cooldowns, inventário e posição no rank.\n"
                    f"*Só você verá o resultado — mensagem desaparece em 60s se ignorada.*"
                ),
                color=disnake.Color.dark_orange()
            )
            embed_conf.set_thumbnail(url=alvo.display_avatar.url)

            view = ViewConfirmarEspionagem(ctx.author.id, alvo, self)
            view.message = await ctx.send(embed=embed_conf, view=view)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !dados: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, erro ao buscar informante. Tente novamente!")

    @dados.error
    async def dados_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Aguarde {error.retry_after:.1f}s.", delete_after=5)
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(f"❌ Jogador não encontrado! Use `!dados @usuario`.", delete_after=8)


    # ── !bio ──────────────────────────────────────────────────────────────────

    @commands.command()
    async def bio(self, ctx, *, texto: str = None):
        """Define uma bio curta que aparece no seu perfil. Máx. 60 caracteres."""
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
        """Abre o painel de cosméticos (só você vê). Equipar, remover, tudo em um lugar."""
        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Use `!trabalhar` primeiro!")

            inv_list  = _parse_inv(user)
            cosm_inv  = [i for i in inv_list if i.startswith("cosmético:") or i.startswith("cosmetico:")]
            cosm_atual = _parse_cosm_str(user)

            embed = _build_embed_visuais(ctx.author, cosm_inv, cosm_atual)
            view  = ViewVisuais(ctx.author, user["row"], cosm_inv, cosm_atual)

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
                "Chimpanzé": "🌴", "Orangutango": "🦧", "Gorila": "🦍",
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