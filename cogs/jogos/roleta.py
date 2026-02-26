import disnake
from disnake.ext import commands
import database as db
import random
import asyncio

LIMITES_CARGO = {
    "Lêmure":      400,
    "Macaquinho":  1500,
    "Babuíno":     4500,
    "Chimpanzé":   12000,
    "Orangutango": 30000,
    "Gorila":      80000,
    "Ancestral":   250000,
    "Rei Símio":   1500000,
}

def get_limite(cargo):
    return LIMITES_CARGO.get(cargo, 250)

def save_achievement(user_data, slug):
    conquistas = str(user_data['data'][9]) if len(user_data['data']) > 9 else ""
    lista = [c.strip() for c in conquistas.split(',') if c.strip()]
    if slug not in lista:
        lista.append(slug)
        db.update_value(user_data['row'], 10, ", ".join(lista))

# ──────────────────────────────────────────────
#  MODAL DE APOSTAS
# ──────────────────────────────────────────────
class ModalApostaRoleta(disnake.ui.Modal):
    def __init__(self, view, tipo: str):
        self.roleta_view = view
        self.tipo = tipo  # "vermelho", "preto", "par", "impar" ou "numero"

        components = []
        
        # Se for aposta em número específico, pede o número primeiro
        if tipo == "numero":
            components.append(disnake.ui.TextInput(
                label="Escolha um número (0 a 36)",
                placeholder="Ex: 7",
                custom_id="numero_escolhido",
                style=disnake.TextInputStyle.short,
                max_length=2
            ))
            title = "🎯 Apostar em um Número"
        else:
            titulos = {
                "vermelho": "🔴 Apostar no Vermelho",
                "preto": "⚫ Apostar no Preto",
                "par": "⚖️ Apostar em Pares",
                "impar": "⚖️ Apostar em Ímpares"
            }
            title = titulos[tipo]
        
        # Pede o valor da aposta
        components.append(disnake.ui.TextInput(
            label="Valor da Aposta (MC)",
            placeholder="Ex: 100",
            custom_id="valor_aposta",
            style=disnake.TextInputStyle.short,
            max_length=10
        ))

        super().__init__(title=title[:45], components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        
        if not self.roleta_view.is_active:
            return await inter.edit_original_response(content="❌ A mesa já fechou! A roleta está girando.")

        valor_raw = inter.text_values.get("valor_aposta", "").strip().replace(",", ".")
        try:
            valor = round(float(valor_raw), 2)
        except ValueError:
            return await inter.edit_original_response(content="❌ Valor inválido! Digite apenas números.")

        if valor <= 0:
            return await inter.edit_original_response(content="❌ A aposta deve ser maior que zero!")

        aposta_em = self.tipo
        if self.tipo == "numero":
            num_raw = inter.text_values.get("numero_escolhido", "").strip()
            if not num_raw.isdigit() or not (0 <= int(num_raw) <= 36):
                return await inter.edit_original_response(content="❌ Número inválido! Escolha um número entre 0 e 36.")
            aposta_em = num_raw

        user = db.get_user_data(str(inter.author.id))
        if not user:
            return await inter.edit_original_response(content="❌ Conta não encontrada!")

        saldo = db.parse_float(user['data'][2])
        cargo = user['data'][3] if len(user['data']) > 3 else "Lêmure"
        limite = get_limite(cargo)

        apostado_ja = sum(a['valor'] for a in self.roleta_view.apostas if a['user'].id == inter.author.id)
        if (apostado_ja + valor) > limite:
            restante = max(round(limite - apostado_ja, 2), 0)
            return await inter.edit_original_response(
                content=f"🚫 Limite como **{cargo}** é **{limite} MC**. Você só pode apostar mais **{restante} MC** nesta rodada."
            )

        if saldo < valor:
            return await inter.edit_original_response(content=f"❌ Saldo insuficiente! Você tem **{saldo:.2f} MC**.")

        # Debita o valor e registra a aposta
        db.update_value(user['row'], 3, round(saldo - valor, 2))
        self.roleta_view.apostas.append({'user': inter.author, 'valor': valor, 'tipo': aposta_em})
        
        await inter.edit_original_response(content=f"✅ Você apostou **{valor:.2f} MC** em `{aposta_em.upper()}`!")

# ──────────────────────────────────────────────
#  VIEW DA ROLETA (Botões)
# ──────────────────────────────────────────────
class RoletaView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=30)
        self.apostas = []
        self.is_active = True

    @disnake.ui.button(label="🔴 Vermelho (2x)", style=disnake.ButtonStyle.danger, row=0)
    async def btn_vermelho(self, button, inter):
        await inter.response.send_modal(ModalApostaRoleta(self, "vermelho"))

    @disnake.ui.button(label="⚫ Preto (2x)", style=disnake.ButtonStyle.secondary, row=0)
    async def btn_preto(self, button, inter):
        await inter.response.send_modal(ModalApostaRoleta(self, "preto"))

    @disnake.ui.button(label="⚖️ Par (2x)", style=disnake.ButtonStyle.primary, row=1)
    async def btn_par(self, button, inter):
        await inter.response.send_modal(ModalApostaRoleta(self, "par"))

    @disnake.ui.button(label="⚖️ Ímpar (2x)", style=disnake.ButtonStyle.primary, row=1)
    async def btn_impar(self, button, inter):
        await inter.response.send_modal(ModalApostaRoleta(self, "impar"))

    @disnake.ui.button(label="🎯 Número 0-36 (36x)", style=disnake.ButtonStyle.success, row=2)
    async def btn_numero(self, button, inter):
        await inter.response.send_modal(ModalApostaRoleta(self, "numero"))

