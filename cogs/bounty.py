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
            if not pagador:
                return await ctx.send("❌ Você não tem conta registrada!")
            
            saldo = db.parse_float(pagador['data'][2])
            if saldo < valor:
                return await ctx.send(f"❌ Saldo insuficiente! Você precisa de **{valor:.2f} MC**.")

            vitima_db = db.get_user_data(str(vitima.id))
            if not vitima_db:
                return await ctx.send(f"❌ {vitima.mention} não tem conta na selva!")

            vitima_id = str(vitima.id)
            db.update_value(pagador['row'], 3, round(saldo - valor, 2))
            self.bot.recompensas[vitima_id] = self.bot.recompensas.get(vitima_id, 0.0) + valor

            # ── FLAG DE SUCESSO DA MISSÃO ──
            ctx._missao_ok = True

            embed = disnake.Embed(
                title="🎯 NOVO ALVO PROCURADO!",
                description=(
                    f"{ctx.author.mention} colocou a cabeça de {vitima.mention} a prêmio!\n\n"
                    f"💰 **Recompensa Adicionada:** `{valor:.2f} MC`\n"
                    f"💀 **Prêmio Acumulado:** `{self.bot.recompensas[vitima_id]:.2f} MC`\n\n"
                    f"*(Quem assaltar este jogador com sucesso leva o prêmio inteiro!)*"
                ),
                color=disnake.Color.dark_red()
            )
            embed.set_thumbnail(url=vitima.display_avatar.url)
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
            embed.add_field(name=f"{prefixo} {nome}", value=f"🎯 Prêmio: `{val:.2f} MC`", inline=False)

        embed.set_footer(text="Assalte os procurados com !roubar para embolsar a grana!")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Bounty(bot))