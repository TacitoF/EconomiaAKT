import disnake
from disnake.ext import commands
import database as db
import asyncio

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def castigo(self, ctx, tipo: str, tempo: int, vitima: disnake.Member):
        """
        Tipos: mute, deaf, total
        Tempos: 1, 5, 10 (minutos)
        Exemplo: !castigo mute 1 @Amigo
        """
        ladrão_id = str(ctx.author.id)
        user = db.get_user_data(ladrão_id)

        if not user:
            return await ctx.send("❌ Você não tem conta! Use `!trabalhar`.")

        # Tabela de Preços (Valores altos para ser algo raro/especial)
        precos = {
            "mute": {1: 1000, 5: 4000, 10: 7000},
            "deaf": {1: 1500, 5: 5000, 10: 9000},
            "total": {1: 3000, 5: 8000, 10: 15000}
        }

        tipo = tipo.lower()
        if tipo not in precos or tempo not in precos[tipo]:
            return await ctx.send("❌ Opção inválida! Escolha entre `mute`, `deaf` ou `total` e tempos de `1`, `5` ou `10` minutos.")

        custo = precos[tipo][tempo]
        saldo_atual = int(user['data'][2])

        if saldo_atual < custo:
            return await ctx.send(f"❌ Você é um macaco pobre! Esse castigo custa **{custo} Conguitos**.")

        if not vitima.voice:
            return await ctx.send(f"❌ **{vitima.display_name}** precisa estar em um canal de voz para ser castigado!")

        # Cobrando o valor
        db.update_value(user['row'], 3, saldo_atual - custo)

        # Aplicando o Castigo
        try:
            segundos = tempo * 60
            if tipo == "mute":
                await vitima.edit(mute=True, reason=f"Castigo de {ctx.author.name}")
                msg = f"🔇 **{vitima.display_name}** foi silenciado por {tempo} minuto(s)!"
            
            elif tipo == "deaf":
                await vitima.edit(deafen=True, reason=f"Castigo de {ctx.author.name}")
                msg = f"🎧 **{vitima.display_name}** foi ensurdecido por {tempo} minuto(s)!"
            
            elif tipo == "total":
                await vitima.edit(mute=True, deafen=True, reason=f"Castigo de {ctx.author.name}")
                msg = f"🤐 **CASTIGO TOTAL!** {vitima.display_name} ficou mudo e surdo por {tempo} minuto(s)!"

            await ctx.send(f"💸 {ctx.author.name} pagou **{custo} Conguitos** e... {msg}")

            # Aguarda o tempo do castigo
            await asyncio.sleep(segundos)

            # Retirando o Castigo
            if vitima.voice: # Verifica se ele ainda está no canal
                await vitima.edit(mute=False, deafen=False)
                await ctx.send(f"✅ O castigo de **{vitima.display_name}** acabou. Use com sabedoria (ou não)!")

        except disnake.Forbidden:
            await ctx.send("❌ Eu não tenho permissão de 'Silenciar/Ensurdecer Membros' para fazer isso!")
        except Exception as e:
            print(f"Erro no castigo: {e}")

def setup(bot):
    bot.add_cog(Fun(bot))