import disnake
from disnake.ext import commands, tasks
import database as db
import random
import time
import asyncio
from datetime import datetime, timezone, timedelta

# Configurações de Dano e Cooldown
BOSS_MAX_HP = 10000
COOLDOWN_ATAQUE = 120 # 2 minutos entre qualquer ataque

# Fuso horário de Brasília (UTC-3)
BRT = timezone(timedelta(hours=-3))

# Janela de spawn diário: entre 13h e 18h BRT
# O boss spawna em um horário aleatório dentro dessa janela, uma vez por dia.
SPAWN_HORA_MIN = 13
SPAWN_HORA_MAX = 18

def gerar_barra_hp(hp_atual, hp_max):
    tamanho = 15
    preenchido = int((hp_atual / hp_max) * tamanho)
    vazio = tamanho - preenchido
    return f"[{'🟥' * preenchido}{'⬛' * vazio}] {hp_atual}/{hp_max} HP"

# ── FUNÇÃO MESTRA PARA CONSUMIR ITENS (IGNORA O CADEADO) ──
def consumir_item(user_row: int, inv_list: list, nome_base: str) -> bool:
    """Verifica se o usuário tem o item (com ou sem 🔒) e consome-o."""
    item_para_remover = None
    
    if nome_base in inv_list:
        item_para_remover = nome_base
    else:
        nome_vinculado = f"{nome_base} 🔒"
        if nome_vinculado in inv_list:
            item_para_remover = nome_vinculado

    if item_para_remover:
        inv_list.remove(item_para_remover)
        db.update_value(user_row, 6, ", ".join(inv_list) if inv_list else "Nenhum")
        return True
    return False

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
            ts_liberacao = int(cd_usuario)
            return await inter.response.send_message(f"⏳ Você está recuperando o fôlego! Tente de novo <t:{ts_liberacao}:R>.", ephemeral=True)

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
            inv = [i.strip() for i in str(user_db['data'][5]).split(",") if i.strip() and i.strip() != "Nenhum"]
            # Usa a função mestra para ignorar o cadeado
            if not consumir_item(user_db['row'], inv, "Pé de Cabra"):
                return await inter.response.send_message("❌ Você não tem um Pé de Cabra no inventário!", ephemeral=True)
            dano = random.randint(400, 600)
            msg_extra = "Você quebrou o Pé de Cabra nas costas do gorila!"

        elif tipo == "c4":
            inv = [i.strip() for i in str(user_db['data'][5]).split(",") if i.strip() and i.strip() != "Nenhum"]
            # Usa a função mestra para ignorar o cadeado
            if not consumir_item(user_db['row'], inv, "Carga de C4"):
                return await inter.response.send_message("❌ Você não tem uma Carga de C4 no inventário!", ephemeral=True)
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
        self._spawn_agendado = False  # garante um único spawn por dia
        
        self.loop_boss_status.start()
        self.loop_spawn_diario.start()

    def cog_unload(self):
        self.loop_boss_status.cancel()
        self.loop_spawn_diario.cancel()

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

    # ── LOOP: SPAWN DIÁRIO ENTRE 13H E 18H BRT ──────────────────────────────
    @tasks.loop(minutes=1.0)
    async def loop_spawn_diario(self):
        agora_brt = datetime.now(BRT)
        hora_atual = agora_brt.hour

        # Fora da janela de spawn → reseta a flag do dia para o próximo ciclo
        if hora_atual < SPAWN_HORA_MIN or hora_atual >= SPAWN_HORA_MAX:
            self._spawn_agendado = False
            return

        # Dentro da janela mas o boss já foi spawnado hoje (ou já está ativo)
        if self._spawn_agendado or self.boss_ativo:
            return

        # Sorteia um minuto aleatório dentro da janela para não spawnar sempre às 13h00 em ponto
        # A chance por minuto é distribuída ao longo dos 300 minutos da janela (13h–18h)
        if random.random() > (1 / 300):
            return

        self._spawn_agendado = True  # trava: não spawna duas vezes no mesmo dia
        canal = self.bot.get_channel(self.canal_id)
        await self.iniciar_boss(canal)

    @loop_spawn_diario.before_loop
    async def before_spawn_diario(self):
        await self.bot.wait_until_ready()

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
            self.mensagem_atual = await canal.send(content="@here ⚠️ **LEMBRETE: O GORILA AINDA ESTÁ VIVO!**", embed=embed, view=BossView(self))

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
            self.mensagem_atual = await canal_envio.send(content="@here", embed=embed, view=BossView(self))

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

            # Recompensa o MVP (somente item vinculado, sem MC)
            user_mvp = db.get_user_data(mvp_id)
            if user_mvp:
                inv = [i.strip() for i in str(user_mvp['data'][5]).split(",") if i.strip() and i.strip() != "Nenhum"]
                inv.extend(["Relíquia Ancestral 🔒", "Gaiola Misteriosa 🔒"])
                db.update_value(user_mvp['row'], 6, ", ".join(inv))

            # Recompensa os participantes (somente item vinculado, sem MC)
            for uid, dmg in rank[1:]:
                u_data = db.get_user_data(uid)
                if u_data:
                    inv = [i.strip() for i in str(u_data['data'][5]).split(",") if i.strip() and i.strip() != "Nenhum"]
                    inv.extend(["Baú do Caçador 🔒", "Caixote de Madeira 🔒"])
                    db.update_value(u_data['row'], 6, ", ".join(inv))

            embed = disnake.Embed(
                title="🏆 O GORILA CAIU!",
                description=(
                    "A selva está salva graças ao esforço conjunto de vocês!\n\n"
                    f"🥇 **MVP da Batalha:** {mvp_nome} (`{mvp_dmg} DMG`)\n"
                    "└ *Prêmio: 1x Relíquia Ancestral 🔒 + 1x Gaiola Misteriosa 🔒*\n\n"
                    "🏅 **Outros Participantes:**\n"
                    "└ *Prêmio: 1x Baú do Caçador 🔒 + 1x Caixote de Madeira 🔒*\n\n"
                    "⚠️ Os itens são **vinculados** — não podem ser vendidos ou trocados. Use-os para dominar a selva!"
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

def setup(bot):
    bot.add_cog(WorldBoss(bot))