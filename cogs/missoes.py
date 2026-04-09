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
#
# REGRA CRÍTICA: "comandos" deve conter o ctx.command.name (nome principal do
# decorator), NÃO os aliases. O disnake sempre expõe o nome principal em
# ctx.command.name, independentemente do alias que o usuário digitou.
#
# "modo": define como o sucesso é detectado para aquele grupo de comandos.
#   "interceptar" → depende do ctx.send retornar um título/texto de sucesso.
#                   Usado para comandos que respondem com ctx.send direto.
#   "args_validos" → basta o comando completar sem erro E ter argumentos válidos.
#                    Usado para jogos que editam mensagens ou usam Views/Interactions.
TIPOS_MISSOES = {
    "trabalhador": {
        "meta": 4,
        "desc": "🔨 Trabalhe duro na selva (`!trabalhar`)",
        "comandos": ["trabalhar"],
        "modo": "interceptar"
    },
    "gatuno": {
        "meta": 3,
        "desc": "🥷 Tente assaltar alguém (`!roubar`)",
        "comandos": ["roubar"],
        "modo": "interceptar"
    },
    "apostador": {
        "meta": 3,
        "desc": "🎰 Jogue no Cassino Solo (`!crash`, `!bicho`, `!minas`, `!raspadinha`)",
        "comandos": ["crash", "bicho", "campo_minado", "raspadinha"],
        "modo": "args_validos"
    },
    "desafiante": {
        "meta": 2,
        "desc": "⚔️ Desafie alguém (`!cipo`, `!bang`, `!duelo`, `!rinha`, `!tesouro`, `!truco`)",
        "comandos": ["cipopodre", "bang", "duelo", "rinha", "explorar", "truco"],
        "modo": "args_validos"
    },
    "sabotador": {
        "meta": 2,
        "desc": "😈 Sabote ou engane (`!casca`, `!c4`, `!taxar`, `!impostor`)",
        "comandos": ["casca", "c4", "taxar", "impostor"],
        "modo": "interceptar"
    },
    "investidor": {
        "meta": 1,
        "desc": "🏦 Faça um investimento no banco (`!investir`)",
        "comandos": ["investir"],
        "modo": "interceptar"
    },
    "generoso": {
        "meta": 2,
        "desc": "💸 Transfira dinheiro a alguém (`!pagar`)",
        "comandos": ["pagar"],
        "modo": "interceptar"
    },
    "cacador": {
        "meta": 1,
        "desc": "🎯 Coloque uma recompensa num alvo (`!recompensa`)",
        "comandos": ["recompensa"],
        "modo": "interceptar"
    },
    "cuidador": {
        "meta": 1,
        "desc": "🍗 Alimente seu mascote (`!alimentar`)",
        "comandos": ["alimentar"],
        "modo": "interceptar"
    },
    "abridor": {
        "meta": 2,
        "desc": "📦 Abra caixas ou gaiolas do inventário (`!abrir`)",
        "comandos": ["abrir_caixa"],
        "modo": "interceptar"
    },
    "comerciante": {
        "meta": 1,
        "desc": "🛒 Coloque um item à venda (`!vender`)",
        "comandos": ["vender"],
        "modo": "interceptar"
    },
    "ditador": {
        "meta": 1,
        "desc": "🔇 Aplique um castigo de voz (`!castigo`, `!desconectar`)",
        "comandos": ["castigo", "desconectar"],
        "modo": "interceptar"
    },
    "blackjack": {
        "meta": 2,
        "desc": "🃏 Sente-se à mesa de Blackjack (`!21`)",
        "comandos": ["blackjack"],
        "modo": "args_validos"
    },
    "roleta": {
        "meta": 2,
        "desc": "🎡 Faça apostas na Roleta (`!roleta`)",
        "comandos": ["roleta"],
        "modo": "args_validos"
    },
}

