import disnake
from disnake.ext import commands
import database as db
import aiohttp
import os
from datetime import datetime, timedelta

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
            name="⚙️ Sistema & API",
            value="`!ligar` / `!desligar` - Trava global de manutenção\n`!patchnotes` - Posta as novidades no canal oficial\n`!apistatus` - Verifica saúde da API de Esportes\n`!pagar_apostas` - Força checagem de jogos finalizados",
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
            await ctx.send(f"✅ Saldo de {membro.mention} definido em **{valor:.2f} MC**.")
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
            await ctx.send(f"📈 **+{valor:.2f} MC** adicionados para {membro.mention}. (Saldo: `{novo_saldo:.2f} MC`)")
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
            await ctx.send(f"📉 **-{valor:.2f} MC** removidos de {membro.mention}. (Saldo: `{novo_saldo:.2f} MC`)")
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

    @commands.command(aliases=["forcar_pagamento", "pagar_apostas"])
    async def pagarapostas(self, ctx):
        """[ADMIN] Força a verificação e pagamento das apostas esportivas pendentes."""
        if ctx.author.id != OWNER_ID:
            return await ctx.send("❌ Você não tem permissão para usar este comando.")

        msg = await ctx.send("🔄 Consultando a API e o Banco de Dados para verificar jogos finalizados...")

        apostas_pendentes = db.obter_apostas_pendentes()
        if not apostas_pendentes:
            return await msg.edit(content="✅ Nenhuma aposta pendente encontrada no banco de dados.")

        agora = datetime.utcnow()
        data_inicio = (agora - timedelta(days=3)).strftime("%Y-%m-%d")
        data_fim = (agora + timedelta(days=1)).strftime("%Y-%m-%d")

        api_url = "https://api.football-data.org/v4"
        api_key = os.getenv("FOOTBALL_API_KEY") or ""
        headers = {"X-Auth-Token": api_key}

        try:
            async with aiohttp.ClientSession() as session:
                params = {"status": "FINISHED", "dateFrom": data_inicio, "dateTo": data_fim}
                async with session.get(f"{api_url}/matches", headers=headers, params=params) as resp:
                    if resp.status != 200:
                        return await msg.edit(content=f"⚠️ Erro ao acessar a API: Status {resp.status}")
                    
                    data = await resp.json()

                    if 'matches' not in data:
                        return await msg.edit(content="⚠️ Nenhum jogo finalizado encontrado na janela de tempo informada.")

                    canal_cassino = disnake.utils.get(self.bot.get_all_channels(), name='🎰・akbet')
                    processadas = 0

                    for aposta in apostas_pendentes:
                        aposta_id = str(aposta['match_id'])
                        
                        jogo_encontrado = None
                        for match in data['matches']:
                            if str(match['id']) == aposta_id:
                                jogo_encontrado = match
                                break
                        
                        if not jogo_encontrado:
                            continue

                        gols_casa = jogo_encontrado['score']['fullTime']['home']
                        gols_fora = jogo_encontrado['score']['fullTime']['away']

                        if gols_casa > gols_fora:   resultado_real = "casa"
                        elif gols_fora > gols_casa: resultado_real = "fora"
                        else:                       resultado_real = "empate"

                        jogador = self.bot.get_user(int(aposta['user_id']))
                        se_venceu = (aposta['palpite'].lower() == resultado_real)

                        processadas += 1

                        if se_venceu:
                            db.atualizar_status_aposta(aposta['row'], 'Venceu')
                            user_db = db.get_user_data(str(aposta['user_id']))
                            if user_db:
                                saldo_atual = db.parse_float(user_db['data'][2])
                                premio = round(aposta['valor'] * aposta['odd'], 2)
                                db.update_value(user_db['row'], 3, round(saldo_atual + premio, 2))
                                
                                if canal_cassino and jogador:
                                    await canal_cassino.send(
                                        f"🏆 **APOSTA ESPORTIVA VENCEDORA!**\n"
                                        f"{jogador.mention} acertou que `{resultado_real.upper()}` venceria "
                                        f"no jogo `{aposta_id}` e faturou **{premio:.2f} MC**!"
                                    )
                        else:
                            db.atualizar_status_aposta(aposta['row'], 'Perdeu')
                            if canal_cassino and jogador:
                                await canal_cassino.send(
                                    f"💀 **APOSTA PERDIDA!**\n"
                                    f"O jogo `{aposta_id}` terminou com vitória de `{resultado_real.upper()}`. "
                                    f"{jogador.mention} perdeu o bilhete."
                                )

                    if processadas > 0:
                        await msg.edit(content=f"✅ Verificação concluída! **{processadas}** apostas foram processadas e os resultados postados no canal.")
                    else:
                        await msg.edit(content="✅ Verificação concluída! Nenhuma aposta pendente teve o jogo finalizado ainda.")

        except Exception as e:
            await msg.edit(content=f"❌ Erro ao forçar pagamentos: `{e}`")

    @commands.command()
    async def patchnotes(self, ctx):
        """Publica as notas de atualização focadas na nova experiência do Blackjack."""
        try: 
            await ctx.message.delete()
        except: 
            pass

        if ctx.author.id != OWNER_ID:
            return

        # ID do canal de patchnotes oficial
        canal_id = 1475606959247065118
        canal_patchnotes = self.bot.get_channel(canal_id)

        if not canal_patchnotes:
            return await ctx.author.send("❌ Erro: Canal de patchnotes não encontrado.")

        embed = disnake.Embed(
            title="🃏 REVOLUÇÃO NO CASSINO: BLACKJACK v4.5 🃏",
            description="A mesa de 21 acaba de se tornar muito mais imersiva e estratégica. Preparem suas fichas!",
            color=disnake.Color.gold() # Dourado combina com a vibe de cassino
        )

        # Novidade 1: Animação e Suspense
        embed.add_field(
            name="🎭 Sistema de Suspense Real", 
            inline=False, 
            value=(
                "• Chega de resultados instantâneos! Agora o Dealer revela sua mão e puxa cartas **em tempo real** (a cada 2 segundos).\n"
                "• Sinta a adrenalina de Las Vegas enquanto a banca decide o seu destino carta por carta."
            )
        )

        # Novidade 2: Botão de Seguro
        embed.add_field(
            name="🛡️ Nova Opção: Seguro (Insurance)", 
            inline=False, 
            value=(
                "• O Dealer tirou um Ás (`A`)? Não entre em pânico!\n"
                "• Agora você pode acionar o **Seguro** para recuperar **50% da sua aposta** e sair da rodada com segurança caso sinta que a banca vai vencer."
            )
        )

        embed.set_footer(text="Koba: Mantendo a selva em ordem. 🌴")

        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await canal_patchnotes.send(
            content="🚨 **NOVIDADES NO CASSINO!** @everyone 🚨\n",
            embed=embed
        )

def setup(bot):
    bot.add_cog(Admin(bot))