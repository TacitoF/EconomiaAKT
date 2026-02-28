import disnake
from disnake.ext import commands
import database as db
import time
import asyncio

ESCUDO_CARGAS = 3  # Número de roubos que o Escudo bloqueia antes de quebrar

class Items(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, 'cascas'): bot.cascas = set()
        # Impostos agora usam cargas de trabalho: {user_id_str: {'cobrador_id': id, 'cargas': 5}}
        if not hasattr(bot, 'impostos'): bot.impostos = {}
        # Escudos ativos: {user_id_str: cargas_restantes}
        if not hasattr(bot, 'escudos_ativos'): bot.escudos_ativos = {}
        # Histórico de compras de escudo: {user_id: (count, timestamp_primeira_compra)}
        if not hasattr(bot, 'escudo_compras'): bot.escudo_compras = {}
        # Cooldown imposto: {user_id: timestamp_liberacao}
        if not hasattr(bot, 'cooldown_imposto'): bot.cooldown_imposto = {}

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, usa itens no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["banana"])
    async def casca(self, ctx, vitima: disnake.Member = None):
        if vitima is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, uso: `!casca @usuario`")
        if vitima.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, não podes atirar uma casca ao próprio pé!")

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user: return await ctx.send("❌ Não tens conta!")

            inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
            if "Casca de Banana" not in inv_list:
                return await ctx.send("❌ Não tens uma **Casca de Banana** no inventário!")

            inv_list.remove("Casca de Banana")
            db.update_value(user['row'], 6, ", ".join(inv_list))
            self.bot.cascas.add(str(vitima.id))
            await ctx.send(f"🍌 {ctx.author.mention} atirou uma Casca de Banana aos pés de {vitima.mention}! O próximo passo dele será uma tragédia...")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !casca de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tenta novamente!")

    @commands.command(aliases=["imposto"])
    async def taxar(self, ctx, vitima: disnake.Member = None):
        if vitima is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, uso: `!taxar @usuario`")
        if vitima.id == ctx.author.id:
            return await ctx.send("❌ Não podes taxar a ti mesmo!")
        if vitima.bot:
            return await ctx.send("🤖 Bots não pagam impostos!")

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user: return await ctx.send("❌ Não tens conta!")

            inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
            if "Imposto do Gorila" not in inv_list:
                return await ctx.send("❌ Não tens o item **Imposto do Gorila** no inventário!")

            vitima_id = str(vitima.id)
            # Verifica cooldown de imunidade (24h após imposto acabar)
            cd = self.bot.cooldown_imposto.get(vitima_id, 0)
            if time.time() < cd:
                return await ctx.send(
                    f"🛡️ {vitima.mention} está **imune** ao Imposto do Gorila! "
                    f"A imunidade expira <t:{int(cd)}:R>."
                )
            # Verifica imposto já ativo
            if vitima_id in self.bot.impostos and self.bot.impostos[vitima_id].get('cargas', 0) > 0:
                cargas_restantes = self.bot.impostos[vitima_id]['cargas']
                return await ctx.send(f"❌ {vitima.mention} já está sob imposto! Restam **{cargas_restantes} trabalhos** taxados para ele.")

            inv_list.remove("Imposto do Gorila")
            db.update_value(user['row'], 6, ", ".join(inv_list))

            self.bot.impostos[vitima_id] = {'cobrador_id': str(ctx.author.id), 'cargas': 5}
            vitima_db = db.get_user_data(vitima_id)
            if vitima_db:
                db.set_imposto(vitima_db['row'], str(ctx.author.id), 5)
            await ctx.send(f"🦍 **DECRETO ASSINADO!** {ctx.author.mention} cobrou o Imposto do Gorila a {vitima.mention}. Durante os próximos **5 trabalhos** dele, 25% do suor irá para ti!")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !taxar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tenta novamente!")

    @commands.command(aliases=["nick", "renomear"])
    async def apelidar(self, ctx, vitima: disnake.Member = None, *, novo_nick: str = None):
        if vitima is None or novo_nick is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, uso: `!apelidar @usuario <novo nick>`")
        if len(novo_nick) > 32:
            return await ctx.send("❌ Nick muito longo (máx: 32 caracteres).")

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user: return await ctx.send("❌ Não tens conta!")

            inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
            if "Troca de Nick" not in inv_list:
                return await ctx.send("❌ Não tens o item **Troca de Nick** no inventário!")

            nick_antigo = vitima.display_name
            try:
                await vitima.edit(nick=novo_nick)
            except disnake.Forbidden:
                return await ctx.send("❌ Não tenho permissão para mudar o nick desta pessoa!")

            inv_list.remove("Troca de Nick")
            db.update_value(user['row'], 6, ", ".join(inv_list))

            tempo_fim = int(time.time() + 1800)
            await ctx.send(f"🪄 {ctx.author.mention} transformou o nome de `{nick_antigo}` em **{novo_nick}**! O efeito passa <t:{tempo_fim}:R>.")

            async def reverter_nick():
                await asyncio.sleep(1800)
                try: await vitima.edit(nick=nick_antigo)
                except: pass

            self.bot.loop.create_task(reverter_nick())

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !apelidar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tenta novamente!")

    @commands.command(aliases=["ativar_escudo", "status_escudo"])
    async def escudo(self, ctx, alvo: disnake.Member = None):
        if alvo is None:
            alvo = ctx.author

        alvo_id = str(alvo.id)
        cargas = self.bot.escudos_ativos.get(alvo_id, 0)

        if cargas > 0:
            if alvo.id == ctx.author.id:
                return await ctx.send(
                    f"🛡️ {ctx.author.mention}, o teu Escudo está **ativo** com **{cargas}/{ESCUDO_CARGAS} cargas** restantes.\n"
                    f"Cada tentativa de roubo sofrida consome 1 carga."
                )
            else:
                return await ctx.send(
                    f"🛡️ {alvo.mention} está protegido por um Escudo com **{cargas}/{ESCUDO_CARGAS} cargas** restantes."
                )

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Conta não encontrada!")

            inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]

            if alvo.id == ctx.author.id and "Escudo" in inv_list:
                if self.bot.escudos_ativos.get(alvo_id, 0) > 0:
                    return await ctx.send(
                        f"🛡️ {ctx.author.mention}, já tens um Escudo **ativo**! "
                        f"Aguarda ele quebrar antes de ativar outro."
                    )
                self.bot.escudos_ativos[alvo_id] = ESCUDO_CARGAS
                inv_list.remove("Escudo")
                db.update_value(user['row'], 6, ", ".join(inv_list))
                return await ctx.send(
                    f"🛡️ {ctx.author.mention} ativou o seu **Escudo**! "
                    f"Estás protegido contra **{ESCUDO_CARGAS} tentativas de roubo**.\n"
                    f"💡 *O Pé de Cabra perfura o escudo, mas também consome 1 carga do alvo.*"
                )

            if alvo.id == ctx.author.id:
                return await ctx.send(
                    f"🛡️ {ctx.author.mention}, não tens nenhum Escudo ativo nem no inventário.\n"
                    f"Compra um na `!loja` por **1.000 MC**!"
                )
            else:
                return await ctx.send(
                    f"🛡️ {alvo.mention} não tem nenhum Escudo ativo no momento."
                )

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !escudo de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tenta novamente!")

def setup(bot):
    bot.add_cog(Items(bot))