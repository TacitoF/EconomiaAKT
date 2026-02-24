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


class AceitarView(disnake.ui.View):
    """View genérica de aceitar/recusar desafio PvP."""
    def __init__(self, oponente: disnake.Member, aposta: float, modo: str):
        super().__init__(timeout=30)
        self.oponente = oponente
        self.aposta = aposta
        self.modo = modo  # "carta" ou "briga"
        self.aceito = False

    @disnake.ui.button(label="✅ Aceitar", style=disnake.ButtonStyle.success)
    async def aceitar(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id != self.oponente.id:
            return await inter.response.send_message("❌ Esse desafio não é para você!", ephemeral=True)
        self.aceito = True
        for item in self.children:
            item.disabled = True
        await inter.response.edit_message(view=self)
        self.stop()

    @disnake.ui.button(label="❌ Recusar", style=disnake.ButtonStyle.danger)
    async def recusar(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id != self.oponente.id:
            return await inter.response.send_message("❌ Esse desafio não é para você!", ephemeral=True)
        for item in self.children:
            item.disabled = True
        await inter.response.edit_message(view=self)
        self.stop()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class PvP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, resolva suas rixas no canal {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["cartas", "duelo_carta", "draw"])
    async def carta(self, ctx, oponente: disnake.Member = None, aposta: float = None):
        if oponente is None or aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!carta @usuario <valor>`")
        if oponente.id == ctx.author.id:
            return await ctx.send(f"🃏 {ctx.author.mention}, você não pode jogar contra o espelho!")
        if aposta <= 0:
            return await ctx.send(f"❌ {ctx.author.mention}, a aposta deve ser maior que zero!")
        aposta = round(aposta, 2)

        try:
            desafiante_db = db.get_user_data(str(ctx.author.id))
            oponente_db = db.get_user_data(str(oponente.id))
            if not desafiante_db or not oponente_db:
                return await ctx.send("❌ Uma das contas não foi encontrada!")

            saldo_d = db.parse_float(desafiante_db['data'][2])
            saldo_o = db.parse_float(oponente_db['data'][2])

            if saldo_d < aposta or saldo_o < aposta:
                return await ctx.send(f"❌ Alguém não tem saldo suficiente para cobrir a aposta!")

            cargo_d = desafiante_db['data'][3] if len(desafiante_db['data']) > 3 else "Lêmure"
            if aposta > get_limite(cargo_d):
                return await ctx.send(f"🚫 Limite de aposta para **{cargo_d}** é de **{get_limite(cargo_d)} C**!")

            view = AceitarView(oponente, aposta, "carta")
            await ctx.send(
                f"🃏 {oponente.mention}, você foi desafiado por {ctx.author.mention} para um **Duelo de Cartas** valendo **{aposta:.2f} C**!",
                view=view
            )
            await view.wait()

            if not view.aceito:
                return await ctx.send(f"❌ {oponente.mention} recusou ou ignorou o desafio. Duelo cancelado!")

            # Re-checagem de saldo
            d_atual = db.get_user_data(str(ctx.author.id))
            o_atual = db.get_user_data(str(oponente.id))
            if db.parse_float(d_atual['data'][2]) < aposta or db.parse_float(o_atual['data'][2]) < aposta:
                return await ctx.send("🚨 Fraude detectada! Saldo insuficiente após aceite. Partida cancelada.")

            valores = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
            naipes = ["♠️", "♥️", "♦️", "♣️"]
            c_d_val, c_o_val = random.choice(valores), random.choice(valores)
            c_d_nai, c_o_nai = random.choice(naipes), random.choice(naipes)
            while c_d_val == c_o_val and c_d_nai == c_o_nai:
                c_o_nai = random.choice(naipes)

            embed = disnake.Embed(title="🃏 DUELO DE CARTAS 🃏", color=disnake.Color.dark_theme())
            embed.add_field(name=f"Sacado por {ctx.author.display_name}:", value=f"**{c_d_val}** {c_d_nai}", inline=True)
            embed.add_field(name=f"Sacado por {oponente.display_name}:", value=f"**{c_o_val}** {c_o_nai}", inline=True)

            peso_d = valores.index(c_d_val)
            peso_o = valores.index(c_o_val)

            if peso_d == peso_o:
                db.update_value(d_atual['row'], 3, round(db.parse_float(d_atual['data'][2]) - aposta, 2))
                db.update_value(o_atual['row'], 3, round(db.parse_float(o_atual['data'][2]) - aposta, 2))
                embed.description = f"🤝 **EMPATE!** Ambos perdem **{aposta:.2f} C** para o Cassino!"
                return await ctx.send(embed=embed)

            vencedor_db = d_atual if peso_d > peso_o else o_atual
            perdedor_db = o_atual if peso_d > peso_o else d_atual
            vencedor = ctx.author if peso_d > peso_o else oponente
            perdedor = oponente if peso_d > peso_o else ctx.author

            db.update_value(vencedor_db['row'], 3, round(db.parse_float(vencedor_db['data'][2]) + aposta, 2))
            db.update_value(perdedor_db['row'], 3, round(db.parse_float(perdedor_db['data'][2]) - aposta, 2))
            embed.description = f"🏆 A carta de **{vencedor.mention}** foi maior! Faturou **{(aposta * 2):.2f} C** de lucro!"
            await ctx.send(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !carta de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    @commands.command(aliases=["briga", "brigar", "luta", "lutar", "x1"])
    async def briga_macaco(self, ctx, vitima: disnake.Member = None, aposta: float = None):
        if vitima is None or aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!briga @usuario <valor>`")
        if vitima.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, não brigue consigo mesmo!")
        if aposta <= 0:
            return await ctx.send("❌ Aposta inválida!")
        aposta = round(aposta, 2)

        try:
            ladrao = db.get_user_data(str(ctx.author.id))
            alvo = db.get_user_data(str(vitima.id))
            if not ladrao or not alvo:
                return await ctx.send("❌ Uma das contas não foi encontrada!")

            saldo_l = db.parse_float(ladrao['data'][2])
            saldo_a = db.parse_float(alvo['data'][2])

            if saldo_l < aposta or saldo_a < aposta:
                return await ctx.send(f"❌ Alguém não tem saldo para essa briga!")

            cargo = ladrao['data'][3] if len(ladrao['data']) > 3 else "Lêmure"
            if aposta > get_limite(cargo):
                return await ctx.send(f"🚫 Limite de aposta para **{cargo}** é de **{get_limite(cargo)} C**!")

            if aposta == 1.0:
                save_achievement(ladrao, "briga_de_bar")

            view = AceitarView(vitima, aposta, "briga")
            await ctx.send(
                f"🥊 {vitima.mention}, {ctx.author.mention} te desafiou para uma **briga** por **{aposta:.2f} C**!",
                view=view
            )
            await view.wait()

            if not view.aceito:
                return await ctx.send(f"⏱️ {vitima.mention} amarelou e fugiu da briga!")

            # Re-checagem de saldo após aceite
            l_atual = db.get_user_data(str(ctx.author.id))
            a_atual = db.get_user_data(str(vitima.id))
            if db.parse_float(l_atual['data'][2]) < aposta or db.parse_float(a_atual['data'][2]) < aposta:
                return await ctx.send("🚨 Fraude detectada! Briga cancelada.")

            vencedor = random.choice([ctx.author, vitima])
            perdedor = vitima if vencedor == ctx.author else ctx.author
            v_db = l_atual if vencedor == ctx.author else a_atual
            p_db = a_atual if vencedor == ctx.author else l_atual

            db.update_value(v_db['row'], 3, round(db.parse_float(v_db['data'][2]) + aposta, 2))
            db.update_value(p_db['row'], 3, round(db.parse_float(p_db['data'][2]) - aposta, 2))
            await ctx.send(f"🏆 **{vencedor.mention}** nocauteou {perdedor.mention} e lucrou **{(aposta * 2):.2f} C**!")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !briga de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(PvP(bot))