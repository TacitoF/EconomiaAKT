import disnake
from disnake.ext import commands
import database as db

# Itens que NÃO podem ser negociados entre jogadores
ITENS_INTRANSFERÍVEIS = {
    "Escudo",           # item de estado ativo — tem lógica de CD própria
    "Pé de Cabra",      # equipado automaticamente, lógica no !roubar
    "Seguro",           # ativado automaticamente ao ser roubado
}

def formatar_moeda(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Propostas pendentes em memória: {proposta_id: dict}
# Não precisa persistir no Sheets — expira com o timeout da View
_propostas: dict[str, dict] = {}


# ── View de confirmação para o COMPRADOR ──────────────────────────────────────

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

        vendedor_id = str(proposta["vendedor_id"])
        comprador_id = str(proposta["comprador_id"])
        item = proposta["item"]
        preco = proposta["preco"]

        # Revalida tudo no momento do aceite
        vendedor_db = db.get_user_data(vendedor_id)
        comprador_db = db.get_user_data(comprador_id)

        if not vendedor_db or not comprador_db:
            return await inter.response.send_message("❌ Conta não encontrada. Transação cancelada.", ephemeral=True)

        # Verifica se vendedor ainda tem o item
        inv_vendedor = [i.strip() for i in str(vendedor_db["data"][5]).split(",") if i.strip()]
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

        # Executa a transferência
        # 1. Remove item do vendedor
        inv_vendedor.remove(item)
        db.update_value(vendedor_db["row"], 6, ", ".join(inv_vendedor) if inv_vendedor else "Nenhum")

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
                f"**Vendedor:** {proposta['vendedor_nome']} `+{formatar_moeda(preco)} MC`\n"
                f"**Comprador:** {inter.author.mention} `-{formatar_moeda(preco)} MC`"
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


# ── Cog principal ─────────────────────────────────────────────────────────────

class Trade(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != "🐒・conguitos":
            canal = disnake.utils.get(ctx.guild.channels, name="🐒・conguitos")
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, negociações apenas no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["negociar", "comercio"])
    async def vender(self, ctx, comprador: disnake.Member = None, item: str = None, preco: float = None):
        """
        Vende um item do inventário para outro jogador.
        Uso: !vender @usuario <nome do item> <preço>
        Exemplo: !vender @João "Casca de Banana" 200
        """
        if comprador is None or item is None or preco is None:
            return await ctx.send(
                f"⚠️ {ctx.author.mention}, uso: `!vender @usuario <item> <preço>`\n"
                f"Exemplo: `!vender @João Casca 200`\n"
                f"*Use `!inventario` para ver seus itens disponíveis.*"
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

            inv_str = str(vendedor_db["data"][5]) if len(vendedor_db["data"]) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(",") if i.strip() and i.lower() != "nenhum"]

            # Busca o item no inventário (case-insensitive, busca parcial)
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

            # Verifica se o item pode ser negociado
            if item_encontrado in ITENS_INTRANSFERÍVEIS:
                return await ctx.send(
                    f"❌ **{item_encontrado}** não pode ser vendido entre jogadores pois tem lógica de estado ativo."
                )

            # Verifica se comprador tem conta
            comprador_db = db.get_user_data(str(comprador.id))
            if not comprador_db:
                return await ctx.send(f"❌ {comprador.mention} não tem conta registrada!")

            saldo_comprador = db.parse_float(comprador_db["data"][2])

            # Cria a proposta
            import uuid
            proposta_id = str(uuid.uuid4())[:8]
            _propostas[proposta_id] = {
                "vendedor_id":   ctx.author.id,
                "vendedor_nome": ctx.author.mention,
                "comprador_id":  comprador.id,
                "item":          item_encontrado,
                "preco":         preco,
            }

            embed = disnake.Embed(
                title="🏪 PROPOSTA DE VENDA",
                description=(
                    f"**Vendedor:** {ctx.author.mention}\n"
                    f"**Item:** `{item_encontrado}`\n"
                    f"**Preço:** `{formatar_moeda(preco)} MC`\n\n"
                    f"{'✅ Você tem saldo suficiente.' if saldo_comprador >= preco else f'⚠️ Seu saldo atual: `{formatar_moeda(saldo_comprador)} MC` (insuficiente)'}\n\n"
                    f"{comprador.mention}, você aceita?"
                ),
                color=disnake.Color.gold()
            )
            embed.set_footer(text="Expira em 60 segundos.")

            view = ViewConfirmarCompra(proposta_id)
            view.message = await ctx.send(embed=embed, view=view)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !vender de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    @commands.command(aliases=["inv", "mochila", "bolsa"])
    async def inventario(self, ctx, membro: disnake.Member = None):
        """Mostra os itens vendíveis do próprio inventário.
        Ver o inventário de outra pessoa requer o dossiê no !perfil."""
        # Bloqueia visualização do inventário alheio — use !perfil @usuario para isso (500 MC)
        if membro and membro.id != ctx.author.id:
            return await ctx.send(
                f"🔒 {ctx.author.mention}, o inventário de outros jogadores é informação privada!
"
                f"Use `!perfil @{membro.display_name}` e clique em **🕵️ Ver dados completos** para espionar."
            )

        alvo = ctx.author
        try:
            user_db = db.get_user_data(str(alvo.id))
            if not user_db:
                return await ctx.send("❌ Conta não encontrada!")

            inv_str = str(user_db["data"][5]) if len(user_db["data"]) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(",") if i.strip() and i.lower() != "nenhum"]
            # Filtra cosméticos — esses são gerenciados pelo !visuais
            inv_list = [i for i in inv_list if not i.startswith("cosmético:") and not i.startswith("cosmetico:")]

            if not inv_list:
                return await ctx.send(
                    f"🎒 {ctx.author.mention}, seu inventário está vazio!
"
                    f"Trabalhe na selva, abra caixas ou compre itens na `!loja`."
                )

            # Agrupa itens repetidos
            contagem: dict[str, int] = {}
            for i in inv_list:
                contagem[i] = contagem.get(i, 0) + 1

            linhas = []
            for item, qtd in contagem.items():
                transferivel = "🔒" if item in ITENS_INTRANSFERÍVEIS else "✅"
                qtd_str = f" ×{qtd}" if qtd > 1 else ""
                linhas.append(f"{transferivel} **{item}**{qtd_str}")

            embed = disnake.Embed(
                title=f"🎒 Seu Inventário",
                description="
".join(linhas),
                color=disnake.Color.dark_theme()
            )
            embed.set_author(name=alvo.display_name, icon_url=alvo.display_avatar.url)
            embed.set_footer(text="✅ Vendível com !vender  |  🔒 Intransferível  |  !visuais para cosméticos")
            # Ephemeral via send normal — inventário é dado sensível
            await ctx.send(embed=embed, delete_after=60)

        except Exception as e:
            print(f"❌ Erro no !inventario de {ctx.author}: {e}")
            await ctx.send("⚠️ Ocorreu um erro ao carregar o inventário.")


def setup(bot):
    bot.add_cog(Trade(bot))