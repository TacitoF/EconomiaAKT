import disnake
from disnake.ext import commands
import database as db
import time
import random

ESCUDO_CARGAS = 3

def formatar_moeda(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ──────────────────────────────────────────────────────────────────────────────
#  PASSIVOS — definição central de efeitos
#  Cada passivo tem um nome exato (igual ao que fica no inventário)
#  e um dict de efeitos que são lidos em !trabalhar e !roubar
# ──────────────────────────────────────────────────────────────────────────────

PASSIVOS_EFEITOS = {
    # ── Tier Comum ──
    "Amuleto da Sorte":     {"chance_roubo": +3},
    "Cinto de Ferramentas": {"bonus_trabalho": +0.04},
    "Carteira Velha":       {"limite_roubavel": -0.005},

    # ── Tier Raro ──
    "Segurança Particular": {"chance_defesa": -8},
    "Luvas de Seda":        {"pct_max_roubo": +0.03},
    "Sindicato":            {"reducao_cd_trabalho": 600},   # segundos
    "Cão de Guarda":        {"multa_bonus": +0.10},

    # ── Tier Épico ──
    "Relíquia do Ancião":   {"bonus_trabalho": +0.10},
    "Escudo de Sangue":     {"devolve_roubo": +0.05},
    "Manto das Sombras":    {"chance_roubo": +12},
    "Talismã da Fortuna":   {"cripto_piso": -0.10},         # reduz prejuízo máximo
}

def get_efeitos_passivos(passivos: list[str]) -> dict:
    """Soma todos os efeitos dos passivos equipados e retorna um dict acumulado."""
    acum = {}
    for nome in passivos:
        efeitos = PASSIVOS_EFEITOS.get(nome, {})
        for chave, val in efeitos.items():
            acum[chave] = acum.get(chave, 0) + val
    return acum


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, 'recompensas'):      bot.recompensas      = {}
        if not hasattr(bot, 'cascas'):            bot.cascas            = set()
        if not hasattr(bot, 'impostos'):          bot.impostos          = {}
        if not hasattr(bot, 'tracker_emblemas'):
            bot.tracker_emblemas = {'trabalhos': {}, 'roubos_sucesso': {}, 'roubos_falha': {}}
        if not hasattr(bot, 'escudos_ativos'):    bot.escudos_ativos    = {}
        if not hasattr(bot, 'cooldown_imposto'):  bot.cooldown_imposto  = {}

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, assuntos de dinheiro são apenas no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    # ──────────────────────────────────────────────────────────────────────────
    #  !trabalhar
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command(aliases=["work"])
    @commands.cooldown(1, 5, commands.BucketType.user)
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

            # ── Passivos do usuário ──
            passivos      = db.get_passivos(user)
            fx            = get_efeitos_passivos(passivos)
            reducao_cd    = fx.get("reducao_cd_trabalho", 0)   # segundos a menos no CD
            bonus_trab    = fx.get("bonus_trabalho", 0.0)       # multiplicador extra

            cd_efetivo = max(0, 3600 - reducao_cd)
            ultimo_work = db.parse_float(user['data'][4] if len(user['data']) > 4 else None)

            if agora - ultimo_work < cd_efetivo:
                volta_em = int(ultimo_work + cd_efetivo)
                return await ctx.send(f"⏳ {ctx.author.mention}, você está exausto! Volte <t:{volta_em}:R>.")

            if user_id in self.bot.cascas:
                self.bot.cascas.remove(user_id)
                db.update_value(user['row'], 5, agora)
                return await ctx.send(f"🍌 **SPLASH!** {ctx.author.mention} escorregou em uma casca de banana e não ganhou nada!")

            cargo = user['data'][3] if len(user['data']) > 3 and user['data'][3] else "Lêmure"

            salarios = {
                "Lêmure":      (40,    80),
                "Macaquinho":  (130,   230),
                "Babuíno":     (320,   530),
                "Chimpanzé":   (780,   1320),
                "Orangutango": (1900,  3200),
                "Gorila":      (4700,  7800),
                "Ancestral":   (11500, 19000),
                "Rei Símio":   (27000, 45000),
            }
            min_ganho, max_ganho = salarios.get(cargo, (40, 80))
            ganho = round(random.uniform(min_ganho, max_ganho), 2)

            # ── GREVE ──
            greve_msg  = ""
            greve_expira = db.get_greve(user)
            if greve_expira > 0 and agora < greve_expira:
                ganho_original = ganho
                ganho = round(ganho * 0.50, 2)
                greve_msg = (
                    f"🪧 **GREVE!** Seus trabalhadores estão em greve!\n"
                    f"Ganho reduzido: ~~{formatar_moeda(ganho_original)} MC~~ → **{formatar_moeda(ganho)} MC**\n"
                    f"*A greve termina <t:{int(greve_expira)}:R>.*"
                )

            # ── PASSIVO: bônus de trabalho ──
            passivo_trab_msg = ""
            if bonus_trab > 0:
                ganho_antes = ganho
                ganho = round(ganho * (1 + bonus_trab), 2)
                passivo_trab_msg = f"🔰 **Passivo:** +{int(bonus_trab * 100)}% no ganho (`+{formatar_moeda(ganho - ganho_antes)} MC`)"

            # ── MASCOTE (Buff de Trabalho) ──
            mascote_msg = ""
            tipo_mascote, fome_mascote = db.get_mascote(user)
            if tipo_mascote and fome_mascote > 0:
                gasto_fome  = 10
                buff_ativado = False

                if tipo_mascote == "capivara":
                    ganho = round(ganho * 1.10, 2); mascote_msg = "🦦 **Capivara:** +10% de lucro extra!\n"; buff_ativado = True
                elif tipo_mascote == "preguica":
                    ganho = round(ganho * 1.15, 2); gasto_fome = 15; mascote_msg = "🦥 **Bicho-Preguiça:** +15% de lucro extra!\n"; buff_ativado = True
                elif tipo_mascote == "sapo_boi":
                    ganho = round(ganho * 1.08, 2)
                    if random.random() <= 0.20:
                        gasto_fome = 0; mascote_msg = "🐸 **Sapo-Boi:** +8% de lucro *(Não gastou energia!)*\n"
                    else:
                        mascote_msg = "🐸 **Sapo-Boi:** +8% de lucro extra!\n"
                    buff_ativado = True
                elif tipo_mascote == "lobo_guara":
                    ganho = round(ganho * 1.10, 2); mascote_msg = "🐺 **Lobo-Guará:** +10% de lucro extra!\n"; buff_ativado = True
                elif tipo_mascote == "onca":
                    ganho = round(ganho * 1.15, 2); mascote_msg = "🐆 **Onça Pintada:** +15% de lucro extra!\n"; buff_ativado = True
                elif tipo_mascote == "gorila_prateado":
                    ganho = round(ganho * 1.25, 2); mascote_msg = "🦍 **Gorila Costas-Prateadas:** +25% de lucro extra!\n"; buff_ativado = True

                if buff_ativado:
                    nova_fome = max(0, fome_mascote - gasto_fome)
                    db.set_mascote(user['row'], tipo_mascote, nova_fome)
                    if nova_fome == 0:    mascote_msg += "💤 *O seu mascote dormiu de fome! Compre Ração na Loja.*"
                    elif gasto_fome > 0:  mascote_msg += f"🍗 *Fome do mascote caiu para {nova_fome}%*"

            # ── IMPOSTOS ──
            if user_id not in self.bot.impostos:
                cobrador_id, cargas, cd_imposto = db.get_imposto(user)
                if cobrador_id and cargas > 0:
                    self.bot.impostos[user_id] = {'cobrador_id': cobrador_id, 'cargas': cargas}
                elif cd_imposto > 0:
                    self.bot.cooldown_imposto[user_id] = cd_imposto

            imposto_msg = ""
            if user_id in self.bot.impostos:
                imposto_data = self.bot.impostos[user_id]
                taxa  = round(ganho * 0.25, 2)
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
                    libera_em = int(agora + 86400)
                    db.set_imposto_cooldown(user['row'], libera_em)
                    self.bot.cooldown_imposto[user_id] = libera_em
                    imposto_msg = f"🦍 **IMPOSTO:** {nome_c} confiscou **{formatar_moeda(taxa)} MC**!\n🕊️ *Você está imune a impostos por **24h**.*"
                else:
                    db.set_imposto(user['row'], imposto_data['cobrador_id'], cargas_restantes)
                    imposto_msg = f"🦍 **IMPOSTO:** {nome_c} confiscou **{formatar_moeda(taxa)} MC**! *(Restam {cargas_restantes} trabalhos taxados)*"

            saldo_atual = db.parse_float(user['data'][2])
            novo_saldo  = round(saldo_atual + ganho, 2)
            db.update_value(user['row'], 3, novo_saldo)
            db.update_value(user['row'], 5, agora)

            # ── DROPS INDEPENDENTES (Lootbox, Gaiolas e Passivos) ──
            drop_msg     = ""
            chance_caixa = random.random()
            caixa_ganha  = None
            emoji_caixa  = ""

            if chance_caixa <= 0.001:   caixa_ganha, emoji_caixa = "Relíquia Ancestral", "🏺"
            elif chance_caixa <= 0.010: caixa_ganha, emoji_caixa = "Baú do Caçador", "🪙"
            elif chance_caixa <= 0.050: caixa_ganha, emoji_caixa = "Caixote de Madeira", "🪵"

            chance_gaiola = random.random()
            gaiola_ganha  = chance_gaiola <= 0.015

            # Drop de passivos (chance pequena, independente da caixa)
            passivo_dropado = _sortear_passivo_drop(random.random())

            if caixa_ganha or gaiola_ganha or passivo_dropado:
                inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
                inv_list = [i.strip() for i in inv_str.split(',') if i.strip() and i.strip().lower() != "nenhum"]

                if caixa_ganha:
                    inv_list.append(caixa_ganha)
                    drop_msg += f"{emoji_caixa} **SORTE GRANDE!** Você encontrou um(a) **{caixa_ganha}**!\n"

                if gaiola_ganha:
                    inv_list.append("Gaiola Misteriosa")
                    drop_msg += f"🐾 **MISTÉRIO!** Você escutou um barulho e resgatou uma **Gaiola Misteriosa**!\n*(Use !abrir gaiola para descobrir o animal)*\n"

                if passivo_dropado:
                    inv_list.append(passivo_dropado["nome"])
                    drop_msg += f"{passivo_dropado['emoji']} **DROP RARO!** Você encontrou **{passivo_dropado['nome']}** *({passivo_dropado['tier']})*!\n*Use `!equipar` para ativar ou `!vender` para negociar.*\n"

                db.update_value(user['row'], 6, ", ".join(inv_list))

            # ── CONQUISTAS ──
            tracker = self.bot.tracker_emblemas['trabalhos']
            if user_id not in tracker: tracker[user_id] = []
            tracker[user_id] = [t for t in tracker[user_id] if agora - t < 86400]
            tracker[user_id].append(agora)

            conquista_msg = ""
            if len(tracker[user_id]) >= 10:
                conquistas_user  = str(user['data'][9]) if len(user['data']) > 9 else ""
                lista_conquistas = [c.strip() for c in conquistas_user.split(',') if c.strip()]
                if "proletario" not in lista_conquistas:
                    lista_conquistas.append("proletario")
                    db.update_value(user['row'], 10, ", ".join(lista_conquistas))
                    conquista_msg = "🏆 Desbloqueou a conquista **Proletário Padrão**!"

            proximo_cd = int(agora + cd_efetivo)
            CARGO_CORES = {
                "Lêmure": 0x8B7540, "Macaquinho": 0x6B8B40, "Babuíno": 0x2E8B57,
                "Chimpanzé": 0x1A6E9A, "Orangutango": 0xC0560A,
                "Gorila": 0x7B2D8B, "Ancestral": 0xA01020, "Rei Símio": 0xFFD700,
            }
            embed = disnake.Embed(color=CARGO_CORES.get(cargo, 0x2E8B57))
            embed.set_author(name=f"{ctx.author.display_name} foi trabalhar", icon_url=ctx.author.display_avatar.url)
            embed.add_field(name="💰 Ganho",         value=f"**+{formatar_moeda(ganho)} MC**",   inline=True)
            embed.add_field(name="🏦 Saldo atual",   value=f"`{formatar_moeda(novo_saldo)} MC`", inline=True)
            embed.add_field(name="⏰ Próximo turno", value=f"<t:{proximo_cd}:R>",                inline=True)

            if greve_msg:        embed.add_field(name="🪧 Greve",            value=greve_msg,        inline=False)
            if passivo_trab_msg: embed.add_field(name="🔰 Passivo",          value=passivo_trab_msg, inline=False)
            if mascote_msg:      embed.add_field(name="🐾 Ajuda do Mascote", value=mascote_msg,      inline=False)
            if imposto_msg:      embed.add_field(name="🦍 Imposto do Gorila",value=imposto_msg,      inline=False)
            if drop_msg:         embed.add_field(name="🎁 Loot Encontrado",  value=drop_msg,         inline=False)
            if conquista_msg:    embed.add_field(name="🏆 Conquista!",       value=conquista_msg,    inline=False)

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

    # ──────────────────────────────────────────────────────────────────────────
    #  !roubar
    # ──────────────────────────────────────────────────────────────────────────

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

            # ── PASSIVOS do ladrão ──
            passivos_ladrao = db.get_passivos(ladrao_data)
            fx_ladrao       = get_efeitos_passivos(passivos_ladrao)
            chance_sucesso += fx_ladrao.get("chance_roubo", 0)
            pct_max_bonus   = fx_ladrao.get("pct_max_roubo", 0.0)
            devolve_pct     = 0.0  # usado na vitima

            # ── PASSIVOS da vítima ──
            passivos_alvo = db.get_passivos(alvo_data)
            fx_alvo       = get_efeitos_passivos(passivos_alvo)
            chance_sucesso    += fx_alvo.get("chance_defesa", 0)   # valor negativo = reduz chance
            limite_reducao     = fx_alvo.get("limite_roubavel", 0.0)
            devolve_pct        = fx_alvo.get("devolve_roubo", 0.0)
            multa_bonus_alvo   = fx_alvo.get("multa_bonus", 0.0)

            msg_passivos = ""
            if fx_ladrao.get("chance_roubo"):
                msg_passivos += f"🔰 Seus passivos: **+{fx_ladrao['chance_roubo']}%** chance\n"
            if fx_alvo.get("chance_defesa"):
                msg_passivos += f"🔰 Passivos de {vitima.display_name}: **{fx_alvo['chance_defesa']}%** chance\n"

            # ── MASCOTES ──
            msg_mascotes        = ""
            multa_multiplicador = 1.0
            roubo_bonus         = 0.0

            tipo_pet_vitima, fome_vitima = db.get_mascote(alvo_data)
            if tipo_pet_vitima and fome_vitima > 0:
                if tipo_pet_vitima == "papagaio":
                    chance_sucesso -= 15
                    msg_mascotes += f"🦜 **Papagaio** de {vitima.display_name} avisou do perigo (-15% chance)\n"
                elif tipo_pet_vitima == "jiboia":
                    chance_sucesso -= 10
                    multa_multiplicador = 1.5
                    msg_mascotes += f"🐍 **Jiboia** de {vitima.display_name} se enrolou em você (-10% chance, multa aumentada)\n"
                elif tipo_pet_vitima == "gamba":
                    chance_sucesso -= 20
                    msg_mascotes += f"🦔 **Gambá** de {vitima.display_name} soltou um gás tóxico (-20% chance)\n"
                    db.set_mascote(alvo_data['row'], tipo_pet_vitima, max(0, fome_vitima - 20))
                elif tipo_pet_vitima == "onca":
                    chance_sucesso -= 15
                    msg_mascotes += f"🐆 **Onça Pintada** de {vitima.display_name} rosnou ferozmente (-15% chance)\n"
                elif tipo_pet_vitima == "dragao_komodo":
                    chance_sucesso -= 25
                    msg_mascotes += f"🐉 **Dragão-de-Komodo** de {vitima.display_name} defendeu a área (-25% chance)\n"

            tipo_pet_ladrao, fome_ladrao = db.get_mascote(ladrao_data)
            if tipo_pet_ladrao and fome_ladrao > 0:
                buff_ativado = False
                if tipo_pet_ladrao == "macaco_prego":
                    chance_sucesso += 15; msg_mascotes += f"🐒 **Macaco-Prego** furtou por você (+15% chance)\n"; buff_ativado = True
                elif tipo_pet_ladrao == "harpia":
                    chance_sucesso += 10; roubo_bonus = 0.05; msg_mascotes += f"🦅 **Harpia** atacou em rasante (+10% chance, bônus no roubo)\n"; buff_ativado = True
                elif tipo_pet_ladrao == "lobo_guara":
                    chance_sucesso += 10; msg_mascotes += f"🐺 **Lobo-Guará** distraiu a vítima (+10% chance)\n"; buff_ativado = True
                elif tipo_pet_ladrao == "onca":
                    chance_sucesso += 15; msg_mascotes += f"🐆 **Onça Pintada** emboscou com você (+15% chance)\n"; buff_ativado = True
                elif tipo_pet_ladrao == "gorila_prateado":
                    chance_sucesso += 20; msg_mascotes += f"🦍 **Gorila Costas-Prateadas** usou a força (+20% chance)\n"; buff_ativado = True
                elif tipo_pet_ladrao == "dragao_komodo":
                    chance_sucesso += 25; msg_mascotes += f"🐉 **Dragão-de-Komodo** imobilizou o alvo (+25% chance)\n"; buff_ativado = True

                if buff_ativado:
                    nova_fome_l = max(0, fome_ladrao - 15)
                    db.set_mascote(ladrao_data['row'], tipo_pet_ladrao, nova_fome_l)

            # ── ESCUDO ──
            if vitima_id not in self.bot.escudos_ativos:
                cargas_db, quebra_ts = db.get_escudo_data(alvo_data)
                if cargas_db > 0:
                    self.bot.escudos_ativos[vitima_id] = cargas_db

            cargas_atuais = self.bot.escudos_ativos.get(vitima_id, 0)

            if cargas_atuais == 0 and "Escudo" in inv_alvo:
                cargas_atuais = ESCUDO_CARGAS
                self.bot.escudos_ativos[vitima_id] = cargas_atuais
                inv_alvo.remove("Escudo")
                db.update_value(alvo_data['row'], 6, ", ".join(inv_alvo))
                db.set_escudo_data(alvo_data['row'], cargas_atuais)

            escudo_ativo = cargas_atuais > 0
            msg_escudo   = ""

            if escudo_ativo:
                cargas_atuais -= 1
                db.update_value(ladrao_data['row'], 7, agora)

                if cargas_atuais > 0:
                    self.bot.escudos_ativos[vitima_id] = cargas_atuais
                    db.set_escudo_data(alvo_data['row'], cargas_atuais)
                    texto_carga = f"*(Cargas restantes: **{cargas_atuais}/{ESCUDO_CARGAS}** 🛡️)*"
                else:
                    del self.bot.escudos_ativos[vitima_id]
                    db.set_escudo_data(alvo_data['row'], 0, agora)
                    texto_carga = f"*(O escudo **QUEBROU** com o impacto! {vitima.mention} está desprotegido 💥)*"

                if usou_pe_de_cabra:
                    msg_escudo = f"🛠️ O seu **Pé de Cabra** arrombou a porta e danificou o **Escudo** de {vitima.mention}! {texto_carga}"
                else:
                    conquistas_ladrao = str(ladrao_data['data'][9]) if len(ladrao_data['data']) > 9 else ""
                    lista_c = [c.strip() for c in conquistas_ladrao.split(',') if c.strip()]
                    if "casca_grossa" not in lista_c:
                        lista_c.append("casca_grossa")
                        db.update_value(ladrao_data['row'], 10, ", ".join(lista_c))

                    emb_b = disnake.Embed(
                        title="🛡️ Ataque bloqueado!",
                        description=f"{vitima.mention} defendeu-se com um **Escudo** e o seu ataque foi repelido.",
                        color=0x3498DB
                    )
                    emb_b.add_field(name="🛡️ Status do Escudo", value=texto_carga, inline=False)
                    if msg_mascotes:  emb_b.add_field(name="🐾 Interferência", value=msg_mascotes.strip(), inline=False)
                    if msg_passivos:  emb_b.add_field(name="🔰 Passivos",      value=msg_passivos.strip(), inline=False)
                    return await ctx.send(embed=emb_b)

            # ── ROUBO ──
            if random.randint(1, 100) <= chance_sucesso:
                if saldo_alvo < 80:
                    return await ctx.send(f"😬 {vitima.mention} está tão pobre que não vale a pena o risco.")

                if saldo_alvo < 500:
                    pct, is_pobre = random.uniform(0.01, 0.05), True
                else:
                    pct, is_pobre = random.uniform(0.05, 0.10 + pct_max_bonus), False

                # Passivo Carteira Velha da vítima reduz % máximo roubável
                pct = min(pct, 0.10 + pct_max_bonus + limite_reducao)

                pct        += roubo_bonus
                limite_saque = 15000.0 if roubo_bonus > 0 else 12000.0
                valor_roubado = min(round(saldo_alvo * pct, 2), limite_saque)

                if valor_roubado < 5:
                    return await ctx.send(f"😬 {vitima.mention} está tão pobre que não valia a pena o risco.")

                bounty_ganho = self.bot.recompensas.pop(vitima_id, 0.0)

                # ── PASSIVO: Escudo de Sangue — devolve % do roubado ──
                escudo_sangue_msg = ""
                if devolve_pct > 0:
                    devolvido   = round(valor_roubado * devolve_pct, 2)
                    corte_saldo = max(0, valor_roubado - devolvido)
                    db.update_value(alvo_data['row'], 3, round(saldo_alvo - corte_saldo, 2))
                    escudo_sangue_msg = f"🔰 **Escudo de Sangue:** {vitima.mention} recuperou **{formatar_moeda(devolvido)} MC** do roubo!"
                
                seguro_msg = ""
                if "Seguro" in inv_alvo:
                    recuperado = round(valor_roubado * 0.6, 2)
                    db.update_value(alvo_data['row'], 3, round(saldo_alvo - valor_roubado + recuperado, 2))
                    inv_alvo.remove("Seguro")
                    db.update_value(alvo_data['row'], 6, ", ".join(inv_alvo))
                    seguro_msg = f"📄 **SEGURO ACIONADO:** {vitima.mention} foi reembolsado em **{formatar_moeda(recuperado)} MC**!"
                elif not escudo_sangue_msg:
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
                    lista_conquistas  = [c.strip() for c in conquistas_ladrao.split(',') if c.strip()]
                    if "mestre_sombras" not in lista_conquistas:
                        lista_conquistas.append("mestre_sombras")
                        db.update_value(ladrao_data['row'], 10, ", ".join(lista_conquistas))
                        conquista_msg = "🏆 Desbloqueou a conquista **Mestre das Sombras**!"

                titulo_s = "🥷 SUCESSO (com pena)..." if is_pobre else "🥷 SUCESSO!"
                desc_s   = f"{vitima.mention} estava quase na miséria." if is_pobre else f"Você saqueou **{vitima.mention}** e sumiu na escuridão."
                emb_s = disnake.Embed(title=titulo_s, description=desc_s, color=0x2ECC71)
                emb_s.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
                emb_s.add_field(name="💸 Roubado", value=f"**+{formatar_moeda(valor_roubado)} MC**", inline=True)
                emb_s.add_field(name="🎯 Alvo",    value=vitima.mention,                             inline=True)

                if usou_pe_de_cabra: emb_s.add_field(name="🕵️ Ferramenta",        value="Usou **Pé de Cabra**",   inline=True)
                if bounty_ganho > 0: emb_s.add_field(name="🎯 Recompensa",        value=f"**+{formatar_moeda(bounty_ganho)} MC**", inline=True)
                if msg_passivos:     emb_s.add_field(name="🔰 Passivos",           value=msg_passivos.strip(),     inline=False)
                if msg_mascotes:     emb_s.add_field(name="🐾 Ajuda Animal",       value=msg_mascotes.strip(),     inline=False)
                if escudo_sangue_msg:emb_s.add_field(name="🔰 Escudo de Sangue",  value=escudo_sangue_msg,        inline=False)
                if seguro_msg:       emb_s.add_field(name="📄 Seguro",             value=seguro_msg,               inline=False)
                if msg_escudo:       emb_s.add_field(name="🛡️ Escudo",             value=msg_escudo,               inline=False)
                if conquista_msg:    emb_s.add_field(name="🏆 Conquista!",         value=conquista_msg,            inline=False)

                emb_s.set_footer(text=f"🚨 Recompensa de {formatar_moeda(bounty_adicionado)} MC colocada na sua cabeça")
                await ctx.send(embed=emb_s)

            else:
                pct_multa  = random.uniform(0.05, 0.10)
                multa_base = max(min(round(saldo_ladrao * pct_multa, 2), 5000.0), 30.0)
                # Passivo Cão de Guarda da vítima aumenta a multa
                multa = round(multa_base * multa_multiplicador * (1 + multa_bonus_alvo), 2)

                db.update_value(ladrao_data['row'], 3, round(saldo_ladrao - multa, 2))
                db.update_value(alvo_data['row'],   3, round(saldo_alvo + multa, 2))
                db.update_value(ladrao_data['row'], 7, agora)
                self.bot.tracker_emblemas['roubos_falha'][ladrao_id] = self.bot.tracker_emblemas['roubos_falha'].get(ladrao_id, 0) + 1

                cao_guarda_msg = ""
                if multa_bonus_alvo > 0:
                    cao_guarda_msg = f"🔰 **Cão de Guarda** de {vitima.display_name} aumentou a multa em +{int(multa_bonus_alvo*100)}%!"

                emb_f = disnake.Embed(
                    title="👮 PRESO! O roubo falhou.",
                    description=f"Você foi pego e pagou uma multa de **{formatar_moeda(multa)} MC** a {vitima.mention}.",
                    color=0xE74C3C
                )
                emb_f.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
                emb_f.add_field(name="💸 Multa paga",     value=f"**-{formatar_moeda(multa)} MC**", inline=True)
                emb_f.add_field(name="👮 Denunciado por", value=vitima.mention,                     inline=True)
                if usou_pe_de_cabra: emb_f.add_field(name="🕵️ Pé de Cabra",   value="Usou mas deu azar",          inline=True)
                if msg_passivos:     emb_f.add_field(name="🔰 Passivos",        value=msg_passivos.strip(),         inline=False)
                if cao_guarda_msg:   emb_f.add_field(name="🔰 Cão de Guarda",   value=cao_guarda_msg,               inline=False)
                if msg_mascotes:     emb_f.add_field(name="🐾 Interferência",   value=msg_mascotes.strip(),         inline=False)
                if msg_escudo:       emb_f.add_field(name="🛡️ Escudo",           value=msg_escudo,                   inline=False)
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

    # ──────────────────────────────────────────────────────────────────────────
    #  !pagar
    # ──────────────────────────────────────────────────────────────────────────

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
            pag       = db.get_user_data(str(ctx.author.id))
            saldo_pag = db.parse_float(pag['data'][2]) if pag else 0.0
            if not pag or saldo_pag < valor:
                return await ctx.send("❌ Saldo insuficiente!")

            rec = db.get_user_data(str(recebedor.id))
            if not rec:
                db.create_user(str(recebedor.id), recebedor.display_name)
                rec = db.get_user_data(str(recebedor.id))

            novo_saldo_pag = round(saldo_pag - valor, 2)
            db.update_value(pag['row'], 3, novo_saldo_pag)
            db.update_value(rec['row'], 3, round(db.parse_float(rec['data'][2]) + valor, 2))

            embed = disnake.Embed(
                title="💸 PIX REALIZADO!",
                description=(
                    f"**{ctx.author.mention}** enviou **{formatar_moeda(valor)} MC** para **{recebedor.mention}**.\n\n"
                    f"🏦 Seu saldo restante: `{formatar_moeda(novo_saldo_pag)} MC`"
                ),
                color=disnake.Color.green()
            )
            await ctx.send(embed=embed)

            if valor == 0.01:
                conquistas_pag   = str(pag['data'][9]) if len(pag['data']) > 9 else ""
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


