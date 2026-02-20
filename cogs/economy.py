import disnake
from disnake.ext import commands
import database as db
import time
import random

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = 757752617722970243
        
        # O dicionário de recompensas agora precisa ser acessível globalmente
        if not hasattr(bot, 'recompensas'):
            bot.recompensas = {}

        # Inicializa os trackers globais se não existirem
        if not hasattr(bot, 'tracker_emblemas'):
            bot.tracker_emblemas = {
                'trabalhos': {}, 'roubos_sucesso': {}, 'roubos_falha': {},
                'esquadrao_suicida': set(), 'palhaco': set(), 'filho_da_sorte': set(),
                'escorregou_banana': set(), 'pix_irritante': set(), 'casca_grossa': set(),
                'briga_de_bar': set(), 'ima_desgraca': set(), 'veterano_coco': set(),
                'queda_livre': set(), 'astronauta_cipo': set()
            }

    async def cog_before_invoke(self, ctx):
        """Restringe comandos de economia ao canal #🐒・conguitos."""
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, assuntos de dinheiro são apenas no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command()
    async def trabalhar(self, ctx):
        user_id = str(ctx.author.id)
        user = db.get_user_data(user_id)
        
        if not user:
            db.create_user(user_id, ctx.author.name)
            user = db.get_user_data(user_id)

        agora = time.time()
        ultimo_work = float(user['data'][4]) if len(user['data']) > 4 and user['data'][4] else 0

        if agora - ultimo_work < 3600:
            restante = int((3600 - (agora - ultimo_work)) / 60)
            return await ctx.send(f"⏳ {ctx.author.mention}, você está exausto! Volte em **{restante} minutos**.")

        cargo = user['data'][3]
        mults = {"Macaquinho": 1.0, "Chimpanzé": 1.5, "Orangutango": 2.5, "Gorila": 4.0}
        ganho = int(random.randint(100, 300) * mults.get(cargo, 1.0))
        
        db.update_value(user['row'], 3, int(user['data'][2]) + ganho)
        db.update_value(user['row'], 5, agora)
        
        # Tracker de Conquista
        if user_id not in self.bot.tracker_emblemas['trabalhos']:
            self.bot.tracker_emblemas['trabalhos'][user_id] = []
        self.bot.tracker_emblemas['trabalhos'][user_id] = [t for t in self.bot.tracker_emblemas['trabalhos'][user_id] if agora - t < 86400]
        self.bot.tracker_emblemas['trabalhos'][user_id].append(agora)

        await ctx.send(f"✅ {ctx.author.mention}, como **{cargo}**, você ganhou **{ganho} conguitos**!")

    # --- NOVO SISTEMA DE RECOMPENSAS (BOUNTY) ---
    @commands.command(aliases=["bounty", "cacada"])
    async def recompensa(self, ctx, vitima: disnake.Member, valor: int):
        """Coloca ou adiciona valor à cabeça de um usuário."""
        if vitima.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, você não pode colocar recompensa na própria cabeça!")
        if valor <= 0:
            return await ctx.send(f"❌ {ctx.author.mention}, o valor precisa ser maior que zero!")

        pagador = db.get_user_data(str(ctx.author.id))
        if not pagador or int(pagador['data'][2]) < valor:
            return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")

        # Desconta do pagador
        db.update_value(pagador['row'], 3, int(pagador['data'][2]) - valor)

        vitima_id = str(vitima.id)
        
        # LÓGICA DE SOMA: Se já existe recompensa, adiciona o novo valor
        self.bot.recompensas[vitima_id] = self.bot.recompensas.get(vitima_id, 0) + valor
        total_acumulado = self.bot.recompensas[vitima_id]

        embed = disnake.Embed(
            title="🚨 CAÇADA ATUALIZADA! 🚨",
            description=f"**{ctx.author.mention}** investiu na caçada contra **{vitima.mention}**!\n\n💰 **Prêmio Total Atual:** `{total_acumulado} Conguitos`\n\n*Quem conseguir roubar esse primata leva tudo!*",
            color=disnake.Color.red()
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=["procurados", "lista_bounty"])
    async def recompensas(self, ctx):
        """Lista todos os usuários que estão com a cabeça a prêmio."""
        if not self.bot.recompensas:
            return await ctx.send("🕊️ A selva está pacífica hoje. Ninguém tem a cabeça a prêmio!")

        embed = disnake.Embed(
            title="📜 Mural de Procurados da Selva",
            description="Roube esses macacos para coletar a recompensa extra!",
            color=disnake.Color.dark_red()
        )

        tem_gente = False
        for user_id, valor in self.bot.recompensas.items():
            if valor > 0:
                user = self.bot.get_user(int(user_id))
                nome = user.mention if user else f"ID: {user_id}"
                embed.add_field(name=f"Alvo: {user.display_name if user else 'Desconhecido'}", value=f"{nome} ➡️ **{valor} C**", inline=False)
                tem_gente = True

        if not tem_gente:
            return await ctx.send("🕊️ As recompensas foram todas zeradas ou coletadas.")

        await ctx.send(embed=embed)

    # --- SISTEMA DE ROUBO ---
    @commands.command(aliases=["assaltar", "furtar", "rob"])
    async def roubar(self, ctx, vitima: disnake.Member):
        ladrao_id = str(ctx.author.id)
        if vitima.id == ctx.author.id: 
            self.bot.tracker_emblemas['palhaco'].add(ladrao_id)
            return await ctx.send("🐒 Achou que eu não ia perceber? Ganhou a conquista de Palhaço por tentar se roubar!")
        
        ladrao_data = db.get_user_data(ladrao_id)
        alvo_data = db.get_user_data(str(vitima.id))
        if not ladrao_data or not alvo_data: return await ctx.send("❌ Conta não encontrada!")

        agora = time.time()
        vitima_id = str(vitima.id)

        ultimo_roubo = float(ladrao_data['data'][6]) if len(ladrao_data['data']) > 6 and ladrao_data['data'][6] else 0
        if agora - ultimo_roubo < 7200:
            restante = int((7200 - (agora - ultimo_roubo)) / 60)
            return await ctx.send(f"👮 Espere **{restante} minutos** para roubar novamente.")

        chance_sucesso = 40
        if "Pé de Cabra" in ladrao_data['data'][5]:
            chance_sucesso = 70
            db.update_value(ladrao_data['row'], 6, "") 

        if "Escudo" in alvo_data['data'][5]:
            db.update_value(alvo_data['row'], 6, "")
            db.update_value(ladrao_data['row'], 7, agora)
            self.bot.tracker_emblemas['casca_grossa'].add(ladrao_id)
            return await ctx.send(f"🛡️ {vitima.mention} estava protegido por um Escudo e você perdeu o seu ataque!")

        if random.randint(1, 100) <= chance_sucesso:
            valor_roubado = int(int(alvo_data['data'][2]) * 0.2)
            bounty_ganho = 0
            
            # Coleta Recompensa Global
            if vitima_id in self.bot.recompensas and self.bot.recompensas[vitima_id] > 0:
                bounty_ganho = self.bot.recompensas.pop(vitima_id)

            ganho_total = valor_roubado + bounty_ganho

            db.update_value(ladrao_data['row'], 3, int(ladrao_data['data'][2]) + ganho_total)
            db.update_value(alvo_data['row'], 3, int(alvo_data['data'][2]) - valor_roubado)
            db.update_value(ladrao_data['row'], 7, agora)
            
            if ladrao_id not in self.bot.tracker_emblemas['roubos_sucesso']: self.bot.tracker_emblemas['roubos_sucesso'][ladrao_id] = []
            self.bot.tracker_emblemas['roubos_sucesso'][ladrao_id].append(agora)
            self.bot.tracker_emblemas['roubos_falha'][ladrao_id] = 0

            mensagem = f"🥷 **SUCESSO!** Roubou **{valor_roubado} C** de {vitima.mention}!"
            if chance_sucesso == 70: mensagem += " (Usou Pé de Cabra 🕵️)"
            if bounty_ganho > 0: mensagem += f"\n🎯 **MERCENÁRIO!** Você coletou a recompensa extra de **{bounty_ganho} C**!"
            await ctx.send(mensagem)
        else:
            multa = int(int(ladrao_data['data'][2]) * 0.15)
            db.update_value(ladrao_data['row'], 3, int(ladrao_data['data'][2]) - multa)
            db.update_value(alvo_data['row'], 3, int(alvo_data['data'][2]) + multa)
            db.update_value(ladrao_data['row'], 7, agora)
            self.bot.tracker_emblemas['roubos_falha'][ladrao_id] = self.bot.tracker_emblemas['roubos_falha'].get(ladrao_id, 0) + 1
            await ctx.send(f"👮 **PRESO!** Pagou **{multa} C** de multa.")

    @commands.command(aliases=["pix", "transferir", "pay"])
    async def pagar(self, ctx, recebedor: disnake.Member, valor: int):
        if recebedor.id == ctx.author.id: return await ctx.send(f"🐒 {ctx.author.mention}, você não pode fazer um Pix para si mesmo!")
        if valor <= 0: return await ctx.send("❌ Valor inválido!")
        pagador_data = db.get_user_data(str(ctx.author.id))
        if not pagador_data or int(pagador_data['data'][2]) < valor: return await ctx.send("❌ Saldo insuficiente!")

        recebedor_data = db.get_user_data(str(recebedor.id))
        if not recebedor_data:
            db.create_user(str(recebedor.id), recebedor.display_name)
            recebedor_data = db.get_user_data(str(recebedor.id))

        db.update_value(pagador_data['row'], 3, int(pagador_data['data'][2]) - valor)
        db.update_value(recebedor_data['row'], 3, int(recebedor_data['data'][2]) + valor)
        
        if valor == 1: self.bot.tracker_emblemas['pix_irritante'].add(str(ctx.author.id))

        embed = disnake.Embed(title="💸 PIX REALIZADO!", description=f"**{ctx.author.mention}** enviou **{valor} C** para **{recebedor.mention}**.", color=disnake.Color.green())
        await ctx.send(embed=embed)

    @commands.command()
    async def setar(self, ctx, membro: disnake.Member, valor: int):
        if ctx.author.id != self.owner_id: return await ctx.send("❌ Sem permissão!")
        user = db.get_user_data(str(membro.id))
        if not user: return await ctx.send("❌ Usuário não encontrado!")
        db.update_value(user['row'], 3, valor)
        await ctx.send(f"✅ O saldo de {membro.mention} agora é **{valor} C**.")

    @commands.command()
    async def wipe(self, ctx):
        if ctx.author.id != self.owner_id: return await ctx.send("❌ Sem permissão!")
        await ctx.send("🧹 Iniciando o reset da economia...")
        try:
            db.wipe_database() 
            await ctx.send("✅ **WIPE CONCLUÍDO!** Todos estão pobres novamente.")
        except Exception as e:
            await ctx.send(f"⚠️ Erro: {e}")

def setup(bot):
    bot.add_cog(Economy(bot))