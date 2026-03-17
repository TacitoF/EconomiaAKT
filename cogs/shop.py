import disnake
from disnake.ext import commands
import database as db
import time

ESCUDO_CARGAS = 3

def formatar_moeda(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ── Preço dinâmico ────────────────────────────────────────────────────────────
# Itens de poder têm preço variável por demanda E por cargo do comprador.
# Cosméticos e cargos sempre têm preço fixo.

ITENS_PRECO_DINAMICO = {
    "item:escudo", "item:pe_de_cabra", "item:seguro",
    "item:casca", "item:imposto", "item:racao",
}

# Quanto cada cargo paga a mais (rico paga mais, pobre paga base)
MULTIPLICADOR_CARGO = {
    "Lêmure":      1.00,
    "Macaquinho":  1.10,
    "Babuíno":     1.22,
    "Chimpanzé":   1.38,
    "Orangutango": 1.58,
    "Gorila":      1.82,
    "Ancestral":   2.10,
    "Rei Símio":   2.45,
}

def preco_dinamico(slug: str, preco_base: float, cargo: str) -> tuple[float, str]:
    """
    Retorna (preco_final, indicador_tendencia).
    - Aplica multiplicador de cargo para itens de poder
    - Aplica variação de demanda (+3% por compra hoje, teto +80%, piso -40%)
    """
    if slug not in ITENS_PRECO_DINAMICO:
        return preco_base, ""

    # Multiplicador de cargo
    mult_cargo = MULTIPLICADOR_CARGO.get(cargo, 1.0)

    # Multiplicador de demanda
    compras = db.get_compras_item(slug)
    variacao_demanda = compras * 0.03
    mult_demanda = max(0.60, min(1.80, 1.0 + variacao_demanda))

    preco_final = round(preco_base * mult_cargo * mult_demanda, 2)

    # Indicador de tendência
    if mult_demanda >= 1.50:   tendencia = "🔥 Alta demanda"
    elif mult_demanda >= 1.20: tendencia = "📈 Em alta"
    elif mult_demanda <= 0.70: tendencia = "📉 Pouca procura"
    else:                      tendencia = ""

    return preco_final, tendencia

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

CATALOGO_CONSUMIVEIS = {
    "item:casca":      (300.0,  "Casca de Banana",  "🍌", "Atrasa o próximo trabalho do alvo"),
    "item:imposto":    (1500.0, "Imposto do Gorila", "🦍", "Rouba 25% dos próximos 5 trabalhos"),
    "item:troca_nick": (3000.0, "Troca de Nick",     "🪄", "Altera o apelido do alvo por 30min"),
    "item:racao":      (250.0,  "Ração Símia",       "🍗", "Restaura 50% da fome do seu mascote"),
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
    "item:casca":       "Casca de Banana",
    "item:imposto":     "Imposto do Gorila",
    "item:troca_nick":  "Troca de Nick",
    "item:racao":       "Ração Símia",
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
    "item:casca":       "Use `!casca @alvo` para jogar.",
    "item:imposto":     "Use `!taxar @alvo` para cobrar.",
    "item:troca_nick":  "Use `!apelidar @alvo <nick>` para renomear.",
    "item:pe_de_cabra": "Equipado automaticamente no `!roubar` — chance 65%.",
    "item:seguro":      "Ativado automaticamente se você for roubado.",
    "item:racao":       "Use `!alimentar` para saciar a fome do seu mascote.",
}

SLUGS_MULTIPLOS = set(CATALOGO_CONSUMIVEIS)

def _batch_compra(row: int, novo_saldo: float, nova_inv: list, col_extra: str = None, val_extra=None):
    inv_str = ", ".join(nova_inv) if nova_inv else "Nenhum"
    updates = [
        {"range": f"C{row}", "values": [[str(round(novo_saldo, 2))]]},
        {"range": f"F{row}", "values": [[inv_str]]},
    ]
    if col_extra:
        updates.append({"range": f"{col_extra}{row}", "values": [[str(val_extra)]]})
    db.sheet.batch_update(updates)

async def processar_compra(inter: disnake.MessageInteraction, slug: str, itens: dict, is_cosm: bool, quantidade: int = 1):
    dados = itens[slug]
    preco_base, label, emoji = dados[0], dados[1], dados[2]

    user = db.get_user_data(str(inter.author.id))
    if not user: return "❌ Conta não encontrada!"

    saldo    = db.parse_float(user["data"][2])
    cargo    = str(user["data"][3]) if len(user["data"]) > 3 else "Lêmure"
    row      = user["row"]
    inv_str  = str(user["data"][5]) if len(user["data"]) > 5 else ""
    inv_list = [i.strip() for i in inv_str.split(",") if i.strip() and i.strip().lower() != "nenhum"]

    # Aplica preço dinâmico (por cargo + demanda) apenas em itens de poder
    preco, tendencia = preco_dinamico(slug, preco_base, cargo)
    preco_total = preco * quantidade

    if saldo < preco_total:
        faltam = round(preco_total - saldo, 2)
        qtd_str = f" (×{quantidade})" if quantidade > 1 else ""
        tend_txt = f"\n{tendencia}" if tendencia else ""
        return f"❌ Saldo insuficiente!\nPrecisa de **{formatar_moeda(preco_total)} MC**{qtd_str} (faltam **{formatar_moeda(faltam)} MC**).{tend_txt}"

    if slug.startswith("cargo:"):
        nome_cargo = NOME_CARGO[slug]
        _batch_compra(row, saldo - preco, inv_list, col_extra="D", val_extra=nome_cargo)
        return f"🎉 Você evoluiu para o cargo **{emoji} {nome_cargo}**!\n💸 **-{formatar_moeda(preco)} MC** debitados."

    # Incrementa contador de demanda para itens de poder
    if slug in ITENS_PRECO_DINAMICO:
        db.incrementar_compras(slug, quantidade)

    if slug == "item:escudo":
        bot, uid, agora = inter.bot, str(inter.author.id), time.time()
        cargas_db, quebra_ts = db.get_escudo_data(user)
        if uid not in bot.escudos_ativos and cargas_db > 0: bot.escudos_ativos[uid] = cargas_db
        if "Escudo" in inv_list or bot.escudos_ativos.get(uid, 0) > 0:
            return "❌ Você já tem um **Escudo**! Só pode ter 1 de cada vez."
        if quebra_ts > 0 and (agora - quebra_ts < 86400):
            return f"⏳ O seu último **Escudo** foi destruído recentemente! Compre outro <t:{int(quebra_ts + 86400)}:R>."

        bot.escudo_compras[uid] = (1, agora)
        inv_list.append("Escudo")
        _batch_compra(row, saldo - preco, inv_list, col_extra="L", val_extra="")
        return f"🛡️ **Escudo** comprado e guardado!\n💸 **-{formatar_moeda(preco)} MC** debitados.\n💡 Use `!escudo` para ativar e proteger-se contra 3 tentativas de roubo."

    if is_cosm:
        chave_inv = f"cosmético:{slug}"
        if chave_inv in inv_list: return f"❌ Você já tem **{emoji} {label}**!\nUse `!visuais`."
        inv_list.append(chave_inv)
        _batch_compra(row, saldo - preco, inv_list)
        return f"✨ **{emoji} {label}** comprado!\n💸 **-{formatar_moeda(preco)} MC**."

    nome_item = NOME_ITEM.get(slug, label)
    inv_list.extend([nome_item] * quantidade)
    _batch_compra(row, saldo - preco_total, inv_list)
    tend_txt = f"\n{tendencia}" if tendencia else ""
    dica = f"\n💡 {DICA_ITEM[slug]}" if slug in DICA_ITEM else ""
    return f"{emoji} **×{quantidade} {nome_item}** comprado{'s' if quantidade > 1 else ''}!\n💸 **-{formatar_moeda(preco_total)} MC**.{tend_txt}{dica}"

class _BotaoQtd(disnake.ui.Button):
    def __init__(self, qtd: int, pode: bool):
        super().__init__(label=f"×{qtd}", style=disnake.ButtonStyle.success if pode else disnake.ButtonStyle.secondary, disabled=not pode, custom_id=f"qtd_{qtd}", row=0)
        self.qtd = qtd
    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.defer(ephemeral=True)
        msg = await processar_compra(inter, self.view.slug, self.view.itens, self.view.is_cosm, quantidade=self.qtd)
        await inter.edit_original_response(content=msg, view=None)

class ViewQuantidade(disnake.ui.View):
    def __init__(self, author_id: int, slug: str, itens: dict, is_cosm: bool, saldo: float):
        super().__init__(timeout=60)
        self.author_id, self.slug, self.itens, self.is_cosm = author_id, slug, itens, is_cosm
        for qtd in [1, 3, 5, 10]: self.add_item(_BotaoQtd(qtd, pode=saldo >= itens[slug][0] * qtd))
    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        if inter.author.id != self.author_id:
            await inter.response.send_message("❌ Esta loja é só sua!", ephemeral=True)
            return False
        return True

class SelectItem(disnake.ui.StringSelect):
    def __init__(self, author_id: int, saldo: float, itens: dict, is_cosm: bool = False):
        self.author_id, self.saldo, self.itens, self.is_cosm = author_id, saldo, itens, is_cosm
        opts = [disnake.SelectOption(label=v[1][:100], description=f"{formatar_moeda(v[0])} MC — {'✅' if saldo >= v[0] else '❌'}", value=k, emoji=v[2]) for k, v in itens.items()]
        super().__init__(placeholder="🛒 Selecione o item...", options=opts[:25])
    async def callback(self, inter: disnake.MessageInteraction):
        slug, preco, label, emoji = self.values[0], self.itens[self.values[0]][0], self.itens[self.values[0]][1], self.itens[self.values[0]][2]
        await inter.response.defer(ephemeral=True)
        if slug in SLUGS_MULTIPLOS and self.saldo >= preco:
            await inter.edit_original_response(content=f"{emoji} **{label}** — `{formatar_moeda(preco)} MC` cada\n**Quantos deseja?**", view=ViewQuantidade(self.author_id, slug, self.itens, self.is_cosm, self.saldo))
        else:
            msg = await processar_compra(inter, slug, self.itens, self.is_cosm)
            await inter.edit_original_response(content=msg)

class SelectCategoria(disnake.ui.StringSelect):
    def __init__(self, author_id: int, saldo: float):
        self.author_id, self.saldo = author_id, saldo
        opts = [
            disnake.SelectOption(label="📈 Progressão (Cargos)",   value="cargos",       emoji="📈", description="Evolua o cargo"),
            disnake.SelectOption(label="🛡️ Equipamentos e Defesa",  value="equipamentos", emoji="🛡️", description="Escudo, Pé de Cabra"),
            disnake.SelectOption(label="😈 Sabotagem & Pets",       value="consumiveis",  emoji="😈", description="Casca, Imposto, Ração"),
            disnake.SelectOption(label="✨ Cosméticos — Comuns",    value="cosm_comum",   emoji="⚪", description="500–1.500 MC"),
            disnake.SelectOption(label="✨ Cosméticos — Raros",     value="cosm_raro",    emoji="🔵", description="2.000–2.500 MC"),
            disnake.SelectOption(label="✨ Cosméticos — Épicos",    value="cosm_epico",   emoji="🟣", description="6.000–8.000 MC"),
        ]
        super().__init__(placeholder="🛒 Escolha uma categoria...", options=opts)
    async def callback(self, inter: disnake.MessageInteraction):
        cat = self.values[0]
        embed, view = _build_categoria(self.author_id, self.saldo, cat)
        await inter.response.edit_message(embed=embed, view=view)

def _build_categoria(author_id, saldo, cat):
    is_cosm = False
    if cat == "cargos": itens, emb = CATALOGO_CARGOS, disnake.Embed(title="📈 CARGOS", color=disnake.Color.gold())
    elif cat == "equipamentos": itens, emb = CATALOGO_EQUIPAMENTOS, disnake.Embed(title="🛡️ EQUIPAMENTOS", color=disnake.Color.blue())
    elif cat == "consumiveis": itens, emb = CATALOGO_CONSUMIVEIS, disnake.Embed(title="😈 SABOTAGEM & MASCOTES", color=disnake.Color.red())
    else:
        rm = {"cosm_comum": "Comum", "cosm_raro": "Raro", "cosm_epico": "Épico"}
        raridade = rm.get(cat, "Comum")
        itens = {k: v for k, v in COSMETICOS_LOJA.items() if v[3] == raridade}
        emb = disnake.Embed(title=f"✨ COSMÉTICOS {raridade.upper()}", color=0xFFD700)
        is_cosm = True

    emb.description = f"💰 Saldo: **{formatar_moeda(saldo)} MC**\nSelecione abaixo:"
    # Para itens de poder, mostra o preço real do cargo do usuário
    user_tmp = db.get_user_data(str(author_id))
    cargo_tmp = str(user_tmp["data"][3]) if user_tmp and len(user_tmp["data"]) > 3 else "Lêmure"
    for slug, (p, l, e, d) in itens.items():
        p_real, tend = preco_dinamico(slug, p, cargo_tmp)
        tend_str = f" {tend}" if tend else ""
        if not is_cosm:
            emb.add_field(name=f"{e} {l}", value=f"`{formatar_moeda(p_real)} MC` {'✅' if saldo >= p_real else '❌'}{tend_str}\n*{d}*", inline=True)
        else:
            emb.add_field(name=f"{e} {l}", value=f"`{formatar_moeda(p_real)} MC` {'✅' if saldo >= p_real else '❌'}", inline=True)
    return emb, ViewItens(author_id, saldo, itens, cat, is_cosm=is_cosm)

def _embed_inicio(saldo: float) -> disnake.Embed:
    embed = disnake.Embed(title="🛒 MERCADO NEGRO", description=f"💰 Seu saldo: **{formatar_moeda(saldo)} MC**\nEscolha uma categoria!", color=disnake.Color.dark_theme())
    embed.add_field(name="📈 Progressão",   value="Cargos que aumentam salário e limite de apostas", inline=False)
    embed.add_field(name="🛡️ Equipamentos", value="Escudo · Pé de Cabra · Seguro", inline=False)
    embed.add_field(name="😈 Sabotagem & Pets",value="Casca · Imposto · Troca de Nick · Ração Símia", inline=False)
    embed.add_field(name="✨ Cosméticos",   value="Cores, molduras e títulos", inline=False)
    return embed

class ViewItens(disnake.ui.View):
    def __init__(self, author_id, saldo, itens, categoria, is_cosm=False):
        super().__init__(timeout=120)
        self.author_id, self.saldo = author_id, saldo
        self.add_item(SelectItem(author_id, saldo, itens, is_cosm=is_cosm))
    async def interaction_check(self, inter): return inter.author.id == self.author_id
    @disnake.ui.button(label="↩️ Voltar", style=disnake.ButtonStyle.secondary, row=1)
    async def btn_v(self, b, i): await i.response.edit_message(embed=_embed_inicio(self.saldo), view=ViewLoja(self.author_id, self.saldo))
    @disnake.ui.button(label="❌ Fechar", style=disnake.ButtonStyle.danger, row=1)
    async def btn_f(self, b, i): await i.response.defer(); await i.delete_original_response()

class ViewLoja(disnake.ui.View):
    def __init__(self, author_id, saldo):
        super().__init__(timeout=120)
        self.author_id, self.saldo = author_id, saldo
        self.add_item(SelectCategoria(author_id, saldo))
    async def interaction_check(self, inter): return inter.author.id == self.author_id
    @disnake.ui.button(label="❌ Fechar", style=disnake.ButtonStyle.danger, row=1)
    async def btn_f(self, b, i): await i.response.defer(); await i.delete_original_response()

class ViewPortalLoja(disnake.ui.View):
    def __init__(self, author_id, saldo):
        super().__init__(timeout=60)
        self.author_id, self.saldo = author_id, saldo
    @disnake.ui.button(label="🛒 Abrir Mercado", style=disnake.ButtonStyle.success)
    async def btn_abrir(self, b, inter):
        if inter.author.id != self.author_id: return await inter.response.send_message("❌ Use `!loja`.", ephemeral=True)
        await inter.response.send_message(embed=_embed_inicio(self.saldo), view=ViewLoja(inter.author.id, self.saldo), ephemeral=True)
        try: await inter.message.delete()
        except: pass
    async def on_timeout(self):
        for item in self.children: item.disabled = True
        try: await self.message.edit(content="⏳ O portal da loja fechou.", view=self)
        except: pass

class Shop(commands.Cog):
    def __init__(self, bot): self.bot = bot
    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・コングイトス')
            mencao = canal.mention if canal else "#🐒・コングイトス"
            await ctx.send(f"⚠️ {ctx.author.mention}, a loja fica no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")
    @commands.command(aliases=["shop", "mercado", "comprar"])
    async def loja(self, ctx):
        user = db.get_user_data(str(ctx.author.id))
        if not user: return await ctx.send("❌ Use `!trabalhar` primeiro!")
        saldo = db.parse_float(user["data"][2])
        view = ViewPortalLoja(ctx.author.id, saldo)
        try: await ctx.message.delete()
        except: pass
        view.message = await ctx.send(content=f"🛒 {ctx.author.mention}, o Mercado Negro está pronto.", view=view)

def setup(bot): bot.add_cog(Shop(bot))