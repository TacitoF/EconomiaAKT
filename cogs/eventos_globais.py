import disnake
from disnake.ext import commands, tasks
import database as db
import random
import asyncio

# Configuração: IDs dos canais onde o Airdrop pode cair
CANAIS_AIRDROP = [1474153029690200105] 

class AirdropView(disnake.ui.View):
    def __init__(self, caixa_nome: str):
        super().__init__(timeout=300)
        self.caixa_nome = caixa_nome
        self.reivindicado = False

    @disnake.ui.button(label="SAQUEAR", style=disnake.ButtonStyle.success, emoji="🥷")
    async def saquear(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if self.reivindicado:
            return await inter.response.send_message("❌ Tarde demais! Outro macaco já levou esse suprimento.", ephemeral=True)

        user_id = str(inter.author.id)
        user = db.get_user_data(user_id)
        
        if not user:
            return await inter.response.send_message("❌ Você precisa de uma conta! Use `!trabalhar`.", ephemeral=True)

        self.reivindicado = True
        self.stop()

        inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
        inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
        inv_list.append(self.caixa_nome)
        db.update_value(user['row'], 6, ", ".join(inv_list))

        # Adicionada a instrução de como abrir a caixa
        nome_curto = self.caixa_nome.split()[0] # Pega a primeira palavra (Caixote, Baú ou Relíquia)
        
        embed = inter.message.embeds[0]
        embed.title = "🏁 AIRDROP REIVINDICADO"
        embed.description = (
            f"```fix\nCARGA CAPTURADA COM SUCESSO\n```\n"
            f"🥷 **{inter.author.mention}** interceptou o suprimento e guardou o **{self.caixa_nome}** no inventário!\n\n"
            f"*(Dica: Use `!abrir {nome_curto}` para ver o que tem dentro!)*"
        )
        embed.color = disnake.Color.dark_grey()
        
        button.disabled = True
        button.label = "SAQUEADO"
        button.style = disnake.ButtonStyle.secondary

        await inter.response.edit_message(embed=embed, view=self)

class EventosGlobais(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.airdrop_loop.start()

    def cog_unload(self):
        self.airdrop_loop.cancel()

    @tasks.loop(minutes=30.0)
    async def airdrop_loop(self):
        # Reduzida a chance de passar o avião para 20%
        if random.random() > 0.20: 
            return

        canal = self.bot.get_channel(random.choice(CANAIS_AIRDROP))
        if not canal: return

        # Novas probabilidades mais difíceis
        sorteio = random.random()
        if sorteio <= 0.02: # Apenas 2% de chance para a Relíquia
            caixa = "Relíquia Ancestral"
            cor = disnake.Color.gold()
            header = "⭐ [ LENDÁRIO ] ⭐"
            visual = "✨ 🏺 ✨"
        elif sorteio <= 0.12: # 10% de chance para o Baú
            caixa = "Baú do Caçador"
            cor = disnake.Color.blue()
            header = "🔷 [ RARO ] 🔷"
            visual = "⛓️ 🪙 ⛓️"
        else: # 88% de chance para o Caixote comum
            caixa = "Caixote de Madeira"
            cor = disnake.Color.from_rgb(139, 69, 19)
            header = "📦 [ COMUM ] 📦"
            visual = "🪵 📦 🪵"

        # Criando um layout visual com emojis e blocos de código
        layout_visual = (
            f"```py\n"
            f"航 {header} 航\n"
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

        view = AirdropView(caixa)
        await canal.send(embed=embed, view=view)

    @airdrop_loop.before_loop
    async def before_airdrop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(random.randint(30, 120))

    @commands.command(name="forcar_airdrop")
    @commands.has_permissions(administrator=True)
    async def forcar_airdrop(self, ctx):
        # Utiliza o mesmo sistema de probabilidades para forçar o drop
        sorteio = random.random()
        if sorteio <= 0.02: caixa = "Relíquia Ancestral"
        elif sorteio <= 0.12: caixa = "Baú do Caçador"
        else: caixa = "Caixote de Madeira"
        
        view = AirdropView(caixa)
        await ctx.send(f"⚠️ **ADMIN:** Forçando queda de **{caixa}**!", view=view)

def setup(bot):
    bot.add_cog(EventosGlobais(bot))