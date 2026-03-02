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
    """Formata um float para o padrão de moeda. Ex: 1234.56 -> 1.234,56"""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class GatilhoGameView(disnake.ui.View):
    """View do Duelo de Reflexos."""
    def __init__(self, p1: disnake.Member, p2: disnake.Member, aposta: float, msg_game: disnake.Message):
        super().__init__(timeout=45)
        self.p1 = p1
        self.p2 = p2
        self.aposta = aposta
        self.msg_game = msg_game
        
        self.estado = "aguardar"  # "aguardar" ou "atirar"
        self.finalizado = False

    @disnake.ui.button(label="Aguarde...", style=disnake.ButtonStyle.secondary, custom_id="btn_shoot")
    async def btn_shoot(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        # Verifica se é um dos duelistas
        if inter.author.id not in [self.p1.id, self.p2.id]:
            return await inter.response.send_message("🐒 Você não está neste duelo! Afaste-se da linha de fogo.", ephemeral=True)

        if self.finalizado:
            return await inter.response.send_message("O duelo já acabou!", ephemeral=True)

        self.finalizado = True
        self.stop()

        if self.estado == "aguardar":
            # FALSA PARTIDA! Clicou antes do tempo.
            atirador_id = inter.author.id
            await self.resolver_jogo(inter, atirador_id, falsa_partida=True)
        elif self.estado == "atirar":
            # TIRO VÁLIDO! O primeiro a clicar ganha.
            atirador_id = inter.author.id
            await self.resolver_jogo(inter, atirador_id, falsa_partida=False)

    async def iniciar_sequencia(self):
        """Inicia o temporizador aleatório e muda o botão para ATIRAR."""
        atraso = random.uniform(4.0, 12.0)
        await asyncio.sleep(atraso)

        if self.finalizado:
            return  # Alguém já fez falsa partida

        self.estado = "atirar"
        
        # Atualiza o botão para o modo de tiro
        botao = self.children[0]
        botao.label = "💥 ATIRAR!"
        botao.style = disnake.ButtonStyle.danger

        embed = self.msg_game.embeds[0]
        embed.title = "💥 ATIREM AGORA!"
        embed.description = f"{self.p1.mention} e {self.p2.mention}, cliquem no botão o mais rápido que conseguirem!"
        embed.color = disnake.Color.red()

        try:
            await self.msg_game.edit(embed=embed, view=self)
        except Exception as e:
            print(f"Erro ao atualizar botão do gatilho: {e}")

    async def resolver_jogo(self, inter: disnake.MessageInteraction, atirador_id: int, falsa_partida: bool):
        # Desativa o botão
        self.children[0].disabled = True

        premio = round(self.aposta * 2, 2)
        
        if falsa_partida:
            perdedor = self.p1 if atirador_id == self.p1.id else self.p2
            vencedor = self.p2 if atirador_id == self.p1.id else self.p1
            
            titulo = "❌ FALSA PARTIDA!"
            desc = (
                f"**{perdedor.mention}** foi impaciente, tentou atirar cedo demais e a arma travou!\n\n"
                f"🏆 **{vencedor.mention}** ganha por desclassificação e leva os **{formatar_moeda(premio)} MC**!"
            )
            cor = disnake.Color.orange()
        else:
            vencedor = self.p1 if atirador_id == self.p1.id else self.p2
            perdedor = self.p2 if atirador_id == self.p1.id else self.p1
            
            titulo = "🔫 GATILHO MAIS RÁPIDO DA SELVA!"
            desc = (
                f"**{vencedor.mention}** sacou a arma em uma fração de segundo e eliminou {perdedor.mention}!\n\n"
                f"🏆 Prêmio total acumulado: **{formatar_moeda(premio)} MC**!"
            )
            cor = disnake.Color.green()

        try:
            u_vencedor = db.get_user_data(str(vencedor.id))
            if u_vencedor:
                saldo = db.parse_float(u_vencedor['data'][2])
                db.update_value(u_vencedor['row'], 3, round(saldo + premio, 2))

            embed = disnake.Embed(title=titulo, description=desc, color=cor)
            await inter.response.edit_message(content=f"{self.p1.mention} {self.p2.mention}", embed=embed, view=self)

        except Exception as e:
            print(f"Erro ao pagar o Gatilho Rápido: {e}")
            await inter.response.edit_message(content="⚠️ Ocorreu um erro no banco durante o pagamento!", embed=None, view=self)

    async def on_timeout(self):
        if self.finalizado:
            return

        # Se passaram 45 segundos e ninguém atirou, devolve o dinheiro
        self.children[0].disabled = True
        try:
            for p_id in [self.p1.id, self.p2.id]:
                u_db = db.get_user_data(str(p_id))
                if u_db:
                    saldo = db.parse_float(u_db['data'][2])
                    db.update_value(u_db['row'], 3, round(saldo + self.aposta, 2))
            
            embed = self.msg_game.embeds[0]
            embed.title = "⏱️ DUELO ADORMECIDO"
            embed.description = "Os dois dormiram com a mão na arma. O duelo foi cancelado e o dinheiro devolvido."
            embed.color = disnake.Color.dark_grey()
            await self.msg_game.edit(embed=embed, view=self)
        except Exception as e:
            print(f"Erro no timeout do Gatilho: {e}")


class GatilhoInviteView(disnake.ui.View):
    """View para o adversário aceitar ou recusar o duelo."""
    def __init__(self, ctx, p1: disnake.Member, p2: disnake.Member, aposta: float):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.p1 = p1
        self.p2 = p2
        self.aposta = aposta
        self.aceito = False
        self.msg_invite = None

    @disnake.ui.button(label="Aceitar Duelo", style=disnake.ButtonStyle.success, emoji="🔫")
    async def btn_aceitar(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id != self.p2.id:
            return await inter.response.send_message("Não foi você o desafiado!", ephemeral=True)

        try:
            u1_db = db.get_user_data(str(self.p1.id))
            u2_db = db.get_user_data(str(self.p2.id))

            if not u2_db:
                return await inter.response.send_message("Você não tem conta na selva!", ephemeral=True)

            s1 = db.parse_float(u1_db['data'][2])
            s2 = db.parse_float(u2_db['data'][2])

            if s1 < self.aposta:
                return await inter.response.send_message(f"O saldo de {self.p1.display_name} já não é suficiente!", ephemeral=True)
            if s2 < self.aposta:
                return await inter.response.send_message(f"Você não tem os {formatar_moeda(self.aposta)} MC necessários!", ephemeral=True)

            # Desconta o dinheiro
            db.update_value(u1_db['row'], 3, round(s1 - self.aposta, 2))
            db.update_value(u2_db['row'], 3, round(s2 - self.aposta, 2))

            self.aceito = True
            for item in self.children:
                item.disabled = True
            await inter.response.edit_message(content=f"🔥 Duelo aceito! O pote é de **{formatar_moeda(self.aposta * 2)} MC**.", view=self)
            self.stop()

            # Inicia o jogo
            embed_game = disnake.Embed(
                title="🤠 DUELO: PREPAREM-SE...",
                description=(
                    f"{self.p1.mention} vs {self.p2.mention}\n\n"
                    f"Fiquem atentos ao botão abaixo.\n"
                    f"**ATENÇÃO:** Se vocês clicarem *antes* da ordem, a arma de vocês trava e vocês perdem!\n\n"
                    f"Aguardem o sinal..."
                ),
                color=disnake.Color.dark_grey()
            )
            
            msg_game = await self.ctx.send(content=f"{self.p1.mention} {self.p2.mention}", embed=embed_game)
            view_game = GatilhoGameView(self.p1, self.p2, self.aposta, msg_game)
            await msg_game.edit(view=view_game)

            # Dispara a tarefa assíncrona que vai mudar o botão depois de um tempo aleatório
            self.ctx.bot.loop.create_task(view_game.iniciar_sequencia())

        except Exception as e:
            print(f"Erro no aceite do Gatilho: {e}")
            await inter.response.send_message("Ocorreu um erro na base de dados.", ephemeral=True)

    @disnake.ui.button(label="Recusar", style=disnake.ButtonStyle.danger)
    async def btn_recusar(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id != self.p2.id and inter.author.id != self.p1.id:
            return await inter.response.send_message("Isso não é da sua conta!", ephemeral=True)
            
        for item in self.children:
            item.disabled = True
        await inter.response.edit_message(content=f"🏳️ O duelo foi recusado por {inter.author.mention}.", view=self)
        self.stop()

    async def on_timeout(self):
        if not self.aceito:
            for item in self.children:
                item.disabled = True
            try:
                await self.msg_invite.edit(content="⏱️ O desafiado teve medo e o tempo esgotou.", view=self)
            except:
                pass


class GatilhoRapido(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name not in ['🎰・akbet', '🐒・conguitos']:
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"⚠️ {ctx.author.mention}, use os duelos no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["gatilho", "duelar_tiro", "reflexo"])
    async def bang(self, ctx, oponente: disnake.Member = None, aposta: float = None):
        """Desafia um jogador para um duelo de velocidade (quem clicar primeiro ganha)."""
        if oponente is None or aposta is None:
            embed = disnake.Embed(
                title="🔫 GATILHO RÁPIDO — Como funciona",
                description=(
                    "Um duelo de reflexos entre dois jogadores.\n"
                    "Ambos veem o botão **Aguarde...**. Em algum momento aleatório (entre 4 e 12 segundos), "
                    "ele muda para **💥 ATIRAR!**.\n\n"
                    "⚠️ **Clicar antes do sinal = Falsa Partida = você perde automaticamente!**\n"
                    "✅ **Quem clicar primeiro após o sinal vence e leva o pote.**\n\n"
                    "**Uso:** `!bang @usuario <valor>`\n"
                    "*Mínimo: 10 MC*"
                ),
                color=disnake.Color.dark_red()
            )
            return await ctx.send(embed=embed)
        if oponente.id == ctx.author.id:
            return await ctx.send(f"🤡 {ctx.author.mention}, você não pode atirar em si mesmo!")
        if oponente.bot:
            return await ctx.send(f"🤖 {ctx.author.mention}, os bots têm 0ms de ping, você ia perder com certeza.")
        if aposta < 10:
            return await ctx.send("❌ O valor mínimo para o duelo de reflexos é **10 MC**.")

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
                return await ctx.send(f"😬 {oponente.display_name} não tem dinheiro suficiente para cobrir este duelo.")

            embed = disnake.Embed(
                title="🔫 DUELO DE REFLEXOS!",
                description=(
                    f"**{ctx.author.mention}** sacou da luva e desafiou **{oponente.mention}** para um Gatilho Rápido!\n\n"
                    f"💰 **Aposta:** `{formatar_moeda(aposta)} MC` (Pote: `{formatar_moeda(aposta * 2)} MC`)\n"
                    f"Aceita testar o seu tempo de reação?"
                ),
                color=disnake.Color.dark_red()
            )

            view = GatilhoInviteView(ctx, ctx.author, oponente, aposta)
            msg = await ctx.send(content=oponente.mention, embed=embed, view=view)
            view.msg_invite = msg

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !bang de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(GatilhoRapido(bot))