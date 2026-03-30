import disnake
from disnake.ext import commands, tasks
import database as db
import json
import os
import random
from datetime import datetime, timedelta, timezone

ARQUIVO_MISSOES = "missoes_db.json"

# Fuso horário de Brasília (UTC-3)
TZ_BR = timezone(timedelta(hours=-3))

# ── CATÁLOGO EXPANDIDO DE MISSÕES DIÁRIAS ──
TIPOS_MISSOES = {
    "trabalhador": {"meta": 4, "desc": "🔨 Trabalhe duro na selva (`!trabalhar`)", "comandos": ["trabalhar", "work"]},
    "gatuno":      {"meta": 3, "desc": "🥷 Tente assaltar alguém (`!roubar`)", "comandos": ["roubar", "assaltar", "furtar", "rob"]},
    "apostador":   {"meta": 3, "desc": "🎰 Jogue no Cassino Solo (`!crash`, `!bicho`, `!minas`, `!raspadinha`)", "comandos": ["crash", "bicho", "minas", "raspadinha", "bilhete", "loto", "loteria"]},
    "desafiante":  {"meta": 2, "desc": "⚔️ Desafie alguém (`!truco`, `!cipo`, `!gatilho`, `!jokenpo`, `!rinha`, `!tesouro`)", "comandos": ["truco", "cipo", "gatilho", "jokenpo", "rinha", "tesouro"]},
    "sabotador":   {"meta": 2, "desc": "😈 Sabote ou engane (`!casca`, `!c4`, `!imposto`, `!impostor`)", "comandos": ["casca", "banana", "c4", "imposto", "impostor"]},
    "investidor":  {"meta": 1, "desc": "🏦 Faça um investimento no banco (`!investir`)", "comandos": ["investir", "banco", "depositar"]},
    "generoso":    {"meta": 2, "desc": "💸 Transfira dinheiro a alguém (`!pagar`)", "comandos": ["pagar", "pix", "transferir", "pay"]},
    "cacador":     {"meta": 1, "desc": "🎯 Coloque uma recompensa num alvo (`!recompensa`)", "comandos": ["recompensa", "bounty", "cacada"]},
    "cuidador":    {"meta": 1, "desc": "🍗 Alimente seu mascote (`!alimentar`)", "comandos": ["alimentar", "dar_comida"]},
    "abridor":     {"meta": 2, "desc": "📦 Abra caixas ou gaiolas do inventário (`!abrir`)", "comandos": ["abrir", "abrir_caixa"]},
    "comerciante": {"meta": 1, "desc": "🛒 Coloque um item à venda (`!vender`)", "comandos": ["vender", "sell", "negociar"]},
    "ditador":     {"meta": 1, "desc": "🔇 Aplique um castigo de voz (`!castigo`, `!desconectar`)", "comandos": ["castigo", "desconectar"]},
    "blackjack":   {"meta": 2, "desc": "🃏 Sente-se à mesa de Blackjack (`!21`)", "comandos": ["blackjack", "bj", "21"]},
    "roleta":      {"meta": 2, "desc": "🎡 Faça apostas na Roleta (`!roleta`)", "comandos": ["roleta"]}
}

