import disnake
from disnake.ext import commands, tasks
import aiohttp
import os
import database as db
from datetime import datetime, timedelta

# Limites de aposta baseados no seu sistema
LIMITES_CARGO = {
    "Lêmure": 250, "Macaquinho": 800, "Babuíno": 2000, "Chimpanzé": 6000,
    "Orangutango": 15000, "Gorila": 45000, "Ancestral": 150000, "Rei Símio": 1500000
}

def get_limite(cargo):
    return LIMITES_CARGO.get(cargo, 250)

class Esportes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://api-football-v1.p.rapidapi.com/v3"
        self.headers = {
            "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }
        self.cache_jogos = None
        self.cache_time = None
        
        # Inicia a verificação automática de resultados (Google Sheets)
        self.checar_resultados.start()

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, as apostas esportivas ficam no {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["jogos_hoje", "futebol"])
    async def jogos(self, ctx):
        """Lista os jogos mais importantes do dia"""
        try: await ctx.message.delete()
        except: pass

        # Sistema de Cache: Evita gastar o limite gratuito da API (100 req/dia)
        agora = datetime.now()
        if self.cache_jogos and self.cache_time and (agora - self.cache_time) < timedelta(minutes=30):
            return await ctx.send(embed=self.cache_jogos)

        await ctx.send("🔎 Buscando os jogos de hoje nas principais ligas... Aguarde!", delete_after=5)

        hoje = agora.strftime("%Y-%m-%d")
        # Ligas: 71 (Brasileirão), 2 (Champions League), 39 (Premier League)
        ligas = "71-2-39" 

        async with aiohttp.ClientSession() as session:
            params = {"date": hoje, "timezone": "America/Sao_Paulo"}
            async with session.get(f"{self.api_url}/fixtures", headers=self.headers, params=params) as resp:
                data = await resp.json()
                
                if 'response' not in data or not data['response']:
                    return await ctx.send("⚽ Não encontrei jogos nas ligas principais para hoje.")

                embed = disnake.Embed(
                    title="⚽ CASA DE APOSTAS DA SELVA ⚽", 
                    description="Use `!palpite <ID> <casa/empate/fora> <valor>` para apostar!\nExemplo: `!palpite 123456 casa 150`",
                    color=disnake.Color.green()
                )

                jogos_encontrados = 0
                for match in data['response']:
                    if str(match['league']['id']) in ligas.split('-'):
                        home = match['teams']['home']['name']
                        away = match['teams']['away']['name']
                        match_id = match['fixture']['id']
                        hora = datetime.fromtimestamp(match['fixture']['timestamp']).strftime('%H:%M')
                        status = match['fixture']['status']['short']
                        
                        if status in ['NS', 'TBD']: # Apenas jogos que não começaram
                            embed.add_field(
                                name=f"🆔 Jogo: {match_id} | ⏰ {hora}",
                                value=f"🏠 **{home}** vs ✈️ **{away}**",
                                inline=False
                            )
                            jogos_encontrados += 1
                        
                        if jogos_encontrados >= 10: # Limite visual do embed
                            break

                if jogos_encontrados == 0:
                    return await ctx.send("⚽ Todos os jogos principais de hoje já começaram ou terminaram!")

                # Salva no cache
                self.cache_jogos = embed
                self.cache_time = agora
                await ctx.send(embed=embed)

    @commands.command()
    async def palpite(self, ctx, match_id: int = None, palpite_escolha: str = None, valor: float = None):
        """Faz uma aposta em um jogo real e salva no Google Sheets"""
        try: await ctx.message.delete()
        except: pass

        if match_id is None or palpite_escolha is None or valor is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!palpite <ID do Jogo> <casa/empate/fora> <valor>`")
        
        palpite_escolha = palpite_escolha.lower()
        if palpite_escolha not in ["casa", "empate", "fora"]:
            return await ctx.send("❌ Opção inválida! Escolha entre: `casa`, `empate` ou `fora`.")
        
        if valor <= 0:
            return await ctx.send("❌ O valor da aposta deve ser maior que zero!")
            
        valor = round(valor, 2)

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send(f"❌ {ctx.author.mention}, conta não encontrada!")

            saldo = db.parse_float(user['data'][2])
            cargo = user['data'][3] if len(user['data']) > 3 else "Lêmure"

            if saldo < valor:
                return await ctx.send(f"❌ {ctx.author.mention}, saldo insuficiente!")
            if valor > get_limite(cargo):
                return await ctx.send(f"🚫 Limite de aposta para **{cargo}** é de **{get_limite(cargo)} C**!")

            msg_buscando = await ctx.send(f"📊 {ctx.author.mention}, calculando as odds (multiplicadores) para este jogo...")

            # Busca a Odd na API (Bookmaker 8 = Bet365)
            async with aiohttp.ClientSession() as session:
                params = {"fixture": match_id, "bookmaker": "8"}
                async with session.get(f"{self.api_url}/odds", headers=self.headers, params=params) as resp:
                    data = await resp.json()

                    if not data['response']:
                        await msg_buscando.delete()
                        return await ctx.send("❌ Não encontrei odds para este jogo. Ele pode já ter começado ou não estar disponível.")

                    # Extrai as odds
                    bets = data['response'][0]['bookmakers'][0]['bets'][0]['values']
                    odd_valor = 1.0
                    for bet in bets:
                        if palpite_escolha == "casa" and bet['value'] == "Home": odd_valor = float(bet['odd'])
                        elif palpite_escolha == "empate" and bet['value'] == "Draw": odd_valor = float(bet['odd'])
                        elif palpite_escolha == "fora" and bet['value'] == "Away": odd_valor = float(bet['odd'])

            # Desconta o saldo e salva a aposta diretamente no Google Sheets
            db.update_value(user['row'], 3, round(saldo - valor, 2))
            
            db.registrar_aposta_esportiva(ctx.author.id, match_id, palpite_escolha, valor, odd_valor)
            ganho_potencial = round(valor * odd_valor, 2)

            await msg_buscando.delete()
            
            embed = disnake.Embed(title="🎟️ APOSTA REGISTRADA!", color=disnake.Color.gold())
            embed.description = (
                f"**Apostador:** {ctx.author.mention}\n"
                f"**Jogo ID:** `{match_id}`\n"
                f"**Palpite:** `{palpite_escolha.upper()}`\n"
                f"**Valor Apostado:** `{valor:.2f} C`\n"
                f"**Multiplicador (Odd):** `{odd_valor}x`\n"
                f"**Retorno Potencial:** `{ganho_potencial:.2f} C`"
            )
            embed.set_footer(text="O pagamento será feito automaticamente quando a partida acabar!")
            await ctx.send(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !palpite de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro ao registrar a aposta.")

    @tasks.loop(minutes=30) # Roda a cada 30 minutos em segundo plano
    async def checar_resultados(self):
        # Busca apenas as apostas marcadas como "Pendente" direto da planilha
        apostas_pendentes = db.obter_apostas_pendentes()
        
        if not apostas_pendentes:
            return # Sai se não houver apostas pendentes

        # Agrupa por match_id para fazer apenas 1 requisição por jogo
        jogos_ids = list(set([str(a['match_id']) for a in apostas_pendentes]))
        
        async with aiohttp.ClientSession() as session:
            for match_id in jogos_ids:
                params = {"id": match_id}
                async with session.get(f"{self.api_url}/fixtures", headers=self.headers, params=params) as resp:
                    data = await resp.json()
                    
                    if not data['response']: continue
                    
                    status_jogo = data['response'][0]['fixture']['status']['short']
                    
                    # FT = Full Time, AET = After Extra Time, PEN = Penalties
                    if status_jogo in ['FT', 'AET', 'PEN']: 
                        gols_casa = data['response'][0]['goals']['home']
                        gols_fora = data['response'][0]['goals']['away']
                        
                        resultado_real = "empate"
                        if gols_casa > gols_fora: resultado_real = "casa"
                        elif gols_fora > gols_casa: resultado_real = "fora"

                        # Atualiza as apostas desse jogo
                        canal_cassino = disnake.utils.get(self.bot.get_all_channels(), name='🎰・akbet')
                        
                        for aposta in apostas_pendentes:
                            if str(aposta['match_id']) == str(match_id):
                                jogador = self.bot.get_user(int(aposta['user_id']))
                                se_venceu = aposta['palpite'] == resultado_real
                                
                                if se_venceu:
                                    # Atualiza status na planilha para "Venceu"
                                    db.atualizar_status_aposta(aposta['row'], 'Venceu')
                                    
                                    # Injeta o dinheiro na conta do usuário
                                    user_db = db.get_user_data(str(aposta['user_id']))
                                    if user_db:
                                        saldo_atual = db.parse_float(user_db['data'][2])
                                        premio = round(aposta['valor'] * aposta['odd'], 2)
                                        db.update_value(user_db['row'], 3, round(saldo_atual + premio, 2))
                                        
                                        if canal_cassino and jogador:
                                            await canal_cassino.send(f"🏆 **APOSTA ESPORTIVA VENCEDORA!**\n{jogador.mention} acertou que `{resultado_real.upper()}` venceria no jogo `{match_id}` e faturou **{premio:.2f} C**!")
                                else:
                                    # Atualiza status na planilha para "Perdeu"
                                    db.atualizar_status_aposta(aposta['row'], 'Perdeu')
                                    if canal_cassino and jogador:
                                        await canal_cassino.send(f"💀 **APOSTA PERDIDA!**\nO jogo `{match_id}` terminou com vitória de `{resultado_real.upper()}`. {jogador.mention} perdeu **{aposta['valor']:.2f} C**.")

    @checar_resultados.before_loop
    async def before_checar_resultados(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(Esportes(bot))