# ──────────────────────────────────────────────
#  COG PRINCIPAL
# ──────────────────────────────────────────────
class Roleta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roleta_aberta = False

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, a roleta fica no cassino! Vai para {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["roulette", "rol"])
    async def roleta(self, ctx):
        if self.roleta_aberta:
            return await ctx.send(f"⚠️ {ctx.author.mention}, a mesa já está aberta! Espere a rodada acabar.")

        self.roleta_aberta = True
        try:
            view = RoletaView()

            embed = disnake.Embed(
                title="🎰 A MESA DE ROLETA ABRIU!",
                description=(
                    "O Chimpanzézio abriu a mesa! Você tem **30 segundos** para apostar.\n\n"
                    "Clique nos botões abaixo para colocar suas fichas na mesa!"
                ),
                color=disnake.Color.gold()
            )
            msg = await ctx.send(embed=embed, view=view)
            
            # Aguarda o tempo da roleta
            await asyncio.sleep(30)
            
            view.is_active = False
            for item in view.children:
                item.disabled = True
            await msg.edit(view=view)

            if not view.apostas:
                return await ctx.send("🦗 Ninguém apostou... O Chimpanzézio fechou a mesa.")

            total_apostado = sum(a['valor'] for a in view.apostas)
            embed_giro = disnake.Embed(
                title="🛑 APOSTAS ENCERRADAS!",
                description=f"Total na mesa: **{total_apostado:.2f} MC**!\n\n🌀 **O Chimpanzézio girou a roleta...**",
                color=disnake.Color.orange()
            )
            msg_spin = await ctx.send(embed=embed_giro)
            await asyncio.sleep(2.5)

            resultado_num = random.randint(0, 36)
            vermelhos = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
            if resultado_num == 0:           
                cor, emoji = "verde", "🟩"
            elif resultado_num in vermelhos: 
                cor, emoji = "vermelho", "🟥"
            else:                            
                cor, emoji = "preto", "⬛"

            vencedores_txt = ""
            perdedores_txt = ""

            for aposta in view.apostas:
                jogador = aposta['user']
                valor = aposta['valor']
                aposta_em = aposta['tipo']

                try:
                    user_db = db.get_user_data(str(jogador.id))
                    if not user_db:
                        continue

                    ganhou = False
                    multiplicador = 0

                    if aposta_em.isdigit() and int(aposta_em) == resultado_num:
                        ganhou, multiplicador = True, 36
                    elif aposta_em == cor:
                        ganhou, multiplicador = True, 2
                    elif aposta_em == "par" and resultado_num != 0 and resultado_num % 2 == 0:
                        ganhou, multiplicador = True, 2
                    elif aposta_em == "impar" and resultado_num != 0 and resultado_num % 2 != 0:
                        ganhou, multiplicador = True, 2

                    if ganhou:
                        lucro = round((valor * multiplicador) - valor, 2)
                        lucro_total = round(valor * multiplicador, 2)
                        db.update_value(user_db['row'], 3, round(db.parse_float(user_db['data'][2]) + lucro_total, 2))
                        if multiplicador == 36:
                            save_achievement(user_db, "filho_da_sorte")
                        vencedores_txt += f"🎉 {jogador.mention} lucrou **{lucro_total:.2f} MC** em `{aposta_em.upper()}`!\n"
                    else:
                        perdedores_txt += f"💀 {jogador.mention} perdeu **{valor:.2f} MC** em `{aposta_em.upper()}`.\n"

                except Exception as e:
                    print(f"❌ Erro ao processar aposta de {jogador}: {e}")

            embed_final = disnake.Embed(
                title=f"🎰 A ROLETA PAROU NO: {emoji} {resultado_num} ({cor.upper()})",
                color=disnake.Color.green() if vencedores_txt else disnake.Color.red()
            )
            embed_final.add_field(name="💰 VENCEDORES", value=vencedores_txt or "Ninguém...", inline=False)
            embed_final.add_field(name="💸 PERDEDORES", value=perdedores_txt or "Ninguém!", inline=False)
            await msg_spin.edit(embed=embed_final)

        finally:
            # Libera a mesa para outra rodada, mesmo se der erro no meio do processo
            self.roleta_aberta = False

def setup(bot):
    bot.add_cog(Roleta(bot))