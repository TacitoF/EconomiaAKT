import disnake
from disnake.ext import commands
import database as db
import time

ESCUDO_CARGAS = 3

def formatar_moeda(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ── Catálogos ─────────────────────────────────────────────────────────────────
# Formato: slug -> (preco, label, emoji, descricao_ou_raridade)

CATALOGO_CARGOS = {
    "cargo:macaquinho":  (1200.0,   "Macaquinho",   "🐒", "Salário: 130–230 MC/h"),
    "cargo:babuino":     (5500.0,   "Babuíno",      "🦍", "Salário: 320–530 MC/h"),
    "cargo:chimpanze":   (14000.0,  "Chimpanzé",    "🐵", "Salário: 780–1.320 MC/h"),
    "cargo:orangutango": (35000.0,  "Orangutango",  "🦧", "Salário: 1.900–3.200 MC/h"),
    "cargo:gorila":      (85000.0,  "Gorila",       "🦍", "Salário: 4.700–7.800 MC/h"),
    "cargo:ancestral":   (210000.0, "Ancestral",    "🗿", "Salário: 11.500–19.000 MC/h"),
    "cargo:rei_simio":   (600000.0, "Rei Símio",    "👑", "Salário: 27.000–45.000 MC/h"),
}

CATALOGO_EQUIPAMENTOS = {
    "item:escudo":      (1000.0, "Escudo",      "🛡️", "Bloqueia 3 roubos · limite 1/dia após quebrar"),
    "item:pe_de_cabra": (1200.0, "Pé de Cabra", "🕵️", "Chance de roubo 65% + fura Escudos"),
    "item:seguro":      (950.0,  "Seguro",      "📄", "Reembolsa 60% se você for roubado"),
}

CATALOGO_LOOTBOXES = {
    "item:caixote":  (800.0,   "Caixote de Madeira", "🪵", "Itens comuns + cosméticos básicos (15%)"),
    "item:bau":      (3500.0,  "Baú do Caçador",     "🪙", "Itens táticos + cosméticos raros (30%)"),
    "item:reliquia": (15000.0, "Relíquia Ancestral", "🏺", "Tesouros + cosméticos épicos/lendários (55%)"),
}

CATALOGO_SABOTAGEM = {
    "item:casca":      (300.0,  "Casca de Banana",  "🍌", "Atrasa o próximo trabalho do alvo"),
    "item:imposto":    (1500.0, "Imposto do Gorila", "🦍", "Rouba 25% dos próximos 5 trabalhos"),
    "item:troca_nick": (3000.0, "Troca de Nick",     "🪄", "Altera o apelido do alvo por 30min"),
    "item:c4":         (2000.0, "Carga de C4",       "🧨", "Destrói o Escudo de qualquer alvo"),
}

COSMETICOS_LOJA = {
    "cor:verde":                 (500,   "Cor Verde Selva",           "🟢", "Comum"),
    "cor:azul":                  (500,   "Cor Azul Tropical",         "🔵", "Comum"),
    "cor:cinza":                 (500,   "Cor Cinza das Pedras",      "⚫", "Comum"),
    "titulo:O Intocável":        (1500,  "Título: O Intocável",       "🏷️", "Comum"),
    "cor:roxo":                  (2000,  "Cor Roxo Místico",          "🟣", "Raro"),
    "cor:laranja":               (2000,  "Cor Laranja Fogo",          "🟠", "Raro"),
    "cor:ciano":                 (2000,  "Cor Ciano Glacial",         "🩵", "Raro"),
    "moldura:💀":                (2500,  "Moldura Caveira",           "💀", "Raro"),
    "moldura:🔥":                (2500,  "Moldura Chamas",            "🔥", "Raro"),
    "moldura:⚡":                (2500,  "Moldura Relâmpago",         "⚡", "Raro"),
    "titulo:Caçador de Sombras": (2500,  "Título: Caçador de Sombras","🏷️", "Raro"),
    "titulo:Fantasma":           (2500,  "Título: Fantasma",          "🏷️", "Raro"),
    "titulo:Mão de Ferro":       (2500,  "Título: Mão de Ferro",      "🏷️", "Raro"),
    "cor:gold":                  (8000,  "Cor Dourado Real",          "🟡", "Épico"),
    "cor:vermelho":              (8000,  "Cor Vermelho Sangue",       "🔴", "Épico"),
    "cor:rosa":                  (8000,  "Cor Rosa Flamingo",         "🌸", "Épico"),
    "moldura:🌙":                (6000,  "Moldura Lua Negra",         "🌙", "Épico"),
    "moldura:👑":                (6000,  "Moldura Coroa Dourada",     "👑", "Épico"),
    "moldura:💎":                (6000,  "Moldura Diamante",          "💎", "Épico"),
    "moldura:🐍":                (6000,  "Moldura Cobra Real",        "🐍", "Épico"),
    "titulo:Rei das Trevas":     (7000,  "Título: Rei das Trevas",    "🏷️", "Épico"),
    "titulo:O Invicto":          (7000,  "Título: O Invicto",         "🏷️", "Épico"),
    "titulo:Senhor do Caos":     (7000,  "Título: Senhor do Caos",    "🏷️", "Épico"),
}

NOME_ITEM = {
    "item:escudo":      "Escudo",
    "item:pe_de_cabra": "Pé de Cabra",
    "item:seguro":      "Seguro",
    "item:caixote":     "Caixote de Madeira",
    "item:bau":         "Baú do Caçador",
    "item:reliquia":    "Relíquia Ancestral",
    "item:casca":       "Casca de Banana",
    "item:imposto":     "Imposto do Gorila",
    "item:troca_nick":  "Troca de Nick",
    "item:c4":          "Carga de C4",
    "item:energetico":  "Energético Símio",
    "item:fumaca":      "Bomba de Fumaça",
}

NOME_CARGO = {
    "cargo:macaquinho":  "Macaquinho",
    "cargo:babuino":     "Babuíno",
    "cargo:chimpanze":   "Chimpanzé",
    "cargo:orangutango": "Orangutango",
    "cargo:gorila":      "Gorila",
    "cargo:ancestral":   "Ancestral",
    "cargo:rei_simio":   "Rei Símio",
}

DICA_ITEM = {
    "item:caixote":     "Use `!abrir caixote` para abrir.",
    "item:bau":         "Use `!abrir baú` para abrir.",
    "item:reliquia":    "Use `!abrir relíquia` para abrir.",
    "item:casca":       "Use `!casca @alvo` para jogar.",
    "item:imposto":     "Use `!taxar @alvo` para cobrar.",
    "item:troca_nick":  "Use `!apelidar @alvo <nick>` para renomear.",
    "item:c4":          "Use `!c4 @alvo` para destruir o Escudo dele.",
    "item:energetico":  "Use `!energetico` para zerar o CD de trabalho.",
    "item:fumaca":      "Use `!fumaca` para zerar o CD de roubo.",
    "item:pe_de_cabra": "Equipado automaticamente no `!roubar` — chance 65%.",
    "item:seguro":      "Ativado automaticamente se você for roubado.",
}

# Slugs que suportam compra em múltiplos
SLUGS_MULTIPLOS = set(CATALOGO_LOOTBOXES) | set(CATALOGO_SABOTAGEM)


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER: 1 batch_update por compra (saldo + inventário + opcional)
# ══════════════════════════════════════════════════════════════════════════════

def _batch_compra(row: int, novo_saldo: float, nova_inv: list,
                  col_extra: str = None, val_extra=None):
    """
    Grava saldo (col C) + inventário (col F) em 1 única requisição HTTP.
    col_extra/val_extra: coluna extra opcional, ex: ("D", "Gorila") para cargo.
    """
    inv_str = ", ".join(nova_inv) if nova_inv else "Nenhum"
    updates = [
        {"range": f"C{row}", "values": [[str(round(novo_saldo, 2))]]},
        {"range": f"F{row}", "values": [[inv_str]]},
    ]
    if col_extra:
        updates.append({"range": f"{col_extra}{row}", "values": [[str(val_extra)]]})
    db.sheet.batch_update(updates)


# ══════════════════════════════════════════════════════════════════════════════
#  LÓGICA DE COMPRA (centralizada)
# ══════════════════════════════════════════════════════════════════════════════

async def processar_compra(inter: disnake.MessageInteraction, slug: str,
                           itens: dict, is_cosm: bool, quantidade: int = 1):
    """Executa a compra — máximo 1 chamada ao Sheets por transação."""
    dados = itens[slug]
    preco, label, emoji = dados[0], dados[1], dados[2]
    preco_total = preco * quantidade

    user = db.get_user_data(str(inter.author.id))
    if not user:
        return "❌ Conta não encontrada!"

    saldo    = db.parse_float(user["data"][2])
    row      = user["row"]
    inv_str  = str(user["data"][5]) if len(user["data"]) > 5 else ""
    inv_list = [i.strip() for i in inv_str.split(",")
                if i.strip() and i.strip().lower() != "nenhum"]

    if saldo < preco_total:
        faltam  = round(preco_total - saldo, 2)
        qtd_str = f" (×{quantidade})" if quantidade > 1 else ""
        return (f"❌ Saldo insuficiente!\n"
                f"Precisa de **{formatar_moeda(preco_total)} MC**{qtd_str} "
                f"(faltam **{formatar_moeda(faltam)} MC**).")

    # ── CARGO — 1 batch: C (saldo) + D (cargo) ───────────────────────────────
    if slug.startswith("cargo:"):
        nome_cargo = NOME_CARGO[slug]
        _batch_compra(row, saldo - preco, inv_list, col_extra="D", val_extra=nome_cargo)
        return (f"🎉 Você evoluiu para o cargo **{emoji} {nome_cargo}**!\n"
                f"💸 **-{formatar_moeda(preco)} MC** debitados.")

    # ── ESCUDO (limite 1/dia) — Lógica reescrita para persistência db ────────
    if slug == "item:escudo":
        bot   = inter.bot
        uid   = str(inter.author.id)
        agora = time.time()

        # Lê do banco (sincroniza bot e db)
        cargas_db, quebra_ts = db.get_escudo_data(user)
        
        if uid not in bot.escudos_ativos and cargas_db > 0:
            bot.escudos_ativos[uid] = cargas_db

        escudo_ativo = bot.escudos_ativos.get(uid, 0) > 0
        if "Escudo" in inv_list or escudo_ativo:
            return (f"❌ Você já tem um **Escudo** "
                    f"{'ativo' if escudo_ativo else 'no inventário'}! "
                    f"Só pode ter 1 de cada vez.")

        # Verifica o cooldown de 24h caso ele tenha sido quebrado!
        if quebra_ts > 0 and (agora - quebra_ts < 86400):
            libera_em = int(quebra_ts + 86400)
            return (f"⏳ O seu último **Escudo** foi destruído recentemente! "
                    f"Você só pode comprar outro <t:{libera_em}:R>.")

        # Se passou na checagem, pode comprar e reseta a quebra no bd (se houver)
        bot.escudo_compras[uid] = (1, agora)
        inv_list.append("Escudo")
        _batch_compra(row, saldo - preco, inv_list, col_extra="L", val_extra="")
        return (f"🛡️ **Escudo** comprado e guardado no inventário!\n"
                f"💸 **-{formatar_moeda(preco)} MC** debitados.\n"
                f"Use `!escudo` para ativar quando precisar.")

    # ── COSMÉTICO — 1 batch: C + F ───────────────────────────────────────────
    if is_cosm:
        chave_inv = f"cosmético:{slug}"
        if chave_inv in inv_list:
            return (f"❌ Você já tem **{emoji} {label}** no inventário!\n"
                    f"Use `!visuais` para equipá-lo.")
        inv_list.append(chave_inv)
        _batch_compra(row, saldo - preco, inv_list)
        return (f"✨ **{emoji} {label}** comprado com sucesso!\n"
                f"💸 **-{formatar_moeda(preco)} MC** debitados.\n"
                f"Use `!visuais` para equipar no seu perfil.")

    # ── ITEM COMUM (suporta quantidade) — 1 batch: C + F ─────────────────────
    nome_item = NOME_ITEM.get(slug, label)
    inv_list.extend([nome_item] * quantidade)
    _batch_compra(row, saldo - preco_total, inv_list)
    dica    = DICA_ITEM.get(slug, "Item adicionado ao inventário.")
    qtd_str = f"**×{quantidade}** " if quantidade > 1 else ""
    return (f"{emoji} {qtd_str}**{nome_item}** comprado{'s' if quantidade > 1 else ''}!\n"
            f"💸 **-{formatar_moeda(preco_total)} MC** debitados.\n"
            f"💡 {dica}")


# ══════════════════════════════════════════════════════════════════════════════
#  SELETOR DE QUANTIDADE (lootboxes e sabotagem)
# ══════════════════════════════════════════════════════════════════════════════

class _BotaoQtd(disnake.ui.Button):
    def __init__(self, qtd: int, pode: bool):
        super().__init__(
            label     = f"×{qtd}",
            style     = disnake.ButtonStyle.success if pode else disnake.ButtonStyle.secondary,
            disabled  = not pode,
            custom_id = f"qtd_{qtd}",
            row       = 0,
        )
        self.qtd = qtd

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.defer(ephemeral=True)
        v: ViewQuantidade = self.view
        msg = await processar_compra(inter, v.slug, v.itens, v.is_cosm, quantidade=self.qtd)
        await inter.edit_original_response(content=msg, view=None)


class ViewQuantidade(disnake.ui.View):
    """Botões ×1 ×3 ×5 ×10 exibidos após selecionar item com compra múltipla."""

    def __init__(self, author_id: int, slug: str, itens: dict, is_cosm: bool, saldo: float):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.slug      = slug
        self.itens     = itens
        self.is_cosm   = is_cosm
        preco = itens[slug][0]
        for qtd in [1, 3, 5, 10]:
            self.add_item(_BotaoQtd(qtd, pode=saldo >= preco * qtd))

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        if inter.author.id != self.author_id:
            await inter.response.send_message("❌ Esta loja é só sua!", ephemeral=True)
            return False
        return True


# ══════════════════════════════════════════════════════════════════════════════
#  SELECT: ITEM
# ══════════════════════════════════════════════════════════════════════════════

class SelectItem(disnake.ui.StringSelect):
    def __init__(self, author_id: int, saldo: float, itens: dict, is_cosm: bool = False):
        self.author_id = author_id
        self.saldo     = saldo
        self.itens     = itens
        self.is_cosm   = is_cosm
        options = []
        for slug, dados in itens.items():
            preco, label, emoji = dados[0], dados[1], dados[2]
            pode = saldo >= preco
            options.append(disnake.SelectOption(
                label       = label[:100],
                description = f"{formatar_moeda(preco)} MC — {'✅ Comprar' if pode else '❌ Saldo insuficiente'}",
                value       = slug,
                emoji       = emoji,
            ))
        super().__init__(placeholder="🛒 Selecione o item para comprar...", options=options[:25])

    async def callback(self, inter: disnake.MessageInteraction):
        slug  = self.values[0]
        preco = self.itens[slug][0]
        label = self.itens[slug][1]
        emoji = self.itens[slug][2]

        await inter.response.defer(ephemeral=True)

        # Itens que suportam múltiplos → mostra botões de quantidade (sem Sheets)
        if slug in SLUGS_MULTIPLOS and self.saldo >= preco:
            view_qtd = ViewQuantidade(self.author_id, slug, self.itens, self.is_cosm, self.saldo)
            await inter.edit_original_response(
                content=(
                    f"{emoji} **{label}** — `{formatar_moeda(preco)} MC` cada\n"
                    f"💰 Seu saldo: `{formatar_moeda(self.saldo)} MC`\n\n"
                    f"**Quantos deseja comprar?**"
                ),
                view=view_qtd
            )
        else:
            # Compra direta — 1 get_user_data + 1 batch_update
            msg = await processar_compra(inter, slug, self.itens, self.is_cosm)
            await inter.edit_original_response(content=msg)


# ══════════════════════════════════════════════════════════════════════════════
#  SELECT: CATEGORIA
# ══════════════════════════════════════════════════════════════════════════════

class SelectCategoria(disnake.ui.StringSelect):
    def __init__(self, author_id: int, saldo: float):
        self.author_id = author_id
        self.saldo     = saldo
        options = [
            disnake.SelectOption(label="📈 Progressão (Cargos)",   value="cargos",       emoji="📈", description="Evolua o cargo e aumente o salário"),
            disnake.SelectOption(label="🛡️ Equipamentos e Defesa",  value="equipamentos", emoji="🛡️", description="Escudo, Pé de Cabra, Seguro"),
            disnake.SelectOption(label="📦 Lootboxes",              value="lootboxes",    emoji="📦", description="Caixas com itens e cosméticos aleatórios"),
            disnake.SelectOption(label="😈 Sabotagem",              value="sabotagem",    emoji="😈", description="Itens para usar contra outros jogadores"),
            disnake.SelectOption(label="✨ Cosméticos — Comuns",    value="cosm_comum",   emoji="⚪", description="Cores e títulos básicos (500–1.500 MC)"),
            disnake.SelectOption(label="✨ Cosméticos — Raros",     value="cosm_raro",    emoji="🔵", description="Cores, molduras e títulos (2.000–2.500 MC)"),
            disnake.SelectOption(label="✨ Cosméticos — Épicos",    value="cosm_epico",   emoji="🟣", description="Visuais premium (6.000–8.000 MC)"),
        ]
        super().__init__(placeholder="🛒 Escolha uma categoria...", options=options)

    async def callback(self, inter: disnake.MessageInteraction):
        cat = self.values[0]
        embed, view = _build_categoria(self.author_id, self.saldo, cat)
        await inter.response.edit_message(embed=embed, view=view)


# ══════════════════════════════════════════════════════════════════════════════
#  BUILDER DE CATEGORIAS (puro — zero chamadas ao Sheets)
# ══════════════════════════════════════════════════════════════════════════════

def _build_categoria(author_id, saldo, cat):
    if cat == "cargos":
        itens = CATALOGO_CARGOS
        embed = disnake.Embed(title="📈 PROGRESSÃO — CARGOS",
                              description=f"💰 Saldo: **{formatar_moeda(saldo)} MC**\nSelecione o cargo desejado:",
                              color=disnake.Color.gold())
        for slug, (preco, label, emoji, desc) in itens.items():
            ok = "✅" if saldo >= preco else "❌"
            embed.add_field(name=f"{emoji} {label}", value=f"`{formatar_moeda(preco)} MC` {ok}\n*{desc}*", inline=True)
        is_cosm = False

    elif cat == "equipamentos":
        itens = CATALOGO_EQUIPAMENTOS
        embed = disnake.Embed(title="🛡️ EQUIPAMENTOS E DEFESA",
                              description=f"💰 Saldo: **{formatar_moeda(saldo)} MC**\nSelecione o item desejado:",
                              color=disnake.Color.blue())
        for slug, (preco, label, emoji, desc) in itens.items():
            ok = "✅" if saldo >= preco else "❌"
            embed.add_field(name=f"{emoji} {label}", value=f"`{formatar_moeda(preco)} MC` {ok}\n*{desc}*", inline=True)
        is_cosm = False

    elif cat == "lootboxes":
        itens = CATALOGO_LOOTBOXES
        embed = disnake.Embed(title="📦 LOOTBOXES — CONTRABANDO",
                              description=f"💰 Saldo: **{formatar_moeda(saldo)} MC**\nSelecione a caixa desejada:",
                              color=disnake.Color.dark_orange())
        for slug, (preco, label, emoji, desc) in itens.items():
            ok = "✅" if saldo >= preco else "❌"
            embed.add_field(name=f"{emoji} {label}", value=f"`{formatar_moeda(preco)} MC` {ok}\n*{desc}*", inline=False)
        embed.set_footer(text="!abrir caixote / !abrir baú / !abrir relíquia para usar")
        is_cosm = False

    elif cat == "sabotagem":
        itens = CATALOGO_SABOTAGEM
        embed = disnake.Embed(title="😈 SABOTAGEM — CONSUMÍVEIS",
                              description=f"💰 Saldo: **{formatar_moeda(saldo)} MC**\nSelecione o item desejado:",
                              color=disnake.Color.red())
        for slug, (preco, label, emoji, desc) in itens.items():
            ok = "✅" if saldo >= preco else "❌"
            embed.add_field(name=f"{emoji} {label}", value=f"`{formatar_moeda(preco)} MC` {ok}\n*{desc}*", inline=True)
        is_cosm = False

    else:
        raridade_map = {"cosm_comum": "Comum", "cosm_raro": "Raro", "cosm_epico": "Épico"}
        raridade = raridade_map.get(cat, "Comum")
        itens    = {k: v for k, v in COSMETICOS_LOJA.items() if v[3] == raridade}
        COR      = {"Comum": 0xAAAAAA, "Raro": 0x5B7FA6, "Épico": 0x9C27B0}
        EMJ      = {"Comum": "⚪",     "Raro": "🔵",     "Épico": "🟣"}
        embed = disnake.Embed(
            title=f"{EMJ.get(raridade,'✨')} COSMÉTICOS — {raridade.upper()}S",
            description=(f"💰 Saldo: **{formatar_moeda(saldo)} MC**\n"
                         "Selecione o cosmético desejado:\n"
                         "*Após comprar, use `!visuais` para equipar.*"),
            color=COR.get(raridade, 0xFFD700)
        )
        for slug, (preco, label, emoji, _) in itens.items():
            ok = "✅" if saldo >= preco else "❌"
            embed.add_field(name=f"{emoji} {label}", value=f"`{formatar_moeda(preco)} MC` {ok}", inline=True)
        embed.set_footer(text="🌟 Lendários só nas Relíquias Ancestrais!")
        is_cosm = True

    view = ViewItens(author_id, saldo, itens, cat, is_cosm=is_cosm)
    return embed, view


def _embed_inicio(saldo: float) -> disnake.Embed:
    embed = disnake.Embed(
        title="🛒 MERCADO NEGRO DA SELVA",
        description=(
            f"💰 Seu saldo: **{formatar_moeda(saldo)} MC**\n\n"
            "Escolha uma **categoria** no menu abaixo!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=disnake.Color.dark_theme()
    )
    embed.add_field(name="📈 Progressão",   value="Cargos que aumentam salário e limite de apostas",           inline=False)
    embed.add_field(name="🛡️ Equipamentos", value="Escudo · Pé de Cabra · Seguro",                             inline=False)
    embed.add_field(name="📦 Lootboxes",    value="Caixas com itens e cosméticos aleatórios",                   inline=False)
    embed.add_field(name="😈 Sabotagem",    value="Casca · Imposto · C4 · Energético · Fumaça · Nick",          inline=False)
    embed.add_field(name="✨ Cosméticos",   value="Cores, molduras e títulos · ⚪ Comuns · 🔵 Raros · 🟣 Épicos", inline=False)
    embed.set_footer(text="Selecione uma categoria para ver itens e preços  ·  !visuais para gerenciar cosméticos")
    return embed


# ══════════════════════════════════════════════════════════════════════════════
#  PORTAL E VIEWS
# ══════════════════════════════════════════════════════════════════════════════

class ViewItens(disnake.ui.View):
    def __init__(self, author_id: int, saldo: float, itens: dict, categoria: str, is_cosm: bool = False):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.saldo     = saldo
        self.add_item(SelectItem(author_id, saldo, itens, is_cosm=is_cosm))

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        if inter.author.id != self.author_id:
            await inter.response.send_message("❌ Esta loja é só sua! Use `!loja` para abrir a sua.", ephemeral=True)
            return False
        return True

    @disnake.ui.button(label="↩️ Voltar", style=disnake.ButtonStyle.secondary, row=1)
    async def btn_voltar(self, button, inter):
        embed = _embed_inicio(self.saldo)
        view  = ViewLoja(self.author_id, self.saldo)
        await inter.response.edit_message(embed=embed, view=view)

    @disnake.ui.button(label="❌ Fechar", style=disnake.ButtonStyle.danger, row=1)
    async def btn_fechar(self, button, inter):
        await inter.response.defer()
        await inter.delete_original_response()


class ViewLoja(disnake.ui.View):
    def __init__(self, author_id: int, saldo: float):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.add_item(SelectCategoria(author_id, saldo))

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        if inter.author.id != self.author_id:
            await inter.response.send_message("❌ Esta loja é só sua! Use `!loja` para abrir a sua.", ephemeral=True)
            return False
        return True

    @disnake.ui.button(label="❌ Fechar", style=disnake.ButtonStyle.danger, row=1)
    async def btn_fechar(self, button, inter):
        await inter.response.defer()
        await inter.delete_original_response()


class ViewPortalLoja(disnake.ui.View):
    """
    Portal público que abre a loja.
    Recebe o saldo já lido no !loja — elimina o get_user_data extra ao clicar.
    """
    def __init__(self, author_id: int, saldo: float):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.saldo     = saldo

    @disnake.ui.button(label="🛒 Abrir Mercado", style=disnake.ButtonStyle.success)
    async def btn_abrir(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id != self.author_id:
            return await inter.response.send_message(
                "❌ Esta loja não é sua! Digite `!loja` para abrir a sua.", ephemeral=True
            )
        # Saldo já em memória — zero chamadas ao Sheets aqui
        embed = _embed_inicio(self.saldo)
        view  = ViewLoja(inter.author.id, self.saldo)
        await inter.response.send_message(embed=embed, view=view, ephemeral=True)
        try:
            await inter.message.delete()
        except Exception:
            pass

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(
                content="⏳ O portal da loja fechou. Digite `!loja` novamente.", view=self
            )
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════════════════════════════════════

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal  = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, use a loja no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["shop", "mercado", "comprar", "cosmeticos"])
    async def loja(self, ctx):
        """Abre o portal para o mercado negro."""
        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Use `!trabalhar` primeiro para se registrar!")

            # Lê saldo aqui e passa para o portal — sem releitura ao clicar no botão
            saldo = db.parse_float(user["data"][2])
            view  = ViewPortalLoja(ctx.author.id, saldo)

            try:
                await ctx.message.delete()
            except (disnake.Forbidden, disnake.NotFound):
                pass

            view.message = await ctx.send(
                content=(f"🛒 {ctx.author.mention}, o Mercado Negro está pronto.\n"
                         f"Clique no botão abaixo para abrir a sua loja."),
                view=view
            )

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !loja de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")


def setup(bot):
    bot.add_cog(Shop(bot))