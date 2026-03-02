import disnake
from disnake.ext import commands
import database as db
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
    """Formata um float para o padrão brasileiro de moeda. Ex: 1234.56 -> 1.234,56"""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class JokenpoGameView(disnake.ui.View):
    """View onde o jogo realmente acontece (botões de escolha)."""
    def __init__(self, p1: disnake.Member, p2: disnake.Member, aposta: float, msg_game: disnake.Message):
        super().__init__(timeout=45)
        self.p1 = p1
        self.p2 = p2
        self.aposta = aposta
        self.msg_game = msg_game
        
        # Armazena as escolhas: None, "gorila", "cacador" ou "casca"
        self.choices = {p1.id: None, p2.id: None}
        self.finalizado = False

    async def registrar_escolha(self, inter: disnake.MessageInteraction, escolha: str, emoji: str):
        if inter.author.id not in self.choices:
            return await inter.response.send_message("🐒 Você não faz parte deste duelo!", ephemeral=True)
            
        if self.choices[inter.author.id] is not None:
            return await inter.response.send_message("⚠️ Você já fez sua escolha! Aguarde o adversário.", ephemeral=True)

        self.choices[inter.author.id] = escolha
        await inter.response.send_message(f"Você escolheu secretamente: {emoji} **{escolha.capitalize()}**!", ephemeral=True)

        # Se ambos escolheram, resolvemos o jogo
        if all(c is not None for c in self.choices.values()):
            self.finalizado = True
            self.stop()
            await self.resolver_duelo()

    @disnake.ui.button(label="Gorila", emoji="🦍", style=disnake.ButtonStyle.primary)
    async def btn_gorila(self, button, inter):
        await self.registrar_escolha(inter, "gorila", "🦍")

    @disnake.ui.button(label="Caçador", emoji="🤠", style=disnake.ButtonStyle.danger)
    async def btn_cacador(self, button, inter):
        await self.registrar_escolha(inter, "cacador", "🤠")

    @disnake.ui.button(label="Casca", emoji="🍌", style=disnake.ButtonStyle.success)
    async def btn_casca(self, button, inter):
        await self.registrar_escolha(inter, "casca", "🍌")

    async def on_timeout(self):
        if self.finalizado:
            return

        # Se o tempo acabar e alguém não jogou, devolvemos o dinheiro para ser justo
        for item in self.children:
            item.disabled = True
            
        try:
            for p_id in [self.p1.id, self.p2.id]:
                u_db = db.get_user_data(str(p_id))
                if u_db:
                    saldo = db.parse_float(u_db['data'][2])
                    db.update_value(u_db['row'], 3, round(saldo + self.aposta, 2))
            
            embed = disnake.Embed(
                title="⏱️ DUELO CANCELADO",
                description="O tempo esgotou antes que ambos escolhessem. O dinheiro foi devolvido.",
                color=disnake.Color.dark_grey()
            )
            await self.msg_game.edit(embed=embed, view=self)
        except Exception as e:
            print(f"Erro no timeout do Jokenpo: {e}")

    async def resolver_duelo(self):
        c1 = self.choices[self.p1.id]
        c2 = self.choices[self.p2.id]
        
        emojis = {"gorila": "🦍", "cacador": "🤠", "casca": "🍌"}
        
        vencedor = None
        motivo = ""
        
        if c1 == c2:
            vencedor = "empate"
            motivo = "Empate técnico! Ninguém se machucou."
        elif (c1 == "gorila" and c2 == "cacador"):
            vencedor = self.p1
            motivo = "🦍 O Gorila amassou o Caçador!"
        elif (c1 == "cacador" and c2 == "casca"):
            vencedor = self.p1
            motivo = "🤠 O Caçador atirou e destruiu a Casca de Banana!"
        elif (c1 == "casca" and c2 == "gorila"):
            vencedor = self.p1
            motivo = "🍌 O Gorila escorregou na Casca e quebrou a cabeça!"
        elif (c2 == "gorila" and c1 == "cacador"):
            vencedor = self.p2
            motivo = "🦍 O Gorila amassou o Caçador!"
        elif (c2 == "cacador" and c1 == "casca"):
            vencedor = self.p2
            motivo = "🤠 O Caçador atirou e destruiu a Casca de Banana!"
        elif (c2 == "casca" and c1 == "gorila"):
            vencedor = self.p2
            motivo = "🍌 O Gorila escorregou na Casca e quebrou a cabeça!"

        for item in self.children:
            item.disabled = True

        try:
            u1_db = db.get_user_data(str(self.p1.id))
            u2_db = db.get_user_data(str(self.p2.id))
            
            s1 = db.parse_float(u1_db['data'][2])
            s2 = db.parse_float(u2_db['data'][2])

            if vencedor == "empate":
                # Devolve o dinheiro
                db.update_value(u1_db['row'], 3, round(s1 + self.aposta, 2))
                db.update_value(u2_db['row'], 3, round(s2 + self.aposta, 2))
                
                embed = disnake.Embed(title="🤝 EMPATE!", description=motivo, color=disnake.Color.yellow())
                embed.add_field(name=self.p1.display_name, value=f"{emojis[c1]} {c1.capitalize()}", inline=True)
                embed.add_field(name=self.p2.display_name, value=f"{emojis[c2]} {c2.capitalize()}", inline=True)
                embed.set_footer(text="As apostas foram devolvidas.")
                
            else:
                perdedor = self.p2 if vencedor == self.p1 else self.p1
                v_db = u1_db if vencedor == self.p1 else u2_db
                p_db = u2_db if vencedor == self.p1 else u1_db
                
                s_v = db.parse_float(v_db['data'][2])
                premio = round(self.aposta * 2, 2)
                
                # O perdedor já teve o dinheiro descontado no convite. Só pagamos o vencedor.
                db.update_value(v_db['row'], 3, round(s_v + premio, 2))
                
                embed = disnake.Embed(title=f"🏆 {vencedor.display_name} VENCEU!", description=motivo, color=disnake.Color.green())
                embed.add_field(name=self.p1.display_name, value=f"{emojis[c1]} {c1.capitalize()}", inline=True)
                embed.add_field(name="vs", value="⚔️", inline=True)
                embed.add_field(name=self.p2.display_name, value=f"{emojis[c2]} {c2.capitalize()}", inline=True)
                embed.add_field(name="💰 Prêmio", value=f"**{formatar_moeda(premio)} MC**", inline=False)
                
            await self.msg_game.edit(content=f"{self.p1.mention} {self.p2.mention}", embed=embed, view=self)

        except Exception as e:
            print(f"Erro no pagamento do Jokenpo: {e}")
            await self.msg_game.edit(content="⚠️ Ocorreu um erro no banco durante o pagamento!", view=None)


