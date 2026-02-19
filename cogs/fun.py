import disnake
from disnake.ext import commands
import database as db
import asyncio

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        """Restringe comandos de diversão/castigo ao canal #🐒・conguitos."""
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, use o canal {mencao} para aplicar castigos e maldades!")
            raise commands.CommandError("Canal de diversão incorreto.")

    @commands.command()
    async def castigo(self, ctx, tipo: str, tempo: int, vitima: disnake.Member):
        """
        Tipos: mudo, surdo, surdomudo
        Tempos: 1, 5, 10 (minutos)
        Exemplo: !castigo mudo 1 @Amigo
        """
        ladrão_id = str(ctx.author.id)
        user = db.get_user_data(ladrão_id)

        if not user:
            return await ctx.send(f"❌ {ctx.author.mention}, você não tem conta! Use `!trabalhar`.")

        # Tabela de Preços
        precos = {
            "mudo": {1: 1500, 5: 7500, 10: 15000},
            "surdo": {1: 1500, 5: 7500, 10: 15000},
            "surdomudo": {1: 3000, 5: 15000, 10: 30000}
        }

        tipo = tipo.lower()
        if tipo not in precos or tempo not in precos[tipo]:
            return await ctx.send(f"❌ {ctx.author.mention}, opção inválida! Escolha entre `mudo`, `surdo` ou `surdomudo` e tempos de `1`, `5` ou `10` minutos.")

        custo = precos[tipo][tempo]
        saldo_atual = int(user['data'][2])

        if saldo_atual < custo:
            return await ctx.send(f"❌ {ctx.author.mention}, você é um macaco pobre! Esse castigo custa **{custo} conguitos**.")

        if not vitima.voice:
            return await ctx.send(f"❌ {vitima.mention} precisa estar em um canal de voz para ser castigado!")

        # Cobrando o valor
        db.update_value(user['row'], 3, saldo_atual - custo)

        # Aplicando o Castigo
        try:
            segundos = tempo * 60
            if tipo == "mudo":
                await vitima.edit(mute=True, reason=f"Castigo de {ctx.author.name}")
                msg = f"🔇 {vitima.mention} foi silenciado por {tempo} minuto(s)!"
            
            elif tipo == "surdo":
                await vitima.edit(deafen=True, reason=f"Castigo de {ctx.author.name}")
                msg = f"🎧 {vitima.mention} foi ensurdecido por {tempo} minuto(s)!"
            
            elif tipo == "surdomudo":
                await vitima.edit(mute=True, deafen=True, reason=f"Castigo de {ctx.author.name}")
                msg = f"🤐 **CASTIGO TOTAL!** {vitima.mention} ficou mudo e surdo por {tempo} minuto(s)!"

            await ctx.send(f"💸 {ctx.author.mention} pagou **{custo} conguitos** e... {msg}")

            # Aguarda o tempo do castigo
            await asyncio.sleep(segundos)

            # Retirando o Castigo
            try:
                if vitima.voice: 
                    await vitima.edit(mute=False, deafen=False)
                    await ctx.send(f"✅ O castigo de {vitima.mention} acabou!")
            except:
                pass 

        except disnake.Forbidden:
            await ctx.send(f"❌ {ctx.author.mention}, eu não tenho permissão de 'Silenciar/Ensurdecer Membros' para fazer isso!")
        except Exception as e:
            print(f"Erro no castigo: {e}")

    @commands.command(name="desconectar", aliases=["kick", "tchau"])
    async def desconectar_usuario(self, ctx, vitima: disnake.Member):
        """Expulsa um usuário do canal de voz."""
        ladrão_id = str(ctx.author.id)
        user = db.get_user_data(ladrão_id)

        if not user:
            return await ctx.send(f"❌ {ctx.author.mention}, você não tem conta! Use `!trabalhar`.")

        custo = 5000
        saldo_atual = int(user['data'][2])

        if saldo_atual < custo:
            return await ctx.send(f"❌ {ctx.author.mention}, você precisa de **{custo} conguitos** para expulsar alguém da call!")

        if not vitima.voice:
            return await ctx.send(f"❌ {vitima.mention} não está em nenhum canal de voz no momento.")

        db.update_value(user['row'], 3, saldo_atual - custo)

        try:
            await vitima.move_to(None, reason=f"Expulso por {ctx.author.name}")
            await ctx.send(f"👟 {ctx.author.mention} pagou **{custo} conguitos** e deu um chute no traseiro de {vitima.mention}! Tchau, tchau!")

        except disnake.Forbidden:
            await ctx.send(f"❌ Eu não tenho a permissão 'Mover Membros' para desconectar o {vitima.mention}!")
        except Exception as e:
            await ctx.send(f"⚠️ Ocorreu um erro ao tentar desconectar: {e}")

def setup(bot):
    bot.add_cog(Fun(bot))