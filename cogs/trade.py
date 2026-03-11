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




# Mapa de nome do item → (slug, preço base) para reembolso ao sistema
ITENS_REEMBOLSAVEIS = {
    "Escudo":              ("item:escudo",      1000.0),
    "Pé de Cabra":         ("item:pe_de_cabra", 1200.0),
    "Seguro":              ("item:seguro",       950.0),
    "Casca de Banana":     ("item:casca",        300.0),
    "Imposto do Gorila":   ("item:imposto",     1500.0),
    "Troca de Nick":       ("item:troca_nick",  3000.0),
    "Ração Símia":         ("item:racao",        250.0),
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
        # Revalida no momento do clique
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

        saldo_atual = db.parse_float(user_db["data"][2])
        db.update_value(user_db["row"], 3, round(saldo_atual + self.valor, 2))

        self.stop()
        for child in self.children:
            child.disabled = True

        embed = disnake.Embed(
            title="♻️ ITEM DEVOLVIDO!",
            description=(
                f"**Item:** `{self.item}`\n**Reembolso:** `+{formatar_moeda(self.valor)} MC` *(100% do preço base)*\n**Novo saldo:** `{formatar_moeda(round(saldo_atual + self.valor, 2))} MC`"
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
    async def vender(self, ctx, *, args: str = ""):
        """
        Vende um item para outro jogador ou para o sistema.
        !vender @usuario <item> <preço>  → proposta para jogador
        !vender <item>                   → vende ao sistema pelo preço base
        """
        if not args.strip():
            return await ctx.send(
                f"⚠️ {ctx.author.mention}, uso:\n"
                f"• Vender para jogador: `!vender @usuario <item> <preço>`\n"
                f"• Vender ao sistema: `!vender <item>`\n"
                f"*Use `!inventario` para ver seus itens.*"
            )

        # Detecta se há menção (@) no início da mensagem
        tem_mencao = bool(ctx.message.mentions)

        if tem_mencao:
            # ── Modo jogador ──────────────────────────────────────────────────
            comprador = ctx.message.mentions[0]

            # Remove a menção do args para sobrar apenas "<item> <preço>"
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

                inv_str = str(vendedor_db["data"][5]) if len(vendedor_db["data"]) > 5 else ""
                inv_list = [i.strip() for i in inv_str.split(",") if i.strip() and i.lower() != "nenhum"]

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

                if item_encontrado in ITENS_INTRANSFERÍVEIS:
                    return await ctx.send(
                        f"❌ **{item_encontrado}** não pode ser vendido entre jogadores pois tem lógica de estado ativo."
                    )

                comprador_db = db.get_user_data(str(comprador.id))
                if not comprador_db:
                    return await ctx.send(f"❌ {comprador.mention} não tem conta registrada!")

                saldo_comprador = db.parse_float(comprador_db["data"][2])

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
                print(f"❌ Erro no !vender (jogador) de {ctx.author}: {e}")
                await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

        else:
            # ── Modo sistema: tudo em args é o nome do item ───────────────────
            await self._vender_sistema(ctx, args.strip())
    @vender.error
    async def vender_error(self, ctx, error):
        if isinstance(error, commands.CommandError):
            raise error
        print(f"❌ Erro inesperado no !vender: {error}")
        await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")


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

            # Busca item no inventário (case-insensitive, parcial)
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

            # Verifica se o item é reembolsável
            if item_encontrado not in ITENS_REEMBOLSAVEIS:
                return await ctx.send(
                    f"❌ **{item_encontrado}** não pode ser devolvido ao sistema.\n"
                    f"Cosméticos, cargos e caixas não são reembolsáveis.\n"
                    f"Tente vender para outro jogador com `!vender @usuario {item_encontrado} <preço>`."
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

    @commands.command(aliases=["inv", "mochila", "bolsa"])
    async def inventario(self, ctx, membro: disnake.Member = None):
        """Mostra os itens vendíveis do próprio inventário.
        Ver o inventário de outra pessoa requer o dossiê no !perfil."""
        # Bloqueia visualização do inventário alheio — use !perfil @usuario para isso (500 MC)
        if membro and membro.id != ctx.author.id:
            return await ctx.send(
                f"🔒 {ctx.author.mention}, o inventário de outros jogadores é informação privada!\nUse `!perfil @{membro.display_name}` e clique em **🕵️ Ver dados completos** para espionar."
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
                    f"🎒 {ctx.author.mention}, seu inventário está vazio!\nTrabalhe na selva, abra caixas ou compre itens na `!loja`."
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
                description="\n".join(linhas),
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