class JokenpoInviteView(disnake.ui.View):
    """View para o adversário aceitar ou recusar o desafio."""
    def __init__(self, ctx, p1: disnake.Member, p2: disnake.Member, aposta: float):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.p1 = p1
        self.p2 = p2
        self.aposta = aposta
        self.aceito = False
        self.msg_invite = None

    @disnake.ui.button(label="Aceitar Duelo", style=disnake.ButtonStyle.success, emoji="⚔️")
    async def btn_aceitar(self, button, inter: disnake.MessageInteraction):
        if inter.author.id != self.p2.id:
            return await inter.response.send_message("Você não foi o desafiado!", ephemeral=True)

        try:
            u1_db = db.get_user_data(str(self.p1.id))
            u2_db = db.get_user_data(str(self.p2.id))

            if not u2_db:
                return await inter.response.send_message("Você não tem conta na selva! Use `!trabalhar`.", ephemeral=True)

            s1 = db.parse_float(u1_db['data'][2])
            s2 = db.parse_float(u2_db['data'][2])

            # Re-checagem de saldo do P1 e P2 para evitar fraudes entre o convite e o aceite
            if s1 < self.aposta:
                return await inter.response.send_message(f"O saldo de {self.p1.display_name} já não é mais suficiente!", ephemeral=True)
            if s2 < self.aposta:
                return await inter.response.send_message(f"Você não tem {formatar_moeda(self.aposta)} MC para cobrir a aposta!", ephemeral=True)

            # Debita a aposta de AMBOS e o pote vai para o limbo (bot) temporariamente
            db.update_value(u1_db['row'], 3, round(s1 - self.aposta, 2))
            db.update_value(u2_db['row'], 3, round(s2 - self.aposta, 2))

            self.aceito = True
            for item in self.children:
                item.disabled = True
            await inter.response.edit_message(content=f"🔥 Duelo aceito! O pote tem **{formatar_moeda(self.aposta * 2)} MC**.", view=self)
            self.stop()

            # Inicia o jogo
            embed_game = disnake.Embed(
                title="⚔️ DUELO NA SELVA: GORILA, CAÇADOR OU CASCA?",
                description=(
                    f"{self.p1.mention} vs {self.p2.mention}\\n\\n"
                    "**REGRAS:**\\n"
                    "🦍 **Gorila** amassa o 🤠 **Caçador**.\\n"
                    "🤠 **Caçador** atira na 🍌 **Casca**.\\n"
                    "🍌 **Casca** derruba o 🦍 **Gorila**.\\n\\n"
                    "*Façam suas escolhas nos botões abaixo! O outro jogador não verá sua escolha.*"
                ),
                color=disnake.Color.orange()
            )
            msg_game = await self.ctx.send(content=f"{self.p1.mention} {self.p2.mention}", embed=embed_game)
            view_game = JokenpoGameView(self.p1, self.p2, self.aposta, msg_game)
            await msg_game.edit(view=view_game)

        except Exception as e:
            print(f"Erro no aceite do Jokenpo: {e}")
            await inter.response.send_message("Ocorreu um erro no banco de dados.", ephemeral=True)

    @disnake.ui.button(label="Recusar", style=disnake.ButtonStyle.danger)
    async def btn_recusar(self, button, inter: disnake.MessageInteraction):
        if inter.author.id != self.p2.id and inter.author.id != self.p1.id:
            return await inter.response.send_message("Isso não é da sua conta!", ephemeral=True)
            
        for item in self.children:
            item.disabled = True
        await inter.response.edit_message(content=f"🏳️ O duelo foi cancelado por {inter.author.mention}.", view=self)
        self.stop()

    async def on_timeout(self):
        if not self.aceito:
            for item in self.children:
                item.disabled = True
            try:
                await self.msg_invite.edit(content="⏱️ O tempo para aceitar o duelo expirou.", view=self)
            except:
                pass


