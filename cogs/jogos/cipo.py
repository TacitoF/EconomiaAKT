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
    """Formata um float para o padrão brasileiro de moeda. Ex: 1234.56 -> 1.234,56"""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class CipoGameView(disnake.ui.View):
    """View do jogo Cipó Podre com os turnos alternados."""
    def __init__(self, p1: disnake.Member, p2: disnake.Member, aposta: float, msg_game: disnake.Message):
        super().__init__(timeout=45)
        self.p1 = p1
        self.p2 = p2
        self.aposta = aposta
        self.msg_game = msg_game
        
        # Decide aleatoriamente quem começa
        self.current_player = random.choice([p1, p2])
        # Sorteia qual será o cipó fatal (de 0 a 5)
        self.rotten_idx = random.randint(0, 5)
        self.finalizado = False

        # Cria os 6 botões (cipós) dinamicamente
        for i in range(6):
            btn = disnake.ui.Button(
                style=disnake.ButtonStyle.secondary,
                label=f"Cipó {i+1}",
                emoji="🌿",
                custom_id=f"cipo_{i}",
                row=0 if i < 3 else 1  # 3 botões em cima, 3 em baixo
            )
            btn.callback = self.make_callback(i, btn)
            self.add_item(btn)

    def make_callback(self, index: int, button: disnake.ui.Button):
        async def callback(inter: disnake.MessageInteraction):
            if inter.author.id != self.current_player.id:
                return await inter.response.send_message("🐒 Calma aí, ainda não é a sua vez de pular!", ephemeral=True)

            if index == self.rotten_idx:
                # 💥 CIPÓ PODRE! O jogador cai e perde.
                self.finalizado = True
                button.style = disnake.ButtonStyle.danger
                button.emoji = "💥"
                button.disabled = True
                
                # Desativa todos os outros botões
                for item in self.children:
                    item.disabled = True
                self.stop()
                await self.resolver_vitoria(inter, perdedor=self.current_player)
            else:
                # 🍃 CIPÓ SEGURO!
                button.style = disnake.ButtonStyle.success
                button.emoji = "🍃"
                button.disabled = True
                
                # Troca o turno para o adversário
                self.current_player = self.p2 if self.current_player == self.p1 else self.p1
                
                embed = self.msg_game.embeds[0]
                embed.description = f"Ufa! O cipó aguentou o peso.\n\nAgora é a vez de **{self.current_player.mention}** pular!"
                await inter.response.edit_message(embed=embed, view=self)

        return callback

    async def resolver_vitoria(self, inter: disnake.MessageInteraction, perdedor: disnake.Member):
        vencedor = self.p1 if perdedor == self.p2 else self.p2
        premio = round(self.aposta * 2, 2)

        try:
            # O dinheiro de ambos já foi descontado no convite. Basta dar o pote ao vencedor.
            u_vencedor = db.get_user_data(str(vencedor.id))
            if u_vencedor:
                saldo = db.parse_float(u_vencedor['data'][2])
                db.update_value(u_vencedor['row'], 3, round(saldo + premio, 2))

            embed = disnake.Embed(
                title="💥 CRAAAACK! O CIPÓ QUEBROU!",
                description=(
                    f"**{perdedor.mention}** agarrou-se no cipó podre e caiu no abismo da selva!\n\n"
                    f"🏆 **{vencedor.mention}** sobreviveu e levou o pote de **{formatar_moeda(premio)} MC**!"
                ),
                color=disnake.Color.red()
            )
            await inter.response.edit_message(content=f"{self.p1.mention} {self.p2.mention}", embed=embed, view=self)
        except Exception as e:
            print(f"Erro ao pagar o Cipó Podre: {e}")
            await inter.response.send_message("⚠️ Ocorreu um erro no banco durante o pagamento!", ephemeral=True)

    async def on_timeout(self):
        if self.finalizado:
            return

        # Se alguém demorar muito, o jogo é cancelado e o dinheiro devolvido para evitar perdas injustas.
        for item in self.children:
            item.disabled = True
            
        try:
            for p_id in [self.p1.id, self.p2.id]:
                u_db = db.get_user_data(str(p_id))
                if u_db:
                    saldo = db.parse_float(u_db['data'][2])
                    db.update_value(u_db['row'], 3, round(saldo + self.aposta, 2))
            
            embed = self.msg_game.embeds[0]
            embed.title = "⏱️ DUELO CANCELADO"
            embed.description = f"**{self.current_player.display_name}** demorou muito tempo para pular! O jogo foi anulado e as apostas devolvidas."
            embed.color = disnake.Color.dark_grey()
            await self.msg_game.edit(embed=embed, view=self)
        except Exception as e:
            print(f"Erro no timeout do Cipó Podre: {e}")


