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

    # ── INTERCEPTADOR: marca falha via ctx.send/reply e via on_command_error ──
    @commands.Cog.listener()
    async def on_command(self, ctx):
        if ctx.author.bot:
            return

        # Flag começa como None (neutra). Só muda para True (sucesso) ou False (falha).
        ctx._missao_status = None

        original_send  = ctx.send
        original_reply = ctx.reply

        EMOJIS_FALHA = ("❌", "⚠️", "🚫", "😬")

        def _conteudo_tem_falha(*args, **kwargs) -> bool:
            partes = []
            if args:
                partes.append(str(args[0]))
            if kwargs.get("content"):
                partes.append(str(kwargs["content"]))
            embed = kwargs.get("embed")
            if embed:
                partes.append(str(getattr(embed, "title", "") or ""))
                partes.append(str(getattr(embed, "description", "") or ""))
            texto = " ".join(partes)
            return any(e in texto for e in EMOJIS_FALHA)

        async def interceptor_send(*args, **kwargs):
            if _conteudo_tem_falha(*args, **kwargs):
                ctx._missao_status = False   # falha confirmada
            return await original_send(*args, **kwargs)

        async def interceptor_reply(*args, **kwargs):
            if _conteudo_tem_falha(*args, **kwargs):
                ctx._missao_status = False
            return await original_reply(*args, **kwargs)

        ctx.send  = interceptor_send
        ctx.reply = interceptor_reply

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Qualquer erro de comando (args errados, sem permissão, cooldown…) = falha."""
        if ctx.author.bot:
            return
        ctx._missao_status = False

    # ── RASTREADOR DE PROGRESSO ──────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        if ctx.author.bot:
            return

        # Aguarda um tick para garantir que todos os ctx.send já foram chamados
        # (inclusive os de erro que chegam via return await ctx.send(...))
        import asyncio
        await asyncio.sleep(0)

        # Se qualquer send/reply enviou emoji de falha, não conta
        if ctx._missao_status is False:
            return

        user_id   = str(ctx.author.id)
        cmd_usado = ctx.command.name

        self._gerar_missoes_usuario(user_id)
        usuario_dados = self.dados[user_id]

        if usuario_dados.get("resgatado", False):
            return

        houve_progresso = False
        user_db = db.get_user_data(user_id)

        for chave_missao, info in usuario_dados["missoes"].items():
            if info["concluida"]:
                continue

            comandos_validos = TIPOS_MISSOES.get(chave_missao, {}).get("comandos", [])
            if cmd_usado not in comandos_validos:
                continue

            # ── Extrai alvo (Member/User) dos argumentos do comando ──
            alvo = None
            for arg in list(ctx.args) + list(ctx.kwargs.values()):
                if isinstance(arg, (disnake.Member, disnake.User)):
                    alvo = arg
                    break

            # ── Validações específicas por missão ─────────────────────────────

            # cuidador: só conta se o pet existia E a fome estava abaixo de 100
            # (ou seja, a ração foi de fato consumida)
            if chave_missao == "cuidador":
                if not user_db:
                    continue
                tipo_pet, fome_pet = db.get_mascote(user_db)
                if not tipo_pet or fome_pet >= 100:
                    continue

            # cacador: só conta se passou um @alvo (não apenas abriu o mural)
            if chave_missao == "cacador":
                if not alvo:
                    continue

            # sabotador/generoso/comerciante/desafiante:
            # alvo não pode ser o próprio usuário nem um bot
            if chave_missao in ("sabotador", "generoso", "comerciante", "desafiante"):
                if alvo and (alvo.bot or alvo.id == ctx.author.id):
                    continue

            # abridor: exige pelo menos 1 argumento (nome da caixa/gaiola)
            if chave_missao == "abridor":
                tem_arg = bool(ctx.args[1:]) or bool(ctx.kwargs)
                if not tem_arg:
                    continue

            # apostador: exige pelo menos 1 argumento (valor da aposta)
            if chave_missao == "apostador":
                tem_arg = bool(ctx.args[1:]) or bool(ctx.kwargs)
                if not tem_arg:
                    continue

            # investidor: exige tipo + valor (pelo menos 2 args além do self/ctx)
            if chave_missao == "investidor":
                args_reais = [a for a in ctx.args if not isinstance(a, commands.Context)]
                if len(args_reais) < 2:
                    continue

            # ditador: exige alvo em voz + tipo + tempo — se não há alvo, era help
            if chave_missao == "ditador":
                if not alvo:
                    continue

            # ─────────────────────────────────────────────────────────────────

            info["atual"] += 1
            houve_progresso = True

            if info["atual"] >= info["meta"]:
                info["atual"] = info["meta"]
                info["concluida"] = True
                try:
                    await ctx.send(
                        f"✅ **{ctx.author.mention}, você concluiu uma Missão Diária!** "
                        f"Use `!missoes` para checar.",
                        delete_after=10
                    )
                except Exception:
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