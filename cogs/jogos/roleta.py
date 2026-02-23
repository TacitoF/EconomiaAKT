import disnake
from disnake.ext import commands
import database as db
import random
import asyncio

LIMITES_CARGO = {
    "Lêmure": 250, "Macaquinho": 800, "Babuíno": 2000, "Chimpanzé": 6000,
    "Orangutango": 15000, "Gorila": 45000, "Ancestral": 150000, "Rei Símio": 1500000
}

def save_achievement(user_data, slug):
    conquistas = str(user_data['data'][9]) if len(user_data['data']) > 9 else ""
    lista = [c.strip() for c in conquistas.split(',') if c.strip()]
    if slug not in lista:
        lista.append(slug)
        db.update_value(user_data['row'], 10, ", ".join(lista))

class Roleta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roleta_aberta = False
        self.apostas = []

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, a roleta fica no cassino! Vai para {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["roulette", "rol"])
    async def roleta(self, ctx):
        if self.roleta_aberta:
            return await ctx.send(f"⚠️ {ctx.author.mention}, a mesa já está aberta! Use `!apostar <valor> <opção>`.")

        self.roleta_aberta = True
        self.apostas = []

        embed = disnake.Embed(
            title="🎰 A MESA DE ROLETA ABRIU!",
            description=(
                "O Chimpanzézio abriu a mesa! Você tem **30 segundos** para apostar.\n\n"
                "**Opções:**\n🔴 `vermelho` (2x)\n⚫ `preto` (2x)\n"
                "⚖️ `par`/`impar` (2x)\n🎯 `0 a 36` (36x)\n\n*Prêmios sem taxa!*"
            ),
            color=disnake.Color.gold()
        )
        await ctx.send(embed=embed)
        await asyncio.sleep(30)
        self.roleta_aberta = False

        if not self.apostas:
            return await ctx.send("🦗 Ninguém apostou... O Chimpanzézio fechou a mesa.")

        total_apostado = sum(a['valor'] for a in self.apostas)
        embed_giro = disnake.Embed(
            title="🛑 APOSTAS ENCERRADAS!",
            description=f"Total na mesa: **{total_apostado:.2f} C**!\n\n🌀 **O Chimpanzézio girou a roleta...**",
            color=disnake.Color.orange()
        )
        msg = await ctx.send(embed=embed_giro)
        await asyncio.sleep(2)

        resultado_num = random.randint(0, 36)
        vermelhos = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
        if resultado_num == 0:       cor, emoji = "verde", "🟩"
        elif resultado_num in vermelhos: cor, emoji = "vermelho", "🟥"
        else:                        cor, emoji = "preto", "⬛"

        vencedores_txt = ""
        perdedores_txt = ""

        for aposta in self.apostas:
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
                    db.update_value(user_db['row'], 3, round(db.parse_float(user_db['data'][2]) + valor + lucro, 2))
                    if multiplicador == 36:
                        save_achievement(user_db, "filho_da_sorte")
                    vencedores_txt += f"🎉 {jogador.mention} lucrou **{lucro:.2f} C** em `{aposta_em.upper()}`!\n"
                else:
                    perdedores_txt += f"💀 {jogador.mention} perdeu **{valor:.2f} C** em `{aposta_em.upper()}`.\n"

            except Exception as e:
                print(f"❌ Erro ao processar aposta de {jogador}: {e}")

        embed_final = disnake.Embed(
            title=f"🎰 A ROLETA PAROU NO: {emoji} {resultado_num} ({cor.upper()})",
            color=disnake.Color.green() if vencedores_txt else disnake.Color.red()
        )
        embed_final.add_field(name="💰 VENCEDORES", value=vencedores_txt or "Ninguém...", inline=False)
        embed_final.add_field(name="💸 PERDEDORES", value=perdedores_txt or "Ninguém!", inline=False)
        await msg.edit(embed=embed_final)

    @commands.command()
    async def apostar(self, ctx, valor: float = None, aposta_em: str = None):
        if valor is None or aposta_em is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!apostar <valor> <opção>`")
        if not self.roleta_aberta:
            return await ctx.send(f"⚠️ {ctx.author.mention}, a mesa está fechada! Use `!roleta` primeiro.")
        if valor <= 0:
            return await ctx.send("❌ Aposta inválida!")
        valor = round(valor, 2)

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send(f"❌ {ctx.author.mention}, conta não encontrada!")

            saldo = db.parse_float(user['data'][2])
            if saldo < valor:
                return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

            cargo = user['data'][3] if len(user['data']) > 3 else "Lêmure"
            limite = LIMITES_CARGO.get(cargo, 250)
            apostado_ja = sum(a['valor'] for a in self.apostas if a['user'] == ctx.author)
            if (apostado_ja + valor) > limite:
                restante = max(round(limite - apostado_ja, 2), 0)
                return await ctx.send(f"🚫 {ctx.author.mention}, limite como **{cargo}** é **{limite} C**. Você pode apostar mais **{restante} C**.")

            aposta_em = aposta_em.lower()
            validas = ['vermelho', 'preto', 'par', 'impar'] + [str(i) for i in range(37)]
            if aposta_em not in validas:
                return await ctx.send("❌ Opção inválida! Escolha: vermelho, preto, par, impar ou 0-36.")

            db.update_value(user['row'], 3, round(saldo - valor, 2))
            self.apostas.append({'user': ctx.author, 'valor': valor, 'tipo': aposta_em})
            await ctx.send(f"🪙 {ctx.author.mention} apostou **{valor:.2f} C** em `{aposta_em.upper()}`!")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !apostar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(Roleta(bot))