class CipoInviteView(disnake.ui.View):
    """View para o adversário aceitar ou recusar o desafio do Cipó Podre."""
    def __init__(self, ctx, p1: disnake.Member, p2: disnake.Member, aposta: float):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.p1 = p1
        self.p2 = p2
        self.aposta = aposta
        self.aceito = False
        self.msg_invite = None

    @disnake.ui.button(label="Aceitar Duelo", style=disnake.ButtonStyle.success, emoji="🌿")
    async def btn_aceitar(self, button, inter: disnake.MessageInteraction):
        if inter.author.id != self.p2.id:
            return await inter.response.send_message("Não foi você o desafiado!", ephemeral=True)

        try:
            u1_db = db.get_user_data(str(self.p1.id))
            u2_db = db.get_user_data(str(self.p2.id))

            if not u2_db:
                return await inter.response.send_message("Você não tem uma conta na selva! Use `!trabalhar`.", ephemeral=True)

            s1 = db.parse_float(u1_db['data'][2])
            s2 = db.parse_float(u2_db['data'][2])

            # Confirma os saldos no exato momento do aceite
            if s1 < self.aposta:
                return await inter.response.send_message(f"O saldo de {self.p1.display_name} já não é suficiente!", ephemeral=True)
            if s2 < self.aposta:
                return await inter.response.send_message(f"Você não tem os {formatar_moeda(self.aposta)} MC necessários para cobrir a aposta!", ephemeral=True)

            # Debita a aposta de AMBOS
            db.update_value(u1_db['row'], 3, round(s1 - self.aposta, 2))
            db.update_value(u2_db['row'], 3, round(s2 - self.aposta, 2))

            self.aceito = True
            for item in self.children:
                item.disabled = True
            await inter.response.edit_message(content=f"🔥 Duelo aceito! O pote tem **{formatar_moeda(self.aposta * 2)} MC**.", view=self)
            self.stop()

            # Inicia o jogo
            embed_game = disnake.Embed(
                title="🌿 SALTO DO CIPÓ PODRE",
                description=(
                    f"Bem-vindos ao penhasco!\n\n"
                    f"Existem 6 cipós pendurados, mas **1 deles está podre**.\n"
                    f"Quem pular no cipó errado, cai. Quem sobreviver, leva tudo.\n\n"
                    f"É a vez de **{self.p1.mention if random.choice([True, False]) else self.p2.mention}** pular primeiro!"
                ),
                color=disnake.Color.green()
            )
            msg_game = await self.ctx.send(content=f"{self.p1.mention} {self.p2.mention}", embed=embed_game)
            view_game = CipoGameView(self.p1, self.p2, self.aposta, msg_game)
            
            # Atualiza a descrição com o jogador sorteado corretamente
            embed_game.description = embed_game.description.replace(
                f"É a vez de **{self.p1.mention if random.choice([True, False]) else self.p2.mention}**",
                f"É a vez de **{view_game.current_player.mention}**"
            )
            await msg_game.edit(embed=embed_game, view=view_game)

        except Exception as e:
            print(f"Erro no aceite do Cipó Podre: {e}")
            await inter.response.send_message("Ocorreu um erro na base de dados.", ephemeral=True)

    @disnake.ui.button(label="Recusar", style=disnake.ButtonStyle.danger)
    async def btn_recusar(self, button, inter: disnake.MessageInteraction):
        if inter.author.id != self.p2.id and inter.author.id != self.p1.id:
            return await inter.response.send_message("Isso não é da sua conta!", ephemeral=True)
            
        for item in self.children:
            item.disabled = True
        await inter.response.edit_message(content=f"🏳️ O desafio do cipó foi recusado por {inter.author.mention}.", view=self)
        self.stop()

    async def on_timeout(self):
        if not self.aceito:
            for item in self.children:
                item.disabled = True
            try:
                await self.msg_invite.edit(content="⏱️ O tempo para aceitar o pulo expirou.", view=self)
            except:
                pass


