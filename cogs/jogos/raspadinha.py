import disnake
from disnake.ext import commands
import database as db
import random
import asyncio

class Raspadinha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name not in ['🐒・conguitos', '🎰・akbet']:
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"⚠️ {ctx.author.mention}, use a raspadinha no canal {mencao} ou #🐒・conguitos.")
            raise commands.CommandError("Canal incorreto para raspadinha.")

    @commands.command(aliases=["bilhete", "loto", "loteria"])
    async def raspadinha(self, ctx, valor: float = None):
        if valor is None:
            embed = disnake.Embed(
                title="🎫 RASPADINHA DA SELVA",
                description=(
                    "Compre um bilhete pelo valor que quiser e raspe na hora!\n\n"
                    "**Prêmios possíveis (acerte 3 iguais):**\n"
                    "💀 `60%` → Nada (0x)\n"
                    "🍀 `18%` → 1.5x\n"
                    "💰 `12%` → 2x\n"
                    "✨ ` 6%` → 3x\n"
                    "🔥 ` 3%` → 5x\n"
                    "👑 ` 1%` → **JACKPOT 10x**\n\n"
                    "**Uso:** `!raspadinha <valor>`\n"
                    "*Limite: mínimo **50 MC**, máximo **500 MC***"
                ),
                color=disnake.Color.gold()
            )
            return await ctx.send(embed=embed)

        if valor < 50:
            return await ctx.send(f"❌ {ctx.author.mention}, valor mínimo é **50 MC**!")
        if valor > 500:
            return await ctx.send(f"❌ {ctx.author.mention}, valor máximo para a raspadinha é de **500 MC**!")
        valor = round(valor, 2)

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send(f"❌ {ctx.author.mention}, conta não encontrada!")

            saldo = db.parse_float(user['data'][2])

            if saldo < valor:
                return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

            db.update_value(user['row'], 3, round(saldo - valor, 2))

            # Sorteio com house edge ~6%
            rolagem = random.random()
            if rolagem < 0.60:
                mult, emoji, resultado = 0,   "💀", "Nada!"
            elif rolagem < 0.78:
                mult, emoji, resultado = 1.5, "🍀", "1.5x"
            elif rolagem < 0.90:
                mult, emoji, resultado = 2,   "💰", "2x"
            elif rolagem < 0.96:
                mult, emoji, resultado = 3,   "✨", "3x"
            elif rolagem < 0.99:
                mult, emoji, resultado = 5,   "🔥", "5x"
            else:
                mult, emoji, resultado = 10,  "👑", "JACKPOT 10x!"

            retorno = round(valor * mult, 2)
            lucro   = round(retorno - valor, 2)

            # Lógica de quais emojis mostrar na raspadinha
            if mult > 0:
                # Se ganhou, os 3 emojis são iguais
                slots = [emoji, emoji, emoji]
            else:
                # Se perdeu, 30% de chance de ser uma derrota "quase lá" (troll)
                opcoes_boas = ["🍀", "💰", "✨", "🔥", "👑"]
                opcoes_ruins = ["🍌", "🍉", "🍒", "💩", "💀"]
                
                if random.random() < 0.30:
                    # Derrota Troll: os 2 primeiros são prêmios altos, o último estraga tudo
                    falso_premio = random.choice(opcoes_boas)
                    estraga_prazer = random.choice(opcoes_ruins)
                    slots = [falso_premio, falso_premio, estraga_prazer]
                else:
                    # Derrota Normal: tudo bagunçado
                    todas_opcoes = opcoes_boas + opcoes_ruins
                    slots = random.choices(todas_opcoes, k=3)
                    # Garante que não caiam 3 iguais por acidente na derrota
                    while len(set(slots)) == 1:
                        slots = random.choices(todas_opcoes, k=3)

            # --- ANIMAÇÃO DA RASPADINHA (AJUSTADA) ---
            msg = await ctx.send(
                f"🎫 {ctx.author.mention} pegou a moeda e começou a raspar o bilhete de **{valor:.2f} MC**...\n\n"
                "`[ ❓ | ❓ | ❓ ]`"
            )
            await asyncio.sleep(1.5) # Mais lento aqui para fazer suspense

            await msg.edit(content=(
                f"🎫 {ctx.author.mention} pegou a moeda e começou a raspar o bilhete de **{valor:.2f} MC**...\n\n"
                f"`[ {slots[0]} | ❓ | ❓ ]`"
            ))
            await asyncio.sleep(1.5) # Mais lento aqui para fazer suspense

            await msg.edit(content=(
                f"🎫 {ctx.author.mention} está suando frio...\n\n"
                f"`[ {slots[0]} | {slots[1]} | ❓ ]`"
            ))
            await asyncio.sleep(0.5) # Pula rápido para o resultado final!
            # ------------------------------

            if mult == 0:
                user_atual = db.get_user_data(str(ctx.author.id))
                
                # Mensagem especial se foi uma derrota troll
                if slots[0] == slots[1]:
                    titulo = "💀 QUASE LÁ! Que azar!"
                    desc = f"Foi por pouco! A combinação foi `[ {slots[0]} | {slots[1]} | {slots[2]} ]`\n{ctx.author.mention} perdeu **{valor:.2f} MC**."
                else:
                    titulo = "💥 Não foi dessa vez!"
                    desc = f"A combinação foi `[ {slots[0]} | {slots[1]} | {slots[2]} ]`\n{ctx.author.mention} perdeu **{valor:.2f} MC**."

                embed = disnake.Embed(
                    title=titulo,
                    description=desc,
                    color=disnake.Color.red()
                )
            else:
                user_atual = db.get_user_data(str(ctx.author.id))
                db.update_value(user_atual['row'], 3, round(db.parse_float(user_atual['data'][2]) + retorno, 2))
                embed = disnake.Embed(
                    title=f"🎉 TEMOS UM VENCEDOR!",
                    description=(
                        f"A combinação foi `[ {slots[0]} | {slots[1]} | {slots[2]} ]`\n"
                        f"{ctx.author.mention} ganhou **{retorno:.2f} MC**! *(lucro: +{lucro:.2f} MC)*\n"
                        f"Bilhete: **{valor:.2f} MC** × **{mult}x**"
                    ),
                    color=disnake.Color.gold() if mult >= 5 else disnake.Color.green()
                )

            embed.set_footer(text="Use !raspadinha <valor> para tentar a sorte de novo!")
            await msg.edit(content="", embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !raspadinha de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(Raspadinha(bot))