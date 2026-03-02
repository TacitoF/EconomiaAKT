import disnake
from disnake.ext import commands
import database as db
import time
import random

ESCUDO_CARGAS = 3

def formatar_moeda(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, 'recompensas'): bot.recompensas = {}
        if not hasattr(bot, 'cascas'): bot.cascas = set()
        if not hasattr(bot, 'impostos'): bot.impostos = {}
        if not hasattr(bot, 'tracker_emblemas'):
            bot.tracker_emblemas = {'trabalhos': {}, 'roubos_sucesso': {}, 'roubos_falha': {}}
        if not hasattr(bot, 'escudos_ativos'): bot.escudos_ativos = {}
        if not hasattr(bot, 'escudo_compras'): bot.escudo_compras = {}
        if not hasattr(bot, 'cooldown_imposto'): bot.cooldown_imposto = {}

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, assuntos de dinheiro são apenas no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["work"])
    @commands.cooldown(1, 5, commands.BucketType.user) # Evita spam
    async def trabalhar(self, ctx):
        user_id = str(ctx.author.id)
        try:
            user = db.get_user_data(user_id)
            if not user:
                db.create_user(user_id, ctx.author.name)
                user = db.get_user_data(user_id)
            if not user:
                return await ctx.send(f"❌ {ctx.author.mention}, erro ao criar a sua conta! Tente novamente.")

            agora = time.time()
            ultimo_work = db.parse_float(user['data'][4] if len(user['data']) > 4 else None)

            if agora - ultimo_work < 3600:
                return await ctx.send(f"⏳ {ctx.author.mention}, você está exausto! Volte <t:{int(ultimo_work + 3600)}:R>.")

            if user_id in self.bot.cascas:
                self.bot.cascas.remove(user_id)
                db.update_value(user['row'], 5, agora)
                return await ctx.send(f"🍌 **SPLASH!** {ctx.author.mention} escorregou em uma casca de banana e não ganhou nada!")

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
                taxa = round(ganho * 0.25, 2)
                ganho = round(ganho - taxa, 2)

                cobrador_db = db.get_user_data(imposto_data['cobrador_id'])
                if cobrador_db:
                    db.update_value(cobrador_db['row'], 3, round(db.parse_float(cobrador_db['data'][2]) + taxa, 2))

                cobrador_user = self.bot.get_user(int(imposto_data['cobrador_id']))
                nome_c = cobrador_user.mention if cobrador_user else "Um Gorila"

                imposto_data['cargas'] -= 1
                cargas_restantes = imposto_data['cargas']

                if cargas_restantes <= 0:
                    del self.bot.impostos[user_id]
                    db.clear_imposto(user['row'])
                    libera_em = int(time.time() + 86400)
                    self.bot.cooldown_imposto[user_id] = libera_em
                    imposto_msg = f"\n🦍 **IMPOSTO ATIVO:** {nome_c} confiscou **{formatar_moeda(taxa)} MC** do seu suor!\n🕊️ *O Imposto acabou. Você está imune a novos impostos por **24h** (<t:{libera_em}:R>).*"
                else:
                    imposto_msg = f"\n🦍 **IMPOSTO ATIVO:** {nome_c} confiscou **{formatar_moeda(taxa)} MC** do seu suor! *(Restam {cargas_restantes} trabalhos taxados)*"

            saldo_atual = db.parse_float(user['data'][2])
            novo_saldo = round(saldo_atual + ganho, 2)
            db.update_value(user['row'], 3, novo_saldo)
            db.update_value(user['row'], 5, agora)

            drop_msg = ""
            chance_drop = random.random()
            caixa_ganha = None

            if chance_drop <= 0.001:
                caixa_ganha = "Relíquia Ancestral"
            elif chance_drop <= 0.010:
                caixa_ganha = "Baú do Caçador"
            elif chance_drop <= 0.050:
                caixa_ganha = "Caixote de Madeira"

            if caixa_ganha:
                inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
                inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
                inv_list.append(caixa_ganha)
                db.update_value(user['row'], 6, ", ".join(inv_list))
                drop_msg = f"\n📦 **SORTE GRANDE!** Você escavou e encontrou um(a) **{caixa_ganha}**!\n*(Use `!abrir {caixa_ganha.split()[0]}` para ver o que tem dentro)*"

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
                    conquista_msg = "\n🏆 Desbloqueou a conquista **Proletário Padrão**!"

            proximo_cd = int(agora + 3600)
            CARGO_CORES = {
                "Lêmure": 0x8B7540, "Macaquinho": 0x6B8B40, "Babuíno": 0x2E8B57,
                "Chimpanzé": 0x1A6E9A, "Orangutango": 0xC0560A,
                "Gorila": 0x7B2D8B, "Ancestral": 0xA01020, "Rei Símio": 0xFFD700,
            }
            embed = disnake.Embed(color=CARGO_CORES.get(cargo, 0x2E8B57))
            embed.set_author(
                name     = f"{ctx.author.display_name} foi trabalhar",
                icon_url = ctx.author.display_avatar.url,
            )
            embed.add_field(name="💰 Ganho",         value=f"**+{formatar_moeda(ganho)} MC**", inline=True)
            embed.add_field(name="🏦 Saldo atual",   value=f"`{formatar_moeda(novo_saldo)} MC`", inline=True)
            embed.add_field(name="⏰ Próximo turno", value=f"<t:{proximo_cd}:R>", inline=True)
            if imposto_msg:
                embed.add_field(name="🦍 Imposto do Gorila", value=imposto_msg.strip().lstrip("\n"), inline=False)
            if drop_msg:
                embed.add_field(name="🎁 Loot Encontrado", value=drop_msg.strip().lstrip("\n"), inline=False)
            if conquista_msg:
                embed.add_field(name="🏆 Conquista!", value=conquista_msg.strip().lstrip("\n"), inline=False)
            embed.set_footer(text=f"💼 Cargo: {cargo}  ·  !perfil para ver o seu progresso")
            await ctx.send(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !trabalhar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    @trabalhar.error
    async def trabalhar_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Calma, macaco! Aguarde {error.retry_after:.1f}s para usar o comando de novo.", delete_after=4)

    @commands.command(aliases=["assaltar", "furtar", "rob"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def roubar(self, ctx, vitima: disnake.Member = None):
        if vitima is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, uso: `!roubar @usuario`")

        ladrao_id = str(ctx.author.id)

        if vitima.id == ctx.author.id:
            ladrao_data = db.get_user_data(ladrao_id)
            if ladrao_data:
                lista_p = [c.strip() for c in str(ladrao_data['data'][9]).split(',') if c.strip()]
                if "palhaco" not in lista_p:
                    lista_p.append("palhaco")
                    db.update_value(ladrao_data['row'], 10, ", ".join(lista_p))
            return await ctx.send("🐒 Palhaço! Você não pode roubar a si mesmo.")

        try:
            ladrao_data = db.get_user_data(ladrao_id)
            alvo_data   = db.get_user_data(str(vitima.id))
            if not ladrao_data or not alvo_data:
                return await ctx.send("❌ Uma das contas não foi encontrada!")

            saldo_ladrao = db.parse_float(ladrao_data['data'][2])
            saldo_alvo   = db.parse_float(alvo_data['data'][2])

            if saldo_alvo < 80:
                return await ctx.send(f"😬 {vitima.mention} está tão pobre que não vale a pena o risco.")

            agora     = time.time()
            vitima_id = str(vitima.id)

            ultimo_roubo = db.parse_float(ladrao_data['data'][6] if len(ladrao_data['data']) > 6 else None)
            if agora - ultimo_roubo < 7200:
                return await ctx.send(f"👮 Só pode roubar novamente <t:{int(ultimo_roubo + 7200)}:R>.")

            if ladrao_id in self.bot.cascas:
                self.bot.cascas.remove(ladrao_id)
                db.update_value(ladrao_data['row'], 7, agora)
                return await ctx.send(f"🍌 **QUE AZAR!** {ctx.author.mention} escorregou numa casca de banana e fugiu de mãos vazias.")

            inv_ladrao = [i.strip() for i in str(ladrao_data['data'][5] if len(ladrao_data['data']) > 5 else "").split(',') if i.strip()]
            inv_alvo   = [i.strip() for i in str(alvo_data['data'][5]   if len(alvo_data['data'])   > 5 else "").split(',') if i.strip()]

            usou_pe_de_cabra = False
            chance_sucesso   = 45

            if "Pé de Cabra" in inv_ladrao:
                chance_sucesso   = 65
                usou_pe_de_cabra = True
                inv_ladrao.remove("Pé de Cabra")
                db.update_value(ladrao_data['row'], 6, ", ".join(inv_ladrao))

            cargas_atuais = self.bot.escudos_ativos.get(vitima_id, 0)

            if cargas_atuais == 0 and "Escudo" in inv_alvo:
                cargas_atuais = ESCUDO_CARGAS
                self.bot.escudos_ativos[vitima_id] = cargas_atuais
                inv_alvo.remove("Escudo")
                db.update_value(alvo_data['row'], 6, ", ".join(inv_alvo))

            escudo_ativo = cargas_atuais > 0
            msg_escudo = ""

            if escudo_ativo:
                cargas_atuais -= 1
                db.update_value(ladrao_data['row'], 7, agora)

                if cargas_atuais > 0:
                    self.bot.escudos_ativos[vitima_id] = cargas_atuais
                    texto_carga = f"*(Cargas restantes: **{cargas_atuais}/{ESCUDO_CARGAS}** 🛡️)*"
                else:
                    del self.bot.escudos_ativos[vitima_id]
                    texto_carga = f"*(O escudo **QUEBROU** com o impacto! {vitima.mention} está desprotegido 💥)*"

                if usou_pe_de_cabra:
                    msg_escudo = f"\n🛠️ O seu **Pé de Cabra** arrombou a porta e danificou o **Escudo** de {vitima.mention}! {texto_carga}"
                else:
                    conquistas_ladrao = str(ladrao_data['data'][9]) if len(ladrao_data['data']) > 9 else ""
                    lista_c = [c.strip() for c in conquistas_ladrao.split(',') if c.strip()]
                    if "casca_grossa" not in lista_c:
                        lista_c.append("casca_grossa")
                        db.update_value(ladrao_data['row'], 10, ", ".join(lista_c))

                    emb_b = disnake.Embed(
                        title       = "🛡️ Ataque bloqueado!",
                        description = f"{vitima.mention} defendeu-se com um **Escudo** e o seu ataque foi repelido.",
                        color       = 0x3498DB,
                    )
                    emb_b.add_field(name="🛡️ Status do Escudo", value=texto_carga, inline=False)
                    return await ctx.send(embed=emb_b)

            if random.randint(1, 100) <= chance_sucesso:
                if saldo_alvo < 500:
                    pct      = random.uniform(0.01, 0.05)
                    is_pobre = True
                else:
                    pct      = random.uniform(0.05, 0.10)
                    is_pobre = False

                valor_roubado = min(round(saldo_alvo * pct, 2), 12000.0)

                if valor_roubado < 5:
                    return await ctx.send(f"😬 {vitima.mention} está tão pobre que não valia a pena o risco.")

                bounty_ganho = self.bot.recompensas.pop(vitima_id, 0.0)

                seguro_msg = ""
                if "Seguro" in inv_alvo:
                    recuperado = round(valor_roubado * 0.6, 2)
                    db.update_value(alvo_data['row'], 3, round(saldo_alvo - valor_roubado + recuperado, 2))
                    inv_alvo.remove("Seguro")
                    db.update_value(alvo_data['row'], 6, ", ".join(inv_alvo))
                    seguro_msg = f"\n📄 **SEGURO ACIONADO:** {vitima.mention} foi reembolsado em **{formatar_moeda(recuperado)} MC**!"
                else:
                    db.update_value(alvo_data['row'], 3, round(saldo_alvo - valor_roubado, 2))

                db.update_value(ladrao_data['row'], 3, round(saldo_ladrao + valor_roubado + bounty_ganho, 2))
                db.update_value(ladrao_data['row'], 7, agora)

                bounty_adicionado = min(round(valor_roubado * 0.12, 2), 2000.0)
                self.bot.recompensas[ladrao_id] = round(self.bot.recompensas.get(ladrao_id, 0.0) + bounty_adicionado, 2)

                tracker = self.bot.tracker_emblemas['roubos_sucesso']
                if ladrao_id not in tracker: tracker[ladrao_id] = []
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
                        conquista_msg = "\n🏆 Desbloqueou a conquista **Mestre das Sombras**!"

                titulo_s = "🥷 SUCESSO (com pena)..." if is_pobre else "🥷 SUCESSO!"
                desc_s   = (
                    f"{vitima.mention} estava quase na miséria — só levou umas moedinhas."
                    if is_pobre else
                    f"Você saqueou **{vitima.mention}** e sumiu na escuridão."
                )
                emb_s = disnake.Embed(title=titulo_s, description=desc_s, color=0x2ECC71)
                emb_s.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
                emb_s.add_field(name="💸 Roubado",    value=f"**+{formatar_moeda(valor_roubado)} MC**", inline=True)
                emb_s.add_field(name="🎯 Alvo",       value=vitima.mention,                             inline=True)
                if usou_pe_de_cabra:
                    emb_s.add_field(name="🕵️ Ferramenta", value="Usou **Pé de Cabra**", inline=True)
                if bounty_ganho > 0:
                    emb_s.add_field(name="🎯 Recompensa", value=f"**+{formatar_moeda(bounty_ganho)} MC**", inline=True)
                if seguro_msg:
                    emb_s.add_field(name="📄 Seguro", value=seguro_msg.strip().lstrip("\n"), inline=False)
                if msg_escudo:
                    emb_s.add_field(name="🛡️ Escudo", value=msg_escudo.strip().lstrip("\n"), inline=False)
                if conquista_msg:
                    emb_s.add_field(name="🏆 Conquista!", value=conquista_msg.strip().lstrip("\n"), inline=False)
                emb_s.set_footer(text=f"🚨 Recompensa de {formatar_moeda(bounty_adicionado)} MC colocada na sua cabeça automaticamente")
                await ctx.send(embed=emb_s)

            else:
                pct_multa = random.uniform(0.05, 0.10)
                multa = max(min(round(saldo_ladrao * pct_multa, 2), 5000.0), 30.0)
                db.update_value(ladrao_data['row'], 3, round(saldo_ladrao - multa, 2))
                db.update_value(alvo_data['row'],   3, round(saldo_alvo + multa, 2))
                db.update_value(ladrao_data['row'], 7, agora)
                self.bot.tracker_emblemas['roubos_falha'][ladrao_id] = self.bot.tracker_emblemas['roubos_falha'].get(ladrao_id, 0) + 1

                emb_f = disnake.Embed(
                    title       = "👮 PRESO! O roubo falhou.",
                    description = f"Você foi pego e pagou uma multa de **{formatar_moeda(multa)} MC** a {vitima.mention}.",
                    color       = 0xE74C3C,
                )
                emb_f.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
                emb_f.add_field(name="💸 Multa paga",     value=f"**-{formatar_moeda(multa)} MC**", inline=True)
                emb_f.add_field(name="👮 Denunciado por", value=vitima.mention,                     inline=True)
                if usou_pe_de_cabra:
                    emb_f.add_field(name="🕵️ Pé de Cabra", value="Usou mas deu azar", inline=True)
                if msg_escudo:
                    emb_f.add_field(name="🛡️ Escudo", value=msg_escudo.strip().lstrip("\n"), inline=False)
                await ctx.send(embed=emb_f)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !roubar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    @roubar.error
    async def roubar_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Agarre a sua máscara! Aguarde {error.retry_after:.1f}s.", delete_after=3)

    @commands.command(aliases=["pix", "transferir", "pay"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pagar(self, ctx, recebedor: disnake.Member = None, valor: float = None):
        if recebedor is None or valor is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, uso: `!pagar @usuario <valor>`")
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
                description=f"**{ctx.author.mention}** enviou **{formatar_moeda(valor)} MC** para **{recebedor.mention}**.",
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

    @pagar.error
    async def pagar_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ O banco central bloqueou o seu pix temporariamente. Aguarde {error.retry_after:.1f}s.", delete_after=3)

def setup(bot):
    bot.add_cog(Economy(bot))