import disnake
from disnake.ext import commands
import database as db
import time
import asyncio

ESCUDO_CARGAS = 3  # Número de roubos que o Escudo bloqueia antes de quebrar

class Items(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, 'cascas'):           bot.cascas           = set()
        if not hasattr(bot, 'impostos'):         bot.impostos         = {}
        if not hasattr(bot, 'escudos_ativos'):   bot.escudos_ativos   = {}
        if not hasattr(bot, 'escudo_compras'):   bot.escudo_compras   = {}
        if not hasattr(bot, 'cooldown_imposto'): bot.cooldown_imposto = {}

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, use itens no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    # ── !casca ────────────────────────────────────────────────────────────────

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
            if "Casca de Banana" not in inv_list:
                return await ctx.send("❌ Você não tem uma **Casca de Banana** no inventário!")

            inv_list.remove("Casca de Banana")
            db.update_value(user['row'], 6, ", ".join(inv_list))
            self.bot.cascas.add(str(vitima.id))
            await ctx.send(
                f"🍌 {ctx.author.mention} atirou uma **Casca de Banana** aos pés de {vitima.mention}!\n"
                f"O próximo trabalho dele será uma tragédia..."
            )

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !casca de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ── !taxar ────────────────────────────────────────────────────────────────

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
            if "Imposto do Gorila" not in inv_list:
                return await ctx.send("❌ Você não tem o item **Imposto do Gorila** no inventário!")

            vitima_id = str(vitima.id)
            vitima_db = db.get_user_data(vitima_id)
            if not vitima_db:
                return await ctx.send("❌ O alvo não tem conta registrada!")

            # LER DO BANCO E SINCRONIZAR A MEMÓRIA
            cobrador_id, cargas, cd_imposto = db.get_imposto(vitima_db)

            # Se estiver em Cooldown
            if cd_imposto > 0 and time.time() < cd_imposto:
                return await ctx.send(
                    f"🛡️ {vitima.mention} está **imune** ao Imposto do Gorila! "
                    f"A imunidade expira <t:{int(cd_imposto)}:R>."
                )
            
            # Se já estiver sob imposto de alguém
            if cargas > 0:
                return await ctx.send(
                    f"❌ {vitima.mention} já está sob imposto! "
                    f"Restam **{cargas} trabalhos** taxados para ele."
                )

            # APLICA O IMPOSTO
            inv_list.remove("Imposto do Gorila")
            db.update_value(user['row'], 6, ", ".join(inv_list))
            
            self.bot.impostos[vitima_id] = {'cobrador_id': str(ctx.author.id), 'cargas': 5}
            db.set_imposto(vitima_db['row'], str(ctx.author.id), 5)
            
            await ctx.send(
                f"🦍 **DECRETO ASSINADO!** {ctx.author.mention} cobrou o **Imposto do Gorila** a {vitima.mention}!\n"
                f"Durante os próximos **5 trabalhos** dele, **25%** do suor vai direto para você!"
            )

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !taxar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ── !apelidar ─────────────────────────────────────────────────────────────

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
            if "Troca de Nick" not in inv_list:
                return await ctx.send("❌ Você não tem o item **Troca de Nick** no inventário!")

            nick_antigo = vitima.display_name
            try:
                await vitima.edit(nick=novo_nick)
            except disnake.Forbidden:
                return await ctx.send("❌ Não tenho permissão para mudar o nick desta pessoa!")

            inv_list.remove("Troca de Nick")
            db.update_value(user['row'], 6, ", ".join(inv_list))

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

    # ── !escudo ───────────────────────────────────────────────────────────────

    @commands.command(aliases=["ativar_escudo", "status_escudo"])
    async def escudo(self, ctx, alvo: disnake.Member = None):
        if alvo is None:
            alvo = ctx.author

        alvo_id = str(alvo.id)
        alvo_db = db.get_user_data(alvo_id)
        
        # Sincroniza memória com DB
        cargas_db, _ = db.get_escudo_data(alvo_db) if alvo_db else (0, 0.0)
        cargas_mem = self.bot.escudos_ativos.get(alvo_id, 0)
        
        cargas = max(cargas_db, cargas_mem) # Confia no maior valor
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

            if alvo.id == ctx.author.id and "Escudo" in inv_list:
                self.bot.escudos_ativos[alvo_id] = ESCUDO_CARGAS
                inv_list.remove("Escudo")
                db.update_value(user['row'], 6, ", ".join(inv_list))
                db.set_escudo_data(user['row'], ESCUDO_CARGAS)
                
                return await ctx.send(
                    f"🛡️ {ctx.author.mention} ativou o seu **Escudo**! "
                    f"Você está protegido contra **{ESCUDO_CARGAS} tentativas de roubo**.\n"
                    f"💡 *O Pé de Cabra perfura o escudo, mas também consome 1 carga do alvo.*"
                )

            if alvo.id == ctx.author.id:
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

    # ── !energetico ───────────────────────────────────────────────────────────

    @commands.command(aliases=["energético", "redbull", "boost"])
    async def energetico(self, ctx):
        """Usa um Energético Símio do inventário para zerar o cooldown de !trabalhar."""
        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Você não tem conta!")

            inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]

            if "Energético Símio" not in inv_list:
                return await ctx.send(
                    f"❌ {ctx.author.mention}, você não tem um **Energético Símio** no inventário!\n"
                    f"Encontre um nas lootboxes ou compre na `!loja`."
                )

            agora       = time.time()
            ultimo_work = db.parse_float(user['data'][4] if len(user['data']) > 4 else None)
            cd_restante = 3600 - (agora - ultimo_work)

            if cd_restante <= 0:
                return await ctx.send(
                    f"⚡ {ctx.author.mention}, seu cooldown de trabalho já está **zerado**!\n"
                    f"Guarde o Energético — use `!trabalhar` direto."
                )

            inv_list.remove("Energético Símio")
            db.update_value(user['row'], 6, ", ".join(inv_list))
            db.update_value(user['row'], 5, 0)

            minutos = int(cd_restante // 60)
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

    # ── !fumaca ───────────────────────────────────────────────────────────────

    @commands.command(aliases=["fumaça", "smoke", "bomba_de_fumaca"])
    async def fumaca(self, ctx):
        """Usa uma Bomba de Fumaça do inventário para zerar o cooldown de !roubar."""
        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Você não tem conta!")

            inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]

            if "Bomba de Fumaça" not in inv_list:
                return await ctx.send(
                    f"❌ {ctx.author.mention}, você não tem uma **Bomba de Fumaça** no inventário!\n"
                    f"Encontre uma nas lootboxes ou compre na `!loja`."
                )

            agora        = time.time()
            ultimo_roubo = db.parse_float(user['data'][6] if len(user['data']) > 6 else None)
            cd_restante  = 7200 - (agora - ultimo_roubo)

            if cd_restante <= 0:
                return await ctx.send(
                    f"💨 {ctx.author.mention}, seu cooldown de roubo já está **zerado**!\n"
                    f"Guarde a Bomba — use `!roubar` direto."
                )

            inv_list.remove("Bomba de Fumaça")
            db.update_value(user['row'], 6, ", ".join(inv_list))
            db.update_value(user['row'], 7, 0)

            horas   = int(cd_restante // 3600)
            minutos = int((cd_restante % 3600) // 60)
            segundos = int(cd_restante % 60)
            if horas:
                tempo_fmt = f"{horas}h {minutos}m"
            elif minutos:
                tempo_fmt = f"{minutos}m {segundos}s"
            else:
                tempo_fmt = f"{segundos}s"

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

    # ── !c4 ───────────────────────────────────────────────────────────────────

    @commands.command(aliases=["explodir", "bomb"])
    async def c4(self, ctx, vitima: disnake.Member = None):
        """Usa uma Carga de C4 para destruir o Escudo de um alvo e ativa o cooldown de 24h nele."""
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

            if "Carga de C4" not in inv_list:
                return await ctx.send(
                    f"❌ {ctx.author.mention}, você não tem uma **Carga de C4** no inventário!\n"
                    f"Encontre uma nas lootboxes ou no **Baú do Caçador**."
                )

            vitima_id = str(vitima.id)
            alvo_db   = db.get_user_data(vitima_id)

            cargas_db, _ = db.get_escudo_data(alvo_db) if alvo_db else (0, 0.0)
            cargas_mem   = self.bot.escudos_ativos.get(vitima_id, 0)
            cargas_escudo = max(cargas_db, cargas_mem)

            escudo_no_inv = False
            if alvo_db:
                inv_alvo = [i.strip() for i in str(alvo_db['data'][5] if len(alvo_db['data']) > 5 else "").split(',') if i.strip()]
                escudo_no_inv = "Escudo" in inv_alvo

            if cargas_escudo == 0 and not escudo_no_inv:
                return await ctx.send(
                    f"💣 {vitima.mention} não tem nenhum **Escudo** ativo para destruir!\n"
                    f"Use `!escudo {vitima.mention}` para verificar."
                )

            # Consome o C4 do ladrão
            inv_list.remove("Carga de C4")
            db.update_value(user['row'], 6, ", ".join(inv_list))

            agora = time.time()

            # Se o escudo estava ativo, quebra e inicia cooldown de 24h
            if cargas_escudo > 0:
                if vitima_id in self.bot.escudos_ativos:
                    del self.bot.escudos_ativos[vitima_id]
                if alvo_db:
                    db.set_escudo_data(alvo_db['row'], 0, agora)

            # Se o escudo estava só guardado no inventário, apenas remove (não dá cooldown)
            elif escudo_no_inv and alvo_db:
                inv_alvo.remove("Escudo")
                db.update_value(alvo_db['row'], 6, ", ".join(inv_alvo))

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


def setup(bot):
    bot.add_cog(Items(bot))