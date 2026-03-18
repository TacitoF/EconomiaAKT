import disnake
from disnake.ext import commands
import database as db
import random

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
    """Formata um float para o padrão brasileiro de moeda."""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class TesouroGameView(disnake.ui.View):
    """View do Caça ao Tesouro (Grade 5x5)."""
    def __init__(self, p1: disnake.Member, p2: disnake.Member, aposta: float, msg_game: disnake.Message):
        super().__init__(timeout=60) # 60 segundos de inatividade cancela o jogo
        self.p1 = p1
        self.p2 = p2
        self.aposta = aposta
        self.msg_game = msg_game
        
        self.current_player = random.choice([p1, p2])
        self.points = {p1.id: 0, p2.id: 0}
        self.bananas_found = 0
        self.finalizado = False

        # Gera os 25 itens do campo minado
        # 10 Bananas, 3 Cobras, 12 Vazios
        conteudo = ["banana"] * 10 + ["cobra"] * 3 + ["vazio"] * 12
        random.shuffle(conteudo)
        self.board = conteudo

        # Cria a grade de botões 5x5
        for i in range(25):
            row = i // 5
            btn = disnake.ui.Button(
                style=disnake.ButtonStyle.secondary,
                emoji="❓",
                custom_id=f"btn_{i}",
                row=row
            )
            btn.callback = self.make_callback(i, btn)
            self.add_item(btn)

    def make_callback(self, index: int, button: disnake.ui.Button):
        async def callback(inter: disnake.MessageInteraction):
            if inter.author.id != self.current_player.id:
                return await inter.response.send_message("🐒 Calma aí, não é a sua vez de cavar!", ephemeral=True)

            item = self.board[index]
            button.disabled = True

            if item == "banana":
                button.emoji = "🍌"
                button.style = disnake.ButtonStyle.success
                self.points[inter.author.id] += 1
                self.bananas_found += 1
                acao_msg = f"🍌 **{inter.author.display_name}** achou uma Banana! *(+1 Ponto e joga de novo)*"
                # O turno não muda (quem acha banana joga novamente)
            
            elif item == "cobra":
                button.emoji = "🐍"
                button.style = disnake.ButtonStyle.danger
                if self.points[inter.author.id] > 0:
                    self.points[inter.author.id] -= 1
                acao_msg = f"🐍 **{inter.author.display_name}** foi picado por uma Cobra! *(-1 Ponto e passa a vez)*"
                self.current_player = self.p2 if self.current_player == self.p1 else self.p1
            
            else:
                button.emoji = "🟫"
                button.style = disnake.ButtonStyle.secondary
                acao_msg = f"🟫 **{inter.author.display_name}** só encontrou terra. *(Passa a vez)*"
                self.current_player = self.p2 if self.current_player == self.p1 else self.p1

            if self.bananas_found >= 10:
                self.finalizado = True
                return await self.finalizar_jogo(inter, acao_msg)

            embed = self.msg_game.embeds[0]
            embed.description = f"{acao_msg}\n\nÉ a vez de **{self.current_player.mention}** cavar!"
            embed.set_field_at(0, name=f"👤 {self.p1.display_name}", value=f"🍌 **{self.points[self.p1.id]}**", inline=True)
            embed.set_field_at(1, name=f"👤 {self.p2.display_name}", value=f"🍌 **{self.points[self.p2.id]}**", inline=True)

            await inter.response.edit_message(embed=embed, view=self)

        return callback

    async def finalizar_jogo(self, inter: disnake.MessageInteraction, ultima_acao: str):
        for item in self.children:
            item.disabled = True
            
        pts1 = self.points[self.p1.id]
        pts2 = self.points[self.p2.id]
        premio = round(self.aposta * 2, 2)
        
        if pts1 > pts2:
            vencedor = self.p1
        elif pts2 > pts1:
            vencedor = self.p2
        else:
            vencedor = None # Empate
            
        try:
            u1_db = db.get_user_data(str(self.p1.id))
            u2_db = db.get_user_data(str(self.p2.id))
            
            if vencedor:
                v_db = u1_db if vencedor == self.p1 else u2_db
                saldo = db.parse_float(v_db['data'][2])
                db.update_value(v_db['row'], 3, round(saldo + premio, 2))
                
                desc = f"{ultima_acao}\n\n🗺️ **TODAS AS BANANAS FORAM ENCONTRADAS!**\n🏆 {vencedor.mention} recolheu mais e levou o pote de **{formatar_moeda(premio)} MC**!"
                cor = disnake.Color.green()
            else:
                s1 = db.parse_float(u1_db['data'][2])
                s2 = db.parse_float(u2_db['data'][2])
                db.update_value(u1_db['row'], 3, round(s1 + self.aposta, 2))
                db.update_value(u2_db['row'], 3, round(s2 + self.aposta, 2))
                
                desc = f"{ultima_acao}\n\n🗺️ **TODAS AS BANANAS FORAM ENCONTRADAS!**\n🤝 O jogo terminou em empate! O pote foi dividido e devolvido."
                cor = disnake.Color.yellow()

            embed = disnake.Embed(title="🗺️ CAÇA AO TESOURO FINALIZADA!", description=desc, color=cor)
            embed.add_field(name=f"👤 {self.p1.display_name}", value=f"🍌 **{pts1}**", inline=True)
            embed.add_field(name=f"👤 {self.p2.display_name}", value=f"🍌 **{pts2}**", inline=True)
            
            await inter.response.edit_message(content=f"{self.p1.mention} {self.p2.mention}", embed=embed, view=self)
        except Exception as e:
            print(f"Erro ao finalizar Caça ao Tesouro: {e}")
            await inter.response.edit_message(content="⚠️ Erro ao processar o pagamento!", embed=None, view=self)

    async def on_timeout(self):
        if self.finalizado:
            return

        for item in self.children:
            item.disabled = True
            
        try:
            for p_id in [self.p1.id, self.p2.id]:
                u_db = db.get_user_data(str(p_id))
                if u_db:
                    saldo = db.parse_float(u_db['data'][2])
                    db.update_value(u_db['row'], 3, round(saldo + self.aposta, 2))
            
            embed = self.msg_game.embeds[0]
            embed.title = "⏱️ JOGO CANCELADO"
            embed.description = f"**{self.current_player.display_name}** demorou muito a jogar! O campo minado fechou e as apostas foram devolvidas."
            embed.color = disnake.Color.dark_grey()
            await self.msg_game.edit(embed=embed, view=self)
        except Exception as e:
            print(f"Erro no timeout do Tesouro: {e}")


