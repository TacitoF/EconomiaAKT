import disnake
from disnake.ext import commands
import database as db

class Bounty(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, 'recompensas'): bot.recompensas = {}

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, assuntos de caçada são apenas no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["bounty", "cacada"])
    async def recompensa(self, ctx, vitima: disnake.Member = None, valor: float = None):
        if vitima is None or valor is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!recompensa @usuario <valor>`")
        if vitima.id == ctx.author.id:
            return await ctx.send(f"🐒 {ctx.author.mention}, você não pode se colocar a prêmio!")
        if valor <= 0:
            return await ctx.send("❌ O valor precisa ser maior que zero!")

        valor = round(valor, 2)
        try:
            pagador = db.get_user_data(str(ctx.author.id))
            saldo   = db.parse_float(pagador['data'][2]) if pagador else 0.0
            if not pagador or saldo < valor:
                return await ctx.send("❌ Saldo insuficiente!")

            db.update_value(pagador['row'], 3, round(saldo - valor, 2))
            vitima_id = str(vitima.id)
            self.bot.recompensas[vitima_id] = round(self.bot.recompensas.get(vitima_id, 0.0) + valor, 2)

            total = self.bot.recompensas[vitima_id]
            embed = disnake.Embed(
                title="🚨 CAÇADA ATUALIZADA!",
                description=(
                    f"**{ctx.author.mention}** colocou um prêmio na cabeça de **{vitima.mention}**!\n\n"
                    f"💰 **Prêmio acumulado:** `{total:.2f} MC`\n\n"
                    f"🥷 *Quem roubar {vitima.mention} com sucesso embolsa o prêmio inteiro.*\n"
                    f"⚠️ *Ladrões também geram bounty automático ao roubar — cuidado com a cabeça!*"
                ),
                color=disnake.Color.red()
            )
            await ctx.send(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !recompensa de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

    @commands.command(aliases=["procurados", "lista_bounty"])
    async def recompensas(self, ctx):
        ativos = {u_id: val for u_id, val in self.bot.recompensas.items() if val > 0}
        if not ativos:
            return await ctx.send("🕊️ Ninguém com a cabeça a prêmio no momento!")

        ordenados = sorted(ativos.items(), key=lambda x: x[1], reverse=True)
        total_em_circulacao = sum(ativos.values())

        embed = disnake.Embed(
            title="📜 Mural de Procurados",
            description=f"💸 **Total em circulação:** `{total_em_circulacao:.2f} MC`",
            color=disnake.Color.dark_red()
        )

        medalhas = ["🥇", "🥈", "🥉"]
        for i, (u_id, val) in enumerate(ordenados):
            user = self.bot.get_user(int(u_id))
            nome = user.display_name if user else f"ID: {u_id}"
            prefixo = medalhas[i] if i < 3 else f"`#{i+1}`"
            embed.add_field(
                name=f"{prefixo} {nome}",
                value=f"💰 **{val:.2f} MC**",
                inline=False
            )

        embed.set_footer(text="Roube um procurado com sucesso para embolsar o prêmio.")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Bounty(bot))