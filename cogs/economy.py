import disnake
from disnake.ext import commands
import database as db
import time
import random

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, 'recompensas'): bot.recompensas = {}
        if not hasattr(bot, 'cascas'): bot.cascas = set()
        if not hasattr(bot, 'impostos'): bot.impostos = {}
        if not hasattr(bot, 'tracker_emblemas'):
            bot.tracker_emblemas = {'trabalhos': {}, 'roubos_sucesso': {}, 'roubos_falha': {}}

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, assuntos de dinheiro são apenas no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["work"])
    async def trabalhar(self, ctx):
        user_id = str(ctx.author.id)
        try:
            user = db.get_user_data(user_id)
            if not user:
                db.create_user(user_id, ctx.author.name)
                user = db.get_user_data(user_id)
            if not user:
                return await ctx.send(f"❌ {ctx.author.mention}, erro ao criar sua conta! Tente novamente.")

            agora = time.time()
            ultimo_work = db.parse_float(user['data'][4] if len(user['data']) > 4 else None)

            if agora - ultimo_work < 3600:
                return await ctx.send(f"⏳ {ctx.author.mention}, você está exausto! Volte <t:{int(ultimo_work + 3600)}:R>.")

            if user_id in self.bot.cascas:
                self.bot.cascas.remove(user_id)
                db.update_value(user['row'], 5, agora)
                return await ctx.send(f"🍌 **SPLASH!** {ctx.author.mention} escorregou numa casca de banana e não ganhou nada!")

            cargo = user['data'][3] if len(user['data']) > 3 and user['data'][3] else "Lêmure"

            salarios = {
                "Lêmure":      (40,   80),
                "Macaquinho":  (130,  230),
                "Babuíno":     (320,  530),
                "Chimpanzé":   (780,  1320),
                "Orangutango": (1900, 3200),
                "Gorila":      (4700, 7800),
                "Ancestral":   (11500, 19000),
                "Rei Símio":   (27000, 45000),
            }
            min_ganho, max_ganho = salarios.get(cargo, (40, 80))
            ganho = round(random.uniform(min_ganho, max_ganho), 2)

            imposto_msg = ""
            if user_id in self.bot.impostos:
                imposto_data = self.bot.impostos[user_id]
                if agora > imposto_data['fim']:
                    del self.bot.impostos[user_id]
                    imposto_msg = "\n🕊️ Seu Imposto do Gorila expirou. Você está livre!"
                else:
                    taxa = round(ganho * 0.25, 2)
                    ganho = round(ganho - taxa, 2)
                    cobrador_db = db.get_user_data(imposto_data['cobrador_id'])
                    if cobrador_db:
                        db.update_value(cobrador_db['row'], 3, round(db.parse_float(cobrador_db['data'][2]) + taxa, 2))
                    cobrador_user = self.bot.get_user(int(imposto_data['cobrador_id']))
                    nome_c = cobrador_user.mention if cobrador_user else "Um Gorila"
                    imposto_msg = f"\n🦍 **IMPOSTO ATIVO:** {nome_c} confiscou **{taxa:.2f} MC** do seu suor! *(Expira <t:{int(imposto_data['fim'])}:R>)*"

            saldo_atual = db.parse_float(user['data'][2])
            db.update_value(user['row'], 3, round(saldo_atual + ganho, 2))
            db.update_value(user['row'], 5, agora)

            # --- SISTEMA DE CONQUISTA: PROLETÁRIO PADRÃO ---
            tracker = self.bot.tracker_emblemas['trabalhos']
            if user_id not in tracker: tracker[user_id] = []
            tracker[user_id] = [t for t in tracker[user_id] if agora - t < 86400]
            tracker[user_id].append(agora)

            conquista_msg = ""
            if len(tracker[user_id]) >= 10:
                conquistas_user = str(user['data'][9]) if len(user['data']) > 9 else ""
                lista_conquistas = [c.strip() for c in conquistas_user.split(',') if c.strip()]
                if "proletario" not in lista_conquistas:
                    lista_conquistas.append("proletario")
                    db.update_value(user['row'], 10, ", ".join(lista_conquistas))
                    conquista_msg = "\n🏆 Você desbloqueou a conquista **Proletário Padrão**!"
            # ------------------------------------------------

            await ctx.send(f"✅ {ctx.author.mention}, como **{cargo}**, você ganhou **{ganho:.2f} Macacoins**!{imposto_msg}{conquista_msg}")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !trabalhar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    @commands.command(aliases=["assaltar", "furtar", "rob"])
    async def roubar(self, ctx, vitima: disnake.Member = None):
        if vitima is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!roubar @usuario`")

        ladrao_id = str(ctx.author.id)

        if vitima.id == ctx.author.id:
            ladrao_data = db.get_user_data(ladrao_id)
            if ladrao_data:
                conquistas = str(ladrao_data['data'][9]) if len(ladrao_data['data']) > 9 else ""
                if "palhaco" not in conquistas:
                    db.update_value(ladrao_data['row'], 10, f"{conquistas}, palhaco".strip(", "))
            return await ctx.send("🐒 Palhaço! Não pode roubar a si mesmo.")

        try:
            ladrao_data = db.get_user_data(ladrao_id)
            alvo_data   = db.get_user_data(str(vitima.id))
            if not ladrao_data or not alvo_data:
                return await ctx.send("❌ Uma das contas não foi encontrada!")

            saldo_ladrao = db.parse_float(ladrao_data['data'][2])
            saldo_alvo   = db.parse_float(alvo_data['data'][2])

            if saldo_alvo < 80:
                return await ctx.send(f"😬 {vitima.mention} está tão pobre que não vale a pena o risco.")

            agora    = time.time()
            vitima_id = str(vitima.id)

            ultimo_roubo = db.parse_float(ladrao_data['data'][6] if len(ladrao_data['data']) > 6 else None)
            if agora - ultimo_roubo < 7200:
                return await ctx.send(f"👮 Você só poderá roubar novamente <t:{int(ultimo_roubo + 7200)}:R>.")

            if ladrao_id in self.bot.cascas:
                self.bot.cascas.remove(ladrao_id)
                db.update_value(ladrao_data['row'], 7, agora)
                return await ctx.send(f"🍌 **QUE FASE!** {ctx.author.mention} escorregou numa casca de banana e fugiu de mãos vazias.")

            inv_ladrao = [i.strip() for i in str(ladrao_data['data'][5] if len(ladrao_data['data']) > 5 else "").split(',') if i.strip()]
            inv_alvo   = [i.strip() for i in str(alvo_data['data'][5]   if len(alvo_data['data'])   > 5 else "").split(',') if i.strip()]

            chance_sucesso = 42
            if "Pé de Cabra" in inv_ladrao:
                chance_sucesso = 62
                inv_ladrao.remove("Pé de Cabra")
                db.update_value(ladrao_data['row'], 6, ", ".join(inv_ladrao))

            if "Escudo" in inv_alvo:
                inv_alvo.remove("Escudo")
                db.update_value(alvo_data['row'], 6, ", ".join(inv_alvo))
                db.update_value(ladrao_data['row'], 7, agora)
                return await ctx.send(f"🛡️ {vitima.mention} estava protegido por um **Escudo** e bloqueou seu ataque!")

            if random.randint(1, 100) <= chance_sucesso:
                # ── NOVA LÓGICA DE BALANCEAMENTO DE POBREZA ──
                if saldo_alvo < 500:
                    pct = random.uniform(0.01, 0.05) # Roubo com pena: 1% a 5%
                    is_pobre = True
                else:
                    pct = random.uniform(0.05, 0.10) # Roubo normal: 5% a 10%
                    is_pobre = False
                    
                valor_roubado = min(round(saldo_alvo * pct, 2), 12000.0)

                if valor_roubado < 5:
                    db.update_value(ladrao_data['row'], 7, agora)
                    return await ctx.send(f"😬 {vitima.mention} está tão pobre que não valia a pena o risco.")

                bounty_ganho = self.bot.recompensas.pop(vitima_id, 0.0)

                seguro_msg = ""
                if "Seguro" in inv_alvo:
                    recuperado = round(valor_roubado * 0.6, 2)
                    db.update_value(alvo_data['row'], 3, round(saldo_alvo - valor_roubado + recuperado, 2))
                    inv_alvo.remove("Seguro")
                    db.update_value(alvo_data['row'], 6, ", ".join(inv_alvo))
                    seguro_msg = f"\n📄 **SEGURO ACIONADO:** {vitima.mention} foi reembolsado em **{recuperado:.2f} MC**!"
                else:
                    db.update_value(alvo_data['row'], 3, round(saldo_alvo - valor_roubado, 2))

                db.update_value(ladrao_data['row'], 3, round(saldo_ladrao + valor_roubado + bounty_ganho, 2))
                db.update_value(ladrao_data['row'], 7, agora)

                # Bounty automático: 12% do roubado, máximo 2.000 MC
                bounty_adicionado = min(round(valor_roubado * 0.12, 2), 2000.0)
                self.bot.recompensas[ladrao_id] = round(self.bot.recompensas.get(ladrao_id, 0.0) + bounty_adicionado, 2)

                # --- SISTEMA DE CONQUISTA: MESTRE DAS SOMBRAS ---
                tracker = self.bot.tracker_emblemas['roubos_sucesso']
                if ladrao_id not in tracker: tracker[ladrao_id] = []
                # Limpa registros mais velhos que 24 horas
                tracker[ladrao_id] = [t for t in tracker[ladrao_id] if agora - t < 86400]
                tracker[ladrao_id].append(agora)
                self.bot.tracker_emblemas['roubos_falha'][ladrao_id] = 0
                
                conquista_msg = ""
                if len(tracker[ladrao_id]) >= 5:
                    conquistas_ladrao = str(ladrao_data['data'][9]) if len(ladrao_data['data']) > 9 else ""
                    lista_conquistas = [c.strip() for c in conquistas_ladrao.split(',') if c.strip()]
                    if "mestre_sombras" not in lista_conquistas:
                        lista_conquistas.append("mestre_sombras")
                        db.update_value(ladrao_data['row'], 10, ", ".join(lista_conquistas))
                        conquista_msg = "\n🏆 Você desbloqueou a conquista **Mestre das Sombras**!"
                # ------------------------------------------------

                # ── MENSAGEM DINÂMICA ──
                if is_pobre:
                    mensagem = f"🥷 **SUCESSO (Mas com pena)...** {vitima.mention} está quase na miséria, então você levou só as moedinhas: **{valor_roubado:.2f} MC**."
                else:
                    mensagem = f"🥷 **SUCESSO!** Você roubou **{valor_roubado:.2f} MC** de {vitima.mention}!"
                    
                if chance_sucesso == 62: mensagem += " *(Usou Pé de Cabra 🕵️)*"
                if bounty_ganho > 0: mensagem += f"\n🎯 **MERCENÁRIO!** Coletou a recompensa de **{bounty_ganho:.2f} MC**!"
                mensagem += seguro_msg
                mensagem += f"\n🚨 *Recompensa automática de **{bounty_adicionado:.2f} MC** colocada na sua cabeça!*"
                mensagem += conquista_msg
                await ctx.send(mensagem)
            else:
                # Multa: 5–10% do saldo do ladrão, mínimo 30 MC, máximo 5.000 MC
                pct_multa = random.uniform(0.05, 0.10)
                multa = max(min(round(saldo_ladrao * pct_multa, 2), 5000.0), 30.0)
                db.update_value(ladrao_data['row'], 3, round(saldo_ladrao - multa, 2))
                db.update_value(alvo_data['row'],   3, round(saldo_alvo + multa, 2))
                db.update_value(ladrao_data['row'], 7, agora)
                self.bot.tracker_emblemas['roubos_falha'][ladrao_id] = self.bot.tracker_emblemas['roubos_falha'].get(ladrao_id, 0) + 1
                await ctx.send(f"👮 **PRESO!** O roubo falhou e você pagou **{multa:.2f} MC** de multa para {vitima.mention}.")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !roubar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    @commands.command(aliases=["pix", "transferir", "pay"])
    async def pagar(self, ctx, recebedor: disnake.Member = None, valor: float = None):
        if recebedor is None or valor is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!pagar @usuario <valor>`")
        if recebedor.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, não pode fazer Pix para si mesmo!")
        if valor <= 0:
            return await ctx.send("❌ O valor deve ser maior que zero!")
        valor = round(valor, 2)
        
        try:
            pag = db.get_user_data(str(ctx.author.id))
            saldo_pag = db.parse_float(pag['data'][2]) if pag else 0.0
            if not pag or saldo_pag < valor:
                return await ctx.send("❌ Saldo insuficiente!")

            rec = db.get_user_data(str(recebedor.id))
            if not rec:
                db.create_user(str(recebedor.id), recebedor.display_name)
                rec = db.get_user_data(str(recebedor.id))

            db.update_value(pag['row'], 3, round(saldo_pag - valor, 2))
            db.update_value(rec['row'], 3, round(db.parse_float(rec['data'][2]) + valor, 2))

            embed = disnake.Embed(
                title="💸 PIX REALIZADO!",
                description=f"**{ctx.author.mention}** enviou **{valor:.2f} MC** para **{recebedor.mention}**.",
                color=disnake.Color.green()
            )
            await ctx.send(embed=embed)
            
            if valor == 0.01:
                conquistas_pag = str(pag['data'][9]) if len(pag['data']) > 9 else ""
                lista_conquistas = [c.strip() for c in conquistas_pag.split(',') if c.strip()]
                
                if "pix_irritante" not in lista_conquistas:
                    lista_conquistas.append("pix_irritante")
                    db.update_value(pag['row'], 10, ", ".join(lista_conquistas))

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !pagar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(Economy(bot))