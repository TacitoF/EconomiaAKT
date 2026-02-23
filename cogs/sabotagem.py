import disnake
from disnake.ext import commands
import database as db
import random
import time

class Sabotagem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Dicionário para guardar quem está amaldiçoado: {ID_DO_USUARIO: TEMPO_FINAL_EM_SEGUNDOS}
        self.amaldicoados = {}

    @commands.command()
    async def impostor(self, ctx, alvo: disnake.Member = None, *, mensagem: str = None):
        """Paga 500 C para mandar uma mensagem se passando por outro macaco."""
        # MENSAGEM DE AJUDA
        if alvo is None or mensagem is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, formato incorreto!\nUse: `!impostor @usuario <mensagem falsa>`")

        custo = 500.0

        if alvo.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, você não pode ser impostor de si mesmo!")
        
        if alvo.bot:
            return await ctx.send(f"🤖 {ctx.author.mention}, você não pode falsificar a identidade de um bot!")

        user = db.get_user_data(str(ctx.author.id))
        if not user or float(user['data'][2]) < custo:
            return await ctx.send(f"❌ {ctx.author.mention}, você precisa de **{custo:.2f} C** para comprar uma identidade falsa!")

        # Cobra o valor
        db.update_value(user['row'], 3, round(float(user['data'][2]) - custo, 2))

        # Apaga a mensagem original de quem usou o comando para não deixar rastros
        try:
            await ctx.message.delete()
        except disnake.Forbidden:
            pass # Se o bot não tiver permissão de apagar mensagens, ele ignora

        # Cria o Webhook temporário, envia a mensagem falsa e deleta o Webhook
        webhook = await ctx.channel.create_webhook(name="Impostor_Temporario")
        try:
            await webhook.send(
                content=mensagem,
                username=alvo.display_name,
                avatar_url=alvo.display_avatar.url
            )
        finally:
            await webhook.delete()

    @commands.command(aliases=["maldicao", "macaco"])
    async def amaldicoar(self, ctx, alvo: disnake.Member = None):
        """Paga 500 C para amaldiçoar o chat do alvo com sons de macaco por 1 minuto."""
        # MENSAGEM DE AJUDA
        if alvo is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, você esqueceu de dizer quem vai amaldiçoar!\nUse: `!amaldicoar @usuario`")

        custo = 500.0

        if alvo.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, não jogue mandingas em si mesmo!")
        
        if alvo.bot:
            return await ctx.send(f"🤖 A maldição não afeta máquinas!")

        user = db.get_user_data(str(ctx.author.id))
        if not user or float(user['data'][2]) < custo:
            return await ctx.send(f"❌ {ctx.author.mention}, você precisa de **{custo:.2f} C** para conjurar a Maldição Símia!")

        # Cobra o valor em decimais
        db.update_value(user['row'], 3, round(float(user['data'][2]) - custo, 2))

        # Adiciona o alvo ao dicionário de amaldiçoados por 60 segundos (1 minuto)
        tempo_fim = int(time.time() + 60)
        self.amaldicoados[alvo.id] = tempo_fim

        embed = disnake.Embed(
            title="🍌 MALDIÇÃO SÍMIA CONJURADA!",
            description=f"Magia negra na selva! {ctx.author.mention} amaldiçoou {alvo.mention}.\n\nAté <t:{tempo_fim}:R>, ele não conseguirá falar direito!",
            color=disnake.Color.dark_green()
        )
        await ctx.send(embed=embed)

    # O "listener" que escuta todas as mensagens do servidor
    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignora bots e ignora comandos (para não quebrar o bot enquanto o cara tá amaldiçoado)
        if message.author.bot or message.content.startswith('!'):
            return

        # Verifica se o autor está na lista de amaldiçoados
        if message.author.id in self.amaldicoados:
            tempo_final = self.amaldicoados[message.author.id]
            
            # Se o tempo já passou, remove a maldição e deixa a mensagem passar normal
            if time.time() > tempo_final:
                del self.amaldicoados[message.author.id]
                return

            # Se ainda estiver amaldiçoado, a magia acontece
            try:
                # Apaga a mensagem original
                await message.delete()
            except disnake.Forbidden:
                pass # Se o bot não tiver permissão de apagar, ele ignora

            # Pega as palavras que o cara tentou digitar
            palavras = message.content.split()
            nova_mensagem = []
            sons = ["UH", "AH", "🍌", "🐒", "UHH AH AH"]

            # Intercala as palavras dele com sons de macaco
            for p in palavras:
                nova_mensagem.append(p)
                if random.random() < 0.35: # 35% de chance de colocar um ruído de macaco após cada palavra
                    nova_mensagem.append(f"**{random.choice(sons)}**")
            
            # Se ele mandou só uma imagem sem texto, força um som de macaco
            if not nova_mensagem:
                nova_mensagem = [f"**{random.choice(sons)}**"]

            texto_final = " ".join(nova_mensagem)

            # Reenvia usando o Webhook com o nome e foto da vítima
            try:
                webhook = await message.channel.create_webhook(name="Maldicao_Simia")
                try:
                    await webhook.send(
                        content=texto_final,
                        username=message.author.display_name,
                        avatar_url=message.author.display_avatar.url
                    )
                finally:
                    await webhook.delete()
            except disnake.Forbidden:
                pass # Se o bot não tiver permissão de gerenciar webhooks, ignora

def setup(bot):
    bot.add_cog(Sabotagem(bot))