class Missoes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dados = self._carregar_dados()

    def _carregar_dados(self):
        if os.path.exists(ARQUIVO_MISSOES):
            try:
                with open(ARQUIVO_MISSOES, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _salvar_dados(self):
        with open(ARQUIVO_MISSOES, "w", encoding="utf-8") as f:
            json.dump(self.dados, f, ensure_ascii=False, indent=4)

    def _obter_data_hoje(self):
        return datetime.now(TZ_BR).strftime("%Y-%m-%d")

    def _tempo_para_reset(self):
        agora = datetime.now(TZ_BR)
        amanha = agora + timedelta(days=1)
        meia_noite = amanha.replace(hour=0, minute=0, second=0, microsecond=0)
        return int(meia_noite.timestamp())

    def _gerar_missoes_usuario(self, user_id: str):
        hoje = self._obter_data_hoje()
        
        if user_id not in self.dados or self.dados[user_id].get("data") != hoje:
            chaves_escolhidas = random.sample(list(TIPOS_MISSOES.keys()), 3)
            
            missoes_geradas = {}
            for chave in chaves_escolhidas:
                missoes_geradas[chave] = {
                    "atual": 0,
                    "meta": TIPOS_MISSOES[chave]["meta"],
                    "desc": TIPOS_MISSOES[chave]["desc"],
                    "concluida": False
                }

            self.dados[user_id] = {
                "data": hoje,
                "missoes": missoes_geradas,
                "resgatado": False
            }
            self._salvar_dados()

    # ── INTERCEPTADOR DE ERROS ──
    @commands.Cog.listener()
    async def on_command(self, ctx):
        if ctx.author.bot: return
        
        ctx.comando_falhou_missao = False
        original_send = ctx.send
        original_reply = ctx.reply
        
        def _verificar_falha(*args, **kwargs):
            texto = ""
            if args: texto += str(args[0])
            if kwargs.get('content'): texto += str(kwargs.get('content'))
            if kwargs.get('embed'):
                texto += str(kwargs.get('embed').title) + str(kwargs.get('embed').description)
            
            if any(emoji in texto for emoji in ["❌", "⚠️", "🚫", "😬"]):
                ctx.comando_falhou_missao = True

        async def interceptor_send(*args, **kwargs):
            _verificar_falha(*args, **kwargs)
            return await original_send(*args, **kwargs)

        async def interceptor_reply(*args, **kwargs):
            _verificar_falha(*args, **kwargs)
            return await original_reply(*args, **kwargs)

        ctx.send = interceptor_send
        ctx.reply = interceptor_reply

    # ── RASTREADOR DE PROGRESSO ──
    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        if ctx.author.bot: return
        
        if getattr(ctx, 'comando_falhou_missao', False):
            return
        
        user_id = str(ctx.author.id)
        cmd_usado = ctx.command.name

        self._gerar_missoes_usuario(user_id)
        usuario_dados = self.dados[user_id]
        
        if usuario_dados.get("resgatado", False):
            return

        houve_progresso = False
        user_db = db.get_user_data(user_id)
        
        for chave_missao, info in usuario_dados["missoes"].items():
            if info["concluida"]: continue
            
            comandos_validos = TIPOS_MISSOES.get(chave_missao, {}).get("comandos", [])
            
            if cmd_usado in comandos_validos:
                
                # ── VALIDAÇÕES ANTI-ESPERTINHOS (CORRIGIDAS) ──
                
                # Extrai o alvo real do comando a partir dos argumentos (kwargs ou args)
                alvo = None
                for arg in list(ctx.args) + list(ctx.kwargs.values()):
                    if isinstance(arg, (disnake.Member, disnake.User)):
                        alvo = arg
                        break

                if chave_missao == "cuidador":
                    if not user_db: continue
                    tipo, fome = db.get_mascote(user_db)
                    # Se não tem pet ou ele já está com fome 100, não conta (não gastou ração)
                    if not tipo or fome >= 100: 
                        continue 

                if chave_missao == "cacador":
                    # Se não houver um alvo nos argumentos, significa que a pessoa só abriu o mural
                    if not alvo:
                        continue
                        
                if chave_missao in ["sabotador", "generoso", "comerciante", "desafiante"]:
                    if alvo:
                        # Se tentou sabotar/pagar a si mesmo ou a um bot
                        if alvo.bot or alvo.id == ctx.author.id:
                            continue
                # ─────────────────────────────────────────────

                info["atual"] += 1
                houve_progresso = True
                
                if info["atual"] >= info["meta"]:
                    info["atual"] = info["meta"]
                    info["concluida"] = True
                    try:
                        await ctx.send(f"✅ **{ctx.author.mention}, você concluiu uma Missão Diária!** Use `!missoes` para checar.", delete_after=10)
                    except:
                        pass

        if houve_progresso:
            self._salvar_dados()

    @commands.command(aliases=["missões", "diarias", "quest"])
    async def missoes(self, ctx):
        user_id = str(ctx.author.id)
        self._gerar_missoes_usuario(user_id)
        usuario_dados = self.dados[user_id]

        ts_reset = self._tempo_para_reset()
        
        embed = disnake.Embed(
            title="📜 QUADRO DE CAÇADAS DIÁRIAS",
            description=(
                f"Complete as 3 tarefas para receber uma Caixa de Suprimentos!\n"
                f"⏳ *O quadro será resetado <t:{ts_reset}:R>*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.gold()
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)

        todas_concluidas = True
        for chave, info in usuario_dados["missoes"].items():
            if info["concluida"]:
                status = "✅ `[CONCLUÍDA]`"
            else:
                status = f"⏳ `[{info['atual']}/{info['meta']}]`"
                todas_concluidas = False

            embed.add_field(
                name=info["desc"],
                value=status,
                inline=False
            )

        if todas_concluidas:
            if usuario_dados.get("resgatado"):
                embed.add_field(
                    name="🎉 RECOMPENSA JÁ RESGATADA!",
                    value="Você já pegou o seu prêmio de hoje. Volte amanhã!",
                    inline=False
                )
                embed.color = disnake.Color.dark_grey()
            else:
                try:
                    user_db = db.get_user_data(user_id)
                    if not user_db:
                        return await ctx.send(f"❌ {ctx.author.mention}, você precisa ter uma conta! Use `!trabalhar`.")

                    saldo = db.parse_float(user_db['data'][2])
                    inv_str = str(user_db['data'][5]) if len(user_db['data']) > 5 else ""
                    inv_list = [i.strip() for i in inv_str.split(',') if i.strip() and i.strip().lower() != "nenhum"]

                    mc_ganho = float(random.randint(300, 900))
                    
                    sorteio_item = random.random()
                    if sorteio_item <= 0.02:   item_ganho = "Relíquia Ancestral"
                    elif sorteio_item <= 0.12: item_ganho = "Gaiola Misteriosa"
                    elif sorteio_item <= 0.25: item_ganho = "Baú do Caçador"
                    elif sorteio_item <= 0.40: item_ganho = "Ração Símia"
                    else:                      item_ganho = "Caixote de Madeira"
                    
                    db.update_value(user_db['row'], 3, round(saldo + mc_ganho, 2))
                    inv_list.append(item_ganho)
                    db.update_value(user_db['row'], 6, ", ".join(inv_list))

                    self.dados[user_id]["resgatado"] = True
                    self._salvar_dados()

                    cor_embed = disnake.Color.green()
                    if item_ganho == "Relíquia Ancestral": cor_embed = disnake.Color.gold()
                    elif item_ganho == "Baú do Caçador": cor_embed = disnake.Color.blue()
                    elif item_ganho == "Gaiola Misteriosa": cor_embed = disnake.Color.dark_theme()

                    embed.color = cor_embed
                    embed.add_field(
                        name="🎁 RECOMPENSA DIÁRIA ENTREGUE!",
                        value=(
                            f"Você terminou o seu turno e a selva te recompensou:\n\n"
                            f"💰 **Dinheiro:** `+{mc_ganho:.2f} MC`\n"
                            f"📦 **Loot Especial:** `1x {item_ganho}`\n\n"
                            f"*(Verifique o seu `!inventario`!)*"
                        ),
                        inline=False
                    )
                except Exception as e:
                    print(f"Erro ao pagar missoes: {e}")
                    embed.add_field(name="⚠️ ERRO", value="O banco falhou ao entregar seu prêmio. Tente dar `!missoes` de novo.", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="resetar_missoes")
    @commands.has_permissions(administrator=True)
    async def resetar_missoes(self, ctx, alvo: disnake.Member = None):
        """[Admin] Força o reset das missões de um jogador (ou de si mesmo)."""
        if alvo is None:
            alvo = ctx.author

        user_id = str(alvo.id)
        
        if user_id in self.dados:
            del self.dados[user_id]
            self._salvar_dados()
            await ctx.send(f"✅ As missões de {alvo.mention} foram completamente zeradas!")
        else:
            await ctx.send(f"⚠️ {alvo.mention} ainda não tem nenhum registro de missões no sistema.")

def setup(bot):
    bot.add_cog(Missoes(bot))