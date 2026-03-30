import disnake
from disnake.ext import commands, tasks
import database as db
import random
import time
import asyncio

# Configurações de Dano e Cooldown
BOSS_MAX_HP = 10000
COOLDOWN_ATAQUE = 120 # 2 minutos entre qualquer ataque

def gerar_barra_hp(hp_atual, hp_max):
    tamanho = 15
    preenchido = int((hp_atual / hp_max) * tamanho)
    vazio = tamanho - preenchido
    return f"[{'🟥' * preenchido}{'⬛' * vazio}] {hp_atual}/{hp_max} HP"

class BossView(disnake.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None) # Não expira, o cog gerencia o encerramento
        self.cog = cog

    async def processar_ataque(self, inter: disnake.MessageInteraction, tipo: str):
        if not self.cog.boss_ativo:
            return await inter.response.send_message("❌ O Boss já foi derrotado ou fugiu!", ephemeral=True)

        user_id = str(inter.author.id)
        agora = time.time()

        # Verifica Cooldown
        cd_usuario = self.cog.cooldowns.get(user_id, 0)
        if agora < cd_usuario:
            faltam = int(cd_usuario - agora)
            return await inter.response.send_message(f"⏳ Você está recuperando o fôlego! Tente de novo em {faltam}s.", ephemeral=True)

        user_db = db.get_user_data(user_id)
        if not user_db:
            return await inter.response.send_message("❌ Você precisa ter uma conta na selva!", ephemeral=True)

        dano = 0
        msg_extra = ""

        # Lógica de cada tipo de ataque
        if tipo == "soco":
            dano = random.randint(80, 150)
            msg_extra = "Você deu um soco no gorila!"

        elif tipo == "pet":
            tipo_pet, fome = db.get_mascote(user_db)
            if not tipo_pet:
                return await inter.response.send_message("❌ Você não tem um mascote para te ajudar!", ephemeral=True)
            if fome < 20:
                return await inter.response.send_message("❌ Seu mascote está com muita fome (<20%) para lutar. Alimente-o!", ephemeral=True)
            
            db.set_mascote(user_db['row'], tipo_pet, fome - 20)
            dano = random.randint(200, 350)
            msg_extra = f"Seu mascote atacou ferozmente! (-20% de Fome)"

        elif tipo == "cabra":
            inv = [i.strip() for i in str(user_db['data'][5]).split(",") if i.strip()]
            if "Pé de Cabra" not in inv:
                return await inter.response.send_message("❌ Você não tem um Pé de Cabra no inventário!", ephemeral=True)
            
            inv.remove("Pé de Cabra")
            db.update_value(user_db['row'], 6, ", ".join(inv) if inv else "Nenhum")
            dano = random.randint(400, 600)
            msg_extra = "Você quebrou o Pé de Cabra nas costas do gorila!"

        elif tipo == "c4":
            inv = [i.strip() for i in str(user_db['data'][5]).split(",") if i.strip()]
            if "Carga de C4" not in inv:
                return await inter.response.send_message("❌ Você não tem uma Carga de C4 no inventário!", ephemeral=True)
            
            inv.remove("Carga de C4")
            db.update_value(user_db['row'], 6, ", ".join(inv) if inv else "Nenhum")
            dano = random.randint(1500, 2500)
            msg_extra = "BOOOM! Você explodiu uma C4 na cara do monstro!"

        # Aplica o dano e o cooldown
        self.cog.cooldowns[user_id] = agora + COOLDOWN_ATAQUE
        self.cog.boss_hp -= dano
        if self.cog.boss_hp < 0: self.cog.boss_hp = 0
        
        # Registra no ranking
        self.cog.dano_jogadores[user_id] = self.cog.dano_jogadores.get(user_id, 0) + dano
        self.cog.nomes_jogadores[user_id] = inter.author.display_name

        await inter.response.send_message(f"💥 **{dano} de Dano!** {msg_extra}", ephemeral=True)

        # Checa se morreu
        if self.cog.boss_hp <= 0:
            await self.cog.encerrar_boss(vitoria=True, canal=inter.channel)
        else:
            await self.cog.atualizar_mensagem()

    @disnake.ui.button(label="Soco", style=disnake.ButtonStyle.primary, emoji="👊")
    async def btn_soco(self, button, inter):
        await self.processar_ataque(inter, "soco")

    @disnake.ui.button(label="Usar Pet", style=disnake.ButtonStyle.success, emoji="🐾")
    async def btn_pet(self, button, inter):
        await self.processar_ataque(inter, "pet")

    @disnake.ui.button(label="Pé de Cabra", style=disnake.ButtonStyle.secondary, emoji="🕵️")
    async def btn_cabra(self, button, inter):
        await self.processar_ataque(inter, "cabra")

    @disnake.ui.button(label="Jogar C4", style=disnake.ButtonStyle.danger, emoji="🧨")
    async def btn_c4(self, button, inter):
        await self.processar_ataque(inter, "c4")


