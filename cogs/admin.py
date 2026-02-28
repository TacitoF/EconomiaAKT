import disnake
from disnake.ext import commands
import database as db
import aiohttp
import os
import asyncio
from datetime import datetime, timedelta

OWNER_ID = 757752617722970243

LIGAS_EMOJI = {
    "BSA": "🇧🇷",
    "PL":  "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "PD":  "🇪🇸",
    "CL":  "⭐",
    "SA":  "🇮🇹",
    "BL1": "🇩🇪",
    "PPL": "🇵🇹",
}

def sanitizar(valor: str) -> str:
    """Remove caracteres surrogate inválidos que causam o erro UTF-8 do disnake."""
    if not isinstance(valor, str):
        return str(valor)
    return valor.encode('utf-8', errors='replace').decode('utf-8')

def formatar_moeda(valor: float) -> str:
    """Formata um float para o padrão brasileiro de moeda."""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

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
            await ctx.send(f"✅ Saldo de {membro.mention} definido em **{formatar_moeda(valor)} MC**.")
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
            saldo_atual = db.parse_float(u['data'][2])
            novo_saldo = round(saldo_atual + valor, 2)
            db.update_value(u['row'], 3, novo_saldo)
            await ctx.send(f"📈 **+{formatar_moeda(valor)} MC** adicionados para {membro.mention}. (Saldo: `{formatar_moeda(novo_saldo)} MC`)")
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
            saldo_atual = db.parse_float(u['data'][2])
            novo_saldo = max(round(saldo_atual - valor, 2), 0.0)
            db.update_value(u['row'], 3, novo_saldo)
            await ctx.send(f"📉 **-{formatar_moeda(valor)} MC** removidos de {membro.mention}. (Saldo: `{formatar_moeda(novo_saldo)} MC`)")
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
                    embed.add_field(name="🔑 Tipo de Conta",                       value=f"`{conta_tipo}`",              inline=False)
                    embed.add_field(name="⏱️ Requisições Livres (Neste Minuto)",   value=f"`{disponivel_minuto} de 10`", inline=False)
                    embed.set_footer(text="A cota de 10 chamadas reinicia a cada 60 segundos.")

                    await msg.edit(content=None, embed=embed)

        except Exception as e:
            print(f"❌ Erro no !apistatus: {e}")
            await msg.edit(content=f"⚠️ Erro ao consultar a API: `{e}`")

    @commands.command(aliases=["forcar_pagamento", "pagar_apostas"])
    async def pagarapostas(self, ctx):
        """[ADMIN] Força a verificação exata por lote para evitar erro 400 da API."""
        if ctx.author.id != OWNER_ID:
            return await ctx.send("❌ Você não tem permissão para usar este comando.")

        msg = await ctx.send("🔄 **Iniciando varredura rápida em lote...**\n*(O bot vai checar todos os jogos recentes pendentes)*")

        apostas_pendentes = db.obter_apostas_pendentes()
        if not apostas_pendentes:
            return await msg.edit(content="✅ Nenhuma aposta consta como 'Pendente' na planilha.")

        match_ids_pendentes = set(str(a['match_id']) for a in apostas_pendentes)
        canal_cassino = disnake.utils.get(self.bot.get_all_channels(), name='🎰・akbet')

        api_url = "https://api.football-data.org/v4"
        api_key = os.getenv("FOOTBALL_API_KEY") or ""
        headers = {"X-Auth-Token": api_key}
        processadas = 0

        agora = datetime.utcnow()
        data_de = (agora - timedelta(days=5)).strftime("%Y-%m-%d")
        data_at = (agora + timedelta(days=1)).strftime("%Y-%m-%d")
        resultados_api = {}

        try:
            async with aiohttp.ClientSession() as session:
                params = {"competitions": "BSA,PL,PD,CL,SA,BL1,PPL", "dateFrom": data_de, "dateTo": data_at}
                async with session.get(f"{api_url}/matches", headers=headers, params=params, timeout=30) as resp:
                    if resp.status == 429:
                        return await msg.edit(content="⚠️ Erro: Rate limit da API atingido. Tente novamente em 1 minuto.")
                    if resp.status != 200:
                        return await msg.edit(content=f"⚠️ API retornou código de erro {resp.status}.")
                    
                    for match in (await resp.json()).get("matches", []):
                        mid = str(match["id"])
                        if mid in match_ids_pendentes:
                            resultados_api[mid] = match
        except Exception as e:
            return await msg.edit(content=f"❌ Erro ao conectar com a API: {e}")

        if not resultados_api:
            return await msg.edit(content="✅ Varredura concluída! Nenhum jogo pendente foi finalizado na vida real ainda.")

        for match_id, match_data in resultados_api.items():
            status = match_data.get('status')
            if status not in ["FINISHED", "AWARDED"]:
                continue

            gols_casa = match_data.get('score', {}).get('fullTime', {}).get('home')
            gols_fora = match_data.get('score', {}).get('fullTime', {}).get('away')

            if gols_casa is None or gols_fora is None:
                continue

            home_nome = match_data['homeTeam']['name']
            away_nome = match_data['awayTeam']['name']
            placar    = f"{gols_casa} x {gols_fora}"
            liga_nome = match_data.get('competition', {}).get('name', '')

            if gols_casa > gols_fora:   resultado_real = "casa"
            elif gols_fora > gols_casa: resultado_real = "fora"
            else:                       resultado_real = "empate"

            LABEL = {"casa": home_nome, "fora": away_nome, "empate": "Empate"}
            apostas_deste_jogo = [a for a in apostas_pendentes if str(a['match_id']) == match_id]
            
            for aposta in apostas_deste_jogo:
                palpite_key = aposta['palpite'].lower()
                palpite_fmt = LABEL.get(palpite_key, aposta['palpite'])

                # Logica de busca de usuario consertada idêntica ao esportes.py
                jogador = self.bot.get_user(int(aposta["user_id"]))
                if jogador is None:
                    try:
                        jogador = await self.bot.fetch_user(int(aposta["user_id"]))
                    except Exception:
                        jogador = None

                se_venceu = (palpite_key == resultado_real)
                processadas += 1

                if se_venceu:
                    db.atualizar_status_aposta(aposta['row'], 'Venceu')
                    user_db = db.get_user_data(str(aposta['user_id']))
                    if user_db:
                        saldo_atual = db.parse_float(user_db['data'][2])
                        premio      = round(aposta['valor'] * aposta['odd'], 2)
                        db.update_value(user_db['row'], 3, round(saldo_atual + premio, 2))

                        if canal_cassino and jogador:
                            embed = disnake.Embed(title="🏆 APOSTA VENCEDORA!", color=disnake.Color.green())
                            embed.set_author(name=jogador.display_name, icon_url=jogador.display_avatar.url)
                            embed.add_field(name="⚽ Partida",  value=f"**{home_nome}** vs **{away_nome}**", inline=False)
                            embed.add_field(name="🏆 Liga",     value=liga_nome or "—",                      inline=True)
                            embed.add_field(name="📊 Placar",   value=f"**{placar}**",                       inline=True)
                            embed.add_field(name="\u200b",      value="\u200b",                              inline=True)
                            embed.add_field(name="🎯 Palpite",  value=palpite_fmt,                           inline=True)
                            embed.add_field(name="💸 Apostado", value=f"`{formatar_moeda(aposta['valor'])} MC`", inline=True)
                            embed.add_field(name="💰 Prêmio",   value=f"**{formatar_moeda(premio)} MC**",        inline=True)
                            embed.set_footer(text="O saldo já foi creditado na sua conta!")
                            await canal_cassino.send(content=f"🎉 {jogador.mention}", embed=embed)
                else:
                    db.atualizar_status_aposta(aposta['row'], 'Perdeu')
                    if canal_cassino and jogador:
                        embed = disnake.Embed(title="💀 APOSTA PERDIDA", color=disnake.Color.red())
                        embed.set_author(name=jogador.display_name, icon_url=jogador.display_avatar.url)
                        embed.add_field(name="⚽ Partida",     value=f"**{home_nome}** vs **{away_nome}**", inline=False)
                        embed.add_field(name="🏆 Liga",        value=liga_nome or "—",                      inline=True)
                        embed.add_field(name="📊 Placar",      value=f"**{placar}**",                       inline=True)
                        embed.add_field(name="\u200b",         value="\u200b",                              inline=True)
                        embed.add_field(name="✅ Resultado",   value=LABEL.get(resultado_real, resultado_real), inline=True)
                        embed.add_field(name="❌ Seu Palpite", value=palpite_fmt,                           inline=True)
                        embed.add_field(name="💸 Perdido",     value=f"`{formatar_moeda(aposta['valor'])} MC`", inline=True)
                        embed.set_footer(text="Veja jogos com !futebol")
                        await canal_cassino.send(content=f"{jogador.mention}", embed=embed)

        await msg.edit(content=f"✅ **Varredura concluída!** {processadas} aposta(s) finalizada(s) e paga(s) aos jogadores.")

def setup(bot):
    bot.add_cog(Admin(bot))