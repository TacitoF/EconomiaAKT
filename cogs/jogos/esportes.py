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
        # URL e Autenticação da nova API (Football-Data.org)
        self.api_url = "https://api.football-data.org/v4"
        self.headers = {"X-Auth-Token": os.getenv("FOOTBALL_API_KEY")}
        
        self.cache_jogos = None
        self.cache_time = None
        
        # Inicia a verificação automática de resultados (Google Sheets)
        self.checar_resultados.start()

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"⚽ {ctx.author.mention}, as apostas esportivas ficam no {mencao}!", delete_after=10)
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["jogos_hoje"])
    async def futebol(self, ctx):
        """Lista os próximos jogos mais importantes programados"""

        # Sistema de Cache: Evita gastar o limite gratuito da API
        agora = datetime.now()
        if self.cache_jogos and self.cache_time and (agora - self.cache_time) < timedelta(minutes=30):
            return await ctx.send(embed=self.cache_jogos)

        await ctx.send("🔎 Consultando o calendário da FIFA para os próximos dias... Aguarde!", delete_after=5)

        async with aiohttp.ClientSession() as session:
            # Busca jogos de hoje até os próximos 3 dias para garantir que a lista nunca fique vazia
            hoje_str = agora.strftime("%Y-%m-%d")
            futuro_str = (agora + timedelta(days=3)).strftime("%Y-%m-%d")

            # Ligas: BSA(Brasil), PL(Inglês), PD(Espanhol), CL(Champions), SA(Italiano), BL1(Alemão), PPL(Português)
            params = {
                "competitions": "BSA,PL,PD,CL,SA,BL1,PPL", 
                "status": "SCHEDULED",
                "dateFrom": hoje_str,
                "dateTo": futuro_str
            }
            async with session.get(f"{self.api_url}/matches", headers=self.headers, params=params) as resp:
                data = await resp.json()
                
                # Tratamento de erro caso a chave seja negada
                if 'errorCode' in data or 'message' in data:
                    print(f"⚠️ Erro na API de Futebol: {data.get('message', 'Erro desconhecido')}")
                    return await ctx.send("❌ Não consegui acessar os jogos no momento. Verifique o console.")

                if 'matches' not in data or not data['matches']:
                    return await ctx.send("⚽ Nenhum jogo das grandes ligas programado para os próximos 3 dias.")

                embed = disnake.Embed(
                    title="⚽ BETS DA SELVA - PRÓXIMOS JOGOS ⚽", 
                    description="Para apostar use: `!palpite <ID> <casa/empate/fora> <valor>`\n*Todos os jogos têm Odd fixa de 1.95x no sistema grátis.*",
                    color=disnake.Color.blue()
                )
                
                # Mostra os próximos 10 jogos
                for match in data['matches'][:10]:
                    match_id = match['id']
                    home = match['homeTeam']['name']
                    away = match['awayTeam']['name']
                    
                    # Converte a hora UTC da API para o horário de Brasília (-3h)
                    data_utc = datetime.fromisoformat(match['utcDate'].replace('Z', ''))
                    hora_br = (data_utc - timedelta(hours=3)).strftime('%d/%m às %H:%M')
                    
                    embed.add_field(
                        name=f"🆔 ID: {match_id} | ⏰ {hora_br}",
                        value=f"🏠 **{home}** (Casa) 🆚 **{away}** (Fora) ✈️",
                        inline=False
                    )

                self.cache_jogos = embed
                self.cache_time = agora
                await ctx.send(embed=embed)

    @commands.command()
    async def palpite(self, ctx, match_id: int = None, palpite_escolha: str = None, valor: float = None):
        """Faz uma aposta em um jogo real e salva no Google Sheets"""
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

            # Como esta API gratuita não fornece as Odds de apostas, 
            # fixamos em 1.95x (padrão de casa de aposta para jogo equilibrado)
            odd_fixa = 1.95

            # Desconta o saldo e salva a aposta diretamente no Google Sheets
            db.update_value(user['row'], 3, round(saldo - valor, 2))
            
            db.registrar_aposta_esportiva(ctx.author.id, match_id, palpite_escolha, valor, odd_fixa)
            ganho_potencial = round(valor * odd_fixa, 2)
            
            embed = disnake.Embed(title="🎟️ BILHETE CADASTRADO!", color=disnake.Color.gold())
            embed.description = (
                f"**Apostador:** {ctx.author.mention}\n"
                f"**Jogo ID:** `{match_id}`\n"
                f"**Palpite:** `{palpite_escolha.upper()}`\n"
                f"**Valor Apostado:** `{valor:.2f} C`\n"
                f"**Multiplicador:** `{odd_fixa}x`\n"
                f"**Retorno Potencial:** `{ganho_potencial:.2f} C`"
            )
            embed.set_footer(text="O pagamento será feito automaticamente quando a partida acabar!")
            await ctx.send(embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !palpite de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro ao registrar a aposta.")

    @tasks.loop(minutes=60) # Roda a cada 1 hora
    async def checar_resultados(self):
        # Busca apenas as apostas marcadas como "Pendente" direto da planilha
        apostas_pendentes = db.obter_apostas_pendentes()
        
        if not apostas_pendentes:
            return # Sai se não houver apostas pendentes

        async with aiohttp.ClientSession() as session:
            # Busca todos os jogos que já terminaram (FINISHED)
            params = {"status": "FINISHED"}
            async with session.get(f"{self.api_url}/matches", headers=self.headers, params=params) as resp:
                data = await resp.json()
                
                if 'matches' not in data: 
                    return
                
                canal_cassino = disnake.utils.get(self.bot.get_all_channels(), name='🎰・akbet')

                # Verifica cada aposta pendente contra os jogos finalizados
                for aposta in apostas_pendentes:
                    for match in data['matches']:
                        if str(match['id']) == str(aposta['match_id']):
                            
                            gols_casa = match['score']['fullTime']['home']
                            gols_fora = match['score']['fullTime']['away']
                            
                            resultado_real = "empate"
                            if gols_casa > gols_fora: resultado_real = "casa"
                            elif gols_fora > gols_casa: resultado_real = "fora"

                            jogador = self.bot.get_user(int(aposta['user_id']))
                            se_venceu = aposta['palpite'] == resultado_real
                            
                            if se_venceu:
                                db.atualizar_status_aposta(aposta['row'], 'Venceu')
                                user_db = db.get_user_data(str(aposta['user_id']))
                                if user_db:
                                    saldo_atual = db.parse_float(user_db['data'][2])
                                    premio = round(aposta['valor'] * aposta['odd'], 2)
                                    db.update_value(user_db['row'], 3, round(saldo_atual + premio, 2))
                                    
                                    if canal_cassino and jogador:
                                        await canal_cassino.send(f"🏆 **APOSTA ESPORTIVA VENCEDORA!**\n{jogador.mention} acertou que `{resultado_real.upper()}` venceria no jogo `{match['id']}` e faturou **{premio:.2f} C**!")
                            else:
                                db.atualizar_status_aposta(aposta['row'], 'Perdeu')
                                if canal_cassino and jogador:
                                    await canal_cassino.send(f"💀 **APOSTA PERDIDA!**\nO jogo `{match['id']}` terminou com vitória de `{resultado_real.upper()}`. {jogador.mention} perdeu o bilhete.")

    @checar_resultados.before_loop
    async def before_checar_resultados(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(Esportes(bot))