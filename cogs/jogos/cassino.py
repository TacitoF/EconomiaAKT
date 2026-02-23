import disnake
from disnake.ext import commands
import database as db
import random
import asyncio

LIMITES_CARGO = {
    "Lêmure": 250, "Macaquinho": 800, "Babuíno": 2000, "Chimpanzé": 6000,
    "Orangutango": 15000, "Gorila": 45000, "Ancestral": 150000, "Rei Símio": 1500000
}

def get_limite(cargo):
    return LIMITES_CARGO.get(cargo, 250)

def save_achievement(user_data, slug):
    conquistas = str(user_data['data'][9]) if len(user_data['data']) > 9 else ""
    lista = [c.strip() for c in conquistas.split(',') if c.strip()]
    if slug not in lista:
        lista.append(slug)
        db.update_value(user_data['row'], 10, ", ".join(lista))

class Cassino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, macaco esperto joga no lugar certo! Vai para {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(name="cassino")
    async def cassino_slots(self, ctx, aposta: float = None):
        if aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!cassino <valor>`")
        if aposta <= 0:
            return await ctx.send(f"⚠️ {ctx.author.mention}, valor inválido!")
        aposta = round(aposta, 2)

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send(f"❌ {ctx.author.mention}, conta não encontrada!")

            saldo = db.parse_float(user['data'][2])
            if saldo < aposta:
                return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

            cargo = user['data'][3] if len(user['data']) > 3 else "Lêmure"
            if aposta > get_limite(cargo):
                return await ctx.send(f"🚫 Limite de aposta para **{cargo}** é de **{get_limite(cargo)} C**!")

            db.update_value(user['row'], 3, round(saldo - aposta, 2))

            emojis = ["🍌", "🐒", "⚡", "🥥", "💎", "🦍", "🌴", "🌊"]
            res = [random.choice(emojis) for _ in range(3)]

            user_atual = db.get_user_data(str(ctx.author.id))
            saldo_atual = db.parse_float(user_atual['data'][2])

            if res[0] == res[1] == res[2]:
                lucro = round(aposta * 9.0, 2)
                db.update_value(user_atual['row'], 3, round(saldo_atual + aposta + lucro, 2))
                save_achievement(user_atual, "filho_da_sorte")
                status_msg = f"🎰 **JACKPOT!** 🎰\nVocê lucrou **{lucro:.2f} C**!"
            elif res[0] == res[1] or res[1] == res[2] or res[0] == res[2]:
                lucro = round(aposta * 1.0, 2)
                db.update_value(user_atual['row'], 3, round(saldo_atual + aposta + lucro, 2))
                status_msg = f"Você lucrou **{lucro:.2f} C**!"
            else:
                status_msg = f"Você perdeu **{aposta:.2f} C**."

            await ctx.send(f"🎰 **CASSINO AKTrovão** 🎰\n**[ {res[0]} | {res[1]} | {res[2]} ]**\n{ctx.author.mention}, {status_msg}")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !cassino de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    @commands.command(name="bicho")
    async def jogo_bicho(self, ctx, bicho: str = None, aposta: float = None):
        if bicho is None or aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!bicho <animal> <valor>`\nAnimais: `leao`, `cobra`, `jacare`, `arara`, `elefante`")

        bichos = ["leao", "cobra", "jacare", "arara", "elefante"]
        bicho = bicho.lower()
        if bicho not in bichos:
            return await ctx.send(f"❌ {ctx.author.mention}, escolha: `leao, cobra, jacare, arara, elefante`")
        if aposta <= 0:
            return await ctx.send("❌ Aposta inválida!")
        aposta = round(aposta, 2)

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send(f"❌ {ctx.author.mention}, conta não encontrada!")

            saldo = db.parse_float(user['data'][2])
            cargo = user['data'][3] if len(user['data']) > 3 else "Lêmure"
            if saldo < aposta:
                return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")
            if aposta > get_limite(cargo):
                return await ctx.send(f"🚫 Limite de aposta para **{cargo}** é de **{get_limite(cargo)} C**!")