class CipoPodre(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name not in ['🎰・akbet', '🐒・conguitos']:
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"⚠️ {ctx.author.mention}, use os duelos no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["cipo", "cipó"])
    async def cipopodre(self, ctx, oponente: disnake.Member = None, aposta: float = None):
        """Desafia um jogador para a Roleta do Cipó Podre."""
        if oponente is None or aposta is None:
            embed = disnake.Embed(
                title="🌿 CIPÓ PODRE — Como funciona",
                description=(
                    "Dois jogadores se revezam escolhendo um dos **6 cipós** pendurados no penhasco.\n"
                    "Um deles está podre. Quem agarrar o cipó errado **cai** e perde!\n"
                    "O sobrevivente leva o pote inteiro.\n\n"
                    "**Dinâmica:** É sua vez → clique em um cipó → se aguentar, passa para o adversário.\n"
                    "O cipó podre é sorteado aleatoriamente e ninguém sabe qual é.\n\n"
                    "**Uso:** `!cipo @usuario <valor>`\n"
                    "*Mínimo: 10 MC*"
                ),
                color=disnake.Color.green()
            )
            return await ctx.send(embed=embed)
        if oponente.id == ctx.author.id:
            return await ctx.send(f"🤡 {ctx.author.mention}, você não pode pular sozinho contra si mesmo!")
        if oponente.bot:
            return await ctx.send(f"🤖 {ctx.author.mention}, os bots flutuam, não caem em penhascos.")
        if aposta < 10:
            return await ctx.send("❌ A aposta mínima para pular no cipó é de **10 MC**.")

        aposta = round(aposta, 2)

        try:
            u1_db = db.get_user_data(str(ctx.author.id))
            if not u1_db:
                return await ctx.send(f"❌ {ctx.author.mention}, você não tem conta!")
                
            s1 = db.parse_float(u1_db['data'][2])
            c1 = u1_db['data'][3] if len(u1_db['data']) > 3 else "Lêmure"
            limite = get_limite(c1)

            if aposta > limite:
                return await ctx.send(f"🚫 O seu limite de aposta para o cargo **{c1}** é de **{formatar_moeda(limite)} MC**!")
            if s1 < aposta:
                return await ctx.send(f"❌ Saldo insuficiente! Você tem apenas **{formatar_moeda(s1)} MC**.")

            u2_db = db.get_user_data(str(oponente.id))
            if not u2_db:
                return await ctx.send(f"❌ {oponente.display_name} não tem uma conta na selva!")
            s2 = db.parse_float(u2_db['data'][2])
            if s2 < aposta:
                return await ctx.send(f"😬 {oponente.display_name} não tem dinheiro suficiente para cobrir este salto.")

            embed = disnake.Embed(
                title="🌿 DESAFIO DO CIPÓ PODRE!",
                description=(
                    f"**{ctx.author.mention}** desafiou **{oponente.mention}** para atravessar o penhasco!\n\n"
                    f"💰 **Aposta:** `{formatar_moeda(aposta)} MC` (Pote: `{formatar_moeda(aposta * 2)} MC`)\n"
                    f"O desafiado tem 60 segundos para criar coragem e aceitar."
                ),
                color=disnake.Color.green()
            )

            view = CipoInviteView(ctx, ctx.author, oponente, aposta)
            msg = await ctx.send(content=oponente.mention, embed=embed, view=view)
            view.msg_invite = msg

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !cipo de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(CipoPodre(bot))