import disnake
from disnake.ext import commands
import database as db
import time
import random
import asyncio

class Bank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Dicionário para rastrear os limites diários do Cripto na memória RAM
        # Formato: {'user_id': [quantidade_usos, timestamp_primeiro_uso]}
        self.cripto_usos = {}

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
            embed.add_field(name="📈 `!investir cripto <valor>`", value="Risco alto! Rende **-25%, -15%, -5%, 0%, +5%, +10% ou +20%**. *Limite: 4x ao dia.*", inline=False)
            embed.add_field(name="🏛️ `!investir fixo <valor>`",  value="Seguro! Rende **+10%** na hora. *Limite: 5.000 C por dia.*", inline=False)
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

            # ── RENDA FIXA ────────────────────────────────────────────────────
            if tipo == 'fixo':
                if valor > 5000.0:
                    return await ctx.send("❌ O banco só aceita até **5.000 C** na Renda Fixa por operação!")

                ultimo_invest = db.parse_float(user['data'][7] if len(user['data']) > 7 else None)
                if agora - ultimo_invest < 86400:
                    return await ctx.send(f"⏳ {ctx.author.mention}, limite diário esgotado! Volte <t:{int(ultimo_invest + 86400)}:R>.")

                lucro = round(valor * 0.10, 2)
                db.update_value(user['row'], 3, round(saldo + lucro, 2))
                db.update_value(user['row'], 8, agora)
                await ctx.send(f"🏛️ **RENDA FIXA!** Rendimento de 10% aplicado. Você ganhou **+{lucro:.2f} C**, {ctx.author.mention}!")

            # ── CRIPTO ────────────────────────────────────────────────────────
            elif tipo == 'cripto':
                # Verifica o limite de 4 vezes ao dia
                if user_id_str not in self.cripto_usos:
                    self.cripto_usos[user_id_str] = [0, agora]
                
                # Se já passou 24h desde o primeiro uso, reseta o contador
                if agora - self.cripto_usos[user_id_str][1] >= 86400:
                    self.cripto_usos[user_id_str] = [0, agora]

                # Se já usou 4 vezes, bloqueia
                if self.cripto_usos[user_id_str][0] >= 4:
                    tempo_restauracao = int(self.cripto_usos[user_id_str][1] + 86400)
                    return await ctx.send(f"⏳ {ctx.author.mention}, você já operou cripto 4 vezes hoje! O mercado reabre para você <t:{tempo_restauracao}:R>.")

                # Debita o saldo ANTES do sleep para evitar double-spend
                db.update_value(user['row'], 3, round(saldo - valor, 2))
                
                # Incrementa o contador de usos
                self.cripto_usos[user_id_str][0] += 1
                
                aviso = await ctx.send(
                    f"📈 {ctx.author.mention} comprou **{valor:.2f} C** em MacacoCoin. "
                    f"O mercado fecha em 30 segundos... 💸"
                )

                try:
                    await asyncio.sleep(30)

                    # Rebusca o saldo atualizado após o sleep (pode ter mudado por outros comandos)
                    user_atual = db.get_user_data(user_id_str)
                    if not user_atual:
                        raise ValueError("Conta não encontrada após o sleep.")

                    # Novas variações fixas
                    opcoes_variacao = [-0.25, -0.15, -0.05, 0.0, 0.05, 0.10, 0.20]
                    variacao  = random.choice(opcoes_variacao)
                    
                    retorno   = round(valor * (1 + variacao), 2)
                    lucro     = round(retorno - valor, 2)

                    db.update_value(user_atual['row'], 3, round(db.parse_float(user_atual['data'][2]) + retorno, 2))

                    if variacao > 0:
                        await ctx.send(f"🚀 **ALTA!** {ctx.author.mention} resgatou **{retorno:.2f} C** (Lucro: `+{lucro:.2f} C`).")
                    elif variacao == 0:
                        await ctx.send(f"⚖️ **ESTÁVEL!** {ctx.author.mention} resgatou exatamente seus **{retorno:.2f} C** (Lucro: `0.00 C`).")
                    else:
                        await ctx.send(f"📉 **CRASH!** {ctx.author.mention} resgatou apenas **{retorno:.2f} C** (Prejuízo: `{lucro:.2f} C`).")

                except Exception as inner_e:
                    # ── CORREÇÃO: qualquer erro após o débito devolve o valor ──
                    print(f"❌ Erro durante o sleep do !investir cripto de {ctx.author}: {inner_e}")
                    try:
                        user_refund = db.get_user_data(user_id_str)
                        if user_refund:
                            saldo_refund = db.parse_float(user_refund['data'][2])
                            db.update_value(user_refund['row'], 3, round(saldo_refund + valor, 2))
                            # Devolve também a chance de tentar de novo, já que deu erro
                            self.cripto_usos[user_id_str][0] -= 1
                            await ctx.send(
                                f"⚠️ {ctx.author.mention}, ocorreu um erro durante o investimento. "
                                f"Seus **{valor:.2f} C** foram devolvidos automaticamente."
                            )
                        else:
                            await ctx.send(
                                f"⚠️ {ctx.author.mention}, ocorreu um erro e não conseguimos encontrar sua conta "
                                f"para devolver os **{valor:.2f} C**. Contate um administrador!"
                            )
                    except Exception as refund_e:
                        print(f"❌ CRÍTICO: falha ao devolver saldo do cripto para {ctx.author}: {refund_e}")
                        await ctx.send(
                            f"🚨 {ctx.author.mention}, erro crítico no investimento. "
                            f"Informe um admin para recuperar seus **{valor:.2f} C**."
                        )

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !investir de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(Bank(bot))