            db.update_value(user['row'], 3, round(saldo - aposta, 2))
            resultado = random.choice(bichos)
            msg = await ctx.send(f"🎰 Sorteando... {ctx.author.mention} apostou no **{bicho.upper()}**!")
            await asyncio.sleep(2)

            user_atual = db.get_user_data(str(ctx.author.id))
            saldo_atual = db.parse_float(user_atual['data'][2])

            if bicho == resultado:
                lucro = round(aposta * 4.0, 2)
                db.update_value(user_atual['row'], 3, round(saldo_atual + aposta + lucro, 2))
                await msg.edit(content=f"🎉 {ctx.author.mention} DEU **{resultado.upper()}**! Você faturou **{lucro:.2f} C** de lucro!")
            else:
                await msg.edit(content=f"💀 {ctx.author.mention} DEU **{resultado.upper()}**! Perdeu **{aposta:.2f} C**.")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !bicho de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    @commands.command(name="corrida")
    async def corrida_macaco(self, ctx, escolha: str = None, aposta: float = None):
        if escolha is None or aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!corrida <animal> <valor>`\nAnimais: `macaquinho`, `gorila`, `orangutango`")

        opcoes = {"macaquinho": "🐒", "gorila": "🦍", "orangutango": "🦧"}
        escolha = escolha.lower()
        if escolha not in opcoes:
            return await ctx.send(f"❌ {ctx.author.mention}, escolha: `macaquinho`, `gorila` ou `orangutango`.")
        if aposta <= 0:
            return await ctx.send("❌ Aposta inválida!")
        aposta = round(aposta, 2)

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send(f"❌ {ctx.author.mention}, conta não encontrada!")

            saldo = db.parse_float(user['data'][2])
            cargo = user['data'][3] if len(user['data']) > 3 else "Lêmure"
            if saldo < aposta:
                return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")
            if aposta > get_limite(cargo):
                return await ctx.send(f"🚫 Limite de aposta para **{cargo}** é de **{get_limite(cargo)} C**!")

            db.update_value(user['row'], 3, round(saldo - aposta, 2))

            macacos_lista = list(opcoes.values())
            nomes_lista = list(opcoes.keys())
            pistas = [0, 0, 0]
            chegada = 10

            msg = await ctx.send(
                f"🏁 **A CORRIDA COMEÇOU!** {ctx.author.mention} apostou no **{escolha.capitalize()}**!\n\n" +
                "\n".join([f"{macacos_lista[i]} 🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦 🏁" for i in range(3)])
            )

            vencedor_idx = -1
            while vencedor_idx == -1:
                await asyncio.sleep(1.2)
                for i in range(3):
                    pistas[i] += random.randint(1, 3)
                    if pistas[i] >= chegada:
                        vencedor_idx = i
                        break
                frame = []
                for i in range(3):
                    progresso = min(pistas[i], chegada)
                    frame.append(f"{macacos_lista[i]} {'🟩' * progresso}{'🟦' * (chegada - progresso)} 🏁")
                await msg.edit(content="🏁 **A CORRIDA ESTÁ QUENTE!**\n\n" + "\n".join(frame))

            nome_vencedor = nomes_lista[vencedor_idx]
            user_atual = db.get_user_data(str(ctx.author.id))
            saldo_atual = db.parse_float(user_atual['data'][2])

            if escolha == nome_vencedor:
                lucro = round(aposta * 2.0, 2)
                db.update_value(user_atual['row'], 3, round(saldo_atual + aposta + lucro, 2))
                await ctx.send(f"🏆 {ctx.author.mention} **VITÓRIA!** O {nome_vencedor.capitalize()} cruzou primeiro! Lucrou **{lucro:.2f} C**!")
            else:
                await ctx.send(f"💀 {ctx.author.mention} **DERROTA!** O {nome_vencedor.capitalize()} venceu. Você perdeu **{aposta:.2f} C**.")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !corrida de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(Cassino(bot))