import disnake
from disnake.ext import commands
import database as db
import time
import asyncio

ESCUDO_CARGAS  = 3
SEGURO_CARGAS  = 5

# ──────────────────────────────────────────────────────────────────────────────
#  CATÁLOGO DE PASSIVOS — usado no !equipar / !desequipar / !passivos
# ──────────────────────────────────────────────────────────────────────────────

PASSIVOS_INFO = {
    # Tier Comum
    "Amuleto da Sorte":     {"emoji": "🍀", "tier": "Comum",     "efeito": "+3% chance de sucesso no !roubar"},
    "Cinto de Ferramentas": {"emoji": "🔧", "tier": "Comum",     "efeito": "+4% ganho no !trabalhar"},
    "Carteira Velha":       {"emoji": "👛", "tier": "Comum",     "efeito": "-0.5% no máximo que podem te roubar"},
    # Tier Raro
    "Segurança Particular": {"emoji": "🔒", "tier": "Raro",      "efeito": "-8% chance do ladrão ter sucesso contra você"},
    "Luvas de Seda":        {"emoji": "🧤", "tier": "Raro",      "efeito": "+3% no máximo que você pode roubar"},
    "Sindicato":            {"emoji": "🏛️", "tier": "Raro",      "efeito": "-10min de cooldown no !trabalhar"},
    "Cão de Guarda":        {"emoji": "🐕", "tier": "Raro",      "efeito": "+10% na multa do ladrão se falhar contra você"},
    # Tier Épico
    "Relíquia do Ancião":   {"emoji": "🏺", "tier": "Épico",     "efeito": "+10% ganho no !trabalhar"},
    "Escudo de Sangue":     {"emoji": "🩸", "tier": "Épico",     "efeito": "Recupera 5% do valor roubado de volta"},
    "Manto das Sombras":    {"emoji": "🌑", "tier": "Épico",     "efeito": "+12% chance de sucesso no !roubar"},
    "Talismã da Fortuna":   {"emoji": "🌟", "tier": "Épico",     "efeito": "Reduz prejuízo máximo no !cripto para 15%"},
    # ── Tier Patrimônio (compráveis na loja) ─────────────────────────────────
    # Raro
    "Bicicleta Elétrica":   {"emoji": "🚲", "tier": "Patrimônio","efeito": "-15min de cooldown no !trabalhar"},
    "Trailer":              {"emoji": "🚐", "tier": "Patrimônio","efeito": "-5% no máximo que podem te roubar"},
    "Moto":                 {"emoji": "🏍️", "tier": "Patrimônio","efeito": "+6% chance de sucesso no !roubar"},
    "Kitnet":               {"emoji": "🏠", "tier": "Patrimônio","efeito": "+8% ganho no !trabalhar"},
    # Lendário
    "Carro Esportivo":      {"emoji": "🏎️", "tier": "Patrimônio","efeito": "+10% chance de sucesso no !roubar e -15% multa se falhar"},
    "Mansão":               {"emoji": "🏰", "tier": "Patrimônio","efeito": "+20% ganho no !trabalhar"},
    "Iate":                 {"emoji": "🛥️", "tier": "Patrimônio","efeito": "-30min de cooldown no !trabalhar"},
    "Helicóptero":          {"emoji": "🚁", "tier": "Patrimônio","efeito": "-20% chance do ladrão ter sucesso contra você"},
    "Ilha Privada":         {"emoji": "🏝️", "tier": "Patrimônio","efeito": "+15% ganho no !trabalhar e -10% chance de ser roubado"},
}

TIER_COR = {
    "Comum":      0x8B8B8B,
    "Raro":       0x1A6E9A,
    "Épico":      0x7B2D8B,
    "Patrimônio": 0xE8A400,  # dourado/âmbar — riqueza
}

GREVE_TURNS = 3     # quantos !trabalhar sofrem o debuff
GREVE_DURACAO = GREVE_TURNS * 3600  # 3h (equivale a 3 turnos se usar todo CD)


