import disnake
from disnake.ext import commands
import database as db
import random
import time

class Sabotagem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.amaldicoados = {}  # {user_id: timestamp de quando a maldição expira}

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, use as sabotagens no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    # ──────────────────────────────────────────────────────────────────────────
    #  !impostor
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command()
    async def impostor(self, ctx, alvo: disnake.Member = None, *, mensagem: str = None):
        if alvo is None or mensagem is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!impostor @usuario <mensagem falsa>`")
        if alvo.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, não pode ser impostor de si mesmo!")
        if alvo.bot:
            return await ctx.send(f"🤖 {ctx.author.mention}, não pode falsificar a identidade de um bot!")

        custo = 500.0
        debitado = False
        try:
            user = db.get_user_data(str(ctx.author.id))
            saldo = db.parse_float(user['data'][2]) if user else 0.0
            if not user or saldo < custo:
                return await ctx.send(f"❌ {ctx.author.mention}, você precisa de **{custo:.2f} MC**!")

            db.update_value(user['row'], 3, round(saldo - custo, 2))
            debitado = True

            try:
                await ctx.message.delete()
            except disnake.Forbidden:
                pass

            webhook = await ctx.channel.create_webhook(name="Impostor_Temporario")
            try:
                await webhook.send(
                    content=mensagem,
                    username=alvo.display_name,
                    avatar_url=alvo.display_avatar.url
                )
                ctx._missao_ok = True  # missão: usar !impostor com sucesso
            finally:
                await webhook.delete()

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !impostor de {ctx.author}: {e}")
            if debitado:
                try:
                    user_ref = db.get_user_data(str(ctx.author.id))
                    if user_ref:
                        saldo_ref = db.parse_float(user_ref['data'][2])
                        db.update_value(user_ref['row'], 3, round(saldo_ref + custo, 2))
                        await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Os **{custo:.2f} MC** foram devolvidos.")
                        return
                except Exception:
                    pass
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ──────────────────────────────────────────────────────────────────────────
    #  !amaldicoar
    # ──────────────────────────────────────────────────────────────────────────

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
                return await ctx.send(
                    f"❌ {ctx.author.mention}, você precisa de **{custo:.2f} MC** para conjurar a Maldição Símia!"
                )

            db.update_value(user['row'], 3, round(saldo - custo, 2))
            tempo_fim = int(time.time() + 60)
            self.amaldicoados[alvo.id] = tempo_fim

            ctx._missao_ok = True  # missão: amaldiçoar alguém

            embed = disnake.Embed(
                title="🍌 MALDIÇÃO SÍMIA CONJURADA!",
                description=(
                    f"{ctx.author.mention} amaldiçoou {alvo.mention}.\n\n"
                    f"Até <t:{tempo_fim}:R>, ele não conseguirá falar direito!"
                ),
                color=disnake.Color.dark_green()
            )
            await ctx.send(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !amaldicoar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    # ──────────────────────────────────────────────────────────────────────────
    #  Listener: distorce mensagens de amaldiçoados
    # ──────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message):
        # ignora bots e comandos para não interferir no funcionamento normal
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