class WorldBoss(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.boss_ativo = False
        self.boss_hp = 0
        self.boss_max_hp = 0
        self.dano_jogadores = {} # user_id: dano
        self.nomes_jogadores = {} # user_id: nome
        self.cooldowns = {} # user_id: tempo_liberacao
        self.fim_evento = 0
        self.canal_id = 1474153029690200105 # Canal principal
        self.mensagem_atual = None
        
        self.loop_boss_status.start()

    def cog_unload(self):
        self.loop_boss_status.cancel()

    def gerar_embed(self):
        tempo_restante = int(self.fim_evento)
        
        embed = disnake.Embed(
            title="🦍 ALERTA DE AMEAÇA: GORILA MUTANTE!",
            description=(
                "Uma aberração invadiu a selva e está a caminho do banco!\n"
                "Usem os botões abaixo para atacar. Trabalhem em equipe!\n\n"
                f"**Vida do Monstro:**\n{gerar_barra_hp(self.boss_hp, self.boss_max_hp)}"
            ),
            color=disnake.Color.dark_red()
        )
        
        if self.dano_jogadores:
            rank = sorted(self.dano_jogadores.items(), key=lambda x: x[1], reverse=True)
            linhas_rank = []
            for i, (uid, dmg) in enumerate(rank[:5]):
                medalha = ["🥇", "🥈", "🥉", "🏅", "🏅"][i]
                linhas_rank.append(f"{medalha} **{self.nomes_jogadores[uid]}** — `{dmg} DMG`")
            
            embed.add_field(name="🏆 Maiores Causadores de Dano", value="\n".join(linhas_rank), inline=False)
        else:
            embed.add_field(name="🏆 Ranking", value="Ninguém atacou ainda!", inline=False)

        embed.set_footer(text="C4 e Pés de Cabra são consumidos ao usar! Pets gastam 20% de fome.")
        embed.add_field(name="⏰ Fuga da Fera", value=f"<t:{tempo_restante}:R>", inline=False)
        
        return embed

    async def atualizar_mensagem(self):
        if not self.boss_ativo or not self.mensagem_atual: return
        try:
            embed = self.gerar_embed()
            await self.mensagem_atual.edit(embed=embed, view=BossView(self))
        except:
            pass

    # ── LOOP: A CADA 10 MINUTOS, REENVIA A MENSAGEM PARA NÃO SUMIR ──
    @tasks.loop(minutes=10.0)
    async def loop_boss_status(self):
        if not self.boss_ativo: return

        agora = time.time()
        if agora >= self.fim_evento:
            canal = self.bot.get_channel(self.canal_id)
            await self.encerrar_boss(vitoria=False, canal=canal)
            return

        canal = self.bot.get_channel(self.canal_id)
        if canal and self.mensagem_atual:
            try:
                await self.mensagem_atual.delete()
            except:
                pass
            
            embed = self.gerar_embed()
            self.mensagem_atual = await canal.send(content="@everyone ⚠️ **LEMBRETE: O GORILA AINDA ESTÁ VIVO!**", embed=embed, view=BossView(self))

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def forcar_boss(self, ctx):
        if self.boss_ativo:
            return await ctx.send("❌ Já existe um Boss ativo!")
        await ctx.send("⚠️ **ADMIN:** Invocando o Gorila Mutante!")
        await self.iniciar_boss(ctx.channel)

    async def iniciar_boss(self, canal=None):
        self.boss_ativo = True
        self.boss_max_hp = BOSS_MAX_HP
        self.boss_hp = BOSS_MAX_HP
        self.dano_jogadores = {}
        self.nomes_jogadores = {}
        self.cooldowns = {}
        self.fim_evento = time.time() + 3600 # 1 hora
        
        canal_envio = canal or self.bot.get_channel(self.canal_id)
        if canal_envio:
            embed = self.gerar_embed()
            self.mensagem_atual = await canal_envio.send(content="@everyone", embed=embed, view=BossView(self))

    async def encerrar_boss(self, vitoria: bool, canal):
        self.boss_ativo = False
        
        if self.mensagem_atual:
            try:
                view_desativada = BossView(self)
                for child in view_desativada.children:
                    child.disabled = True
                await self.mensagem_atual.edit(view=view_desativada)
            except: pass

        if vitoria:
            rank = sorted(self.dano_jogadores.items(), key=lambda x: x[1], reverse=True)
            if not rank: return

            mvp_id, mvp_dmg = rank[0]
            mvp_nome = self.nomes_jogadores[mvp_id]

            # Recompensa o MVP
            user_mvp = db.get_user_data(mvp_id)
            if user_mvp:
                saldo = db.parse_float(user_mvp['data'][2])
                db.update_value(user_mvp['row'], 3, saldo + 5000.0)
                inv = [i.strip() for i in str(user_mvp['data'][5]).split(",") if i.strip() and i.strip() != "Nenhum"]
                inv.append("Relíquia Ancestral 🔒")
                db.update_value(user_mvp['row'], 6, ", ".join(inv))

            # Recompensa os participantes
            for uid, dmg in rank[1:]:
                u_data = db.get_user_data(uid)
                if u_data:
                    saldo = db.parse_float(u_data['data'][2])
                    db.update_value(u_data['row'], 3, saldo + 1000.0)
                    inv = [i.strip() for i in str(u_data['data'][5]).split(",") if i.strip() and i.strip() != "Nenhum"]
                    inv.append("Baú do Caçador 🔒")
                    db.update_value(u_data['row'], 6, ", ".join(inv))

            embed = disnake.Embed(
                title="🏆 O GORILA CAIU!",
                description=(
                    "A selva está salva graças ao esforço conjunto de vocês!\n\n"
                    f"🥇 **MVP da Batalha:** {mvp_nome} (`{mvp_dmg} DMG`)\n"
                    "└ *Prêmio: 5.000 MC + Relíquia Ancestral 🔒*\n\n"
                    "🏅 **Outros Participantes:**\n"
                    "└ *Prêmio: 1.000 MC + Baú do Caçador 🔒*"
                ),
                color=disnake.Color.green()
            )
            await canal.send(embed=embed)

        else:
            # Derrota (Tempo acabou)
            embed = disnake.Embed(
                title="💀 A FERA VENCEU!",
                description=(
                    "Vocês foram lentos demais! O Gorila Mutante arrombou os cofres do banco "
                    "e causou um prejuízo severo à economia da selva.\n\n"
                    "💸 **Punição Global:** O banco cobrou uma taxa de emergência de todos os jogadores para cobrir os danos!"
                ),
                color=disnake.Color.dark_red()
            )
            await canal.send(embed=embed)
            
            # Punição (Remove MC do banco se quiser implementar no futuro)
            # Para não ser TÃO cruel no começo, vamos apenas deixar o susto. 
            # Se quiser subtrair dinheiro, precisaria iterar sobre todos os usuários do GSheet, o que pode dar limite na API.

def setup(bot):
    bot.add_cog(WorldBoss(bot))