class Items(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, 'cascas'):           bot.cascas           = set()
        if not hasattr(bot, 'impostos'):         bot.impostos         = {}
        if not hasattr(bot, 'escudos_ativos'):   bot.escudos_ativos   = {}
        if not hasattr(bot, 'seguros_ativos'):   bot.seguros_ativos   = {}
        if not hasattr(bot, 'escudo_compras'):   bot.escudo_compras   = {}
        if not hasattr(bot, 'cooldown_imposto'): bot.cooldown_imposto = {}

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, use itens no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    # ── FUNÇÃO MESTRA PARA CONSUMIR ITENS (IGNORA O CADEADO) ──
    def _consumir_item(self, user_row: int, inv_list: list, nome_base: str) -> bool:
        """Verifica se o usuário tem o item (com ou sem 🔒) e o consome."""
        item_para_remover = None
        
        # Procura primeiro pela versão normal
        if nome_base in inv_list:
            item_para_remover = nome_base
        # Se não achar, procura pela versão vinculada
        else:
            nome_vinculado = f"{nome_base} 🔒"
            if nome_vinculado in inv_list:
                item_para_remover = nome_vinculado

        if item_para_remover:
            inv_list.remove(item_para_remover)
            db.update_value(user_row, 6, ", ".join(inv_list) if inv_list else "Nenhum")
            return True
        return False

    # ──────────────────────────────────────────────────────────────────────────
    #  !casca
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command(aliases=["banana"])
    async def casca(self, ctx, vitima: disnake.Member = None):
        if vitima is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, uso: `!casca @usuario`")
        if vitima.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, não pode jogar a casca no próprio pé!")

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user: return await ctx.send("❌ Você não tem conta!")

            inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
            
            if not self._consumir_item(user['row'], inv_list, "Casca de Banana"):
                return await ctx.send("❌ Você não tem uma **Casca de Banana** no inventário!")

            self.bot.cascas.add(str(vitima.id))
            
            ctx._missao_ok = True

            await ctx.send(
                f"🍌 {ctx.author.mention} atirou uma **Casca de Banana** aos pés de {vitima.mention}!\n"
                f"O próximo trabalho dele será uma tragédia..."
            )

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !casca de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ──────────────────────────────────────────────────────────────────────────
    #  !taxar
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command(aliases=["imposto"])
    async def taxar(self, ctx, vitima: disnake.Member = None):
        if vitima is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, uso: `!taxar @usuario`")
        if vitima.id == ctx.author.id:
            return await ctx.send("❌ Não pode taxar a si mesmo!")
        if vitima.bot:
            return await ctx.send("🤖 Bots não pagam impostos!")

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user: return await ctx.send("❌ Você não tem conta!")

            inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]

            # Verifica se o alvo é taxável ANTES de consumir o item
            vitima_id = str(vitima.id)
            vitima_db = db.get_user_data(vitima_id)
            if not vitima_db:
                return await ctx.send("❌ O alvo não tem conta registrada!")

            cobrador_id, cargas, cd_imposto = db.get_imposto(vitima_db)

            if cd_imposto > 0 and time.time() < cd_imposto:
                return await ctx.send(
                    f"🛡️ {vitima.mention} está **imune** ao Imposto do Gorila! "
                    f"A imunidade expira <t:{int(cd_imposto)}:R>."
                )

            if cargas > 0:
                return await ctx.send(
                    f"❌ {vitima.mention} já está sob imposto! "
                    f"Restam **{cargas} trabalhos** taxados para ele."
                )

            if not self._consumir_item(user['row'], inv_list, "Imposto do Gorila"):
                return await ctx.send("❌ Você não tem o item **Imposto do Gorila** no inventário!")

            # ── Verificar se a vítima tem Escudo Anti-Imposto ──
            vitima_inv_str  = str(vitima_db['data'][5]) if len(vitima_db['data']) > 5 else ""
            vitima_inv_list = [i.strip() for i in vitima_inv_str.split(',') if i.strip()]

            if self._consumir_item(vitima_db['row'], vitima_inv_list, "Escudo Anti-Imposto"):
                ctx._missao_ok = True
                # Ambos os itens são consumidos: o escudo da vítima E o Imposto do Gorila do cobrador
                return await ctx.send(
                    f"🛡️ **BLOQUEADO!** {vitima.mention} usou um **Escudo Anti-Imposto** e destruiu o decreto!\n"
                    f"💥 O **Imposto do Gorila** de {ctx.author.mention} foi consumido no confronto."
                )

            self.bot.impostos[vitima_id] = {'cobrador_id': str(ctx.author.id), 'cargas': 5}
            db.set_imposto(vitima_db['row'], str(ctx.author.id), 5)
            
            ctx._missao_ok = True

            cargo_cobrador = user['data'][3] if len(user['data']) > 3 and user['data'][3] else "Lêmure"
            await ctx.send(
                f"🦍 **DECRETO ASSINADO!** {ctx.author.mention} cobrou o **Imposto do Gorila** a {vitima.mention}!\n"
                f"Durante os próximos **5 trabalhos** dele, o valor do seu cargo (**{cargo_cobrador}**) será descontado do ganho dele e enviado para você!"
            )

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !taxar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ──────────────────────────────────────────────────────────────────────────
    #  !apelidar
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command(aliases=["nick", "renomear"])
    async def apelidar(self, ctx, vitima: disnake.Member = None, *, novo_nick: str = None):
        if vitima is None or novo_nick is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, uso: `!apelidar @usuario <novo nick>`")
        if len(novo_nick) > 32:
            return await ctx.send("❌ Nick muito longo (máx: 32 caracteres).")

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user: return await ctx.send("❌ Você não tem conta!")

            inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
            
            # Testa a permissão antes de consumir o item
            nick_antigo = vitima.display_name
            try:
                await vitima.edit(nick=novo_nick)
            except disnake.Forbidden:
                return await ctx.send("❌ Não tenho permissão para mudar o nick desta pessoa!")

            if not self._consumir_item(user['row'], inv_list, "Troca de Nick"):
                # Reverte a troca se o cara burlou o inventário
                try: await vitima.edit(nick=nick_antigo)
                except: pass
                return await ctx.send("❌ Você não tem o item **Troca de Nick** no inventário!")

            ctx._missao_ok = True
            
            tempo_fim = int(time.time() + 1800)
            await ctx.send(
                f"🪄 {ctx.author.mention} transformou o nome de `{nick_antigo}` em **{novo_nick}**!\n"
                f"O efeito passa <t:{tempo_fim}:R>."
            )

            async def reverter_nick():
                await asyncio.sleep(1800)
                try: await vitima.edit(nick=nick_antigo)
                except: pass

            self.bot.loop.create_task(reverter_nick())

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !apelidar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ──────────────────────────────────────────────────────────────────────────
    #  !escudo
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command(aliases=["ativar_escudo", "status_escudo"])
    async def escudo(self, ctx, alvo: disnake.Member = None):
        if alvo is None:
            alvo = ctx.author

        alvo_id = str(alvo.id)
        alvo_db = db.get_user_data(alvo_id)

        cargas_db, _ = db.get_escudo_data(alvo_db) if alvo_db else (0, 0.0)
        cargas_mem   = self.bot.escudos_ativos.get(alvo_id, 0)
        cargas       = max(cargas_db, cargas_mem)
        if cargas > 0:
            self.bot.escudos_ativos[alvo_id] = cargas

        if cargas > 0:
            if alvo.id == ctx.author.id:
                return await ctx.send(
                    f"🛡️ {ctx.author.mention}, o seu Escudo está **ativo** com "
                    f"**{cargas}/{ESCUDO_CARGAS} cargas** restantes.\n"
                    f"Cada tentativa de roubo sofrida consome 1 carga."
                )
            else:
                return await ctx.send(
                    f"🛡️ {alvo.mention} está protegido por um Escudo com "
                    f"**{cargas}/{ESCUDO_CARGAS} cargas** restantes."
                )

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Conta não encontrada!")

            inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]

            if alvo.id == ctx.author.id:
                if self._consumir_item(user['row'], inv_list, "Escudo"):
                    self.bot.escudos_ativos[alvo_id] = ESCUDO_CARGAS
                    db.set_escudo_data(user['row'], ESCUDO_CARGAS)
                    ctx._missao_ok = True
                    return await ctx.send(
                        f"🛡️ {ctx.author.mention} ativou o seu **Escudo**! "
                        f"Você está protegido contra **{ESCUDO_CARGAS} tentativas de roubo**.\n"
                        f"💡 *O Pé de Cabra perfura o escudo, mas também consome 1 carga do alvo.*"
                    )
                else:
                    return await ctx.send(
                        f"🛡️ {ctx.author.mention}, você não tem nenhum Escudo ativo nem no inventário.\n"
                        f"Compra um na `!loja` por **1.000 MC**!"
                    )
            else:
                return await ctx.send(f"🛡️ {alvo.mention} não tem nenhum Escudo ativo no momento.")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !escudo de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ──────────────────────────────────────────────────────────────────────────
    #  !seguro
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command(aliases=["ativar_seguro", "status_seguro"])
    async def seguro(self, ctx, alvo: disnake.Member = None):
        if alvo is None:
            alvo = ctx.author

        alvo_id = str(alvo.id)
        alvo_db = db.get_user_data(alvo_id)

        cargas_db  = db.get_seguro_cargas(alvo_db) if alvo_db else 0
        cargas_mem = self.bot.seguros_ativos.get(alvo_id, 0)
        cargas     = max(cargas_db, cargas_mem)
        if cargas > 0:
            self.bot.seguros_ativos[alvo_id] = cargas

        if cargas > 0:
            if alvo.id == ctx.author.id:
                return await ctx.send(
                    f"📄 {ctx.author.mention}, o seu Seguro está **ativo** com "
                    f"**{cargas}/{SEGURO_CARGAS} cargas** restantes.\n"
                    f"Cada roubo sofrido consome 1 carga e reembolsa **60%** do valor roubado."
                )
            else:
                return await ctx.send(
                    f"📄 {alvo.mention} está protegido por um Seguro com "
                    f"**{cargas}/{SEGURO_CARGAS} cargas** restantes."
                )

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Conta não encontrada!")

            inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]

            if alvo.id == ctx.author.id:
                tem_seguro = "Seguro" in inv_list or "Seguro 🔒" in inv_list
                if tem_seguro:
                    # Ativa o seguro e remove o item do inventário
                    for nome_seg in ("Seguro 🔒", "Seguro"):
                        if nome_seg in inv_list:
                            inv_list.remove(nome_seg)
                            break
                    db.update_value(user['row'], 6, ", ".join(inv_list) if inv_list else "Nenhum")
                    self.bot.seguros_ativos[alvo_id] = SEGURO_CARGAS
                    db.set_seguro_cargas(user['row'], SEGURO_CARGAS)
                    
                    ctx._missao_ok = True

                    return await ctx.send(
                        f"📄 {ctx.author.mention} ativou o seu **Seguro**! "
                        f"Você está coberto por **{SEGURO_CARGAS} roubos**.\n"
                        f"💡 *A cada roubo sofrido, 60% do valor é reembolsado e 1 carga é consumida.*"
                    )
                else:
                    return await ctx.send(
                        f"📄 {ctx.author.mention}, você não tem nenhum Seguro ativo nem no inventário.\n"
                        f"Compre um na `!loja` por **950 MC**!"
                    )
            else:
                return await ctx.send(f"📄 {alvo.mention} não tem nenhum Seguro ativo no momento.")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !seguro de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ──────────────────────────────────────────────────────────────────────────
    #  !energetico
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command(aliases=["energético", "redbull", "boost"])
    async def energetico(self, ctx):
        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Você não tem conta!")

            inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]

            agora       = time.time()
            ultimo_work = db.parse_float(user['data'][4] if len(user['data']) > 4 else None)
            cd_restante = 3600 - (agora - ultimo_work)

            if cd_restante <= 0:
                return await ctx.send(
                    f"⚡ {ctx.author.mention}, seu cooldown de trabalho já está **zerado**!\n"
                    f"Guarde o Energético — use `!trabalhar` direto."
                )

            if not self._consumir_item(user['row'], inv_list, "Energético Símio"):
                return await ctx.send(
                    f"❌ {ctx.author.mention}, você não tem um **Energético Símio** no inventário!\n"
                    f"Encontre um nas lootboxes ou compre na `!loja`."
                )

            db.update_value(user['row'], 5, 0)
            
            ctx._missao_ok = True

            minutos  = int(cd_restante // 60)
            segundos = int(cd_restante % 60)
            tempo_fmt = f"{minutos}m {segundos}s" if minutos else f"{segundos}s"

            embed = disnake.Embed(
                title="⚡ ENERGÉTICO SÍMIO ATIVADO!",
                description=(
                    f"{ctx.author.mention} tomou o Energético Símio e está **pronto para trabalhar** de novo!\n\n"
                    f"⏱️ Cooldown pulado: **{tempo_fmt}**\n"
                    f"💪 Use `!trabalhar` agora!"
                ),
                color=disnake.Color.yellow()
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !energetico de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ──────────────────────────────────────────────────────────────────────────
    #  !fumaca
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command(aliases=["fumaça", "smoke", "bomba_de_fumaca"])
    async def fumaca(self, ctx):
        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Você não tem conta!")

            inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]

            agora        = time.time()
            ultimo_roubo = db.parse_float(user['data'][6] if len(user['data']) > 6 else None)
            cd_restante  = 7200 - (agora - ultimo_roubo)

            if cd_restante <= 0:
                return await ctx.send(
                    f"💨 {ctx.author.mention}, seu cooldown de roubo já está **zerado**!\n"
                    f"Guarde a Bomba — use `!roubar` direto."
                )

            if not self._consumir_item(user['row'], inv_list, "Bomba de Fumaça"):
                return await ctx.send(
                    f"❌ {ctx.author.mention}, você não tem uma **Bomba de Fumaça** no inventário!\n"
                    f"Encontre uma nas lootboxes ou compre na `!loja`."
                )

            db.update_value(user['row'], 7, 0)
            
            ctx._missao_ok = True

            horas    = int(cd_restante // 3600)
            minutos  = int((cd_restante % 3600) // 60)
            segundos = int(cd_restante % 60)
            if horas:       tempo_fmt = f"{horas}h {minutos}m"
            elif minutos:   tempo_fmt = f"{minutos}m {segundos}s"
            else:           tempo_fmt = f"{segundos}s"

            embed = disnake.Embed(
                title="💨 BOMBA DE FUMAÇA LANÇADA!",
                description=(
                    f"{ctx.author.mention} desapareceu na fumaça e está **pronto para roubar** de novo!\n\n"
                    f"⏱️ Cooldown pulado: **{tempo_fmt}**\n"
                    f"🥷 Use `!roubar @alvo` agora!"
                ),
                color=disnake.Color.dark_gray()
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !fumaca de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ──────────────────────────────────────────────────────────────────────────
    #  !c4
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command(aliases=["explodir", "bomb"])
    async def c4(self, ctx, vitima: disnake.Member = None):
        if vitima is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, uso: `!c4 @usuario`")
        if vitima.id == ctx.author.id:
            return await ctx.send(f"💥 {ctx.author.mention}, não pode explodir o seu próprio escudo!")

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Você não tem conta!")

            inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]

            vitima_id = str(vitima.id)
            alvo_db   = db.get_user_data(vitima_id)

            cargas_db, _  = db.get_escudo_data(alvo_db) if alvo_db else (0, 0.0)
            cargas_mem    = self.bot.escudos_ativos.get(vitima_id, 0)
            cargas_escudo = max(cargas_db, cargas_mem)

            escudo_no_inv = False
            item_escudo_no_inv = None
            if alvo_db:
                inv_alvo = [i.strip() for i in str(alvo_db['data'][5] if len(alvo_db['data']) > 5 else "").split(',') if i.strip()]
                if "Escudo" in inv_alvo:
                    escudo_no_inv = True
                    item_escudo_no_inv = "Escudo"
                elif "Escudo 🔒" in inv_alvo:
                    escudo_no_inv = True
                    item_escudo_no_inv = "Escudo 🔒"

            if cargas_escudo == 0 and not escudo_no_inv:
                return await ctx.send(
                    f"💣 {vitima.mention} não tem nenhum **Escudo** ativo para destruir!\n"
                    f"Use `!escudo {vitima.mention}` para verificar."
                )

            if not self._consumir_item(user['row'], inv_list, "Carga de C4"):
                return await ctx.send(
                    f"❌ {ctx.author.mention}, você não tem uma **Carga de C4** no inventário!\n"
                    f"Encontre uma nas lootboxes ou no **Baú do Caçador**."
                )

            agora = time.time()

            if cargas_escudo > 0:
                if vitima_id in self.bot.escudos_ativos:
                    del self.bot.escudos_ativos[vitima_id]
                if alvo_db:
                    db.set_escudo_data(alvo_db['row'], 0, agora)
            elif escudo_no_inv and alvo_db and item_escudo_no_inv:
                inv_alvo.remove(item_escudo_no_inv)
                db.update_value(alvo_db['row'], 6, ", ".join(inv_alvo))

            ctx._missao_ok = True

            embed = disnake.Embed(
                title="💥 BOOM! ESCUDO DESTRUÍDO!",
                description=(
                    f"{ctx.author.mention} detonou uma **Carga de C4** e destruiu o Escudo de {vitima.mention}!\n\n"
                    f"🛡️ ~~Escudo~~ → 💥 **DESTRUÍDO**\n"
                    f"🥷 {vitima.mention} está **desprotegido** — hora de roubar!"
                ),
                color=disnake.Color.orange()
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !c4 de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ──────────────────────────────────────────────────────────────────────────
    #  !greve — aplica debuff de -50% no !trabalhar do alvo por 3 horas
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command(aliases=["strike", "paralisacao"])
    async def greve(self, ctx, vitima: disnake.Member = None):
        """Usa o item Greve para reduzir o salário do alvo em 50% por 3 horas."""
        if vitima is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, uso: `!greve @usuario`")
        if vitima.id == ctx.author.id:
            return await ctx.send(f"🪧 {ctx.author.mention}, não pode declarar greve contra si mesmo!")
        if vitima.bot:
            return await ctx.send("🤖 Bots não têm trabalhadores para entrar em greve!")

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Você não tem conta!")

            inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]

            vitima_db = db.get_user_data(str(vitima.id))
            if not vitima_db:
                return await ctx.send("❌ O alvo não tem conta registrada!")

            agora         = time.time()
            greve_expira  = db.get_greve(vitima_db)
            if greve_expira > 0 and agora < greve_expira:
                return await ctx.send(
                    f"🪧 {vitima.mention} já está em **greve**! "
                    f"A atual termina <t:{int(greve_expira)}:R>."
                )

            if not self._consumir_item(user['row'], inv_list, "Greve"):
                return await ctx.send(
                    f"❌ {ctx.author.mention}, você não tem o item **Greve** no inventário!\n"
                    f"Encontre um nas lootboxes."
                )

            nova_expira = agora + GREVE_DURACAO
            db.set_greve(vitima_db['row'], nova_expira)
            
            ctx._missao_ok = True

            embed = disnake.Embed(
                title="🪧 GREVE DECLARADA!",
                description=(
                    f"{ctx.author.mention} organizou os trabalhadores de {vitima.mention}!\n\n"
                    f"📉 **Salário reduzido em 50%** por **3 horas**.\n"
                    f"⏳ A greve dura até <t:{int(nova_expira)}:R>.\n"
                    f"*(Expira pelo tempo — independente de quantos trabalhos fizer.)*"
                ),
                color=disnake.Color.orange()
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !greve de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ──────────────────────────────────────────────────────────────────────────
    #  !equipar — equipa um passivo do inventário (máx 3 simultâneos)
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command(aliases=["equip"])
    async def equipar(self, ctx, *, nome_item: str = None):
        """Equipa um item passivo do inventário. Máximo de 3 passivos simultâneos."""
        if nome_item is None:
            return await self._mostrar_passivos_disponiveis(ctx)

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Você não tem conta!")

            inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip() and i.strip().lower() != "nenhum"]

            item_encontrado_no_inv = None
            nome_base_passivo = None

            # Busca no inventário, ignorando cadeado na checagem do PASSIVOS_INFO
            for inv_item in inv_list:
                item_limpo = inv_item.replace("🔒", "").strip()
                if nome_item.lower() in item_limpo.lower() and item_limpo in PASSIVOS_INFO:
                    item_encontrado_no_inv = inv_item
                    nome_base_passivo = item_limpo
                    break

            if not item_encontrado_no_inv:
                # Verifica se existe mas não é passivo
                for inv_item in inv_list:
                    item_limpo = inv_item.replace("🔒", "").strip()
                    if nome_item.lower() in item_limpo.lower():
                        return await ctx.send(
                            f"❌ **{inv_item}** não é um item passivo e não pode ser equipado.\n"
                            f"Use `!equipar` sem argumentos para ver seus passivos disponíveis."
                        )
                return await ctx.send(
                    f"❌ Passivo **{nome_item}** não encontrado no seu inventário.\n"
                    f"Use `!equipar` para ver o que você tem disponível."
                )

            passivos_atuais = db.get_passivos(user)

            # Usamos o nome BASE (sem 🔒) para guardar no BD, para não quebrar a lógica global
            if nome_base_passivo in passivos_atuais:
                return await ctx.send(
                    f"🔰 **{nome_base_passivo}** já está **equipado**!\n"
                    f"Use `!desequipar {nome_base_passivo}` para removê-lo."
                )

            if len(passivos_atuais) >= db.MAX_PASSIVOS:
                slots_fmt = "\n".join(
                    f"• {PASSIVOS_INFO[p]['emoji']} **{p}**" if p in PASSIVOS_INFO else f"• **{p}**"
                    for p in passivos_atuais
                )
                return await ctx.send(
                    f"❌ Você já tem **{db.MAX_PASSIVOS} passivos equipados** (limite máximo)!\n\n"
                    f"**Equipados atualmente:**\n{slots_fmt}\n\n"
                    f"Use `!desequipar <item>` para liberar um slot."
                )

            passivos_atuais.append(nome_base_passivo)
            db.set_passivos(user['row'], passivos_atuais)
            
            ctx._missao_ok = True

            info  = PASSIVOS_INFO[nome_base_passivo]
            slots_usados = len(passivos_atuais)

            # Verifica se o item no inventário era a versão vinculada para avisar o usuário
            aviso_vinculo = ""
            if "🔒" in item_encontrado_no_inv:
                aviso_vinculo = "\n*(Lembrando que este item é **vinculado** e não pode ser negociado)*"

            embed = disnake.Embed(
                title=f"{info['emoji']} PASSIVO EQUIPADO!",
                description=(
                    f"**{nome_base_passivo}** foi ativado e seus efeitos já estão em vigor!{aviso_vinculo}\n\n"
                    f"✨ **Efeito:** {info['efeito']}\n"
                    f"🏷️ **Tier:** {info['tier']}\n"
                    f"🔰 **Slots:** {slots_usados}/{db.MAX_PASSIVOS}"
                ),
                color=TIER_COR.get(info['tier'], 0x888888)
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            embed.set_footer(text="Use !desequipar para remover · Passivos equipados aparecem em !inventario")
            await ctx.send(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !equipar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ──────────────────────────────────────────────────────────────────────────
    #  !desequipar — remove um passivo dos slots ativos
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command(aliases=["unequip", "remover_passivo"])
    async def desequipar(self, ctx, *, nome_item: str = None):
        """Remove um passivo dos slots ativos. O item continua no inventário."""
        if nome_item is None:
            return await self._mostrar_passivos_equipados(ctx)

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Você não tem conta!")

            passivos_atuais = db.get_passivos(user)

            if not passivos_atuais:
                return await ctx.send(
                    f"🔰 {ctx.author.mention}, você não tem nenhum passivo equipado.\n"
                    f"Use `!equipar` para ativar um."
                )

            item_base_encontrado = None
            for p in passivos_atuais:
                if nome_item.lower() in p.lower():
                    item_base_encontrado = p
                    break

            if not item_base_encontrado:
                slots_fmt = "\n".join(
                    f"• {PASSIVOS_INFO[p]['emoji']} **{p}**" if p in PASSIVOS_INFO else f"• **{p}**"
                    for p in passivos_atuais
                )
                return await ctx.send(
                    f"❌ **{nome_item}** não está entre seus passivos equipados.\n\n"
                    f"**Equipados:**\n{slots_fmt}"
                )

            passivos_atuais.remove(item_base_encontrado)
            db.set_passivos(user['row'], passivos_atuais)
            
            ctx._missao_ok = True

            info = PASSIVOS_INFO.get(item_base_encontrado, {})
            emoji = info.get('emoji', '🔰')

            embed = disnake.Embed(
                title=f"{emoji} PASSIVO REMOVIDO",
                description=(
                    f"**{item_base_encontrado}** foi desequipado.\n"
                    f"O item continua no seu inventário — use `!equipar` para reativar.\n\n"
                    f"🔰 **Slots livres:** {db.MAX_PASSIVOS - len(passivos_atuais)}/{db.MAX_PASSIVOS}"
                ),
                color=disnake.Color.dark_gray()
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !desequipar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ──────────────────────────────────────────────────────────────────────────
    #  !passivos — mostra os passivos equipados e disponíveis no inventário
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command(aliases=["meus_passivos", "passive"])
    async def passivos(self, ctx, membro: disnake.Member = None):
        """Mostra os passivos equipados. Sem argumento = seus próprios."""
        alvo = membro or ctx.author
        try:
            user_db = db.get_user_data(str(alvo.id))
            if not user_db:
                return await ctx.send("❌ Conta não encontrada!")

            passivos_equipados = db.get_passivos(user_db)

            # Passivos no inventário (não equipados)
            inv_str  = str(user_db['data'][5]) if len(user_db['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip() and i.strip().lower() != "nenhum"]
            
            passivos_inv = []
            contagem_inv: dict[str, int] = {}
            
            for item in inv_list:
                item_limpo = item.replace("🔒", "").strip()
                if item_limpo in PASSIVOS_INFO and item_limpo not in passivos_equipados:
                    passivos_inv.append(item)
                    contagem_inv[item] = contagem_inv.get(item, 0) + 1

            embed = disnake.Embed(
                title=f"🔰 Passivos de {alvo.display_name}",
                color=0x7B2D8B
            )
            embed.set_author(name=alvo.display_name, icon_url=alvo.display_avatar.url)

            # Slots equipados
            if passivos_equipados:
                linhas_eq = []
                for p in passivos_equipados:
                    info = PASSIVOS_INFO.get(p, {})
                    emoji = info.get('emoji', '🔰')
                    efeito = info.get('efeito', '?')
                    tier   = info.get('tier', '?')
                    linhas_eq.append(f"{emoji} **{p}** *({tier})*\n　└ {efeito}")
                embed.add_field(
                    name=f"⚔️ Equipados ({len(passivos_equipados)}/{db.MAX_PASSIVOS})",
                    value="\n".join(linhas_eq),
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"⚔️ Equipados (0/{db.MAX_PASSIVOS})",
                    value="*Nenhum passivo equipado.*\nUse `!equipar <item>` para ativar.",
                    inline=False
                )

            # Passivos no inventário (não equipados)
            if passivos_inv and alvo.id == ctx.author.id:
                linhas_inv = []
                vistos = set()
                for p in passivos_inv:
                    if p in vistos: continue
                    vistos.add(p)
                    nome_base = p.replace("🔒", "").strip()
                    info  = PASSIVOS_INFO.get(nome_base, {})
                    emoji = info.get('emoji', '🔰')
                    qtd   = contagem_inv[p]
                    qtd_str = f" ×{qtd}" if qtd > 1 else ""
                    linhas_inv.append(f"{emoji} **{p}**{qtd_str}")
                embed.add_field(
                    name="🎒 No inventário (não equipados)",
                    value="\n".join(linhas_inv),
                    inline=False
                )

            embed.set_footer(text="!equipar <item> · !desequipar <item> · Passivos podem ser vendidos com !vender")
            await ctx.send(embed=embed, delete_after=90)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !passivos de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ──────────────────────────────────────────────────────────────────────────
    #  Helpers internos
    # ──────────────────────────────────────────────────────────────────────────

    async def _mostrar_passivos_disponiveis(self, ctx):
        """Mostra passivos no inventário que podem ser equipados."""
        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Conta não encontrada!")

            inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip() and i.strip().lower() != "nenhum"]
            passivos_equipados = db.get_passivos(user)
            
            disponiveis = []
            for item in inv_list:
                item_limpo = item.replace("🔒", "").strip()
                if item_limpo in PASSIVOS_INFO and item_limpo not in passivos_equipados:
                    disponiveis.append(item)

            if not disponiveis:
                return await ctx.send(
                    f"🔰 {ctx.author.mention}, você não tem passivos disponíveis para equipar.\n"
                    f"Abra lootboxes para encontrar passivos!\n\n"
                    f"**Slots:** {len(passivos_equipados)}/{db.MAX_PASSIVOS} ocupados · "
                    f"Use `!passivos` para ver os equipados."
                )

            linhas = []
            vistos = set()
            for p in disponiveis:
                if p in vistos: continue
                vistos.add(p)
                nome_base = p.replace("🔒", "").strip()
                info  = PASSIVOS_INFO[nome_base]
                linhas.append(f"{info['emoji']} **{p}** *({info['tier']})*\n　└ {info['efeito']}")

            embed = disnake.Embed(
                title="🔰 Passivos disponíveis para equipar",
                description="\n".join(linhas),
                color=0x1A6E9A
            )
            embed.set_footer(
                text=f"Slots: {len(passivos_equipados)}/{db.MAX_PASSIVOS} · "
                     f"Use: !equipar <nome do item>"
            )
            await ctx.send(embed=embed, delete_after=60)

        except Exception as e:
            print(f"❌ Erro em _mostrar_passivos_disponiveis: {e}")

    async def _mostrar_passivos_equipados(self, ctx):
        """Atalho: mostra passivos equipados quando !desequipar é chamado sem args."""
        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Conta não encontrada!")

            passivos = db.get_passivos(user)
            if not passivos:
                return await ctx.send(
                    f"🔰 {ctx.author.mention}, nenhum passivo equipado.\n"
                    f"Use `!equipar` para ativar um."
                )

            linhas = []
            for p in passivos:
                info  = PASSIVOS_INFO.get(p, {})
                emoji = info.get('emoji', '🔰')
                linhas.append(f"{emoji} **{p}**")

            await ctx.send(
                f"🔰 **Passivos equipados:**\n" + "\n".join(linhas) +
                f"\n\nUse `!desequipar <nome>` para remover um.",
                delete_after=60
            )
        except Exception as e:
            print(f"❌ Erro em _mostrar_passivos_equipados: {e}")


def setup(bot):
    bot.add_cog(Items(bot))