# ──────────────────────────────────────────────────────────────────────────────
#  DROP DE PASSIVOS — tabela de chances por tier
# ──────────────────────────────────────────────────────────────────────────────

PASSIVOS_DROP_TABLE = [
    # (chance acumulada, nome, emoji, tier)
    # Tier Comum: ~3% no total
    (0.0100, "Amuleto da Sorte",     "🍀", "Comum"),
    (0.0200, "Cinto de Ferramentas", "🔧", "Comum"),
    (0.0300, "Carteira Velha",       "👛", "Comum"),
    # Tier Raro: ~1.5% no total
    (0.0370, "Segurança Particular", "🔒", "Raro"),
    (0.0420, "Luvas de Seda",        "🧤", "Raro"),
    (0.0470, "Sindicato",            "🏛️", "Raro"),
    (0.0500, "Cão de Guarda",        "🐕", "Raro"),
    # Tier Épico: ~0.5% no total
    (0.0515, "Relíquia do Ancião",   "🏺", "Épico"),
    (0.0525, "Escudo de Sangue",     "🩸", "Épico"),
    (0.0535, "Manto das Sombras",    "🌑", "Épico"),
    (0.0540, "Talismã da Fortuna",   "🌟", "Épico"),
]

def _sortear_passivo_drop(roll: float) -> dict | None:
    """Recebe um float 0–1 e retorna o passivo dropado ou None."""
    for chance_acum, nome, emoji, tier in PASSIVOS_DROP_TABLE:
        if roll <= chance_acum:
            return {"nome": nome, "emoji": emoji, "tier": tier}
    return None


def setup(bot):
    bot.add_cog(Economy(bot))