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
    async def castigo(self, ctx, tipo: str = None, tempo: int = None, vitima: disnake.Member = None):
        """
        Tipos: mudo, surdo, surdomudo
        Tempos: 1, 5, 10 (minutos)
        Exemplo: !castigo mudo 1 @Amigo
        """
        # MENSAGEM DE AJUDA
        if tipo is None or tempo is None or vitima is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, formato incorreto!\nUse: `!castigo <mudo/surdo/surdomudo> <1/5/10> @usuario`")

        if vitima.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, você não pode castigar a si mesmo! Procure ajuda médica.")

        ladrão_id = str(ctx.author.id)
        user = db.get_user_data(ladrão_id)

        if not user:
            return await ctx.send(f"❌ {ctx.author.mention}, você não tem conta! Use `!trabalhar`.")

        # Tabela de Preços Atualizada (Deflação e Float)
        precos = {
            "mudo": {1: 300.0, 5: 1500.0, 10: 3000.0},
            "surdo": {1: 300.0, 5: 1500.0, 10: 3000.0},
            "surdomudo": {1: 600.0, 5: 3000.0, 10: 6000.0}
        }

        tipo = tipo.lower()
        if tipo not in precos or tempo not in precos[tipo]:
            return await ctx.send(f"❌ {ctx.author.mention}, opção inválida! Escolha entre `mudo`, `surdo` ou `surdomudo` e tempos de `1`, `5` ou `10` minutos.")

        custo = precos[tipo][tempo]
        saldo_atual = float(user['data'][2])

        if saldo_atual < custo:
            return await ctx.send(f"❌ {ctx.author.mention}, você é um macaco pobre! Esse castigo custa **{custo:.2f} C**.")

        if not vitima.voice:
            return await ctx.send(f"❌ {vitima.mention} precisa estar em um canal de voz para ser castigado!")

        # Cobrando o valor
        db.update_value(user['row'], 3, round(saldo_atual - custo, 2))

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

            await ctx.send(f"💸 {ctx.author.mention} pagou **{custo:.2f} C** e... {msg}")

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
            # Reembolso se o bot não tiver permissão
            db.update_value(user['row'], 3, round(float(user['data'][2]) + custo, 2))
            await ctx.send(f"❌ {ctx.author.mention}, eu não tenho permissão de 'Silenciar/Ensurdecer Membros' para fazer isso! O seu dinheiro foi devolvido.")
        except Exception as e:
            print(f"Erro no castigo: {e}")

    @commands.command(name="desconectar", aliases=["kick", "tchau"])
    async def desconectar_usuario(self, ctx, vitima: disnake.Member = None):
        """Expulsa um usuário do canal de voz."""
        if vitima is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, formato incorreto!\nUse: `!desconectar @usuario`")

        if vitima.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, você não pode expulsar a si mesmo da call!")

        ladrão_id = str(ctx.author.id)
        user = db.get_user_data(ladrão_id)

        if not user:
            return await ctx.send(f"❌ {ctx.author.mention}, você não tem conta! Use `!trabalhar`.")

        # Custo atualizado
        custo = 1200.0
        saldo_atual = float(user['data'][2])

        if saldo_atual < custo:
            return await ctx.send(f"❌ {ctx.author.mention}, você precisa de **{custo:.2f} C** para expulsar alguém da call!")

        if not vitima.voice:
            return await ctx.send(f"❌ {vitima.mention} não está em nenhum canal de voz no momento.")

        db.update_value(user['row'], 3, round(saldo_atual - custo, 2))

        try:
            await vitima.move_to(None, reason=f"Expulso por {ctx.author.name}")
            await ctx.send(f"👟 {ctx.author.mention} pagou **{custo:.2f} C** e deu um chute no traseiro de {vitima.mention}! Tchau, tchau!")

        except disnake.Forbidden:
            # Reembolso se falhar
            db.update_value(user['row'], 3, round(float(user['data'][2]) + custo, 2))
            await ctx.send(f"❌ Eu não tenho a permissão 'Mover Membros' para desconectar o {vitima.mention}! Seu dinheiro foi devolvido.")
        except Exception as e:
            await ctx.send(f"⚠️ Ocorreu um erro ao tentar desconectar: {e}")

def setup(bot):
    bot.add_cog(Fun(bot))