class Jokenpo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name not in ['🎰・akbet', '🐒・conguitos']:
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"⚠️ {ctx.author.mention}, use os duelos no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["jokenpo", "jkp"])
    async def duelo(self, ctx, oponente: disnake.Member = None, aposta: float = None):
        """Desafia um jogador para o Jokenpô da Selva (Gorila, Caçador, Casca)."""
        if oponente is None or aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!duelo @usuario <valor>`")
        if oponente.id == ctx.author.id:
            return await ctx.send(f"🤡 {ctx.author.mention}, você não pode duelar contra si mesmo!")
        if oponente.bot:
            return await ctx.send(f"🤖 {ctx.author.mention}, bots não têm dinheiro nem sentimentos.")
        if aposta < 10:
            return await ctx.send("❌ O valor mínimo para duelo é de **10 MC**.")

        aposta = round(aposta, 2)

        try:
            u1_db = db.get_user_data(str(ctx.author.id))
            if not u1_db:
                return await ctx.send(f"❌ {ctx.author.mention}, você não tem conta!")
                
            s1 = db.parse_float(u1_db['data'][2])
            c1 = u1_db['data'][3] if len(u1_db['data']) > 3 else "Lêmure"
            limite = get_limite(c1)

            if aposta > limite:
                return await ctx.send(f"🚫 Seu limite de aposta para o cargo **{c1}** é de **{formatar_moeda(limite)} MC**!")
            if s1 < aposta:
                return await ctx.send(f"❌ Saldo insuficiente! Você tem apenas **{formatar_moeda(s1)} MC**.")

            u2_db = db.get_user_data(str(oponente.id))
            if not u2_db:
                return await ctx.send(f"❌ {oponente.display_name} não tem uma conta na selva!")
            s2 = db.parse_float(u2_db['data'][2])
            if s2 < aposta:
                return await ctx.send(f"😬 {oponente.display_name} não tem dinheiro suficiente para cobrir essa aposta.")

            embed = disnake.Embed(
                title="⚔️ DESAFIO DE JOKENPÔ DA SELVA!",
                description=(
                    f"**{ctx.author.mention}** desafiou **{oponente.mention}** para um duelo!\n\n"
                    f"💰 **Aposta:** `{formatar_moeda(aposta)} MC` (Pote: `{formatar_moeda(aposta * 2)} MC`)\n"
                    f"O desafiado tem 60 segundos para aceitar."
                ),
                color=disnake.Color.blue()
            )
            embed.set_thumbnail(url="https://i.imgur.com/02a5A3g.png") # Link genérico de espadas (pode trocar depois se quiser)

            view = JokenpoInviteView(ctx, ctx.author, oponente, aposta)
            msg = await ctx.send(content=oponente.mention, embed=embed, view=view)
            view.msg_invite = msg

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !duelo de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(Jokenpo(bot))