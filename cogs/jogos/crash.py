import disnake
from disnake.ext import commands
import database as db
import random
import asyncio

LIMITES_CARGO = {
    "Lêmure":      400,
    "Macaquinho":  1500,
    "Babuíno":     4500,
    "Chimpanzé":   12000,
    "Orangutango": 30000,
    "Gorila":      80000,
    "Ancestral":   250000,
    "Rei Símio":   1500000,
}

def get_limite(cargo):
    return LIMITES_CARGO.get(cargo, 250)

def save_achievement(user_data, slug):
    conquistas = str(user_data['data'][9]) if len(user_data['data']) > 9 else ""
    lista = [c.strip() for c in conquistas.split(',') if c.strip()]
    if slug not in lista:
        lista.append(slug)
        db.update_value(user_data['row'], 10, ", ".join(lista))


class CrashView(disnake.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=35)
        self.author_id = author_id
        self.sacou = False

    @disnake.ui.button(label="🪂 SACAR", style=disnake.ButtonStyle.danger)
    async def sacar_btn(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id != self.author_id:
            return await inter.response.send_message("❌ Não é o seu jogo!", ephemeral=True)
        self.sacou = True
        button.disabled = True
        button.label = "✅ Sacado!"
        await inter.response.edit_message(view=self)
        self.stop()


class CrashGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, voa para o canal {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["foguetinho"])
    async def crash(self, ctx, aposta: float = None):
        if aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!crash <valor>`")
        if aposta <= 0:
            return await ctx.send(f"❌ {ctx.author.mention}, a aposta deve ser maior que zero!")
        aposta = round(aposta, 2)

        # Flag para controlar se o débito já foi feito (para reembolso em caso de erro)
        debito_realizado = False

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send(f"❌ {ctx.author.mention}, conta não encontrada!")

            saldo = db.parse_float(user['data'][2])
            cargo = user['data'][3] if len(user['data']) > 3 else "Lêmure"
            if saldo < aposta:
                return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")
            if aposta > get_limite(cargo):
                return await ctx.send(f"🚫 Limite de aposta para **{cargo}** é de **{get_limite(cargo)} MC**!")

            db.update_value(user['row'], 3, round(saldo - aposta, 2))
            debito_realizado = True

            chance = random.random()
            if chance < 0.05:      crash_point = 1.0
            elif chance < 0.65:    crash_point = random.uniform(1.1, 2.0)
            elif chance < 0.90:    crash_point = random.uniform(2.0, 4.0)
            else:                  crash_point = random.uniform(4.0, 10.0)
            crash_point = round(crash_point, 1)

            view = CrashView(ctx.author.id)

            embed = disnake.Embed(
                title="📈 CRASH DO CIPÓ 🐒",
                description=f"{ctx.author.mention} apostou **{aposta:.2f} MC**!\n\n🌿 O macaco começou a subir...\n**Multiplicador:** `1.0x`",
                color=disnake.Color.green()
            )
            msg = await ctx.send(embed=embed, view=view)

            if crash_point == 1.0:
                await asyncio.sleep(1)
                view.stop()
                embed.color = disnake.Color.red()
                embed.description = f"💥 **ARREBENTOU INSTANTANEAMENTE!**\nO cipó rasgou no `1.0x`.\n\n💀 {ctx.author.mention} perdeu **{aposta:.2f} MC**."
                for item in view.children:
                    item.disabled = True
                await msg.edit(embed=embed, view=view)
                user_atual = db.get_user_data(str(ctx.author.id))
                if user_atual:
                    save_achievement(user_atual, "queda_livre")
                return

            current_mult = 1.0

            while current_mult < crash_point:
                await asyncio.sleep(1.5)
                if view.sacou:
                    break
                current_mult = round(min(current_mult + round(random.uniform(0.1, 0.4), 1), crash_point), 1)
                if not view.sacou:
                    embed.description = (
                        f"{ctx.author.mention} apostou **{aposta:.2f} MC**!\n\n"
                        f"🌿 Subindo alto...\n**Multiplicador:** `{current_mult}x`"
                    )
                    try:
                        await msg.edit(embed=embed, view=view)
                    except:
                        pass

            user_atual = db.get_user_data(str(ctx.author.id))
            for item in view.children:
                item.disabled = True

            if view.sacou:
                ganho_total = round(aposta * current_mult, 2)
                db.update_value(user_atual['row'], 3, round(db.parse_float(user_atual['data'][2]) + ganho_total, 2))
                embed.color = disnake.Color.blue()
                embed.description = f"✅ **SACOU A TEMPO!**\nNo `{current_mult}x`.\n\n💰 {ctx.author.mention} lucrou **{ganho_total:.2f} MC**!"
                await msg.edit(embed=embed, view=view)
                if current_mult >= 5.0:
                    save_achievement(user_atual, "astronauta_cipo")
            else:
                embed.color = disnake.Color.red()
                embed.description = f"💥 **ARREBENTOU!**\nO cipó rasgou no `{crash_point}x`.\n\n💀 {ctx.author.mention} perdeu **{aposta:.2f} MC**."
                await msg.edit(embed=embed, view=view)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !crash de {ctx.author}: {e}")
            # FIX BUG 2: reembolsa o jogador se o débito já foi feito antes do erro
            if debito_realizado:
                try:
                    user_refund = db.get_user_data(str(ctx.author.id))
                    if user_refund:
                        s = db.parse_float(user_refund['data'][2])
                        db.update_value(user_refund['row'], 3, round(s + aposta, 2))
                        await ctx.send(
                            f"⚠️ {ctx.author.mention}, ocorreu um erro durante o jogo. "
                            f"Seus **{aposta:.2f} MC** foram devolvidos automaticamente."
                        )
                    else:
                        await ctx.send(
                            f"⚠️ {ctx.author.mention}, ocorreu um erro e não foi possível encontrar sua conta "
                            f"para devolver os **{aposta:.2f} MC**. Contate um administrador!"
                        )
                except Exception as refund_e:
                    print(f"❌ CRÍTICO: falha ao devolver saldo do crash para {ctx.author}: {refund_e}")
                    await ctx.send(
                        f"🚨 {ctx.author.mention}, erro crítico. "
                        f"Informe um admin para recuperar seus **{aposta:.2f} MC**."
                    )
            else:
                await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(CrashGame(bot))