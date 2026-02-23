import disnake
from disnake.ext import commands
import database as db
import random
import time

class Sabotagem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.amaldicoados = {}  # {user_id: timestamp_fim}

    @commands.command()
    async def impostor(self, ctx, alvo: disnake.Member = None, *, mensagem: str = None):
        if alvo is None or mensagem is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!impostor @usuario <mensagem falsa>`")
        if alvo.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, não pode ser impostor de si mesmo!")
        if alvo.bot:
            return await ctx.send(f"🤖 {ctx.author.mention}, não pode falsificar a identidade de um bot!")

        custo = 500.0
        try:
            user = db.get_user_data(str(ctx.author.id))
            saldo = db.parse_float(user['data'][2]) if user else 0.0
            if not user or saldo < custo:
                return await ctx.send(f"❌ {ctx.author.mention}, você precisa de **{custo:.2f} C**!")

            db.update_value(user['row'], 3, round(saldo - custo, 2))

            try:
                await ctx.message.delete()
            except disnake.Forbidden:
                pass

            webhook = await ctx.channel.create_webhook(name="Impostor_Temporario")
            try:
                await webhook.send(content=mensagem, username=alvo.display_name, avatar_url=alvo.display_avatar.url)
            finally:
                await webhook.delete()

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !impostor de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    @commands.command(aliases=["maldicao", "macaco"])
    async def amaldicoar(self, ctx, alvo: disnake.Member = None):
        if alvo is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!amaldicoar @usuario`")
        if alvo.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, não jogue mandingas em si mesmo!")
        if alvo.bot:
            return await ctx.send("🤖 A maldição não afeta máquinas!")

        custo = 500.0
        try:
            user = db.get_user_data(str(ctx.author.id))
            saldo = db.parse_float(user['data'][2]) if user else 0.0
            if not user or saldo < custo:
                return await ctx.send(f"❌ {ctx.author.mention}, você precisa de **{custo:.2f} C** para conjurar a Maldição Símia!")

            db.update_value(user['row'], 3, round(saldo - custo, 2))
            tempo_fim = int(time.time() + 60)
            self.amaldicoados[alvo.id] = tempo_fim

            embed = disnake.Embed(
                title="🍌 MALDIÇÃO SÍMIA CONJURADA!",
                description=f"{ctx.author.mention} amaldiçoou {alvo.mention}.\n\nAté <t:{tempo_fim}:R>, ele não conseguirá falar direito!",
                color=disnake.Color.dark_green()
            )
            await ctx.send(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !amaldicoar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignora bots e comandos para não interferir com o funcionamento normal do bot
        if message.author.bot or message.content.startswith('!'):
            return

        if message.author.id not in self.amaldicoados:
            return

        tempo_final = self.amaldicoados[message.author.id]
        if time.time() > tempo_final:
            del self.amaldicoados[message.author.id]
            return

        try:
            await message.delete()
        except disnake.Forbidden:
            pass

        palavras = message.content.split()
        sons = ["UH", "AH", "🍌", "🐒", "UHH AH AH"]
        nova_mensagem = []
        for p in palavras:
            nova_mensagem.append(p)
            if random.random() < 0.35:
                nova_mensagem.append(f"**{random.choice(sons)}**")

        if not nova_mensagem:
            nova_mensagem = [f"**{random.choice(sons)}**"]

        try:
            webhook = await message.channel.create_webhook(name="Maldicao_Simia")
            try:
                await webhook.send(
                    content=" ".join(nova_mensagem),
                    username=message.author.display_name,
                    avatar_url=message.author.display_avatar.url
                )
            finally:
                await webhook.delete()
        except disnake.Forbidden:
            pass

def setup(bot):
    bot.add_cog(Sabotagem(bot))