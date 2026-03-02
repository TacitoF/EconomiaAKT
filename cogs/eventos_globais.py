import disnake
from disnake.ext import commands, tasks
import database as db
import random
import asyncio

# Configuração: IDs dos canais onde o Airdrop pode cair
# Recomendo colocar o ID do canal '🐒・conguitos' ou '🎰・akbet'
CANAIS_AIRDROP = [1474153029690200105] # Substitua pelos IDs reais dos seus canais

class AirdropView(disnake.ui.View):
    """Botão para saquear o airdrop."""
    def __init__(self, caixa_nome: str):
        super().__init__(timeout=300) # O airdrop fica disponível por 5 minutos
        self.caixa_nome = caixa_nome
        self.reivindicado = False

    @disnake.ui.button(label="📦 SAQUEAR", style=disnake.ButtonStyle.success, emoji="🥷")
    async def saquear(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if self.reivindicado:
            return await inter.response.send_message("❌ Tarde demais! Outro macaco já levou esse suprimento.", ephemeral=True)

        user_id = str(inter.author.id)
        user = db.get_user_data(user_id)
        
        if not user:
            return await inter.response.send_message("❌ Você precisa de uma conta para saquear! Use `!trabalhar` primeiro.", ephemeral=True)

        self.reivindicado = True
        self.stop()

        # Adiciona a caixa ao inventário
        inv_str = str(user['data'][5]) if len(user['data']) > 5 else ""
        inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]
        inv_list.append(self.caixa_nome)
        db.update_value(user['row'], 6, ", ".join(inv_list))

        # Atualiza a mensagem original
        embed = inter.message.embeds[0]
        embed.title = "📦 AIRDROP SAQUEADO!"
        embed.description = f"🥷 **{inter.author.mention}** foi o mais rápido da selva e capturou o **{self.caixa_nome}**!"
        embed.color = disnake.Color.dark_grey()
        embed.set_footer(text="Fique atento, outro avião pode passar a qualquer momento...")
        
        button.disabled = True
        button.label = "SAQUEADO"
        button.style = disnake.ButtonStyle.secondary

        await inter.response.edit_message(embed=embed, view=self)

class EventosGlobais(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.airdrop_loop.start() # Inicia o loop ao carregar o bot

    def cog_unload(self):
        self.airdrop_loop.cancel() # Para o loop se o cog for descarregado

    @tasks.loop(minutes=30.0) # Verifica a cada 30 minutos
    async def airdrop_loop(self):
        """Task que decide aleatoriamente se um airdrop vai cair."""
        # Chance de 25% de ocorrer um airdrop a cada 30 minutos
        if random.random() > 0.25:
            return

        # Escolhe um canal aleatório da lista
        canal_id = random.choice(CANAIS_AIRDROP)
        canal = self.bot.get_channel(canal_id)
        if not canal:
            return

        # Define qual caixa vai cair (mesma raridade do sistema anterior)
        sorteio = random.random()
        if sorteio <= 0.05: # 5% Relíquia
            caixa = "Relíquia Ancestral"
            cor = disnake.Color.gold()
            msg_hura = "🚨 UM TESOURO LENDÁRIO ESTÁ CAINDO DO CÉU!"
        elif sorteio <= 0.20: # 20% Baú
            caixa = "Baú do Caçador"
            cor = disnake.Color.blue()
            msg_hura = "✈️ Um carregamento tático foi avistado!"
        else: # 80% Caixote
            caixa = "Caixote de Madeira"
            cor = disnake.Color.from_rgb(139, 69, 19)
            msg_hura = "📦 Um caixote de suprimentos caiu na mata!"

        embed = disnake.Embed(
            title="✈️ AIRDROP DE CONTRABANDO!",
            description=(
                f"{msg_hura}\n\n"
                f"Item: **{caixa}**\n"
                "Status: **Aguardando Saque**\n\n"
                "O primeiro macaco a clicar no botão abaixo leva o prêmio para o inventário!"
            ),
            color=cor
        )
        embed.set_image(url="https://i.imgur.com/vHq0A6S.png") # Sugestão: Uma imagem de paraquedas/caixa
        embed.set_footer(text="Ação rápida é a lei da selva.")

        view = AirdropView(caixa)
        await canal.send(embed=embed, view=view)

    @airdrop_loop.before_loop
    async def before_airdrop(self):
        await self.bot.wait_until_ready()
        # Espera um tempo aleatório inicial para não dropar logo que o bot liga
        await asyncio.sleep(random.randint(60, 600))

    @commands.command(name="forcar_airdrop")
    @commands.has_permissions(administrator=True)
    async def forcar_airdrop(self, ctx):
        """[ADMIN] Força a queda de um airdrop imediato para testes."""
        # Reutiliza a lógica do sorteio
        sorteio = random.random()
        if sorteio <= 0.10: caixa = "Relíquia Ancestral"
        elif sorteio <= 0.40: caixa = "Baú do Caçador"
        else: caixa = "Caixote de Madeira"
        
        view = AirdropView(caixa)
        embed = disnake.Embed(
            title="✈️ AIRDROP FORÇADO PELO ADM!",
            description=f"Um carregamento de **{caixa}** caiu! Corram!",
            color=disnake.Color.red()
        )
        await ctx.send(embed=embed, view=view)

def setup(bot):
    bot.add_cog(EventosGlobais(bot))