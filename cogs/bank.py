import disnake
from disnake.ext import commands
import database as db
import time
import random
import asyncio

class Bank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, vá ao banco no canal {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["banco", "depositar"])
    async def investir(self, ctx, tipo: str = None, valor: float = None):
        if not tipo or tipo.lower() not in ['cripto', 'fixo'] or valor is None or valor <= 0:
            embed = disnake.Embed(title="🏦 Banco da Selva AKTrovão", color=disnake.Color.green())
            embed.add_field(
                name="🏛️ `!investir fixo <valor>`",
                value=(
                    "Investimento seguro: rende **+10% na hora**.\n"
                    "Limite: **5.000 MC por dia** · Cooldown: **24h**."
                ),
                inline=False
            )
            embed.add_field(
                name="📈 `!investir cripto <valor>`",
                value=(
                    "Alto risco! Resultado sorteado após **30 segundos**:\n"
                    "`-25%` · `-15%` · `-5%` · `0%` · `+5%` · `+10%` · `+20%`\n"
                    "Limite: **4 operações por dia**.\n"
                    "*(🌟 Talismã da Fortuna reduz o prejuízo máximo de 25% para 15%.)*"
                ),
                inline=False
            )
            return await ctx.send(embed=embed)

        tipo  = tipo.lower()
        valor = round(valor, 2)
        user_id_str = str(ctx.author.id)

        try:
            user = db.get_user_data(user_id_str)
            if not user:
                return await ctx.send(f"❌ {ctx.author.mention}, conta não encontrada!")

            agora = time.time()
            saldo = db.parse_float(user['data'][2])

            if saldo < valor:
                return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

            if tipo == 'fixo':
                if valor > 5000.0:
                    return await ctx.send("❌ O banco só aceita até **5.000 MC** na Renda Fixa por dia!")

                ultimo_invest = db.parse_float(user['data'][7] if len(user['data']) > 7 else None)
                if agora - ultimo_invest < 86400:
                    return await ctx.send(f"⏳ {ctx.author.mention}, limite diário esgotado! Volte <t:{int(ultimo_invest + 86400)}:R>.")

                lucro = round(valor * 0.10, 2)
                novo_saldo = round(saldo + lucro, 2)
                db.update_value(user["row"], 3, novo_saldo)
                db.update_value(user["row"], 8, agora)

                ctx._missao_ok = True  # missão: investir na renda fixa

                proximo = int(agora + 86400)
                embed_fixo = disnake.Embed(
                    title="🏛️ RENDA FIXA — RENDIMENTO APLICADO!",
                    description=(
                        f"{ctx.author.mention} resgatou o rendimento de **10%** na hora!\n\n"
                        f"💵 Investido: `{valor:.2f} MC`\n"
                        f"📈 Lucro: **+{lucro:.2f} MC**\n"
                        f"🏦 Novo saldo: `{novo_saldo:.2f} MC`\n\n"
                        f"⏳ Próximo investimento fixo: <t:{proximo}:R>"
                    ),
                    color=disnake.Color.green()
                )
                embed_fixo.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
                await ctx.send(embed=embed_fixo)

            elif tipo == 'cripto':
                # usos persistidos no banco pra não perder entre restarts
                usos_atual, timestamp_inicio = db.get_cripto_usos(user)

                if agora - timestamp_inicio >= 86400:
                    usos_atual       = 0
                    timestamp_inicio = agora

                if usos_atual >= 4:
                    tempo_restauracao = int(timestamp_inicio + 86400)
                    return await ctx.send(
                        f"⏳ {ctx.author.mention}, você já operou cripto 4 vezes hoje! "
                        f"O mercado reabre para você <t:{tempo_restauracao}:R>."
                    )

                # debita antes do sleep pra evitar double-spend
                db.update_value(user['row'], 3, round(saldo - valor, 2))
                ctx._missao_ok = True  # missão: investir em cripto (independente do resultado)
                usos_atual += 1
                db.set_cripto_usos(user['row'], usos_atual, timestamp_inicio)

                aviso = await ctx.send(
                    f"📈 {ctx.author.mention} comprou **{valor:.2f} MC** em BNN (Banana). "
                    f"O mercado fecha em 30 segundos... 💸"
                )

                try:
                    await asyncio.sleep(30)

                    user_atual = db.get_user_data(user_id_str)
                    if not user_atual:
                        raise ValueError("Conta não encontrada após o sleep.")

                    opcoes_variacao = [-0.25, -0.15, -0.05, 0.0, 0.05, 0.10, 0.20]
                    variacao = random.choice(opcoes_variacao)
                    retorno  = round(valor * (1 + variacao), 2)
                    lucro    = round(retorno - valor, 2)

                    db.update_value(user_atual['row'], 3, round(db.parse_float(user_atual['data'][2]) + retorno, 2))

                    ctx._missao_ok = True  # missão: operar cripto (independente do resultado)

                    if variacao > 0:
                        await ctx.send(f"🚀 **ALTA!** {ctx.author.mention} resgatou **{retorno:.2f} MC** (Lucro: `+{lucro:.2f} MC`).")
                    elif variacao == 0:
                        await ctx.send(f"⚖️ **ESTÁVEL!** {ctx.author.mention} resgatou exatamente seus **{retorno:.2f} MC** (Lucro: `0.00 MC`).")
                    else:
                        await ctx.send(f"📉 **CRASH!** {ctx.author.mention} resgatou apenas **{retorno:.2f} MC** (Prejuízo: `{lucro:.2f} MC`).")

                except Exception as inner_e:
                    # qualquer erro após o débito devolve o valor e decrementa o uso
                    print(f"❌ Erro durante o sleep do !investir cripto de {ctx.author}: {inner_e}")
                    try:
                        user_refund = db.get_user_data(user_id_str)
                        if user_refund:
                            saldo_refund = db.parse_float(user_refund['data'][2])
                            db.update_value(user_refund['row'], 3, round(saldo_refund + valor, 2))
                            usos_refund, ts_refund = db.get_cripto_usos(user_refund)
                            if usos_refund > 0:
                                db.set_cripto_usos(user_refund['row'], usos_refund - 1, ts_refund)
                            await ctx.send(
                                f"⚠️ {ctx.author.mention}, ocorreu um erro durante o investimento. "
                                f"Seus **{valor:.2f} MC** foram devolvidos automaticamente."
                            )
                        else:
                            await ctx.send(
                                f"⚠️ {ctx.author.mention}, ocorreu um erro e não conseguimos encontrar sua conta "
                                f"para devolver os **{valor:.2f} MC**. Contate um administrador!"
                            )
                    except Exception as refund_e:
                        print(f"❌ CRÍTICO: falha ao devolver saldo do cripto para {ctx.author}: {refund_e}")
                        await ctx.send(
                            f"🚨 {ctx.author.mention}, erro crítico no investimento. "
                            f"Informe um admin para recuperar seus **{valor:.2f} MC**."
                        )

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !investir de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(Bank(bot))