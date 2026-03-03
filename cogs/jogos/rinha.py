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
    return LIMITES_CARGO.get(cargo, 400)

def formatar_moeda(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def gerar_barra_hp(hp_atual, hp_maximo=100):
    hp_atual = max(0, hp_atual)
    blocos_cheios = int((hp_atual / hp_maximo) * 10)
    blocos_vazios = 10 - blocos_cheios
    # Muda a cor da barra se estiver morrendo
    emoji_bloco = "🟩" if hp_atual > 40 else ("🟨" if hp_atual > 20 else "🟥")
    return (emoji_bloco * blocos_cheios) + ("⬛" * blocos_vazios)

class RinhaGameView(disnake.ui.View):
    def __init__(self, p1: disnake.Member, p2: disnake.Member, aposta: float):
        super().__init__(timeout=45) # 45 segundos para agir
        self.p1 = p1
        self.p2 = p2
        self.aposta = aposta
        self.hp = {p1.id: 100, p2.id: 100}
        self.escolhas = {p1.id: None, p2.id: None}
        self.rodada = 1
        self.log_batalha = "A poeira subiu! Preparem-se para a luta!"
        self.encerrado = False
        self.message = None

    async def atualizar_arena(self, inter: disnake.MessageInteraction = None):
        if self.encerrado:
            for item in self.children:
                item.disabled = True

        hp_p1 = self.hp[self.p1.id]
        hp_p2 = self.hp[self.p2.id]

        embed = disnake.Embed(
            title=f"🥊 RINHA SÍMIA: Rodada {self.rodada}",
            description=f"**O Pote:** `{formatar_moeda(self.aposta * 2)} MC`\n\n📜 **Narrador:**\n> *{self.log_batalha}*\n━━━━━━━━━━━━━━━━━━━━",
            color=disnake.Color.dark_red()
        )
        embed.add_field(
            name=f"🦍 {self.p1.display_name}", 
            value=f"**HP:** {hp_p1}/100\n{gerar_barra_hp(hp_p1)}", 
            inline=False
        )
        embed.add_field(
            name=f"🦧 {self.p2.display_name}", 
            value=f"**HP:** {hp_p2}/100\n{gerar_barra_hp(hp_p2)}", 
            inline=False
        )

        status_p1 = "✅ Escolheu" if self.escolhas[self.p1.id] else "⏳ Pensando..."
        status_p2 = "✅ Escolheu" if self.escolhas[self.p2.id] else "⏳ Pensando..."
        embed.set_footer(text=f"{self.p1.display_name}: {status_p1}  |  {self.p2.display_name}: {status_p2}")

        if inter:
            await inter.response.edit_message(embed=embed, view=self)
        elif self.message:
            await self.message.edit(embed=embed, view=self)

    async def resolver_rodada(self, inter: disnake.MessageInteraction):
        e1 = self.escolhas[self.p1.id]
        e2 = self.escolhas[self.p2.id]

        dano_soco = random.randint(15, 25)
        dano_voadora = random.randint(25, 35)
        recoil_defesa = 10

        log = ""

        # Lógica Pedra, Papel, Tesoura da Selva
        if e1 == e2:
            log = f"Ambos tentaram usar **{e1.capitalize()}**! Seus golpes colidiram e os dois levaram 5 de dano!"
            self.hp[self.p1.id] -= 5
            self.hp[self.p2.id] -= 5

        elif e1 == "soco" and e2 == "voadora":
            log = f"**{self.p2.display_name}** pulou para a voadora, mas levou um **Soco Rápido** de **{self.p1.display_name}** no ar! (-{dano_soco} HP)"
            self.hp[self.p2.id] -= dano_soco
        elif e2 == "soco" and e1 == "voadora":
            log = f"**{self.p1.display_name}** pulou para a voadora, mas levou um **Soco Rápido** de **{self.p2.display_name}** no ar! (-{dano_soco} HP)"
            self.hp[self.p1.id] -= dano_soco

        elif e1 == "voadora" and e2 == "bloqueio":
            log = f"**{self.p1.display_name}** veio com os dois pés no peito e QUEBROU a defesa de **{self.p2.display_name}**! (-{dano_voadora} HP)"
            self.hp[self.p2.id] -= dano_voadora
        elif e2 == "voadora" and e1 == "bloqueio":
            log = f"**{self.p2.display_name}** veio com os dois pés no peito e QUEBROU a defesa de **{self.p1.display_name}**! (-{dano_voadora} HP)"
            self.hp[self.p1.id] -= dano_voadora

        elif e1 == "bloqueio" and e2 == "soco":
            log = f"**{self.p2.display_name}** tentou socar, mas **{self.p1.display_name}** bloqueou e revidou o golpe! (-{recoil_defesa} HP)"
            self.hp[self.p2.id] -= recoil_defesa
        elif e2 == "bloqueio" and e1 == "soco":
            log = f"**{self.p1.display_name}** tentou socar, mas **{self.p2.display_name}** bloqueou e revidou o golpe! (-{recoil_defesa} HP)"
            self.hp[self.p1.id] -= recoil_defesa

        self.log_batalha = log
        self.escolhas = {self.p1.id: None, self.p2.id: None}
        self.rodada += 1

        # Verifica mortes
        if self.hp[self.p1.id] <= 0 or self.hp[self.p2.id] <= 0:
            self.encerrado = True
            await self.declarar_vencedor(inter)
        else:
            await self.atualizar_arena(inter)

    async def declarar_vencedor(self, inter: disnake.MessageInteraction = None, wo_id=None):
        self.encerrado = True
        pote = round(self.aposta * 2, 2)
        
        vencedor = None
        perdedor = None

        if wo_id:
            perdedor = self.p1 if self.p1.id == wo_id else self.p2
            vencedor = self.p2 if self.p1.id == wo_id else self.p1
            self.log_batalha = f"🥱 **{perdedor.display_name}** fugiu da arena ou demorou demais! Vitória por W.O.!"
        else:
            if self.hp[self.p1.id] <= 0 and self.hp[self.p2.id] <= 0:
                self.log_batalha += "\n\n💀 **EMPATE DUPLO!** Os dois nocautearam um ao outro. O dinheiro foi devolvido!"
                # Devolve a aposta pra ambos
                for player in [self.p1, self.p2]:
                    db_user = db.get_user_data(str(player.id))
                    if db_user:
                        saldo = db.parse_float(db_user['data'][2])
                        db.update_value(db_user['row'], 3, round(saldo + self.aposta, 2))
                return await self.atualizar_arena(inter)
            
            elif self.hp[self.p1.id] <= 0:
                vencedor = self.p2
                perdedor = self.p1
            else:
                vencedor = self.p1
                perdedor = self.p2

            self.log_batalha += f"\n\n🏆 **K.O.!** **{vencedor.display_name}** nocauteou o adversário e faturou os **{formatar_moeda(pote)} MC**!"

        # Paga o vencedor
        if vencedor:
            db_venc = db.get_user_data(str(vencedor.id))
            if db_venc:
                saldo = db.parse_float(db_venc['data'][2])
                db.update_value(db_venc['row'], 3, round(saldo + pote, 2))

        await self.atualizar_arena(inter)

    async def registrar_escolha(self, inter: disnake.MessageInteraction, escolha: str):
        if inter.author.id not in [self.p1.id, self.p2.id]:
            return await inter.response.send_message("❌ Você não está lutando!", ephemeral=True)
        
        if self.escolhas[inter.author.id] is not None:
            return await inter.response.send_message("⏳ Você já escolheu seu golpe nesta rodada! Aguarde seu oponente.", ephemeral=True)

        self.escolhas[inter.author.id] = escolha
        
        if self.escolhas[self.p1.id] and self.escolhas[self.p2.id]:
            await self.resolver_rodada(inter)
        else:
            await self.atualizar_arena(inter)

    @disnake.ui.button(label="Soco", style=disnake.ButtonStyle.primary, emoji="🥊")
    async def btn_soco(self, button, inter):
        await self.registrar_escolha(inter, "soco")

    @disnake.ui.button(label="Voadora", style=disnake.ButtonStyle.danger, emoji="🦵")
    async def btn_voadora(self, button, inter):
        await self.registrar_escolha(inter, "voadora")

    @disnake.ui.button(label="Bloqueio", style=disnake.ButtonStyle.success, emoji="🛡️")
    async def btn_bloqueio(self, button, inter):
        await self.registrar_escolha(inter, "bloqueio")

    async def on_timeout(self):
        if not self.encerrado:
            # Quem não escolheu perde por WO
            if not self.escolhas[self.p1.id]:
                await self.declarar_vencedor(wo_id=self.p1.id)
            elif not self.escolhas[self.p2.id]:
                await self.declarar_vencedor(wo_id=self.p2.id)
            else:
                await self.declarar_vencedor(wo_id=self.p1.id) # fallback de segurança


class RinhaAcceptView(disnake.ui.View):
    def __init__(self, desafiante, alvo, aposta):
        super().__init__(timeout=60)
        self.desafiante = desafiante
        self.alvo = alvo
        self.aposta = aposta
        self.aceito = False

    @disnake.ui.button(label="🥊 ACEITAR DUELO", style=disnake.ButtonStyle.success)
    async def aceitar(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id != self.alvo.id:
            return await inter.response.send_message("❌ Este desafio não é para você!", ephemeral=True)

        # Checa os saldos novamente antes de iniciar
        user1 = db.get_user_data(str(self.desafiante.id))
        user2 = db.get_user_data(str(self.alvo.id))

        if not user1 or db.parse_float(user1['data'][2]) < self.aposta:
            return await inter.response.send_message(f"❌ {self.desafiante.mention} não tem mais o saldo suficiente!", ephemeral=True)
        if not user2 or db.parse_float(user2['data'][2]) < self.aposta:
            return await inter.response.send_message("❌ Você não tem saldo suficiente!", ephemeral=True)

        # Cobra a aposta de ambos
        db.update_value(user1['row'], 3, round(db.parse_float(user1['data'][2]) - self.aposta, 2))
        db.update_value(user2['row'], 3, round(db.parse_float(user2['data'][2]) - self.aposta, 2))

        self.aceito = True
        for item in self.children: item.disabled = True
        await inter.response.edit_message(content="🔥 **DESAFIO ACEITO! Preparando arena...**", embed=None, view=self)

        arena_view = RinhaGameView(self.desafiante, self.alvo, self.aposta)
        # O Embed inicial da arena
        embed = disnake.Embed(
            title="🥊 RINHA SÍMIA: Rodada 1",
            description=f"**O Pote:** `{formatar_moeda(self.aposta * 2)} MC`\n\n📜 **Narrador:**\n> *{arena_view.log_batalha}*\n━━━━━━━━━━━━━━━━━━━━",
            color=disnake.Color.dark_red()
        )
        embed.add_field(name=f"🦍 {self.desafiante.display_name}", value=f"**HP:** 100/100\n{gerar_barra_hp(100)}", inline=False)
        embed.add_field(name=f"🦧 {self.alvo.display_name}", value=f"**HP:** 100/100\n{gerar_barra_hp(100)}", inline=False)
        embed.set_footer(text=f"{self.desafiante.display_name}: ⏳ Pensando...  |  {self.alvo.display_name}: ⏳ Pensando...")

        arena_view.message = await inter.message.channel.send(embed=embed, view=arena_view)
        self.stop()

    async def on_timeout(self):
        if not self.aceito:
            for item in self.children: item.disabled = True
            try:
                await self.message.edit(content=f"🥱 {self.alvo.mention} amarelou e ignorou o desafio.", embed=None, view=self)
            except:
                pass


class JogosRinha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"⚠️ {ctx.author.mention}, as rinhas acontecem no submundo do {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["luta"])
    async def rinha(self, ctx, adversario: disnake.Member = None, aposta: float = None):
        if adversario is None or aposta is None:
            embed = disnake.Embed(
                title="🥊 COMO JOGAR RINHA SÍMIA",
                description=(
                    "Desafie um amigo para uma luta até a morte e leve o dinheiro dele!\n"
                    "**Comando:** `!rinha @Adversario <valor>`\n\n"
                    "**A Dinâmica (Pedra, Papel, Tesoura):**\n"
                    "🥊 **Soco** ganha da **Voadora** (interrompe no ar).\n"
                    "🦵 **Voadora** ganha do **Bloqueio** (quebra a defesa e dá muito dano).\n"
                    "🛡️ **Bloqueio** ganha do **Soco** (regride o dano de volta pro atacante)."
                ),
                color=disnake.Color.dark_red()
            )
            return await ctx.send(embed=embed)

        if adversario.bot:
            return await ctx.send("❌ Você não pode desafiar um robô!")
        if adversario.id == ctx.author.id:
            return await ctx.send("❌ Você tem problemas? Não pode bater em si mesmo!")
        if aposta <= 0:
            return await ctx.send("❌ A aposta deve ser maior que zero!")

        aposta = round(aposta, 2)
        user = db.get_user_data(str(ctx.author.id))
        
        if not user:
            return await ctx.send("❌ Você precisa se registrar com `!trabalhar` primeiro.")
        
        saldo = db.parse_float(user['data'][2])
        cargo = user['data'][3] if len(user['data']) > 3 else "Lêmure"
        
        if saldo < aposta:
            return await ctx.send(f"❌ Você não tem saldo! Possui apenas **{formatar_moeda(saldo)} MC**.")
        if aposta > get_limite(cargo):
            return await ctx.send(f"🚫 A aposta excede seu limite do cargo **{cargo}** ({formatar_moeda(get_limite(cargo))} MC)!")

        view = RinhaAcceptView(ctx.author, adversario, aposta)
        embed = disnake.Embed(
            title="🥊 DESAFIO DE RINHA!",
            description=f"{ctx.author.mention} intimou {adversario.mention} para uma rinha sangrenta!\n\n💰 **Pote em jogo:** `{formatar_moeda(aposta * 2)} MC`",
            color=disnake.Color.dark_red()
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        
        view.message = await ctx.send(content=adversario.mention, embed=embed, view=view)


def setup(bot):
    bot.add_cog(JogosRinha(bot))