import disnake
from disnake.ext import commands
import database as db
import asyncio

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, use o canal {mencao} para aplicar castigos!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command()
    async def castigo(self, ctx, tipo: str = None, tempo: int = None, vitima: disnake.Member = None):
        if tipo is None or tempo is None or vitima is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!castigo <mudo/surdo/surdomudo> <1/5/10> @usuario`")
        if vitima.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, você não pode castigar a si mesmo!")

        precos = {
            "mudo":      {1: 300.0,  5: 1500.0,  10: 3000.0},
            "surdo":     {1: 300.0,  5: 1500.0,  10: 3000.0},
            "surdomudo": {1: 600.0,  5: 3000.0,  10: 6000.0}
        }
        tipo = tipo.lower()
        if tipo not in precos or tempo not in precos[tipo]:
            return await ctx.send(f"❌ Opção inválida! Use: `mudo`, `surdo` ou `surdomudo` com tempos `1`, `5` ou `10` minutos.")

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send(f"❌ {ctx.author.mention}, você não tem conta!")

            custo = precos[tipo][tempo]
            saldo = db.parse_float(user['data'][2])
            if saldo < custo:
                return await ctx.send(f"❌ {ctx.author.mention}, esse castigo custa **{custo:.2f} MC**.")
            if not vitima.voice:
                return await ctx.send(f"❌ {vitima.mention} precisa estar em um canal de voz!")

            db.update_value(user['row'], 3, round(saldo - custo, 2))
            try:
                if tipo == "mudo":
                    await vitima.edit(mute=True, reason=f"Castigo de {ctx.author.name}")
                    msg = f"🔇 {vitima.mention} foi silenciado por {tempo} minuto(s)!"
                elif tipo == "surdo":
                    await vitima.edit(deafen=True, reason=f"Castigo de {ctx.author.name}")
                    msg = f"🎧 {vitima.mention} foi ensurdecido por {tempo} minuto(s)!"
                else:
                    await vitima.edit(mute=True, deafen=True, reason=f"Castigo de {ctx.author.name}")
                    msg = f"🤐 **CASTIGO TOTAL!** {vitima.mention} ficou mudo e surdo por {tempo} minuto(s)!"

                await ctx.send(f"💸 {ctx.author.mention} pagou **{custo:.2f} MC** e... {msg}")
                await asyncio.sleep(tempo * 60)

                try:
                    if vitima.voice:
                        await vitima.edit(mute=False, deafen=False)
                        await ctx.send(f"✅ O castigo de {vitima.mention} acabou!")
                except:
                    pass

            except disnake.Forbidden:
                db.update_value(user['row'], 3, round(saldo, 2))
                await ctx.send(f"❌ Sem permissão para silenciar/ensurdecer! O dinheiro foi devolvido.")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !castigo de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    @commands.command(name="desconectar", aliases=["kick", "tchau"])
    async def desconectar_usuario(self, ctx, vitima: disnake.Member = None):
        if vitima is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!desconectar @usuario`")
        if vitima.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, não pode expulsar a si mesmo da call!")

        custo = 1200.0
        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send(f"❌ {ctx.author.mention}, você não tem conta!")

            saldo = db.parse_float(user['data'][2])
            if saldo < custo:
                return await ctx.send(f"❌ {ctx.author.mention}, você precisa de **{custo:.2f} MC**!")
            if not vitima.voice:
                return await ctx.send(f"❌ {vitima.mention} não está em nenhum canal de voz.")

            db.update_value(user['row'], 3, round(saldo - custo, 2))
            try:
                await vitima.move_to(None, reason=f"Expulso por {ctx.author.name}")
                await ctx.send(f"👟 {ctx.author.mention} pagou **{custo:.2f} MC** e expulsou {vitima.mention} da call!")
            except disnake.Forbidden:
                db.update_value(user['row'], 3, round(saldo, 2))
                await ctx.send(f"❌ Sem permissão para mover membros! O dinheiro foi devolvido.")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !desconectar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(Fun(bot))