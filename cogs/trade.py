import disnake
from disnake.ext import commands
import database as db
import uuid

# Itens que NÃO podem ser negociados entre jogadores
ITENS_INTRANSFERÍVEIS = {
    "Escudo",           # item de estado ativo — tem lógica de CD própria
    "Pé de Cabra",      # equipado automaticamente, lógica no !roubar
    "Seguro",           # ativado automaticamente ao ser roubado
}

# Passivos reconhecidos (mesma lista do items.py)
PASSIVOS_NOMES = {
    "Amuleto da Sorte", "Cinto de Ferramentas", "Carteira Velha",
    "Segurança Particular", "Luvas de Seda", "Sindicato", "Cão de Guarda",
    "Relíquia do Ancião", "Escudo de Sangue", "Manto das Sombras", "Talismã da Fortuna",
}

def formatar_moeda(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Propostas de venda pendentes: {proposta_id: dict}
_propostas: dict[str, dict] = {}

# Propostas de troca pendentes: {troca_id: dict}
_trocas: dict[str, dict] = {}


# ──────────────────────────────────────────────────────────────────────────────
#  VENDA — View de confirmação para o COMPRADOR
#  Anti-scam: o comprador vê o item E o preço antes de confirmar
# ──────────────────────────────────────────────────────────────────────────────

class ViewConfirmarCompra(disnake.ui.View):
    def __init__(self, proposta_id: str):
        super().__init__(timeout=60)
        self.proposta_id = proposta_id

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        proposta = _propostas.get(self.proposta_id)
        if not proposta:
            await inter.response.send_message("❌ Esta proposta expirou.", ephemeral=True)
            return False
        if inter.author.id != proposta["comprador_id"]:
            await inter.response.send_message("❌ Esta proposta não é para você.", ephemeral=True)
            return False
        return True

    @disnake.ui.button(label="✅ Aceitar e Pagar", style=disnake.ButtonStyle.success)
    async def btn_aceitar(self, button, inter: disnake.MessageInteraction):
        proposta = _propostas.pop(self.proposta_id, None)
        if not proposta:
            return await inter.response.send_message("❌ Proposta expirou ou já foi processada.", ephemeral=True)

        vendedor_id  = str(proposta["vendedor_id"])
        comprador_id = str(proposta["comprador_id"])
        item         = proposta["item"]
        preco        = proposta["preco"]

        # Revalida tudo no momento do aceite
        vendedor_db  = db.get_user_data(vendedor_id)
        comprador_db = db.get_user_data(comprador_id)

        if not vendedor_db or not comprador_db:
            return await inter.response.send_message("❌ Conta não encontrada. Transação cancelada.", ephemeral=True)

        # Verifica se vendedor ainda tem o item
        inv_vendedor = [i.strip() for i in str(vendedor_db["data"][5]).split(",") if i.strip() and i.lower() != "nenhum"]
        if item not in inv_vendedor:
            return await inter.response.send_message(
                f"❌ **{proposta['vendedor_nome']}** não tem mais **{item}** no inventário. Transação cancelada.",
                ephemeral=True
            )

        # Verifica se comprador tem saldo
        saldo_comprador = db.parse_float(comprador_db["data"][2])
        if saldo_comprador < preco:
            faltam = round(preco - saldo_comprador, 2)
            return await inter.response.send_message(
                f"❌ Saldo insuficiente! Faltam **{formatar_moeda(faltam)} MC**.",
                ephemeral=True
            )

        # ── Executa a transferência ──
        # 1. Remove item do vendedor e desequipa se for passivo equipado
        inv_vendedor.remove(item)
        db.update_value(vendedor_db["row"], 6, ", ".join(inv_vendedor) if inv_vendedor else "Nenhum")
        
        # Limpa nome caso o passivo tenha 🔒 para poder desequipar corretamente
        item_base = item.replace("🔒", "").strip()
        if item_base in PASSIVOS_NOMES:
            passivos_v = db.get_passivos(vendedor_db)
            if item in passivos_v:
                passivos_v.remove(item)
                db.set_passivos(vendedor_db["row"], passivos_v)

        # 2. Adiciona item ao comprador
        inv_comprador = [i.strip() for i in str(comprador_db["data"][5]).split(",") if i.strip() and i.lower() != "nenhum"]
        inv_comprador.append(item)
        db.update_value(comprador_db["row"], 6, ", ".join(inv_comprador))

        # 3. Transfere MC
        saldo_vendedor = db.parse_float(vendedor_db["data"][2])
        db.update_value(vendedor_db["row"], 3, round(saldo_vendedor + preco, 2))
        db.update_value(comprador_db["row"], 3, round(saldo_comprador - preco, 2))

        self.stop()
        for child in self.children:
            child.disabled = True

        embed = disnake.Embed(
            title="🤝 NEGÓCIO FECHADO!",
            description=(
                f"**Item:** `{item}`\n"
                f"**Vendedor:** {proposta['vendedor_nome']} → `+{formatar_moeda(preco)} MC`\n"
                f"**Comprador:** {inter.author.mention} → `-{formatar_moeda(preco)} MC`"
            ),
            color=disnake.Color.green()
        )
        await inter.response.edit_message(embed=embed, view=self)

    @disnake.ui.button(label="❌ Recusar", style=disnake.ButtonStyle.danger)
    async def btn_recusar(self, button, inter: disnake.MessageInteraction):
        _propostas.pop(self.proposta_id, None)
        self.stop()
        await inter.response.edit_message(
            content=f"❌ {inter.author.mention} recusou a proposta.",
            embed=None, view=None
        )

    async def on_timeout(self):
        _propostas.pop(self.proposta_id, None)
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(content="⏳ Proposta expirou.", embed=None, view=self)
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
#  TROCA DIRETA — ambos os lados veem exatamente o que estão trocando
#  Anti-scam:
#    1. Proponente declara seu(s) item(ns) + item do alvo
#    2. Alvo vê embed claro com "você dá X e recebe Y" antes de confirmar
#    3. No aceite, revalida inventários dos dois lados em tempo real
# ──────────────────────────────────────────────────────────────────────────────

class ViewConfirmarTroca(disnake.ui.View):
    def __init__(self, troca_id: str):
        super().__init__(timeout=90)
        self.troca_id = troca_id

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        troca = _trocas.get(self.troca_id)
        if not troca:
            await inter.response.send_message("❌ Esta proposta de troca expirou.", ephemeral=True)
            return False
        if inter.author.id != troca["alvo_id"]:
            await inter.response.send_message("❌ Esta proposta não é para você.", ephemeral=True)
            return False
        return True

    @disnake.ui.button(label="✅ Aceitar troca", style=disnake.ButtonStyle.success)
    async def btn_aceitar(self, button, inter: disnake.MessageInteraction):
        troca = _trocas.pop(self.troca_id, None)
        if not troca:
            return await inter.response.send_message("❌ Proposta expirou ou já foi processada.", ephemeral=True)

        prop_id     = str(troca["proponente_id"])
        alvo_id     = str(troca["alvo_id"])
        itens_prop  = troca["itens_proponente"]   # lista de strings
        item_alvo   = troca["item_alvo"]           # string única

        prop_db = db.get_user_data(prop_id)
        alvo_db = db.get_user_data(alvo_id)

        if not prop_db or not alvo_db:
            return await inter.response.send_message("❌ Conta não encontrada. Troca cancelada.", ephemeral=True)

        inv_prop = [i.strip() for i in str(prop_db["data"][5]).split(",") if i.strip() and i.lower() != "nenhum"]
        inv_alvo = [i.strip() for i in str(alvo_db["data"][5]).split(",") if i.strip() and i.lower() != "nenhum"]

        # Revalida: proponente ainda tem todos os itens prometidos?
        inv_prop_temp = list(inv_prop)
        for it in itens_prop:
            if it not in inv_prop_temp:
                return await inter.response.send_message(
                    f"❌ **{troca['proponente_nome']}** não tem mais **{it}** no inventário. Troca cancelada.",
                    ephemeral=True
                )
            inv_prop_temp.remove(it)

        # Revalida: alvo ainda tem o item prometido?
        if item_alvo not in inv_alvo:
            return await inter.response.send_message(
                f"❌ Você não tem mais **{item_alvo}** no inventário. Troca cancelada.",
                ephemeral=True
            )

        # ── Executa a troca ──
        # Remove itens do proponente (e desequipa passivos se necessário)
        for it in itens_prop:
            inv_prop.remove(it)
            item_base = it.replace("🔒", "").strip()
            if item_base in PASSIVOS_NOMES:
                passivos_p = db.get_passivos(prop_db)
                if it in passivos_p:
                    passivos_p.remove(it)
                    db.set_passivos(prop_db["row"], passivos_p)

        # Remove item do alvo (e desequipa passivo se necessário)
        inv_alvo.remove(item_alvo)
        item_alvo_base = item_alvo.replace("🔒", "").strip()
        if item_alvo_base in PASSIVOS_NOMES:
            passivos_a = db.get_passivos(alvo_db)
            if item_alvo in passivos_a:
                passivos_a.remove(item_alvo)
                db.set_passivos(alvo_db["row"], passivos_a)

        # Adiciona itens do proponente ao alvo
        for it in itens_prop:
            inv_alvo.append(it)

        # Adiciona item do alvo ao proponente
        inv_prop.append(item_alvo)

        # Grava nos dois lados
        db.update_value(prop_db["row"], 6, ", ".join(inv_prop) if inv_prop else "Nenhum")
        db.update_value(alvo_db["row"], 6, ", ".join(inv_alvo) if inv_alvo else "Nenhum")

        self.stop()
        for child in self.children:
            child.disabled = True

        itens_prop_fmt = " + ".join(f"`{i}`" for i in itens_prop)
        embed = disnake.Embed(
            title="🔄 TROCA CONCLUÍDA!",
            description=(
                f"**{troca['proponente_nome']}** deu: {itens_prop_fmt}\n"
                f"**{inter.author.mention}** deu: `{item_alvo}`"
            ),
            color=disnake.Color.green()
        )
        embed.set_footer(text="Passivos desequipados automaticamente se necessário.")
        await inter.response.edit_message(embed=embed, view=self)

    @disnake.ui.button(label="❌ Recusar", style=disnake.ButtonStyle.danger)
    async def btn_recusar(self, button, inter: disnake.MessageInteraction):
        troca = _trocas.pop(self.troca_id, None)
        self.stop()
        nome_prop = troca["proponente_nome"] if troca else "o proponente"
        await inter.response.edit_message(
            content=f"❌ {inter.author.mention} recusou a troca proposta por {nome_prop}.",
            embed=None, view=None
        )

    async def on_timeout(self):
        _trocas.pop(self.troca_id, None)
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(content="⏳ Proposta de troca expirou.", embed=None, view=self)
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
#  REEMBOLSO ao sistema
# ──────────────────────────────────────────────────────────────────────────────

ITENS_REEMBOLSAVEIS = {
    "Escudo":              ("item:escudo",      1000.0),
    "Pé de Cabra":         ("item:pe_de_cabra", 1200.0),
    "Seguro":              ("item:seguro",       950.0),
    "Casca de Banana":     ("item:casca",        300.0),
    "Imposto do Gorila":   ("item:imposto",     1500.0),
    "Troca de Nick":       ("item:troca_nick",  3000.0),
    "Ração Símia":         ("item:racao",        250.0),
    # Passivos também são reembolsáveis (valor base fixo)
    "Amuleto da Sorte":     ("passivo:amuleto",   800.0),
    "Cinto de Ferramentas": ("passivo:cinto",      800.0),
    "Carteira Velha":       ("passivo:carteira",   800.0),
    "Segurança Particular": ("passivo:seguranca", 2000.0),
    "Luvas de Seda":        ("passivo:luvas",     2000.0),
    "Sindicato":            ("passivo:sindicato", 2000.0),
    "Cão de Guarda":        ("passivo:cao",       2000.0),
    "Relíquia do Ancião":   ("passivo:reliquia",  5000.0),
    "Escudo de Sangue":     ("passivo:esangue",   5000.0),
    "Manto das Sombras":    ("passivo:manto",     5000.0),
    "Talismã da Fortuna":   ("passivo:talismo",   5000.0),
}
TAXA_REEMBOLSO = 1.0


class ViewConfirmarReembolso(disnake.ui.View):
    def __init__(self, autor: disnake.Member, item: str, valor: float, user_row: int, inv_list: list):
        super().__init__(timeout=30)
        self.autor    = autor
        self.item     = item
        self.valor    = valor
        self.user_row = user_row
        self.inv_list = list(inv_list)

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        if inter.author.id != self.autor.id:
            await inter.response.send_message("❌ Esta confirmação não é sua!", ephemeral=True)
            return False
        return True

    @disnake.ui.button(label="✅ Confirmar devolução", style=disnake.ButtonStyle.success)
    async def btn_confirmar(self, button, inter: disnake.MessageInteraction):
        user_db = db.get_user_data(str(self.autor.id))
        if not user_db:
            return await inter.response.send_message("❌ Conta não encontrada!", ephemeral=True)

        inv_atual = [i.strip() for i in str(user_db["data"][5]).split(",") if i.strip() and i.lower() != "nenhum"]
        if self.item not in inv_atual:
            self.stop()
            return await inter.response.edit_message(
                content=f"❌ **{self.item}** não está mais no seu inventário.",
                embed=None, view=None
            )

        inv_atual.remove(self.item)
        db.update_value(user_db["row"], 6, ", ".join(inv_atual) if inv_atual else "Nenhum")

        # Se for passivo equipado, desequipa automaticamente
        item_base = self.item.replace("🔒", "").strip()
        if item_base in PASSIVOS_NOMES:
            passivos = db.get_passivos(user_db)
            if self.item in passivos:
                passivos.remove(self.item)
                db.set_passivos(user_db["row"], passivos)

        saldo_atual = db.parse_float(user_db["data"][2])
        db.update_value(user_db["row"], 3, round(saldo_atual + self.valor, 2))

        self.stop()
        for child in self.children:
            child.disabled = True

        embed = disnake.Embed(
            title="♻️ ITEM DEVOLVIDO!",
            description=(
                f"**Item:** `{self.item}`\n"
                f"**Reembolso:** `+{formatar_moeda(self.valor)} MC` *(100% do preço base)*\n"
                f"**Novo saldo:** `{formatar_moeda(round(saldo_atual + self.valor, 2))} MC`"
            ),
            color=disnake.Color.blurple()
        )
        await inter.response.edit_message(embed=embed, view=self)

    @disnake.ui.button(label="❌ Cancelar", style=disnake.ButtonStyle.secondary)
    async def btn_cancelar(self, button, inter: disnake.MessageInteraction):
        self.stop()
        await inter.response.edit_message(
            content="↩️ Devolução cancelada. O item continua no seu inventário.",
            embed=None, view=None
        )

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(content="⏳ Confirmação expirou.", embed=None, view=self)
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _inv_transferivel(inv_list: list) -> list:
    """Retorna apenas itens que podem ser negociados (ignora cosméticos, intransferíveis e vinculados com 🔒)."""
    return [
        i for i in inv_list
        if not i.startswith("cosmético:")
        and not i.startswith("cosmetico:")
        and i not in ITENS_INTRANSFERÍVEIS
        and "🔒" not in i
    ]

def _embed_troca(
    proponente: disnake.Member,
    alvo: disnake.Member,
    itens_prop: list,
    item_alvo: str,
) -> disnake.Embed:
    """Embed anti-scam que o alvo vê antes de aceitar."""
    itens_prop_fmt = " + ".join(f"`{i}`" for i in itens_prop)
    embed = disnake.Embed(
        title="🔄 PROPOSTA DE TROCA",
        color=disnake.Color.gold()
    )
    embed.set_author(name=proponente.display_name, icon_url=proponente.display_avatar.url)
    embed.add_field(
        name=f"📤 {proponente.display_name} oferece",
        value=itens_prop_fmt,
        inline=False
    )
    embed.add_field(
        name=f"📥 {alvo.display_name} dá em troca",
        value=f"`{item_alvo}`",
        inline=False
    )
    embed.add_field(
        name="⚠️ Leia com atenção",
        value=(
            "Você está trocando **exatamente** os itens acima.\n"
            "Nenhum MC é transferido nesta operação.\n"
            "A troca é **irreversível** após confirmação."
        ),
        inline=False
    )
    embed.set_footer(text="Expira em 90 segundos.")
    return embed


# ──────────────────────────────────────────────────────────────────────────────
#  Cog principal
# ──────────────────────────────────────────────────────────────────────────────

class Trade(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != "🐒・conguitos":
            canal = disnake.utils.get(ctx.guild.channels, name="🐒・conguitos")
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, negociações apenas no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    # ──────────────────────────────────────────────────────────────────────────
    #  !vender
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command(aliases=["negociar", "comercio"])
    async def vender(self, ctx, *, args: str = ""):
        """
        !vender @usuario <item> <preço>  → proposta para jogador
        !vender <item>                   → vende ao sistema pelo preço base
        """
        if not args.strip():
            return await ctx.send(
                f"⚠️ {ctx.author.mention}, uso:\n"
                f"• Vender para jogador: `!vender @usuario <item> <preço>`\n"
                f"• Vender ao sistema: `!vender <item>`\n"
                f"• Trocar sem MC: `!trocar @usuario <seu item> por <item do alvo>`\n"
                f"*Use `!inventario` para ver seus itens.*"
            )

        tem_mencao = bool(ctx.message.mentions)

        if tem_mencao:
            comprador = ctx.message.mentions[0]

            resto = args
            for fmt in [f"<@{comprador.id}>", f"<@!{comprador.id}>"]:
                resto = resto.replace(fmt, "").strip()

            partes = resto.rsplit(None, 1)
            if len(partes) != 2:
                return await ctx.send(
                    f"⚠️ {ctx.author.mention}, uso: `!vender @usuario <item> <preço>`\n"
                    f"Exemplo: `!vender @João Imposto do Gorila 1000`"
                )
            try:
                preco = float(partes[1].replace(",", "."))
                item  = partes[0].strip()
            except ValueError:
                return await ctx.send(
                    f"⚠️ {ctx.author.mention}, o preço precisa ser um número.\n"
                    f"Exemplo: `!vender @João Imposto do Gorila 1000`"
                )

            if comprador.id == ctx.author.id:
                return await ctx.send(f"🐒 {ctx.author.mention}, não pode vender para si mesmo!")
            if comprador.bot:
                return await ctx.send("🤖 Bots não compram itens!")
            if preco <= 0:
                return await ctx.send("❌ O preço precisa ser maior que zero!")

            preco = round(preco, 2)

            try:
                vendedor_db = db.get_user_data(str(ctx.author.id))
                if not vendedor_db:
                    return await ctx.send("❌ Você não tem conta!")

                inv_str  = str(vendedor_db["data"][5]) if len(vendedor_db["data"]) > 5 else ""
                inv_list = [i.strip() for i in inv_str.split(",") if i.strip() and i.lower() != "nenhum"]

                item_encontrado = None
                for inv_item in inv_list:
                    if item.lower() in inv_item.lower():
                        item_encontrado = inv_item
                        break

                if not item_encontrado:
                    itens_fmt = "\n".join(f"• {i}" for i in _inv_transferivel(inv_list)) or "*Inventário vazio*"
                    return await ctx.send(
                        f"❌ **{item}** não encontrado no seu inventário!\n\n"
                        f"**Seus itens negociáveis:**\n{itens_fmt}"
                    )

                if item_encontrado in ITENS_INTRANSFERÍVEIS:
                    return await ctx.send(
                        f"❌ **{item_encontrado}** não pode ser vendido entre jogadores pois tem lógica de estado ativo."
                    )

                # 🔒 TRAVA DE VINCULAÇÃO DE ITEM
                if "🔒" in item_encontrado:
                    return await ctx.send(
                        f"❌ **{item_encontrado}** está vinculado à sua conta e não pode ser negociado!"
                    )

                comprador_db = db.get_user_data(str(comprador.id))
                if not comprador_db:
                    return await ctx.send(f"❌ {comprador.mention} não tem conta registrada!")

                saldo_comprador = db.parse_float(comprador_db["data"][2])

                proposta_id = str(uuid.uuid4())[:8]
                _propostas[proposta_id] = {
                    "vendedor_id":   ctx.author.id,
                    "vendedor_nome": ctx.author.mention,
                    "comprador_id":  comprador.id,
                    "item":          item_encontrado,
                    "preco":         preco,
                }

                # Embed anti-scam: comprador vê item e preço claramente em campos separados
                embed = disnake.Embed(
                    title="🏪 PROPOSTA DE VENDA",
                    color=disnake.Color.gold()
                )
                embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
                embed.add_field(name="📦 Item",   value=f"`{item_encontrado}`",          inline=True)
                embed.add_field(name="💰 Preço",  value=f"`{formatar_moeda(preco)} MC`", inline=True)
                embed.add_field(
                    name="💳 Seu saldo",
                    value=f"`{formatar_moeda(saldo_comprador)} MC` {'✅' if saldo_comprador >= preco else '❌ insuficiente'}",
                    inline=True
                )
                embed.add_field(
                    name="⚠️ Atenção",
                    value=(
                        f"{comprador.mention}, você está comprando **`{item_encontrado}`** "
                        f"por **`{formatar_moeda(preco)} MC`**.\n"
                        f"Confirme apenas se concordar com o preço e o item."
                    ),
                    inline=False
                )
                embed.set_footer(text="Expira em 60 segundos.")

                view = ViewConfirmarCompra(proposta_id)
                view.message = await ctx.send(embed=embed, view=view)

            except commands.CommandError:
                raise
            except Exception as e:
                print(f"❌ Erro no !vender (jogador) de {ctx.author}: {e}")
                await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

        else:
            await self._vender_sistema(ctx, args.strip())

    async def _vender_sistema(self, ctx, item: str):
        """Vende um item ao sistema pelo preço base."""
        try:
            user_db = db.get_user_data(str(ctx.author.id))
            if not user_db:
                return await ctx.send("❌ Você não tem conta!")

            inv_str  = str(user_db["data"][5]) if len(user_db["data"]) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(",") if i.strip() and i.lower() != "nenhum"]
            inv_list = [i for i in inv_list if not i.startswith("cosmético:") and not i.startswith("cosmetico:")]

            item_encontrado = None
            for inv_item in inv_list:
                if item.lower() in inv_item.lower():
                    item_encontrado = inv_item
                    break

            if not item_encontrado:
                itens_fmt = "\n".join(f"• {i}" for i in inv_list) if inv_list else "*Inventário vazio*"
                return await ctx.send(
                    f"❌ **{item}** não encontrado no seu inventário!\n\n"
                    f"**Seus itens:**\n{itens_fmt}"
                )

            # 🔒 TRAVA DE VINCULAÇÃO DE ITEM
            if "🔒" in item_encontrado:
                return await ctx.send(
                    f"❌ **{item_encontrado}** está vinculado à sua conta e não pode ser devolvido ao sistema!"
                )

            if item_encontrado not in ITENS_REEMBOLSAVEIS:
                return await ctx.send(
                    f"❌ **{item_encontrado}** não pode ser vendido ao sistema.\n"
                    f"Cosméticos, cargos e caixas não são reembolsáveis.\n"
                    f"Tente vender para outro jogador: `!vender @usuario {item_encontrado} <preço>`\n"
                    f"Ou trocar: `!trocar @usuario {item_encontrado} por <item do alvo>`"
                )

            _, preco_base = ITENS_REEMBOLSAVEIS[item_encontrado]
            valor_reembolso = round(preco_base * TAXA_REEMBOLSO, 2)

            embed = disnake.Embed(
                title="♻️ VENDER AO SISTEMA?",
                description=(
                    f"**Item:** `{item_encontrado}`\n"
                    f"**Você recebe:** `{formatar_moeda(valor_reembolso)} MC` *(preço base)*\n\n"
                    f"⚠️ Esta ação é **irreversível**. O item será removido do seu inventário."
                ),
                color=disnake.Color.orange()
            )
            embed.set_footer(text="Expira em 30 segundos.")

            view = ViewConfirmarReembolso(ctx.author, item_encontrado, valor_reembolso, user_db["row"], inv_list)
            view.message = await ctx.send(embed=embed, view=view)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !vender sistema de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    @vender.error
    async def vender_error(self, ctx, error):
        if isinstance(error, commands.CommandError):
            raise error
        print(f"❌ Erro inesperado no !vender: {error}")
        await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ──────────────────────────────────────────────────────────────────────────
    #  !trocar — troca de itens sem MC
    #  Uso: !trocar @usuario <seu item> por <item do alvo>
    #  Multi: !trocar @usuario <item1> + <item2> por <item do alvo>
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command(aliases=["swap", "trocar"])
    async def troca(self, ctx, *, args: str = ""):
        """
        Propõe uma troca direta de itens sem envolver MC.
        !trocar @usuario <seu item> por <item do alvo>
        !trocar @usuario <item1> + <item2> por <item do alvo>
        """
        if not args.strip() or not ctx.message.mentions:
            return await ctx.send(
                f"⚠️ {ctx.author.mention}, uso:\n"
                f"• `!trocar @usuario <seu item> por <item do alvo>`\n"
                f"• `!trocar @usuario <item1> + <item2> por <item do alvo>`\n\n"
                f"Exemplo: `!trocar @João Manto das Sombras por Cão de Guarda`\n"
                f"Exemplo 2: `!trocar @João Amuleto da Sorte + Cinto de Ferramentas por Luvas de Seda`"
            )

        alvo = ctx.message.mentions[0]

        if alvo.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, não pode trocar consigo mesmo!")
        if alvo.bot:
            return await ctx.send("🤖 Bots não trocam itens!")

        # Remove a menção do args
        resto = args
        for fmt in [f"<@{alvo.id}>", f"<@!{alvo.id}>"]:
            resto = resto.replace(fmt, "").strip()

        # Divide pelo " por " (case-insensitive)
        separador = " por "
        idx = resto.lower().find(separador)
        if idx == -1:
            return await ctx.send(
                f"⚠️ {ctx.author.mention}, formato inválido!\n"
                f"Use: `!trocar @usuario <seu item> por <item do alvo>`\n"
                f"A palavra **`por`** separa os dois lados da troca."
            )

        lado_prop = resto[:idx].strip()
        lado_alvo = resto[idx + len(separador):].strip()

        if not lado_prop or not lado_alvo:
            return await ctx.send(
                f"⚠️ {ctx.author.mention}, especifique os itens dos **dois lados** da troca."
            )

        # Separa itens do proponente por " + "
        nomes_prop = [p.strip() for p in lado_prop.split("+") if p.strip()]
        nome_alvo  = lado_alvo.strip()

        if not nomes_prop:
            return await ctx.send("❌ Especifique pelo menos um item do seu lado.")
        if len(nomes_prop) > 3:
            return await ctx.send("❌ Você pode oferecer no máximo **3 itens** por troca.")

        try:
            prop_db = db.get_user_data(str(ctx.author.id))
            alvo_db = db.get_user_data(str(alvo.id))

            if not prop_db:
                return await ctx.send("❌ Você não tem conta!")
            if not alvo_db:
                return await ctx.send(f"❌ {alvo.mention} não tem conta registrada!")

            inv_prop_str = str(prop_db["data"][5]) if len(prop_db["data"]) > 5 else ""
            inv_prop = [i.strip() for i in inv_prop_str.split(",") if i.strip() and i.lower() != "nenhum"]

            inv_alvo_str = str(alvo_db["data"][5]) if len(alvo_db["data"]) > 5 else ""
            inv_alvo = [i.strip() for i in inv_alvo_str.split(",") if i.strip() and i.lower() != "nenhum"]

            # Resolve itens do proponente (busca parcial, descontando duplicatas)
            itens_prop_resolvidos = []
            inv_prop_temp = list(inv_prop)
            erros = []

            for nome in nomes_prop:
                encontrado = None
                for inv_item in inv_prop_temp:
                    if nome.lower() in inv_item.lower():
                        encontrado = inv_item
                        break
                if not encontrado:
                    erros.append(nome)
                else:
                    if encontrado in ITENS_INTRANSFERÍVEIS:
                        return await ctx.send(f"❌ **{encontrado}** não pode ser negociado (item intransferível).")
                    
                    # 🔒 TRAVA DE VINCULAÇÃO DE ITEM
                    if "🔒" in encontrado:
                        return await ctx.send(f"❌ **{encontrado}** está vinculado à sua conta e não pode ser trocado!")

                    itens_prop_resolvidos.append(encontrado)
                    inv_prop_temp.remove(encontrado)

            if erros:
                erros_fmt = ", ".join(f"**{e}**" for e in erros)
                itens_disp = "\n".join(f"• {i}" for i in _inv_transferivel(inv_prop)) or "*Inventário vazio*"
                return await ctx.send(
                    f"❌ Item(ns) não encontrado(s) no seu inventário: {erros_fmt}\n\n"
                    f"**Seus itens negociáveis:**\n{itens_disp}"
                )

            # Resolve item do alvo (busca parcial)
            item_alvo_resolvido = None
            for inv_item in inv_alvo:
                if nome_alvo.lower() in inv_item.lower():
                    item_alvo_resolvido = inv_item
                    break

            if not item_alvo_resolvido:
                itens_alvo_disp = "\n".join(f"• {i}" for i in _inv_transferivel(inv_alvo)) or "*Inventário vazio*"
                return await ctx.send(
                    f"❌ **{nome_alvo}** não encontrado no inventário de {alvo.mention}!\n\n"
                    f"**Itens negociáveis de {alvo.display_name}:**\n{itens_alvo_disp}"
                )

            if item_alvo_resolvido in ITENS_INTRANSFERÍVEIS:
                return await ctx.send(f"❌ **{item_alvo_resolvido}** não pode ser negociado (item intransferível).")
            
            # 🔒 TRAVA DE VINCULAÇÃO DE ITEM
            if "🔒" in item_alvo_resolvido:
                return await ctx.send(f"❌ **{item_alvo_resolvido}** está vinculado à conta de {alvo.mention} e não pode ser trocado!")

            # Registra proposta de troca
            troca_id = str(uuid.uuid4())[:8]
            _trocas[troca_id] = {
                "proponente_id":    ctx.author.id,
                "proponente_nome":  ctx.author.mention,
                "alvo_id":          alvo.id,
                "itens_proponente": itens_prop_resolvidos,
                "item_alvo":        item_alvo_resolvido,
            }

            # Embed anti-scam: alvo vê os dois lados claramente
            embed = _embed_troca(ctx.author, alvo, itens_prop_resolvidos, item_alvo_resolvido)
            view  = ViewConfirmarTroca(troca_id)
            view.message = await ctx.send(content=alvo.mention, embed=embed, view=view)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !trocar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    @troca.error
    async def troca_error(self, ctx, error):
        if isinstance(error, commands.CommandError):
            raise error
        print(f"❌ Erro inesperado no !trocar: {error}")
        await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ──────────────────────────────────────────────────────────────────────────
    #  !reembolso
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command(aliases=["devolver", "retornar", "sellback"])
    async def reembolso(self, ctx, *, item: str = None):
        if not item:
            itens_fmt = "\n".join(
                f"• **{nome}** → `+{formatar_moeda(preco * TAXA_REEMBOLSO)} MC`"
                for nome, (_, preco) in ITENS_REEMBOLSAVEIS.items()
            )
            return await ctx.send(
                f"♻️ {ctx.author.mention}, use `!reembolso <item>` para devolver um item ao sistema.\n"
                f"Você recebe **100% do preço base** de volta.\n\n"
                f"**Itens aceitos:**\n{itens_fmt}",
                delete_after=60
            )

        try:
            user_db = db.get_user_data(str(ctx.author.id))
            if not user_db:
                return await ctx.send("❌ Você não tem conta!")

            inv_str  = str(user_db["data"][5]) if len(user_db["data"]) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(",") if i.strip() and i.lower() != "nenhum"]
            inv_list = [i for i in inv_list if not i.startswith("cosmético:") and not i.startswith("cosmetico:")]

            item_encontrado = None
            for inv_item in inv_list:
                if item.lower() in inv_item.lower():
                    item_encontrado = inv_item
                    break

            if not item_encontrado:
                return await ctx.send(
                    f"❌ {ctx.author.mention}, **{item}** não encontrado no inventário.\n"
                    f"Use `!inventario` para ver seus itens."
                )
                
            # 🔒 TRAVA DE VINCULAÇÃO DE ITEM
            if "🔒" in item_encontrado:
                return await ctx.send(
                    f"❌ **{item_encontrado}** está vinculado à sua conta e não pode ser devolvido ao sistema!"
                )

            if item_encontrado not in ITENS_REEMBOLSAVEIS:
                return await ctx.send(
                    f"❌ **{item_encontrado}** não pode ser devolvido ao sistema.\n"
                    f"Cosméticos, cargos e caixas não são reembolsáveis.\n"
                    f"Tente vender para outro jogador: `!vender @usuario {item_encontrado} <preço>`"
                )

            _, preco_base = ITENS_REEMBOLSAVEIS[item_encontrado]
            valor_reembolso = round(preco_base * TAXA_REEMBOLSO, 2)

            embed = disnake.Embed(
                title="♻️ DEVOLVER AO SISTEMA?",
                description=(
                    f"**Item:** `{item_encontrado}`\n"
                    f"**Preço base:** `{formatar_moeda(preco_base)} MC`\n"
                    f"**Você recebe:** `{formatar_moeda(valor_reembolso)} MC` *(100%)*\n\n"
                    f"⚠️ Esta ação é **irreversível**. O item será removido do seu inventário."
                ),
                color=disnake.Color.orange()
            )
            embed.set_footer(text="Expira em 30 segundos.")

            view = ViewConfirmarReembolso(ctx.author, item_encontrado, valor_reembolso, user_db["row"], inv_list)
            view.message = await ctx.send(embed=embed, view=view)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !reembolso de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ──────────────────────────────────────────────────────────────────────────
    #  !inventario
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command(aliases=["inv", "mochila", "bolsa"])
    async def inventario(self, ctx, membro: disnake.Member = None):
        """Mostra os itens do próprio inventário."""
        if membro and membro.id != ctx.author.id:
            return await ctx.send(
                f"🔒 {ctx.author.mention}, o inventário de outros jogadores é informação privada!\n"
                f"Use `!perfil @{membro.display_name}` e clique em **🕵️ Ver dados completos** para espionar."
            )

        alvo = ctx.author
        try:
            user_db = db.get_user_data(str(alvo.id))
            if not user_db:
                return await ctx.send("❌ Conta não encontrada!")

            inv_str  = str(user_db["data"][5]) if len(user_db["data"]) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(",") if i.strip() and i.lower() != "nenhum"]
            inv_list = [i for i in inv_list if not i.startswith("cosmético:") and not i.startswith("cosmetico:")]

            if not inv_list:
                return await ctx.send(
                    f"🎒 {ctx.author.mention}, seu inventário está vazio!\n"
                    f"Trabalhe na selva, abra caixas ou compre itens na `!loja`."
                )

            passivos_equipados = db.get_passivos(user_db)

            # Agrupa itens repetidos
            contagem: dict[str, int] = {}
            for item in inv_list:
                contagem[item] = contagem.get(item, 0) + 1

            linhas = []
            for item, qtd in contagem.items():
                if item in ITENS_INTRANSFERÍVEIS or "🔒" in item:
                    icone = "🔒"
                elif item in passivos_equipados:
                    icone = "🔰"   # passivo ativo
                else:
                    icone = "✅"
                qtd_str = f" ×{qtd}" if qtd > 1 else ""
                linhas.append(f"{icone} **{item}**{qtd_str}")

            embed = disnake.Embed(
                title="🎒 Seu Inventário",
                description="\n".join(linhas),
                color=disnake.Color.dark_theme()
            )
            embed.set_author(name=alvo.display_name, icon_url=alvo.display_avatar.url)
            embed.set_footer(
                text="✅ Vendível/trocável  |  🔰 Passivo equipado  |  🔒 Intransferível\n"
                     "!vender · !trocar · !reembolso · !passivos · !visuais"
            )
            await ctx.send(embed=embed, delete_after=60)

        except Exception as e:
            print(f"❌ Erro no !inventario de {ctx.author}: {e}")
            await ctx.send("⚠️ Ocorreu um erro ao carregar o inventário.")


def setup(bot):
    bot.add_cog(Trade(bot))