class TesouroInviteView(disnake.ui.View):
    def __init__(self, ctx, p1: disnake.Member, p2: disnake.Member, aposta: float):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.p1 = p1
        self.p2 = p2
        self.aposta = aposta
        self.aceito = False
        self.msg_invite = None

    @disnake.ui.button(label="Aceitar Duelo", style=disnake.ButtonStyle.success, emoji="🗺️")
    async def btn_aceitar(self, button, inter: disnake.MessageInteraction):
        if inter.author.id != self.p2.id:
            return await inter.response.send_message("Não foi você quem foi desafiado!", ephemeral=True)

        try:
            u1_db = db.get_user_data(str(self.p1.id))
            u2_db = db.get_user_data(str(self.p2.id))

            if not u2_db:
                return await inter.response.send_message("Você não tem conta na selva!", ephemeral=True)

            s1 = db.parse_float(u1_db['data'][2])
            s2 = db.parse_float(u2_db['data'][2])

            if s1 < self.aposta:
                return await inter.response.send_message(f"O saldo de {self.p1.display_name} já não é mais suficiente!", ephemeral=True)
            if s2 < self.aposta:
                return await inter.response.send_message(f"Você não tem os {formatar_moeda(self.aposta)} MC necessários!", ephemeral=True)

            # Desconta o dinheiro
            db.update_value(u1_db['row'], 3, round(s1 - self.aposta, 2))
            db.update_value(u2_db['row'], 3, round(s2 - self.aposta, 2))

            self.aceito = True
            for item in self.children:
                item.disabled = True
            await inter.response.edit_message(content=f"🔥 Desafio aceito! O pote é de **{formatar_moeda(self.aposta * 2)} MC**.", view=self)
            self.stop()

            # Inicia o jogo
            embed_game = disnake.Embed(
                title="🗺️ CAÇA AO TESOURO",
                description=(
                    f"Existem **10 Bananas** (🍌) e **3 Cobras** (🐍) escondidas.\n"
                    f"Quem achar mais bananas leva o pote!\n\n"
                    f"O primeiro a cavar é: **[NOME]**"
                ),
                color=disnake.Color.gold()
            )
            embed_game.add_field(name=f"👤 {self.p1.display_name}", value="🍌 **0**", inline=True)
            embed_game.add_field(name=f"👤 {self.p2.display_name}", value="🍌 **0**", inline=True)

            msg_game = await self.ctx.send(content=f"{self.p1.mention} {self.p2.mention}", embed=embed_game)
            view_game = TesouroGameView(self.p1, self.p2, self.aposta, msg_game)
            
            embed_game.description = embed_game.description.replace("[NOME]", view_game.current_player.mention)
            await msg_game.edit(embed=embed_game, view=view_game)

        except Exception as e:
            print(f"Erro no aceite do Tesouro: {e}")
            await inter.response.send_message("Ocorreu um erro ao processar o banco de dados.", ephemeral=True)

    @disnake.ui.button(label="Recusar", style=disnake.ButtonStyle.danger)
    async def btn_recusar(self, button, inter: disnake.MessageInteraction):
        if inter.author.id != self.p2.id and inter.author.id != self.p1.id:
            return await inter.response.send_message("Isso não é da sua conta!", ephemeral=True)
            
        for item in self.children:
            item.disabled = True
        await inter.response.edit_message(content=f"🏳️ O desafio de exploração foi cancelado por {inter.author.mention}.", view=self)
        self.stop()

    async def on_timeout(self):
        if not self.aceito:
            for item in self.children:
                item.disabled = True
            try:
                await self.msg_invite.edit(content="⏱️ O convite para explorar a selva expirou.", view=self)
            except:
                pass


