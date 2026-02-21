import disnake
from disnake.ext import commands
import database as db
import random
import asyncio

class Roleta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roleta_aberta = False
        self.apostas = [] # Vai guardar dicionários: {'user': ctx.author, 'valor': aposta, 'tipo': aposta_em}

    async def save_achievement(self, user_data, slug):
        conquistas_atuais = str(user_data['data'][9]) if len(user_data['data']) > 9 else ""
        lista = [c.strip() for c in conquistas_atuais.split(',') if c.strip()]
        if slug not in lista:
            lista.append(slug)
            db.update_value(user_data['row'], 10, ", ".join(lista))
            return True
        return False

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, a roleta fica no cassino! Vai para o canal {mencao}.")
            raise commands.CommandError("Canal de apostas incorreto.")

    @commands.command(aliases=["roulette", "rol"])
    async def roleta(self, ctx):
        """Abre a mesa de roleta para apostas."""
        if self.roleta_aberta:
            return await ctx.send(f"⚠️ {ctx.author.mention}, a mesa já está aberta! Usa `!apostar <valor> <vermelho/preto/par/impar/numero>` para entrar na rodada.")

        self.roleta_aberta = True
        self.apostas = []

        embed_abertura = disnake.Embed(
            title="🎰 A MESA DE ROLETA ABRIU!",
            description=f"O Chimpanzézio abriu a mesa! Vocês têm **30 segundos** para fazer as suas apostas.\n\n**Como jogar:**\n`!apostar <valor> <opção>`\n*Opções: vermelho (2x), preto (2x), par (2x), impar (2x), 0 a 36 (36x)*",
            color=disnake.Color.gold()
        )
        await ctx.send(embed=embed_abertura)

        # Espera 30 segundos para a galera apostar
        await asyncio.sleep(30)

        self.roleta_aberta = False

        if not self.apostas:
            return await ctx.send("🦗 Ninguém apostou... O Chimpanzézio fechou a mesa por falta de macacos.")

        # --- FASE 1: FECHOU A MESA ---
        total_apostado = sum(a['valor'] for a in self.apostas)
        embed_giro = disnake.Embed(
            title="🛑 APOSTAS ENCERRADAS!",
            description=f"Temos **{len(self.apostas)} apostas** na mesa totalizando **{total_apostado} C**!\n\n🌀 **O Chimpanzézio girou a roleta...**",
            color=disnake.Color.orange()
        )
        # CORREÇÃO: Adicionado o "embed=" que estava faltando e causando o bug visual
        msg = await ctx.send(embed=embed_giro) 
        await asyncio.sleep(2)

        # --- FASE 2: SUSPENSE ---
        embed_giro.description = f"Temos **{len(self.apostas)} apostas** na mesa totalizando **{total_apostado} C**!\n\n⚪ *A bolinha está pulando e perdendo força...*"
        await msg.edit(embed=embed_giro)
        await asyncio.sleep(2)

        # --- LÓGICA DO SORTEIO ---
        resultado_num = random.randint(0, 36)
        vermelhos = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
        
        if resultado_num == 0:
            cor = "verde"
            emoji = "🟩"
        elif resultado_num in vermelhos:
            cor = "vermelho"
            emoji = "🟥"
        else:
            cor = "preto"
            emoji = "⬛"

        # --- FASE 3: PAGAMENTOS ---
        vencedores_txt = ""
        perdedores_txt = ""

        for aposta in self.apostas:
            jogador = aposta['user']
            valor = aposta['valor']
            aposta_em = aposta['tipo']
            user_db = db.get_user_data(str(jogador.id))

            ganhou = False
            multiplicador = 0

            if aposta_em.isdigit() and int(aposta_em) == resultado_num:
                ganhou = True
                multiplicador = 36
            elif aposta_em == cor:
                ganhou = True
                multiplicador = 2
            elif aposta_em == "par" and resultado_num != 0 and resultado_num % 2 == 0:
                ganhou = True
                multiplicador = 2
            elif aposta_em == "impar" and resultado_num != 0 and resultado_num % 2 != 0:
                ganhou = True
                multiplicador = 2

            if ganhou:
                ganho_total = valor * multiplicador
                if user_db: db.update_value(user_db['row'], 3, int(user_db['data'][2]) + ganho_total)
                vencedores_txt += f"🎉 {jogador.mention} apostou em `{aposta_em.upper()}` e ganhou **{ganho_total} C**!\n"
                
                # Conquista de Sorte se acertar o número em cheio
                if multiplicador == 36 and user_db:
                    await self.save_achievement(user_db, "filho_da_sorte")
            else:
                perdedores_txt += f"💀 {jogador.mention} apostou em `{aposta_em.upper()}` e perdeu **{valor} C**.\n"

        # --- RESULTADO FINAL NO CHAT ---
        if not vencedores_txt: vencedores_txt = "Nenhum macaco teve sorte..."
        if not perdedores_txt: perdedores_txt = "O casino tomou prejuízo, ninguém perdeu!"

        embed_final = disnake.Embed(
            title=f"🎰 A ROLETA PAROU NO: {emoji} {resultado_num} ({cor.upper()})",
            color=disnake.Color.green() if "🎉" in vencedores_txt else disnake.Color.red()
        )
        embed_final.add_field(name="💰 VENCEDORES", value=vencedores_txt, inline=False)
        embed_final.add_field(name="💸 PERDEDORES", value=perdedores_txt, inline=False)
        
        # O embed substitui perfeitamente a mensagem de suspense
        await msg.edit(embed=embed_final)

    @commands.command()
    async def apostar(self, ctx, valor: int, aposta_em: str):
        """Entra na rodada atual da roleta."""
        if not self.roleta_aberta:
            return await ctx.send(f"⚠️ {ctx.author.mention}, a mesa está fechada! Usa `!roleta` para abrir uma nova rodada.")
        
        if valor <= 0:
            return await ctx.send(f"❌ {ctx.author.mention}, a aposta tem de ser maior que zero!")

        user = db.get_user_data(str(ctx.author.id))
        if not user or int(user['data'][2]) < valor:
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        aposta_em = aposta_em.lower()
        opcoes_validas = ['vermelho', 'preto', 'par', 'impar'] + [str(i) for i in range(37)]
        
        if aposta_em not in opcoes_validas:
            return await ctx.send(f"❌ {ctx.author.mention}, aposta inválida! Escolhe: vermelho, preto, par, impar ou um número de 0 a 36.")

        # Cobra o valor
        db.update_value(user['row'], 3, int(user['data'][2]) - valor)
        
        # Adiciona na mesa
        self.apostas.append({'user': ctx.author, 'valor': valor, 'tipo': aposta_em})
        
        # Confirmação simples para não poluir
        await ctx.send(f"🪙 {ctx.author.mention} apostou **{valor} C** em `{aposta_em.upper()}`!")

def setup(bot):
    bot.add_cog(Roleta(bot))