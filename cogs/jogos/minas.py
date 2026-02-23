import disnake
from disnake.ext import commands
import database as db
import random
import asyncio

def get_limite(cargo):
    """Limites da V4.4 para os jogos"""
    limites = {
        "Lêmure": 250, "Macaquinho": 800, "Babuíno": 2000, "Chimpanzé": 6000,
        "Orangutango": 15000, "Gorila": 45000, "Ancestral": 150000, "Rei Símio": 1500000
    }
    return limites.get(cargo, 250)

class MinasGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, vá para o canal {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(name="minas")
    async def campo_minado(self, ctx, bombas: int = None, aposta: float = None):
        # MENSAGEM DE AJUDA
        if bombas is None or aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, formato incorreto!\nUse: `!minas <quantidade de bombas 1-5> <valor>`\nExemplo: `!minas 5 100.50`")

        # Validações Iniciais
        if not (1 <= bombas <= 5): 
            return await ctx.send(f"❌ {ctx.author.mention}, escolha entre 1 e 5 bombas apenas.")

        if aposta <= 0: 
            return await ctx.send(f"❌ {ctx.author.mention}, aposta inválida!")
            
        aposta = round(aposta, 2)
        user = db.get_user_data(str(ctx.author.id))
        
        if not user or aposta > float(user['data'][2]): 
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        cargo = user['data'][3]
        limite = get_limite(cargo)
        if aposta > limite: 
            return await ctx.send(f"🚫 Limite de aposta para **{cargo}** é de **{limite} C**!")

        # Retira o dinheiro antes de jogar (em float)
        db.update_value(user['row'], 3, round(float(user['data'][2]) - aposta, 2))

        await ctx.send(f"💣 {ctx.author.mention} entrando no campo com {bombas} minas... 🏃💨")
        await asyncio.sleep(1.5)

        # --- A NOVA MATEMÁTICA DE TIRO ÚNICO (Sem Taxa de 15%) ---
        tabela_risco = {
            1: {"chance": 85, "mult": 1.10},
            2: {"chance": 70, "mult": 1.30},
            3: {"chance": 60, "mult": 1.50},
            4: {"chance": 50, "mult": 1.75},
            5: {"chance": 40, "mult": 2.00}
        }
        
        config = tabela_risco[bombas]
        sorteio = random.randint(1, 100)
        user_atual = db.get_user_data(str(ctx.author.id))

        if sorteio <= config["chance"]:
            # Ganhou
            ganho_total = round(aposta * config["mult"], 2)
            lucro_liquido = round(ganho_total - aposta, 2)
            
            db.update_value(user_atual['row'], 3, round(float(user_atual['data'][2]) + ganho_total, 2))
            
            # Adicionando conquista para as 5 minas
            conquistas_atuais = str(user_atual['data'][9]) if len(user_atual['data']) > 9 else ""
            lista_conquistas = [c.strip() for c in conquistas_atuais.split(',') if c.strip()]
            if bombas == 5 and "esquadrao_suicida" not in lista_conquistas:
                lista_conquistas.append("esquadrao_suicida")
                db.update_value(user_atual['row'], 10, ", ".join(lista_conquistas))
            
            await ctx.send(f"🚩 **LIMPO!** {ctx.author.mention} sobreviveu e faturou **{lucro_liquido:.2f} C** de lucro! (`{config['mult']}x` - *Prêmio isento de taxa*)")
        else:
            # Perdeu
            conquistas_atuais = str(user_atual['data'][9]) if len(user_atual['data']) > 9 else ""
            lista_conquistas = [c.strip() for c in conquistas_atuais.split(',') if c.strip()]
            if bombas == 1 and "escorregou_banana" not in lista_conquistas:
                lista_conquistas.append("escorregou_banana")
                db.update_value(user_atual['row'], 10, ", ".join(lista_conquistas))
                
            await ctx.send(f"💥 **BOOOOM!** {ctx.author.mention} pisou em uma mina e virou paçoca. Perdeu **{aposta:.2f} C**.")

def setup(bot):
    bot.add_cog(MinasGame(bot))