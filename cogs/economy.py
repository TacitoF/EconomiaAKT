import disnake
from disnake.ext import commands
import database as db
import time
import random

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, 'recompensas'): bot.recompensas = {}
        if not hasattr(bot, 'cascas'): bot.cascas = set()
        if not hasattr(bot, 'impostos'): bot.impostos = {}
        if not hasattr(bot, 'tracker_emblemas'):
            bot.tracker_emblemas = {
                'trabalhos': {}, 'roubos_sucesso': {}, 'roubos_falha': {},
                'esquadrao_suicida': set(), 'palhaco': set(), 'filho_da_sorte': set(),
                'escorregou_banana': set(), 'pix_irritante': set(), 'casca_grossa': set(),
                'briga_de_bar': set(), 'ima_desgraca': set(), 'veterano_coco': set(),
                'queda_livre': set(), 'astronauta_cipo': set()
            }

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, assuntos de dinheiro são apenas no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["work"])
    async def trabalhar(self, ctx):
        user_id = str(ctx.author.id)
        user = db.get_user_data(user_id)
        if not user:
            db.create_user(user_id, ctx.author.name)
            user = db.get_user_data(user_id)

        agora = time.time()
        ultimo_work = float(user['data'][4]) if len(user['data']) > 4 and user['data'][4] else 0

        # Cooldown de 1 Hora (3600 segundos)
        if agora - ultimo_work < 3600:
            tempo_liberacao = int(ultimo_work + 3600)
            return await ctx.send(f"⏳ {ctx.author.mention}, você está exausto! Volte <t:{tempo_liberacao}:R>.")

        if user_id in self.bot.cascas:
            self.bot.cascas.remove(user_id)
            db.update_value(user['row'], 5, agora)
            return await ctx.send(f"🍌 **SPLASH!** {ctx.author.mention} escorregou numa casca de banana a caminho do trabalho, caiu na lama e não ganhou nada!")

        # --- TABELA DE SALÁRIOS V4.4 ---
        cargo = user['data'][3]
        salarios = {
            "Lêmure": (60, 120),
            "Macaquinho": (150, 300),
            "Babuíno": (400, 800),
            "Chimpanzé": (1000, 2000),
            "Orangutango": (3000, 5500),
            "Gorila": (8000, 15000),
            "Ancestral": (20000, 40000),
            "Rei Símio": (60000, 120000)
        }
        
        min_ganho, max_ganho = salarios.get(cargo, (60, 120))
        ganho = round(random.uniform(min_ganho, max_ganho), 2)
        
        imposto_msg = ""
        if user_id in self.bot.impostos:
            imposto_data = self.bot.impostos[user_id]
            if agora > imposto_data['fim']:
                del self.bot.impostos[user_id]
                imposto_msg = "\n🕊️ O período do seu Imposto do Gorila expirou. Você está livre!"
            else:
                taxa = round(ganho * 0.25, 2)
                ganho = round(ganho - taxa, 2)
                
                cobrador_id = imposto_data['cobrador_id']
                cobrador_db = db.get_user_data(cobrador_id)
                if cobrador_db:
                    db.update_value(cobrador_db['row'], 3, round(float(cobrador_db['data'][2]) + taxa, 2))
                    
                    tempo_fim_imposto = int(imposto_data['fim'])
                    cobrador_user = self.bot.get_user(int(cobrador_id))
                    nome_c = cobrador_user.mention if cobrador_user else "Um Gorila"
                    imposto_msg = f"\n🦍 **IMPOSTO ATIVO:** {nome_c} confiscou **{taxa:.2f} C** do seu suor! *(Expira <t:{tempo_fim_imposto}:R>)*"

        db.update_value(user['row'], 3, round(float(user['data'][2]) + ganho, 2))
        db.update_value(user['row'], 5, agora)
        
        if user_id not in self.bot.tracker_emblemas['trabalhos']: self.bot.tracker_emblemas['trabalhos'][user_id] = []
        self.bot.tracker_emblemas['trabalhos'][user_id] = [t for t in self.bot.tracker_emblemas['trabalhos'][user_id] if agora - t < 86400]
        self.bot.tracker_emblemas['trabalhos'][user_id].append(agora)

        await ctx.send(f"✅ {ctx.author.mention}, como **{cargo}**, você ganhou **{ganho:.2f} conguitos**!{imposto_msg}")

    @commands.command(aliases=["assaltar", "furtar", "rob"])
    async def roubar(self, ctx, vitima: disnake.Member = None):
        if vitima is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, você esqueceu de dizer quem quer roubar!\nUse: `!roubar @usuario`")

        ladrao_id = str(ctx.author.id)
        if vitima.id == ctx.author.id: 
            ladrao_data = db.get_user_data(ladrao_id)
            if ladrao_data:
                conquistas_atuais = str(ladrao_data['data'][9]) if len(ladrao_data['data']) > 9 else ""
                if "palhaco" not in conquistas_atuais:
                    nova_lista = f"{conquistas_atuais}, palhaco".strip(", ")
                    db.update_value(ladrao_data['row'], 10, nova_lista)
            return await ctx.send("🐒 Achou que eu não ia perceber? Palhaço! Não pode roubar a si mesmo.")
        
        ladrao_data = db.get_user_data(ladrao_id)
        alvo_data = db.get_user_data(str(vitima.id))
        
        if not ladrao_data or not alvo_data: 
            return await ctx.send("❌ Uma das contas não foi encontrada no banco de dados!")

        if float(ladrao_data['data'][2]) < 50:
            return await ctx.send("❌ Você precisa ter pelo menos **50 C** na conta para tentar um assalto!")

        agora = time.time()
        vitima_id = str(vitima.id)

        # Cooldown de 2 Horas
        ultimo_roubo = float(ladrao_data['data'][6]) if len(ladrao_data['data']) > 6 and ladrao_data['data'][6] else 0
        if agora - ultimo_roubo < 7200:
            tempo_liberacao = int(ultimo_roubo + 7200)
            return await ctx.send(f"👮 Espere! Você só poderá roubar novamente <t:{tempo_liberacao}:R>.")

        if ladrao_id in self.bot.cascas:
            self.bot.cascas.remove(ladrao_id)
            db.update_value(ladrao_data['row'], 7, agora)
            return await ctx.send(f"🍌 **QUE FASE!** {ctx.author.mention} escorregou numa casca de banana no meio do assalto! Fez barulho e fugiu de mãos vazias.")

        chance_sucesso = 40
        inv_ladrao_str = str(ladrao_data['data'][5]) if len(ladrao_data['data']) > 5 else ""
        inv_alvo_str = str(alvo_data['data'][5]) if len(alvo_data['data']) > 5 else ""
        inv_ladrao = [i.strip() for i in inv_ladrao_str.split(',') if i.strip()]
        inv_alvo = [i.strip() for i in inv_alvo_str.split(',') if i.strip()]

        if "Pé de Cabra" in inv_ladrao:
            chance_sucesso = 70
            inv_ladrao.remove("Pé de Cabra")
            db.update_value(ladrao_data['row'], 6, ", ".join(inv_ladrao))

        if "Escudo" in inv_alvo:
            inv_alvo.remove("Escudo")
            db.update_value(alvo_data['row'], 6, ", ".join(inv_alvo))
            db.update_value(ladrao_data['row'], 7, agora)
            self.bot.tracker_emblemas['casca_grossa'].add(ladrao_id)
            return await ctx.send(f"🛡️ {vitima.mention} estava protegido por um **Escudo** e você perdeu o seu ataque!")

        if random.randint(1, 100) <= chance_sucesso:
            # Rebalanceamento: Rouba entre 5% e 12% do saldo do alvo (mais saudável para a economia)
            percentual_roubo = random.uniform(0.05, 0.12)
            valor_roubado = round(float(alvo_data['data'][2]) * percentual_roubo, 2)
            
            if valor_roubado <= 1:
                db.update_value(ladrao_data['row'], 7, agora)
                return await ctx.send(f"😬 {vitima.mention} está tão pobre que não valia a pena o risco. Você sentiu pena e foi embora de mãos abanando.")

            bounty_ganho = self.bot.recompensas.pop(vitima_id) if vitima_id in self.bot.recompensas and self.bot.recompensas[vitima_id] > 0 else 0.0
            
            seguro_msg = ""
            if "Seguro" in inv_alvo:
                recuperado = round(valor_roubado * 0.6, 2)
                db.update_value(alvo_data['row'], 3, round(float(alvo_data['data'][2]) - valor_roubado + recuperado, 2))
                inv_alvo.remove("Seguro")
                db.update_value(alvo_data['row'], 6, ", ".join(inv_alvo))
                seguro_msg = f"\n📄 **SEGURO ACIONADO:** {vitima.mention} foi roubado, mas o Banco reembolsou **{recuperado:.2f} C**!"
            else:
                db.update_value(alvo_data['row'], 3, round(float(alvo_data['data'][2]) - valor_roubado, 2))

            ganho_total = round(valor_roubado + bounty_ganho, 2)
            db.update_value(ladrao_data['row'], 3, round(float(ladrao_data['data'][2]) + ganho_total, 2))
            db.update_value(ladrao_data['row'], 7, agora)
            
            # --- SISTEMA DE PROCURADOS AUTOMÁTICO ---
            # A polícia injeta um bounty na cabeça do ladrão equivalente a 15% do que ele roubou (capado a 5k)
            bounty_adicionado = round(valor_roubado * 0.15, 2)
            if bounty_adicionado > 5000: bounty_adicionado = 5000.0
            self.bot.recompensas[ladrao_id] = self.bot.recompensas.get(ladrao_id, 0.0) + bounty_adicionado
            
            if ladrao_id not in self.bot.tracker_emblemas['roubos_sucesso']: self.bot.tracker_emblemas['roubos_sucesso'][ladrao_id] = []
            self.bot.tracker_emblemas['roubos_sucesso'][ladrao_id].append(agora)
            self.bot.tracker_emblemas['roubos_falha'][ladrao_id] = 0

            mensagem = f"🥷 **SUCESSO!** Você roubou **{valor_roubado:.2f} C** de {vitima.mention}!"
            if chance_sucesso == 70: mensagem += " (Usou Pé de Cabra 🕵️)"
            if bounty_ganho > 0: mensagem += f"\n🎯 **MERCENÁRIO!** Você coletou a recompensa extra de **{bounty_ganho:.2f} C**!"
            mensagem += seguro_msg
            mensagem += f"\n🚨 *A polícia notou! Uma recompensa automática de **{bounty_adicionado:.2f} C** foi colocada na sua cabeça pelo sistema!*"
            await ctx.send(mensagem)
        else:
            # Rebalanceamento: Multa varia de 8% a 15%
            percentual_multa = random.uniform(0.08, 0.15)
            multa = round(float(ladrao_data['data'][2]) * percentual_multa, 2)
            if multa < 10: multa = 10.0 # Multa mínima
            
            db.update_value(ladrao_data['row'], 3, round(float(ladrao_data['data'][2]) - multa, 2))
            db.update_value(alvo_data['row'], 3, round(float(alvo_data['data'][2]) + multa, 2))
            db.update_value(ladrao_data['row'], 7, agora)
            self.bot.tracker_emblemas['roubos_falha'][ladrao_id] = self.bot.tracker_emblemas['roubos_falha'].get(ladrao_id, 0) + 1
            await ctx.send(f"👮 **PRESO!** O roubo falhou e você pagou **{multa:.2f} C** de multa/indenização para {vitima.mention}.")

    @commands.command(aliases=["pix", "transferir", "pay"])
    async def pagar(self, ctx, recebedor: disnake.Member = None, valor: float = None):
        if recebedor is None or valor is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, formato incorreto!\nUse: `!pagar @usuario <valor>`")

        if recebedor.id == ctx.author.id: 
            return await ctx.send(f"🐒 {ctx.author.mention}, você não pode fazer um Pix para si mesmo!")
            
        if valor <= 0: return await ctx.send("❌ O valor do Pix deve ser maior que zero!")
        valor = round(valor, 2)
        
        pag = db.get_user_data(str(ctx.author.id))
        if not pag or float(pag['data'][2]) < valor: 
            return await ctx.send("❌ Saldo insuficiente!")

        rec = db.get_user_data(str(recebedor.id))
        if not rec:
            db.create_user(str(recebedor.id), recebedor.display_name)
            rec = db.get_user_data(str(recebedor.id))

        db.update_value(pag['row'], 3, round(float(pag['data'][2]) - valor, 2))
        db.update_value(rec['row'], 3, round(float(rec['data'][2]) + valor, 2))
        
        if valor == 1.0: self.bot.tracker_emblemas['pix_irritante'].add(str(ctx.author.id))
        
        await ctx.send(embed=disnake.Embed(
            title="💸 PIX REALIZADO!", 
            description=f"**{ctx.author.mention}** enviou **{valor:.2f} C** para **{recebedor.mention}**.", 
            color=disnake.Color.green()
        ))

def setup(bot):
    bot.add_cog(Economy(bot))