# ── Comandos que usam modo "args_validos" — conjunto para lookup rápido ──
CMDS_ARGS_VALIDOS = {
    cmd
    for info in TIPOS_MISSOES.values()
    if info["modo"] == "args_validos"
    for cmd in info["comandos"]
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

    # ── INTERCEPTADOR DE RESULTADO (apenas para comandos modo="interceptar") ────
    # Só intercepta ctx.send/reply para detectar sucesso/falha em comandos que
    # respondem diretamente com ctx.send (economy, bank, items, sabotagem...).
    # Comandos de jogo (crash, minas, cipo, etc.) usam msg.edit / inter.response,
    # portanto são tratados no on_command_completion por "args_validos".
    @commands.Cog.listener()
    async def on_command(self, ctx):
        if ctx.author.bot:
            return

        cmd_nome = ctx.command.name if ctx.command else ""

        # Comandos args_validos não precisam de interceptação — saímos cedo.
        if cmd_nome in CMDS_ARGS_VALIDOS:
            ctx._missao_status = "args_validos"
            return

        ctx._missao_status   = False  # padrão: falha
        ctx._missao_impostor = False  # flag especial para !impostor

        original_send  = ctx.send
        original_reply = ctx.reply

        # ── Sinais de FALHA: apenas no content (texto puro) ou no TÍTULO do embed ──
        SINAIS_FALHA_CONTENT = ("❌", "⚠️", "🚫", "😬", "⏳")
        SINAIS_FALHA_TITLE   = ("❌", "⚠️", "🚫")

        # ── Títulos EXATOS de embeds de sucesso ──
        TITULOS_SUCESSO = {
            # economy.py — !roubar
            "🥷 SUCESSO!",
            "🥷 SUCESSO (com pena)...",
            "💀 SAQUE DE PURGE!",
            "👮 PRESO! O roubo falhou.",    # tentativa de roubo ainda conta para "gatuno"
            "🛡️ Ataque bloqueado!",         # escudo ativado ainda conta para "gatuno"
            # economy.py — !pagar
            "💸 PIX REALIZADO!",
            # bank.py — !investir
            "🏛️ RENDA FIXA — RENDIMENTO APLICADO!",
            # bounty.py — !recompensa
            "🚨 CAÇADA ATUALIZADA!",
            # items.py — !c4
            "💥 BOOM! ESCUDO DESTRUÍDO!",
            # sabotagem.py — !amaldicoar
            "🍌 MALDIÇÃO SÍMIA CONJURADA!",
            # lootbox.py — !abrir_caixa
            "🎉 🪵 LOOT OBTIDO!", "🎉 🪙 LOOT OBTIDO!", "🎉 🏺 LOOT OBTIDO!", "🎉 🐾 LOOT OBTIDO!",
            # trade.py — !vender
            "🏪 PROPOSTA DE VENDA",
            "♻️ VENDER AO SISTEMA?",
        }

        # ── Strings em textos puros (content) que indicam sucesso ──
        TEXTOS_SUCESSO_CONTENT = (
            "atirou uma **Casca de Banana**",   # items.py — !casca
            "DECRETO ASSINADO!",                # items.py — !taxar
            "Fome restaurada:",                 # pets.py — !alimentar
            "pagou **",                         # fun.py — !castigo / !desconectar
            "🚀 **ALTA!**",                     # bank.py — !investir cripto
            "⚖️ **ESTÁVEL!**",
            "📉 **CRASH!**",
        )

        # ── Field names que indicam sucesso (ex: !trabalhar usa set_author sem title) ──
        FIELD_NAMES_SUCESSO = (
            "💰 Ganho",   # !trabalhar
        )

        def _e_falha(content_texto: str, embed_title: str) -> bool:
            if any(s in content_texto for s in SINAIS_FALHA_CONTENT):
                return True
            if any(s in embed_title for s in SINAIS_FALHA_TITLE):
                return True
            return False

        def _e_sucesso(content_texto: str, embed_title: str, field_names: list) -> bool:
            if embed_title in TITULOS_SUCESSO:
                return True
            if any(s in content_texto for s in TEXTOS_SUCESSO_CONTENT):
                return True
            if any(fn in field_names for fn in FIELD_NAMES_SUCESSO):
                return True
            return False

        def _extrair(args, kwargs):
            content_texto = ""
            embed_title   = ""
            field_names   = []
            if args:
                content_texto = str(args[0])
            elif kwargs.get("content"):
                content_texto = str(kwargs["content"])
            emb = kwargs.get("embed")
            if emb:
                embed_title = str(getattr(emb, "title", "") or "")
                field_names = [str(getattr(f, "name", "") or "") for f in getattr(emb, "fields", [])]
            return content_texto, embed_title, field_names

        async def interceptor_send(*args, **kwargs):
            ct, et, fn = _extrair(args, kwargs)
            ctx._missao_teve_send = True
            if _e_falha(ct, et):
                ctx._missao_status = False
            elif _e_sucesso(ct, et, fn) and ctx._missao_status is not False:
                ctx._missao_status = True
            return await original_send(*args, **kwargs)

        async def interceptor_reply(*args, **kwargs):
            ct, et, fn = _extrair(args, kwargs)
            ctx._missao_teve_send = True
            if _e_falha(ct, et):
                ctx._missao_status = False
            elif _e_sucesso(ct, et, fn) and ctx._missao_status is not False:
                ctx._missao_status = True
            return await original_reply(*args, **kwargs)

        ctx._missao_teve_send = False
        ctx.send  = interceptor_send
        ctx.reply = interceptor_reply

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Qualquer erro de comando = falha na missão."""
        if ctx.author.bot:
            return
        ctx._missao_status = False

    # ── RASTREADOR DE PROGRESSO ──────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        if ctx.author.bot:
            return

        import asyncio
        await asyncio.sleep(0)

        cmd_usado = ctx.command.name if ctx.command else ""

        # ── Caso especial: !impostor usa webhook.send, nunca passa pelo interceptador.
        # Se o comando foi "impostor" E não houve nenhum ctx.send, chegou até o
        # webhook sem erros → contamos como sucesso.
        if cmd_usado == "impostor" and not getattr(ctx, "_missao_teve_send", True):
            ctx._missao_status = True

        # ── Modo "args_validos": basta ter completado sem erro e ter args válidos.
        # O on_command_error já trava o status em False se houve erro.
        if getattr(ctx, "_missao_status", None) == "args_validos":
            # Se on_command_error foi chamado, o status terá sido sobrescrito para False.
            # Aqui significa que completou normalmente → sucesso.
            ctx._missao_status = True

        # Só avança se há sinal explícito de sucesso
        if getattr(ctx, "_missao_status", None) is not True:
            return

        user_id = str(ctx.author.id)
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

            # ── Validações específicas por missão ──────────────────────────────

            # gatuno: exige @vitima
            if chave_missao == "gatuno":
                if not alvo:
                    continue

            # apostador: exige pelo menos 1 argumento numérico (valor da aposta)
            if chave_missao == "apostador":
                args_reais = [a for a in ctx.args if not isinstance(a, (commands.Context, disnake.Member, disnake.User))]
                if not args_reais:
                    continue

            # desafiante: exige @alvo diferente do próprio autor e não-bot
            if chave_missao == "desafiante":
                if not alvo or alvo.bot or alvo.id == ctx.author.id:
                    continue

            # sabotador: exige @alvo diferente do próprio autor e não-bot
            if chave_missao == "sabotador":
                if not alvo or alvo.bot or alvo.id == ctx.author.id:
                    continue

            # investidor: exige tipo + valor (mínimo 2 args reais)
            if chave_missao == "investidor":
                args_reais = [a for a in ctx.args if not isinstance(a, commands.Context)]
                if len(args_reais) < 2:
                    continue

            # generoso: exige @recebedor diferente do próprio autor e não-bot
            if chave_missao == "generoso":
                if not alvo or alvo.bot or alvo.id == ctx.author.id:
                    continue

            # cacador: exige @vitima diferente do próprio autor e não-bot
            if chave_missao == "cacador":
                if not alvo or alvo.bot or alvo.id == ctx.author.id:
                    continue

            # cuidador: verifica que o mascote existe
            if chave_missao == "cuidador":
                if not user_db:
                    continue
                tipo_pet, _ = db.get_mascote(user_db)
                if not tipo_pet:
                    continue

            # abridor: exige nome da caixa como argumento
            if chave_missao == "abridor":
                tem_nome_caixa = bool(ctx.kwargs.get("nome_caixa")) or bool(ctx.args[1:])
                if not tem_nome_caixa:
                    continue

            # ditador: exige @alvo real (não bot, não si mesmo)
            if chave_missao == "ditador":
                if not alvo or alvo.bot or alvo.id == ctx.author.id:
                    continue

            # blackjack/roleta: exige valor apostado como argumento
            if chave_missao in ("blackjack", "roleta"):
                args_reais = [a for a in ctx.args if not isinstance(a, (commands.Context, disnake.Member, disnake.User))]
                if not args_reais:
                    continue

            # ──────────────────────────────────────────────────────────────────

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
                    elif item_ganho == "Baú do Caçador":   cor_embed = disnake.Color.blue()
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