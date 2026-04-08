import disnake
from disnake.ext import commands, tasks
import database as db
import random
import asyncio
import time

# canais onde os eventos (airdrop e purge) podem cair
CANAIS_EVENTOS = [1474153029690200105]

class AirdropView(disnake.ui.View):
    def __init__(self, caixa_nome: str):
        super().__init__(timeout=300)
        self.caixa_nome   = caixa_nome
        self.reivindicado = False
        self.message: disnake.Message = None  # preenchido após o envio

    @disnake.ui.button(label="SAQUEAR", style=disnake.ButtonStyle.success, emoji="🥷")
    async def saquear(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if self.reivindicado:
            return await inter.response.send_message("❌ Tarde demais! Outro macaco já levou esse suprimento.", ephemeral=True)

        user_id = str(inter.author.id)
        user    = db.get_user_data(user_id)

        if not user:
            return await inter.response.send_message("❌ Você precisa de uma conta! Use `!trabalhar`.", ephemeral=True)

        # Verificação especial para Gaiola: usuário não pode ter mascote ativo
        if self.caixa_nome == "Gaiola Misteriosa":
            tipo_mascote, fome = db.get_mascote(user)
            if tipo_mascote:
                return await inter.response.send_message(
                    "❌ Você já tem um mascote! Liberte-o antes de pegar outra gaiola.",
                    ephemeral=True
                )

        self.reivindicado = True
        self.stop()

        inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
        inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
        inv_list.append(self.caixa_nome)
        db.update_value(user['row'], 6, ", ".join(inv_list))

        nome_curto = self.caixa_nome.split()[0].lower()
        if self.caixa_nome == "Gaiola Misteriosa":
            nome_curto = "gaiola"

        embed = inter.message.embeds[0]
        embed.title = "🏁 AIRDROP REIVINDICADO"
        embed.description = (
            f"```fix\nCARGA CAPTURADA COM SUCESSO\n```\n"
            f"🥷 **{inter.author.mention}** interceptou o suprimento e guardou o/a **{self.caixa_nome}** no inventário!\n\n"
            f"*(Dica: Use `!abrir {nome_curto}` para ver o que tem dentro!)*"
        )
        embed.color = disnake.Color.dark_grey()

        button.disabled = True
        button.label    = "SAQUEADO"
        button.style    = disnake.ButtonStyle.secondary

        await inter.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        """Expira visualmente o airdrop quando ninguém saqueou no tempo."""
        if self.reivindicado:
            return  # já foi saqueado, não precisa fazer nada

        for child in self.children:
            child.disabled = True
            child.label    = "EXPIRADO"
            child.style    = disnake.ButtonStyle.danger
            child.emoji    = None

        try:
            if self.message:
                embed = self.message.embeds[0]
                embed.title       = "💨 AIRDROP PERDIDO"
                embed.description = (
                    "```diff\n- CARGA NÃO REIVINDICADA\n```\n"
                    "☁️ O suprimento se perdeu na selva — nenhum macaco foi rápido o suficiente.\n\n"
                    "*Fique ligado no próximo airdrop!*"
                )
                embed.color = disnake.Color.dark_red()
                await self.message.edit(embed=embed, view=self)
        except Exception:
            pass

class EventosGlobais(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Variáveis globais do Purge
        self.bot.purge_ativo = False
        self.bot.purge_end_time = 0
        
        self.airdrop_loop.start()
        self.purge_loop.start()

    def cog_unload(self):
        self.airdrop_loop.cancel()
        self.purge_loop.cancel()

    # ── EVENTO 1: AIRDROP ──────────────────────────────────────────────────
    @tasks.loop(minutes=30.0)
    async def airdrop_loop(self):
        if getattr(self.bot, 'purge_ativo', False): return # Sem airdrops durante o Purge
        
        # 20% de chance de passar o avião a cada 30 minutos
        if random.random() > 0.20:
            return

        canal = self.bot.get_channel(random.choice(CANAIS_EVENTOS))
        if not canal: return

        sorteio = random.random()
        if sorteio <= 0.02:    # 2% — lendário
            caixa  = "Relíquia Ancestral"
            cor    = disnake.Color.gold()
            header = "⭐ [ LENDÁRIO ] ⭐"
            visual = "✨ 🏺 ✨"
        elif sorteio <= 0.12:  # 10% — raro
            caixa  = "Baú do Caçador"
            cor    = disnake.Color.blue()
            header = "🔷 [ RARO ] 🔷"
            visual = "⛓️ 🪙 ⛓️"
        elif sorteio <= 0.17:  # 5% — mascote
            caixa  = "Gaiola Misteriosa"
            cor    = disnake.Color.dark_theme()
            header = "🐾 [ MASCOTE ] 🐾"
            visual = "⛓️ 🐾 ⛓️"
        else:                  # 83% — comum
            caixa  = "Caixote de Madeira"
            cor    = disnake.Color.from_rgb(139, 69, 19)
            header = "📦 [ COMUM ] 📦"
            visual = "🪵 📦 🪵"

        layout_visual = (
            f"```py\n"
            f"{header}\n"
            f"STATUS: CARGA EM QUEDA\n"
            f"```\n"
            f"☁️ ☁️ ☁️ ☁️ ☁️ ☁️ ☁️\n"
            f"ㅤㅤㅤㅤ✈️\n"
            f"ㅤㅤㅤ 🪂\n"
            f"ㅤㅤ  {visual}\n"
            f"‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\n\n"
            f"📍 **Item Detectado:** `{caixa}`\n"
            f"👉 O primeiro a clicar no botão leva o loot!"
        )

        embed = disnake.Embed(title="✈️ INTERCEPÇÃO DE CARGA", description=layout_visual, color=cor)
        embed.set_footer(text="Radar Símio: Suprimentos detectados no setor.")

        view         = AirdropView(caixa)
        view.message = await canal.send(embed=embed, view=view)

    @airdrop_loop.before_loop
    async def before_airdrop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(random.randint(30, 120))

    @commands.command(name="forcar_airdrop")
    @commands.has_permissions(administrator=True)
    async def forcar_airdrop(self, ctx):
        sorteio = random.random()
        if sorteio <= 0.02:   caixa = "Relíquia Ancestral"
        elif sorteio <= 0.12: caixa = "Baú do Caçador"
        elif sorteio <= 0.17: caixa = "Gaiola Misteriosa"
        else:                 caixa = "Caixote de Madeira"

        view         = AirdropView(caixa)
        view.message = await ctx.send(f"⚠️ **ADMIN:** Forçando queda de **{caixa}**!", view=view)

    # ── EVENTO 2: A HORA DO PURGE ──────────────────────────────────────────
    @tasks.loop(minutes=60.0)
    async def purge_loop(self):
        # 10% de chance de acontecer a cada hora
        if random.random() > 0.10: return
        if getattr(self.bot, 'purge_ativo', False): return
        await self._iniciar_purge()

    @purge_loop.before_loop
    async def before_purge(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(random.randint(60, 300))

    @commands.command(name="forcar_purge")
    @commands.has_permissions(administrator=True)
    async def forcar_purge(self, ctx):
        if getattr(self.bot, 'purge_ativo', False):
            return await ctx.send("❌ O Purge já está ativo!")
        await ctx.send("⚠️ **ADMIN:** Iniciando A Hora do Purge manualmente!")
        await self._iniciar_purge(ctx.channel)

    async def _iniciar_purge(self, canal_forçado=None):
        self.bot.purge_ativo = True
        self.bot.purge_end_time = time.time() + 1800  # Dura 30 minutos
        ts_fim_purge = int(self.bot.purge_end_time)

        canal = canal_forçado or self.bot.get_channel(random.choice(CANAIS_EVENTOS))
        
        if canal:
            embed = disnake.Embed(
                title="🚨 💀 A HORA DO PURGE COMEÇOU! 💀 🚨",
                description=(
                    "**As leis da selva foram suspensas!**\n\n"
                    "🔨 `!trabalhar` **está bloqueado.** O trabalho honesto não rende nada agora.\n"
                    "🥷 `!roubar` **tem cooldown de apenas 5 minutos** e a multa por falha foi zerada!\n\n"
                    "Protejam as suas carteiras, comprem escudos e rezem pelos seus pets. "
                    "Que o caos comece!\n\n"
                    f"⏰ **O purge termina** <t:{ts_fim_purge}:R>."
                ),
                color=disnake.Color.dark_red()
            )
            await canal.send(content="@here", embed=embed)

        # Espera 30 minutos sem travar o bot
        await asyncio.sleep(1800)

        # Encerra o Purge
        self.bot.purge_ativo = False
        if canal:
            embed_fim = disnake.Embed(
                title="🌅 O SOL NASCEU NA SELVA",
                description="A Hora do Purge terminou. As leis voltaram ao normal. Recolham os feridos e voltem ao trabalho honesto.",
                color=disnake.Color.green()
            )
            await canal.send(embed=embed_fim)

def setup(bot):
    bot.add_cog(EventosGlobais(bot))