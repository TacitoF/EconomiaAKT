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

        if user_id in self.bot.cascas:
            self.bot.cascas.remove(user_id)
            db.update_value(user['row'], 5, agora)
            return await ctx.send(f"🍌 **SPLASH!** {ctx.author.mention} escorregou numa casca de banana a caminho do trabalho, caiu na lama e não ganhou nada!")

        # --- NOVA LÓGICA DE SALÁRIOS RESTRITOS (v4.4) ---
        cargo = user['data'][3]
        salarios = {
            "Lêmure": (40, 100),
            "Macaquinho": (120, 250),
            "Babuíno": (300, 650),
            "Chimpanzé": (700, 1400),
            "Orangutango": (1600, 3200),
            "Gorila": (4500, 9000),
            "Ancestral": (12000, 22000),
            "Rei Símio": (35000, 70000)
        }
        
        # O default para caso não encontre ou seja um usuário muito antigo não catalogado é o Lêmure
        min_ganho, max_ganho = salarios.get(cargo, (40, 100))
        ganho = random.randint(min_ganho, max_ganho)
        
        imposto_msg = ""
        if user_id in self.bot.impostos:
            imposto_data = self.bot.impostos[user_id]
            if agora > imposto_data['fim']:
                del self.bot.impostos[user_id]
                imposto_msg = "\n🕊️ O período do seu Imposto do Gorila expirou. Você está livre!"
            else:
                taxa = int(ganho * 0.25)
                ganho -= taxa
                cobrador_id = imposto_data['cobrador_id']
                cobrador_db = db.get_user_data(cobrador_id)
                if cobrador_db:
                    db.update_value(cobrador_db['row'], 3, int(cobrador_db['data'][2]) + taxa)
                    horas_restantes = int((imposto_data['fim'] - agora) / 3600)
                    minutos_restantes = int(((imposto_data['fim'] - agora) % 3600) / 60)
                    cobrador_user = self.bot.get_user(int(cobrador_id))
                    nome_c = cobrador_user.mention if cobrador_user else "Um Gorila"
                    imposto_msg = f"\n🦍 **IMPOSTO ATIVO:** {nome_c} confiscou **{taxa} C** do seu suor! *(Restam {horas_restantes}h {minutos_restantes}m)*"

        db.update_value(user['row'], 3, int(user['data'][2]) + ganho)
        db.update_value(user['row'], 5, agora)
        
        if user_id not in self.bot.tracker_emblemas['trabalhos']: self.bot.tracker_emblemas['trabalhos'][user_id] = []
        self.bot.tracker_emblemas['trabalhos'][user_id] = [t for t in self.bot.tracker_emblemas['trabalhos'][user_id] if agora - t < 86400]
        self.bot.tracker_emblemas['trabalhos'][user_id].append(agora)

        await ctx.send(f"✅ {ctx.author.mention}, como **{cargo}**, você ganhou **{ganho} conguitos**!{imposto_msg}")

    @commands.command(aliases=["assaltar", "furtar", "rob"])
    async def roubar(self, ctx, vitima: disnake.Member):
        ladrao_id = str(ctx.author.id)
        if vitima.id == ctx.author.id: 
            ladrao_data = db.get_user_data(ladrao_id)
            if ladrao_data:
                conquistas_atuais = str(ladrao_data['data'][9]) if len(ladrao_data['data']) > 9 else ""
                if "palhaco" not in conquistas_atuais:
                    nova_lista = f"{conquistas_atuais}, palhaco".strip(", ")
                    db.update_value(ladrao_data['row'], 10, nova_lista)
            return await ctx.send("🐒 Achou que eu não ia perceber? Palhaço!")
        
        ladrao_data = db.get_user_data(ladrao_id)
        alvo_data = db.get_user_data(str(vitima.id))
        if not ladrao_data or not alvo_data: return await ctx.send("❌ Conta não encontrada!")

        agora = time.time()
        vitima_id = str(vitima.id)

        ultimo_roubo = float(ladrao_data['data'][6]) if len(ladrao_data['data']) > 6 and ladrao_data['data'][6] else 0
        if agora - ultimo_roubo < 7200:
            restante = int((7200 - (agora - ultimo_roubo)) / 60)
            return await ctx.send(f"👮 Espere **{restante} minutos** para roubar novamente.")

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
            valor_roubado = int(int(alvo_data['data'][2]) * 0.2)
            bounty_ganho = self.bot.recompensas.pop(vitima_id) if vitima_id in self.bot.recompensas and self.bot.recompensas[vitima_id] > 0 else 0
            
            seguro_msg = ""
            if "Seguro" in inv_alvo:
                recuperado = int(valor_roubado * 0.6)
                db.update_value(alvo_data['row'], 3, int(alvo_data['data'][2]) - valor_roubado + recuperado)
                inv_alvo.remove("Seguro")
                db.update_value(alvo_data['row'], 6, ", ".join(inv_alvo))
                seguro_msg = f"\n📄 **SEGURO ACIONADO:** {vitima.mention} foi roubado, mas o Banco da Selva reembolsou **{recuperado} C**!"
            else:
                db.update_value(alvo_data['row'], 3, int(alvo_data['data'][2]) - valor_roubado)

            ganho_total = valor_roubado + bounty_ganho
            db.update_value(ladrao_data['row'], 3, int(ladrao_data['data'][2]) + ganho_total)
            db.update_value(ladrao_data['row'], 7, agora)
            
            if ladrao_id not in self.bot.tracker_emblemas['roubos_sucesso']: self.bot.tracker_emblemas['roubos_sucesso'][ladrao_id] = []
            self.bot.tracker_emblemas['roubos_sucesso'][ladrao_id].append(agora)
            self.bot.tracker_emblemas['roubos_falha'][ladrao_id] = 0

            mensagem = f"🥷 **SUCESSO!** Roubou **{valor_roubado} C** de {vitima.mention}!"
            if chance_sucesso == 70: mensagem += " (Usou Pé de Cabra 🕵️)"
            if bounty_ganho > 0: mensagem += f"\n🎯 **MERCENÁRIO!** Você coletou a recompensa extra de **{bounty_ganho} C**!"
            mensagem += seguro_msg
            await ctx.send(mensagem)
        else:
            multa = int(int(ladrao_data['data'][2]) * 0.15)
            db.update_value(ladrao_data['row'], 3, int(ladrao_data['data'][2]) - multa)
            db.update_value(alvo_data['row'], 3, int(alvo_data['data'][2]) + multa)
            db.update_value(ladrao_data['row'], 7, agora)
            self.bot.tracker_emblemas['roubos_falha'][ladrao_id] = self.bot.tracker_emblemas['roubos_falha'].get(ladrao_id, 0) + 1
            await ctx.send(f"👮 **PRESO!** Pagou **{multa} C** de multa para {vitima.mention}.")

    @commands.command(aliases=["pix", "transferir", "pay"])
    async def pagar(self, ctx, recebedor: disnake.Member, valor: int):
        if recebedor.id == ctx.author.id: return await ctx.send(f"🐒 {ctx.author.mention}, você não pode fazer um Pix para si!")
        if valor <= 0: return await ctx.send("❌ Valor inválido!")
        
        pag = db.get_user_data(str(ctx.author.id))
        if not pag or int(pag['data'][2]) < valor: return await ctx.send("❌ Saldo insuficiente!")

        rec = db.get_user_data(str(recebedor.id))
        if not rec:
            db.create_user(str(recebedor.id), recebedor.display_name)
            rec = db.get_user_data(str(recebedor.id))

        db.update_value(pag['row'], 3, int(pag['data'][2]) - valor)
        db.update_value(rec['row'], 3, int(rec['data'][2]) + valor)
        
        if valor == 1: self.bot.tracker_emblemas['pix_irritante'].add(str(ctx.author.id))
        await ctx.send(embed=disnake.Embed(title="💸 PIX REALIZADO!", description=f"**{ctx.author.mention}** enviou **{valor} C** para **{recebedor.mention}**.", color=disnake.Color.green()))

def setup(bot):
    bot.add_cog(Economy(bot))