class Tesouro(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name not in ['🎰・akbet', '🐒・conguitos']:
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"⚠️ {ctx.author.mention}, use os duelos no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["tesouro", "cacar"])
    async def explorar(self, ctx, oponente: disnake.Member = None, aposta: float = None):
        """Desafia um jogador para a Caça ao Tesouro (Mini Campo Minado PvP)."""
        if oponente is None or aposta is None:
            embed = disnake.Embed(
                title="🗺️ CAÇA AO TESOURO — Como funciona",
                description=(
                    "Dois jogadores cavam alternadamente um campo **5×5** (25 casas) escondendo:\n"
                    "🍌 **10 Bananas** — valem +1 ponto e você joga de novo!\n"
                    "🐍 **3 Cobras** — -1 ponto e passa a vez\n"
                    "🟫 **12 Vazios** — nada acontece, passa a vez\n\n"
                    "Quando todas as 10 bananas forem encontradas, quem tiver mais pontos **leva o pote**!\n"
                    "Em caso de empate, a aposta é devolvida para ambos.\n\n"
                    "**Uso:** `!explorar @usuario <valor>`\n"
                    "*Mínimo: 10 MC*"
                ),
                color=disnake.Color.gold()
            )
            return await ctx.send(embed=embed)
        if oponente.id == ctx.author.id:
            return await ctx.send(f"🤡 {ctx.author.mention}, você não pode cavar a terra sozinho!")
        if oponente.bot:
            return await ctx.send(f"🤖 {ctx.author.mention}, bots usam radares, seria injusto.")
        if aposta < 10:
            return await ctx.send("❌ O custo da expedição é de pelo menos **10 MC**.")

        aposta = round(aposta, 2)

        try:
            u1_db = db.get_user_data(str(ctx.author.id))
            if not u1_db:
                return await ctx.send(f"❌ {ctx.author.mention}, você não tem conta!")
                
            s1 = db.parse_float(u1_db['data'][2])
            c1 = u1_db['data'][3] if len(u1_db['data']) > 3 else "Lêmure"
            limite = get_limite(c1)

            if aposta > limite:
                return await ctx.send(f"🚫 O seu limite de expedição para o cargo **{c1}** é de **{formatar_moeda(limite)} MC**!")
            if s1 < aposta:
                return await ctx.send(f"❌ Saldo insuficiente! Você tem apenas **{formatar_moeda(s1)} MC**.")

            u2_db = db.get_user_data(str(oponente.id))
            if not u2_db:
                return await ctx.send(f"❌ {oponente.display_name} não tem uma conta na selva!")
            s2 = db.parse_float(u2_db['data'][2])
            if s2 < aposta:
                return await ctx.send(f"😬 {oponente.display_name} não tem dinheiro suficiente para pagar a expedição.")

            embed = disnake.Embed(
                title="🗺️ DESAFIO: CAÇA AO TESOURO!",
                description=(
                    f"**{ctx.author.mention}** desafiou **{oponente.mention}** para o campo minado da selva!\n\n"
                    f"💰 **Aposta:** `{formatar_moeda(aposta)} MC` (Pote: `{formatar_moeda(aposta * 2)} MC`)\n"
                    f"O desafiado tem 60 segundos para aceitar a expedição."
                ),
                color=disnake.Color.gold()
            )

            view = TesouroInviteView(ctx, ctx.author, oponente, aposta)
            msg = await ctx.send(content=oponente.mention, embed=embed, view=view)
            view.msg_invite = msg

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !explorar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(Tesouro(bot))