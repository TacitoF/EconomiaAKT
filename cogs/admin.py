import disnake
from disnake.ext import commands
import database as db
import aiohttp
import os

OWNER_ID = 757752617722970243

def sanitizar(valor: str) -> str:
    """Remove caracteres surrogate inválidos que causam o erro UTF-8 do disnake."""
    if not isinstance(valor, str):
        return str(valor)
    return valor.encode('utf-8', errors='replace').decode('utf-8')

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ajudaadm(self, ctx):
        if ctx.author.id != OWNER_ID:
            return

        embed = disnake.Embed(
            title="🛠️ Painel de Controle Administrativo",
            description="Comandos exclusivos para a gerência da selva.",
            color=disnake.Color.dark_grey()
        )
        embed.add_field(
            name="🏆 Conquistas",
            value="`!darconquista @membro slug` - Grava conquista\n`!removerconquista @membro slug` - Remove conquista",
            inline=False
        )
        embed.add_field(
            name="💰 Economia",
            value="`!setar @membro valor` - Define saldo exato\n`!adicionar @membro valor` - Soma ao saldo\n`!remover @membro valor` - Subtrai do saldo\n`!wipe` - Reseta toda a planilha",
            inline=False
        )
        embed.add_field(
            name="⚙️ Sistema & Avisos",
            value="`!ligar` / `!desligar` - Trava global de manutenção\n`!postar_regras` - Envia e fixa as regras\n`!patchnotes` - Posta as novidades no canal oficial",
            inline=False
        )
        embed.add_field(
            name="🎰 Loteria",
            value="`!sortear_loteria` - Sorteia o pote atual da loteria e premia o vencedor",
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def darconquista(self, ctx, membro: disnake.Member = None, slug: str = None):
        if ctx.author.id != OWNER_ID: return
        if membro is None or slug is None:
            return await ctx.send("⚠️ Use: `!darconquista @membro slug_da_conquista`")
        try:
            u = db.get_user_data(str(membro.id))
            if not u: return await ctx.send("❌ Usuário não encontrado!")
            conquistas = str(u['data'][9]) if len(u['data']) > 9 else ""
            lista = [c.strip() for c in conquistas.split(',') if c.strip()]
            if slug in lista: return await ctx.send(f"⚠️ {membro.display_name} já possui esta conquista!")
            lista.append(slug)
            db.update_value(u['row'], 10, ", ".join(lista))
            await ctx.send(f"🏆 Conquista `{slug}` gravada para {membro.mention}!")
        except Exception as e:
            print(f"Erro no !darconquista: {e}")

    @commands.command()
    async def removerconquista(self, ctx, membro: disnake.Member = None, slug: str = None):
        if ctx.author.id != OWNER_ID: return
        if membro is None or slug is None:
            return await ctx.send("⚠️ Use: `!removerconquista @membro slug_da_conquista`")
        try:
            u = db.get_user_data(str(membro.id))
            if not u: return await ctx.send("❌ Usuário não encontrado!")
            conquistas = str(u['data'][9]) if len(u['data']) > 9 else ""
            lista = [c.strip() for c in conquistas.split(',') if c.strip()]
            if slug not in lista: return await ctx.send(f"❌ {membro.display_name} não possui essa conquista.")
            lista.remove(slug)
            db.update_value(u['row'], 10, ", ".join(lista))
            await ctx.send(f"🧹 Conquista `{slug}` removida de {membro.mention}!")
        except Exception as e:
            print(f"Erro no !removerconquista: {e}")

    @commands.command()
    async def setar(self, ctx, membro: disnake.Member = None, valor: float = None):
        if ctx.author.id != OWNER_ID: return
        if membro is None or valor is None:
            return await ctx.send("⚠️ Use: `!setar @membro <valor>`")
        try:
            u = db.get_user_data(str(membro.id))
            if not u: return await ctx.send("❌ Usuário não encontrado!")
            valor = round(valor, 2)
            db.update_value(u['row'], 3, valor)
            await ctx.send(f"✅ Saldo de {membro.mention} definido em **{valor:.2f} C**.")
        except Exception as e:
            print(f"Erro no !setar: {e}")

    @commands.command(aliases=["add", "dar"])
    async def adicionar(self, ctx, membro: disnake.Member = None, valor: float = None):
        if ctx.author.id != OWNER_ID: return
        if membro is None or valor is None:
            return await ctx.send("⚠️ Use: `!adicionar @membro <valor>`")
        try:
            u = db.get_user_data(str(membro.id))
            if not u: return await ctx.send("❌ Usuário não encontrado!")
            saldo_atual = float(str(u['data'][2]).replace(',', '.'))
            novo_saldo = round(saldo_atual + valor, 2)
            db.update_value(u['row'], 3, novo_saldo)
            await ctx.send(f"📈 **+{valor:.2f} C** adicionados para {membro.mention}. (Saldo: `{novo_saldo:.2f} C`)")
        except Exception as e:
            print(f"Erro no !adicionar: {e}")

    @commands.command(aliases=["tirar", "subtrair"])
    async def remover(self, ctx, membro: disnake.Member = None, valor: float = None):
        if ctx.author.id != OWNER_ID: return
        if membro is None or valor is None:
            return await ctx.send("⚠️ Use: `!remover @membro <valor>`")
        try:
            u = db.get_user_data(str(membro.id))
            if not u: return await ctx.send("❌ Usuário não encontrado!")
            saldo_atual = float(str(u['data'][2]).replace(',', '.'))
            novo_saldo = max(round(saldo_atual - valor, 2), 0.0)
            db.update_value(u['row'], 3, novo_saldo)
            await ctx.send(f"📉 **-{valor:.2f} C** removidos de {membro.mention}. (Saldo: `{novo_saldo:.2f} C`)")
        except Exception as e:
            print(f"Erro no !remover: {e}")

    @commands.command()
    async def wipe(self, ctx):
        if ctx.author.id != OWNER_ID: return
        await ctx.send("🧹 Resetando toda a economia da selva...")
        try:
            db.wipe_database()
            await ctx.send("✅ **WIPE CONCLUÍDO!** Todos os macacos voltaram ao zero.")
        except Exception as e:
            await ctx.send(f"⚠️ Erro ao realizar wipe: {e}")

    @commands.command()
    async def apistatus(self, ctx):
        """[ADMIN] Checa o status e o uso da API de Futebol"""
        if ctx.author.id != OWNER_ID:
            return await ctx.send("❌ Você não tem permissão para usar este comando.")

        msg = await ctx.send("📡 Consultando os servidores da Football-Data.org...")

        api_url = "https://api.football-data.org/v4"
        api_key = os.getenv("FOOTBALL_API_KEY") or ""
        headers = {"X-Auth-Token": api_key}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{api_url}/competitions", headers=headers, params={"limit": 1}) as resp:
                    status_code = resp.status
                    resp_headers = resp.headers

                    disponivel_minuto = sanitizar(resp_headers.get('X-Requests-Available-Minute', 'N/A'))
                    conta_tipo        = sanitizar(resp_headers.get('X-Authenticated-Client', 'Desconhecido'))

                    if status_code == 200:
                        cor        = disnake.Color.green()
                        status_msg = "✅ API Online e Conectada!"
                    elif status_code == 429:
                        cor        = disnake.Color.red()
                        status_msg = "🚨 ALERTA: Limite de requisições excedido (Rate Limit)!"
                    elif status_code == 403:
                        cor        = disnake.Color.orange()
                        status_msg = "🔑 Chave inválida ou sem permissão (403 Forbidden)."
                    else:
                        cor        = disnake.Color.orange()
                        status_msg = f"⚠️ Status desconhecido ou erro ({status_code})."

                    embed = disnake.Embed(
                        title="📊 Painel de Controle - API de Futebol",
                        color=cor
                    )
                    embed.description = status_msg
                    embed.add_field(name="🔑 Tipo de Conta",                       value=f"`{conta_tipo}`",         inline=False)
                    embed.add_field(name="⏱️ Requisições Livres (Neste Minuto)",   value=f"`{disponivel_minuto} de 10`", inline=False)
                    embed.set_footer(text="A cota de 10 chamadas reinicia a cada 60 segundos.")

                    await msg.edit(content=None, embed=embed)

        except Exception as e:
            print(f"❌ Erro no !apistatus: {e}")
            await msg.edit(content=f"⚠️ Erro ao consultar a API: `{e}`")

    @commands.command()
    async def patchnotes(self, ctx):
        try: await ctx.message.delete()
        except: pass

        if ctx.author.id != OWNER_ID:
            return

        canal_id = 1475606959247065118
        canal_patchnotes = self.bot.get_channel(canal_id)

        if not canal_patchnotes:
            return await ctx.author.send("❌ Erro: Não consegui encontrar o canal de patchnotes. Verifique o ID.")

        embed = disnake.Embed(
            title="📢 NOTAS DE ATUALIZAÇÃO DA SELVA 🐒",
            description="Confira as novidades no mercado de investimentos e uma correção muito aguardada no submundo!",
            color=disnake.Color.dark_red()
        )

        embed.add_field(name="📈 Mercado Cripto (!investir cripto)", inline=False, value=(
            "• **Anti-Vício:** Para evitar spam e quebras de banco, a compra de criptomoedas agora é limitada a **4 vezes por dia**.\n"
            "• **Volatilidade Fixa:** Os resultados agora são cravados, variando de um Crash de **-25%** até uma Alta Máxima de **+20%**."
        ))

        embed.add_field(name="🥷 Correção de Bug (!roubar)", inline=False, value=(
            "• **Bug Resolvido:** O erro que estava punindo os jogadores com uma multa absurda de **50%** ao serem pegos em um roubo foi corrigido!\n"
            "• A taxa de punição voltou ao normal (a multa baseia-se novamente numa porcentagem justa do seu saldo)."
        ))

        embed.set_footer(text="A economia da selva agradece! Boa sorte e bons lucros. 👑")

        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await canal_patchnotes.send(
            content="🚨 **ATUALIZAÇÃO IMPORTANTE!** @everyone 🚨\n",
            embed=embed
        )

def setup(bot):
    bot.add_cog(Admin(bot))