import disnake
from disnake.ext import commands
import database as db
import time
import asyncio

ESCUDO_CARGAS = 3  # Número de roubos que o Escudo bloqueia antes de quebrar

def formatar_moeda(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

class Items(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, 'cascas'): bot.cascas = set()
        if not hasattr(bot, 'impostos'): bot.impostos = {}
        if not hasattr(bot, 'escudos_ativos'): bot.escudos_ativos = {}
        if not hasattr(bot, 'escudo_compras'): bot.escudo_compras = {}
        if not hasattr(bot, 'cooldown_imposto'): bot.cooldown_imposto = {}

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, use os itens no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["banana"])
    async def casca(self, ctx, vitima: disnake.Member = None):
        if vitima is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, uso: `!casca @usuario`")
        if vitima.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, você não pode atirar uma casca no próprio pé!")

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user: return await ctx.send("❌ Você não tem conta!")

            inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
            if "Casca de Banana" not in inv_list:
                return await ctx.send("❌ Você não tem uma **Casca de Banana** no inventário!")

            inv_list.remove("Casca de Banana")
            db.update_value(user['row'], 6, ", ".join(inv_list))
            self.bot.cascas.add(str(vitima.id))
            await ctx.send(f"🍌 {ctx.author.mention} atirou uma Casca de Banana aos pés de {vitima.mention}! O próximo passo dele será uma tragédia...")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !casca de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    @commands.command(aliases=["imposto"])
    async def taxar(self, ctx, vitima: disnake.Member = None):
        if vitima is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, uso: `!taxar @usuario`")
        if vitima.id == ctx.author.id:
            return await ctx.send("❌ Você não pode taxar a si mesmo!")
        if vitima.bot:
            return await ctx.send("🤖 Bots não pagam impostos!")

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user: return await ctx.send("❌ Você não tem conta!")

            inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
            if "Imposto do Gorila" not in inv_list:
                return await ctx.send("❌ Você não tem o item **Imposto do Gorila** no inventário!")

            vitima_id = str(vitima.id)
            cd = self.bot.cooldown_imposto.get(vitima_id, 0)
            if time.time() < cd:
                return await ctx.send(
                    f"🛡️ {vitima.mention} está **imune** ao Imposto do Gorila! "
                    f"A imunidade expira <t:{int(cd)}:R>."
                )
            if vitima_id in self.bot.impostos and self.bot.impostos[vitima_id].get('cargas', 0) > 0:
                cargas_restantes = self.bot.impostos[vitima_id]['cargas']
                return await ctx.send(f"❌ {vitima.mention} já está sob imposto! Restam **{cargas_restantes} trabalhos** taxados para ele.")

            inv_list.remove("Imposto do Gorila")
            db.update_value(user['row'], 6, ", ".join(inv_list))

            self.bot.impostos[vitima_id] = {'cobrador_id': str(ctx.author.id), 'cargas': 5}
            vitima_db = db.get_user_data(vitima_id)
            if vitima_db:
                db.set_imposto(vitima_db['row'], str(ctx.author.id), 5)
            await ctx.send(f"🦍 **DECRETO ASSINADO!** {ctx.author.mention} cobrou o Imposto do Gorila de {vitima.mention}. Durante os próximos **5 trabalhos** dele, 25% do suor irá para você!")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !taxar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    @commands.command(aliases=["nick", "renomear"])
    async def apelidar(self, ctx, vitima: disnake.Member = None, *, novo_nick: str = None):
        if vitima is None or novo_nick is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, uso: `!apelidar @usuario <novo nick>`")
        if len(novo_nick) > 32:
            return await ctx.send("❌ Nick muito longo (máx: 32 caracteres).")

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user: return await ctx.send("❌ Você não tem conta!")

            inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
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
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    @commands.command(aliases=["ativar_escudo", "status_escudo"])
    async def escudo(self, ctx, alvo: disnake.Member = None):
        if alvo is None:
            alvo = ctx.author

        alvo_id = str(alvo.id)
        cargas = self.bot.escudos_ativos.get(alvo_id, 0)

        if cargas > 0:
            if alvo.id == ctx.author.id:
                return await ctx.send(
                    f"🛡️ {ctx.author.mention}, o seu Escudo está **ativo** com **{cargas}/{ESCUDO_CARGAS} cargas** restantes.\n"
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
                        f"🛡️ {ctx.author.mention}, você já tem um Escudo **ativo**! "
                        f"Aguarde ele quebrar antes de ativar outro."
                    )
                self.bot.escudos_ativos[alvo_id] = ESCUDO_CARGAS
                inv_list.remove("Escudo")
                db.update_value(user['row'], 6, ", ".join(inv_list))
                return await ctx.send(
                    f"🛡️ {ctx.author.mention} ativou o seu **Escudo**! "
                    f"Você está protegido contra **{ESCUDO_CARGAS} tentativas de roubo**.\n"
                    f"💡 *O Pé de Cabra perfura o escudo, mas também consome 1 carga do alvo.*"
                )

            if alvo.id == ctx.author.id:
                return await ctx.send(
                    f"🛡️ {ctx.author.mention}, você não tem nenhum Escudo ativo nem no inventário.\n"
                    f"Compre um na `!loja` por **1.000 MC** ou procure em Caixas!"
                )
            else:
                return await ctx.send(
                    f"🛡️ {alvo.mention} não tem nenhum Escudo ativo no momento."
                )

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !escudo de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ────────────────────────────────────────────────────────────────
    # NOVOS ITENS DAS LOOTBOXES
    # ────────────────────────────────────────────────────────────────

    @commands.command(aliases=["energético", "energia"])
    async def energetico(self, ctx):
        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user: return await ctx.send("❌ Você não tem conta!")

            inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
            if "Energético Símio" not in inv_list:
                return await ctx.send("❌ Você não tem o item **Energético Símio** no inventário!")

            inv_list.remove("Energético Símio")
            db.update_value(user['row'], 6, ", ".join(inv_list))
            
            # Zera o tempo do ultimo_work (coluna 5, índice 4)
            db.update_value(user['row'], 5, 0)
            
            await ctx.send(f"⚡ {ctx.author.mention} bebeu um **Energético Símio** e está a mil por hora! O cooldown do seu `!trabalhar` foi **zerado**!")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !energetico de {ctx.author}: {e}")

    @commands.command(aliases=["fumaça", "ninja"])
    async def fumaca(self, ctx):
        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user: return await ctx.send("❌ Você não tem conta!")

            inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
            if "Bomba de Fumaça" not in inv_list:
                return await ctx.send("❌ Você não tem o item **Bomba de Fumaça** no inventário!")

            inv_list.remove("Bomba de Fumaça")
            db.update_value(user['row'], 6, ", ".join(inv_list))
            
            # Zera o tempo do ultimo_roubo (coluna 7, índice 6)
            db.update_value(user['row'], 7, 0)
            
            await ctx.send(f"💨 {ctx.author.mention} jogou uma **Bomba de Fumaça** no chão e sumiu da vista da polícia! O cooldown do seu `!roubar` foi **zerado**!")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !fumaca de {ctx.author}: {e}")

    @commands.command(aliases=["bomba", "explodir"])
    async def c4(self, ctx, alvo: disnake.Member = None):
        if alvo is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, uso: `!c4 @usuario`")
        
        if alvo.id == ctx.author.id:
            return await ctx.send(f"🤡 Você quer mesmo explodir a si próprio?")

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user: return await ctx.send("❌ Você não tem conta!")

            inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
            if "Carga de C4" not in inv_list:
                return await ctx.send("❌ Você não tem o item **Carga de C4** no inventário!")

            alvo_id = str(alvo.id)
            cargas_alvo = self.bot.escudos_ativos.get(alvo_id, 0)

            if cargas_alvo <= 0:
                return await ctx.send(f"⚠️ {alvo.display_name} não tem nenhum escudo ativo para você explodir. Guarde sua C4 para depois!")

            # Consome a C4
            inv_list.remove("Carga de C4")
            db.update_value(user['row'], 6, ", ".join(inv_list))
            
            # Destrói o escudo completamente
            del self.bot.escudos_ativos[alvo_id]
            
            await ctx.send(f"🧨 **KABOOOOM!** {ctx.author.mention} detonou uma **Carga de C4** na base de {alvo.mention}! O escudo de proteção foi totalmente **DESTRUÍDO**!")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !c4 de {ctx.author}: {e}")

    @commands.command(aliases=["sell", "vendas"])
    async def vender(self, ctx, *, item_nome: str = None):
        if item_nome is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, uso: `!vender <nome do tesouro>`. Tesouros disponíveis: Diamante Bruto, Estátua de Ouro.")

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user: return await ctx.send("❌ Você não tem conta!")

            inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]

            item_nome = item_nome.lower()
            if "diamante" in item_nome:
                if "Diamante Bruto" not in inv_list:
                    return await ctx.send("❌ Você não tem um **Diamante Bruto** no inventário!")
                inv_list.remove("Diamante Bruto")
                valor_venda = 30000.0
                nome_formatado = "Diamante Bruto 💎"
            elif "estátua" in item_nome or "estatua" in item_nome or "ouro" in item_nome:
                if "Estátua de Ouro" not in inv_list:
                    return await ctx.send("❌ Você não tem uma **Estátua de Ouro** no inventário!")
                inv_list.remove("Estátua de Ouro")
                valor_venda = 15000.0
                nome_formatado = "Estátua de Ouro 🗿"
            else:
                return await ctx.send("❌ Só é possível vender **Tesouros** (Diamante Bruto ou Estátua de Ouro). Outros itens não têm valor de mercado secundário!")

            db.update_value(user['row'], 6, ", ".join(inv_list))
            
            saldo_atual = db.parse_float(user['data'][2])
            db.update_value(user['row'], 3, round(saldo_atual + valor_venda, 2))

            await ctx.send(f"🤝 **NEGÓCIO FECHADO!** {ctx.author.mention} vendeu um(a) **{nome_formatado}** no mercado negro por `{formatar_moeda(valor_venda)} MC`!")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !vender de {ctx.author}: {e}")

def setup(bot):
    bot.add_cog(Items(bot))