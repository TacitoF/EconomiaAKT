import disnake
from disnake.ext import commands
import database as db
import time
import asyncio

class Items(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, 'cascas'): bot.cascas = set()
        if not hasattr(bot, 'impostos'): bot.impostos = {}

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, use itens no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["banana"])
    async def casca(self, ctx, vitima: disnake.Member = None):
        # MENSAGEM DE AJUDA
        if vitima is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, formato incorreto!\nUse: `!casca @usuario`")

        if vitima.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, você é burro? Não pode jogar uma casca de banana no próprio pé!")

        user = db.get_user_data(str(ctx.author.id))
        if not user: return await ctx.send("❌ Você não tem conta!")

        inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
        inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
        
        if "Casca de Banana" not in inv_list: 
            return await ctx.send("❌ Você não tem uma **Casca de Banana** no inventário! Compre na `!loja`.")
            
        inv_list.remove("Casca de Banana")
        db.update_value(user['row'], 6, ", ".join(inv_list))
        
        self.bot.cascas.add(str(vitima.id))
        await ctx.send(f"🍌 {ctx.author.mention} jogou silenciosamente uma Casca de Banana no pé de {vitima.mention}! O próximo passo dele será uma tragédia...")

    @commands.command(aliases=["imposto"])
    async def taxar(self, ctx, vitima: disnake.Member = None):
        if vitima is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, formato incorreto!\nUse: `!taxar @usuario`")

        if vitima.id == ctx.author.id: 
            return await ctx.send("❌ Você não pode taxar a si mesmo!")
            
        if vitima.bot:
            return await ctx.send("🤖 Bots não pagam impostos, amigo!")
        
        user = db.get_user_data(str(ctx.author.id))
        inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
        inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]

        if "Imposto do Gorila" not in inv_list: 
            return await ctx.send("❌ Você não tem o item **Imposto do Gorila** no inventário!")
            
        if str(vitima.id) in self.bot.impostos and self.bot.impostos[str(vitima.id)]['fim'] > time.time():
            tempo_restante = int(self.bot.impostos[str(vitima.id)]['fim'])
            return await ctx.send(f"❌ {vitima.mention} já está sob os efeitos de um Imposto! Espere o tempo dele acabar <t:{tempo_restante}:R>.")
        
        inv_list.remove("Imposto do Gorila")
        db.update_value(user['row'], 6, ", ".join(inv_list))
        
        tempo_fim = time.time() + 86400
        self.bot.impostos[str(vitima.id)] = {'cobrador_id': str(ctx.author.id), 'fim': tempo_fim}
        
        await ctx.send(f"🦍 **DECRETO ASSINADO!** {ctx.author.mention} cobrou o Imposto do Gorila de {vitima.mention}. Durante **24 horas** (até <t:{int(tempo_fim)}:f>), 25% do trabalho dele irá para você!")

    @commands.command(aliases=["nick", "renomear"])
    async def apelidar(self, ctx, vitima: disnake.Member = None, *, novo_nick: str = None):
        if vitima is None or novo_nick is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, formato incorreto!\nUse: `!apelidar @usuario <novo nick>`")

        if len(novo_nick) > 32: 
            return await ctx.send("❌ Nick muito longo (Máx: 32 caracteres).")
        
        user = db.get_user_data(str(ctx.author.id))
        inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
        inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]

        if "Troca de Nick" not in inv_list: 
            return await ctx.send("❌ Você não tem o item **Troca de Nick** no inventário!")
            
        nick_antigo = vitima.display_name
        try: 
            await vitima.edit(nick=novo_nick)
        except disnake.errors.Forbidden: 
            return await ctx.send("❌ Não tenho permissão (Hierarquia de Cargos do Discord) para mudar o nick dessa pessoa!")
            
        inv_list.remove("Troca de Nick")
        db.update_value(user['row'], 6, ", ".join(inv_list))
        
        tempo_fim = int(time.time() + 1800)
        await ctx.send(f"🪄 {ctx.author.mention} usou magia negra e transformou o nome de `{nick_antigo}` em **{novo_nick}**! O efeito passa <t:{tempo_fim}:R>.")
        
        async def reverter_nick():
            await asyncio.sleep(1800)
            try: await vitima.edit(nick=nick_antigo)
            except: pass
            
        self.bot.loop.create_task(reverter_nick())

def setup(bot):
    bot.add_cog(Items(bot))