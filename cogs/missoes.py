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
# Mapeamento verificado contra os cogs:
#   trabalhar   → economy.py  @commands.command(aliases=["work"])
#   roubar      → economy.py  @commands.command(aliases=["assaltar","furtar","rob"])
#   crash/bicho/minas/raspadinha → arquivos de cassino (nome principal confirmado)
#   truco/cipo/gatilho/jokenpo/rinha/tesouro → arquivos de duelo (nome principal)
#   casca       → items.py    @commands.command(aliases=["banana"])
#   taxar       → items.py    @commands.command(aliases=["imposto"])   ← nome principal é "taxar"
#   c4          → items.py    @commands.command(aliases=["explodir","bomb"])
#   impostor    → sabotagem.py
#   investir    → bank.py     @commands.command(aliases=["banco","depositar"])  ← nome principal é "investir"
#   pagar       → economy.py  @commands.command(aliases=["pix","transferir","pay"])
#   recompensa  → bounty.py   @commands.command(aliases=["bounty","cacada"])
#   alimentar   → pets.py     @commands.command(aliases=["darcomida","comida"])  ← sem "dar_comida"
#   abrir_caixa → lootbox.py  @commands.command(aliases=["abrir"])  ← nome principal é "abrir_caixa"
#   vender      → trade.py    @commands.command(aliases=["negociar","comercio"])  ← sem "sell"
#   castigo     → fun.py      @commands.command()
#   desconectar → fun.py      @commands.command(name="desconectar", ...)
#   blackjack/roleta → arquivos de cassino (nome principal confirmado)
TIPOS_MISSOES = {
    "trabalhador": {"meta": 4, "desc": "🔨 Trabalhe duro na selva (`!trabalhar`)",                                               "comandos": ["trabalhar"]},
    "gatuno":      {"meta": 3, "desc": "🥷 Tente assaltar alguém (`!roubar`)",                                                   "comandos": ["roubar"]},
    "apostador":   {"meta": 3, "desc": "🎰 Jogue no Cassino Solo (`!crash`, `!bicho`, `!minas`, `!raspadinha`)",                 "comandos": ["crash", "bicho", "minas", "raspadinha", "bilhete", "loto", "loteria"]},
    "desafiante":  {"meta": 2, "desc": "⚔️ Desafie alguém (`!truco`, `!cipo`, `!gatilho`, `!jokenpo`, `!rinha`, `!tesouro`)",   "comandos": ["truco", "cipo", "gatilho", "jokenpo", "rinha", "tesouro"]},
    "sabotador":   {"meta": 2, "desc": "😈 Sabote ou engane (`!casca`, `!c4`, `!taxar`, `!impostor`)",                          "comandos": ["casca", "c4", "taxar", "impostor"]},
    "investidor":  {"meta": 1, "desc": "🏦 Faça um investimento no banco (`!investir`)",                                         "comandos": ["investir"]},
    "generoso":    {"meta": 2, "desc": "💸 Transfira dinheiro a alguém (`!pagar`)",                                              "comandos": ["pagar"]},
    "cacador":     {"meta": 1, "desc": "🎯 Coloque uma recompensa num alvo (`!recompensa`)",                                     "comandos": ["recompensa"]},
    "cuidador":    {"meta": 1, "desc": "🍗 Alimente seu mascote (`!alimentar`)",                                                 "comandos": ["alimentar"]},
    "abridor":     {"meta": 2, "desc": "📦 Abra caixas ou gaiolas do inventário (`!abrir`)",                                     "comandos": ["abrir_caixa"]},
    "comerciante": {"meta": 1, "desc": "🛒 Coloque um item à venda (`!vender`)",                                                 "comandos": ["vender"]},
    "ditador":     {"meta": 1, "desc": "🔇 Aplique um castigo de voz (`!castigo`, `!desconectar`)",                              "comandos": ["castigo", "desconectar"]},
    "blackjack":   {"meta": 2, "desc": "🃏 Sente-se à mesa de Blackjack (`!21`)",                                                "comandos": ["blackjack", "bj", "21"]},
    "roleta":      {"meta": 2, "desc": "🎡 Faça apostas na Roleta (`!roleta`)",                                                  "comandos": ["roleta"]}
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

    # ── INTERCEPTADOR DE RESULTADO ───────────────────────────────────────────
    # Lógica opt-in: padrão = False (falha).
    # Só muda para True se o bot responder com título/texto EXATO de sucesso.
    #
    # REGRAS DE DETECÇÃO:
    #   FALHA  → verifica apenas content (texto puro) e title do embed.
    #            NÃO verifica fields — eles podem conter ⚠️/❌ informativos
    #            dentro de embeds de sucesso (ex: bounty, boss, lootbox).
    #   SUCESSO → verifica títulos EXATOS dos embeds de cada comando,
    #             ou strings únicas de textos puros de sucesso.
    #             Para !impostor: o sucesso é detectado via flag ctx._missao_impostor
    #             definida antes do webhook.send (já que o webhook não passa pelo interceptor).
    @commands.Cog.listener()
    async def on_command(self, ctx):
        if ctx.author.bot:
            return

        ctx._missao_status   = False  # padrão: falha
        ctx._missao_impostor = False  # flag especial para !impostor

        original_send  = ctx.send
        original_reply = ctx.reply

        # ── Sinais de FALHA: apenas no content (texto puro) ou no TÍTULO do embed ──
        # Não verificamos fields — eles podem ter ⚠️/❌ em contextos informativos.
        SINAIS_FALHA_CONTENT = ("❌", "⚠️", "🚫", "😬", "⏳")
        SINAIS_FALHA_TITLE   = ("❌", "⚠️", "🚫")

        # ── Títulos EXATOS de embeds de sucesso (mapeados diretamente dos cogs) ──
        TITULOS_SUCESSO = {
            # economy.py — !trabalhar: embed sem title, detectado pelo set_author
            # economy.py — !roubar
            "🥷 SUCESSO!",
            "🥷 SUCESSO (com pena)...",
            "💀 SAQUE DE PURGE!",
            "👮 PRESO! O roubo falhou.",   # falha no roubo ainda conta para "gatuno"
            "🛡️ Ataque bloqueado!",        # escudo ativado ainda conta para "gatuno"
            # economy.py — !pagar
            "💸 PIX REALIZADO!",
            # bank.py — !investir
            "🏛️ RENDA FIXA — RENDIMENTO APLICADO!",
            # bounty.py — !recompensa
            "🚨 CAÇADA ATUALIZADA!",
            # items.py — !c4
            "💥 BOOM! ESCUDO DESTRUÍDO!",
            # items.py — !taxar (usa texto puro, não embed — tratado abaixo)
            # sabotagem.py — !amaldicoar
            "🍌 MALDIÇÃO SÍMIA CONJURADA!",
            # lootbox.py — !abrir_caixa
            "🎉 🪵 LOOT OBTIDO!", "🎉 🪙 LOOT OBTIDO!", "🎉 🏺 LOOT OBTIDO!", "🎉 🐾 LOOT OBTIDO!",
            # trade.py — !vender
            "🏪 PROPOSTA DE VENDA",
            "♻️ VENDER AO SISTEMA?",
            # blackjack / roleta / cassino (títulos dos jogos — completar se necessário)
            "🃏 BLACKJACK", "🎡 ROLETA", "🎰 CASSINO", "💥 CRASH",
        }

        # ── Strings EXATAS em textos puros (content) de sucesso ──
        # Apenas frases únicas que NÃO aparecem em mensagens de erro.
        TEXTOS_SUCESSO_CONTENT = (
            # economy.py — !trabalhar: embed sem title, usa set_author → não tem texto puro
            # economy.py — !roubar fallback (purge sem embed)
            # items.py — !casca (texto puro, sem embed)
            "atirou uma **Casca de Banana**",
            # items.py — !taxar (texto puro, sem embed)
            "DECRETO ASSINADO!",
            # pets.py — !alimentar (texto puro, sem embed)
            "Fome restaurada:",
            # fun.py — !castigo / !desconectar (textos puros)
            "pagou **",          # "pagou **300.00 MC** e..." — único nos sucessos
            # bank.py — !investir cripto (textos puros após o sleep)
            "🚀 **ALTA!**",
            "⚖️ **ESTÁVEL!**",
            "📉 **CRASH!**",
        )

        # ── Detecção via set_author: !trabalhar usa embed sem title ──
        # O embed tem set_author com "foi trabalhar" — detectamos pela descrição ausente
        # e pelo field name "💰 Ganho". Usamos o field NAME (não value) que é seguro.
        FIELD_NAMES_SUCESSO = (
            "💰 Ganho",   # !trabalhar
        )

        def _e_falha(content_texto: str, embed_title: str) -> bool:
            """Verifica falha apenas no content e no título do embed."""
            if any(s in content_texto for s in SINAIS_FALHA_CONTENT):
                return True
            if any(s in embed_title for s in SINAIS_FALHA_TITLE):
                return True
            return False

        def _e_sucesso(content_texto: str, embed_title: str, field_names: list) -> bool:
            """Verifica sucesso por título exato, texto puro exato, ou field name seguro."""
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
            # Texto puro (positional arg ou kwarg "content")
            if args:
                content_texto = str(args[0])
            elif kwargs.get("content"):
                content_texto = str(kwargs["content"])
            # Embed
            emb = kwargs.get("embed")
            if emb:
                embed_title = str(getattr(emb, "title", "") or "")
                field_names = [str(getattr(f, "name", "") or "") for f in getattr(emb, "fields", [])]
            return content_texto, embed_title, field_names

        async def interceptor_send(*args, **kwargs):
            ct, et, fn = _extrair(args, kwargs)
            ctx._missao_teve_send = True            # registra que o bot enviou algo
            if _e_falha(ct, et):
                ctx._missao_status = False          # trava em falha — não pode voltar
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

        ctx._missao_teve_send = False   # ainda não enviou nada
        ctx.send  = interceptor_send
        ctx.reply = interceptor_reply

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Qualquer erro de comando (args inválidos, sem permissão, cooldown…) = falha."""
        if ctx.author.bot:
            return
        ctx._missao_status = False

    # ── RASTREADOR DE PROGRESSO ──────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        if ctx.author.bot:
            return

        # Aguarda um tick para que todos os ctx.send assíncronos já tenham rodado
        import asyncio
        await asyncio.sleep(0)

        # Caso especial: !impostor — o sucesso usa webhook.send (não ctx.send),
        # então o interceptador nunca vê a mensagem de sucesso.
        # Se o comando foi "impostor" E o bot não enviou NADA via ctx.send
        # (ou seja, _missao_teve_send é False), significa que chegou até o
        # webhook.send sem erros → contamos como sucesso.
        cmd_usado = ctx.command.name
        if cmd_usado == "impostor" and not getattr(ctx, "_missao_teve_send", True):
            ctx._missao_status = True

        # Só conta se o comando gerou sinal EXPLÍCITO de sucesso
        if ctx._missao_status is not True:
            return

        user_id   = str(ctx.author.id)
        cmd_usado = ctx.command.name  # sempre o nome PRINCIPAL, nunca o alias

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

            # trabalhador: !trabalhar sem args — nenhuma validação extra necessária,
            # o interceptador já garante que o embed de sucesso foi enviado.

            # gatuno: qualquer tentativa de roubo conta (sucesso OU falha com multa),
            # mas exige @vitima. Sem alvo = exibiu o "uso:" → já bloqueado pelo interceptador.
            if chave_missao == "gatuno":
                if not alvo:
                    continue

            # apostador: exige pelo menos 1 argumento (valor da aposta).
            # Sem valor = exibiu o tutorial com ⚠️ → já bloqueado pelo interceptador.
            # Validação extra: garante que o arg não é um Member (evita !crash @alguem)
            if chave_missao == "apostador":
                args_reais = [a for a in ctx.args if not isinstance(a, (commands.Context, disnake.Member, disnake.User))]
                if not args_reais:
                    continue

            # desafiante: exige @alvo que não seja o próprio usuário nem bot
            if chave_missao == "desafiante":
                if not alvo or alvo.bot or alvo.id == ctx.author.id:
                    continue

            # sabotador: exige @alvo que não seja o próprio usuário nem bot.
            # Cobertura: casca @alvo, c4 @alvo, taxar @alvo, impostor @alvo msg
            if chave_missao == "sabotador":
                if not alvo or alvo.bot or alvo.id == ctx.author.id:
                    continue

            # investidor: exige tipo ("fixo"/"cripto") + valor.
            # Sem args = exibiu o menu com ⚠️ → já bloqueado.
            # Validação extra: confirma que há pelo menos 2 args reais (tipo + valor)
            if chave_missao == "investidor":
                args_reais = [a for a in ctx.args if not isinstance(a, commands.Context)]
                if len(args_reais) < 2:
                    continue

            # generoso: exige @recebedor + valor > 0, e recebedor ≠ si mesmo/bot.
            # Sem args = ⚠️ já bloqueado. Validação extra:
            if chave_missao == "generoso":
                if not alvo or alvo.bot or alvo.id == ctx.author.id:
                    continue

            # cacador: exige @vitima + valor.
            # !recompensas (mural) tem nome de comando diferente → não bate em "recompensa"
            # Mas !recompensa @alvo sem valor retorna ⚠️ → já bloqueado.
            # Validação extra: confirma que há @alvo
            if chave_missao == "cacador":
                if not alvo or alvo.bot or alvo.id == ctx.author.id:
                    continue

            # cuidador: !alimentar só avança se havia mascote ativo com fome < 100
            # E havia Ração Símia no inventário. Lê o estado ANTES da execução
            # não é possível (já foi consumida), então verifica que o mascote EXISTE
            # e que a fome atual é > 0 (após alimentar, nunca seria 0 se havia ração).
            # O interceptador já garante que o bot enviou "🍗" + "Fome restaurada".
            if chave_missao == "cuidador":
                if not user_db:
                    continue
                tipo_pet, _ = db.get_mascote(user_db)
                if not tipo_pet:
                    continue

            # abridor: abrir_caixa exige nome_caixa como argumento.
            # Sem arg = ⚠️ já bloqueado pelo interceptador.
            # Validação extra: confirma que há pelo menos 1 arg real (nome da caixa)
            if chave_missao == "abridor":
                # ctx.kwargs pode conter "nome_caixa" ou ctx.args pode ter o valor
                tem_nome_caixa = bool(ctx.kwargs.get("nome_caixa")) or bool(ctx.args[1:])
                if not tem_nome_caixa:
                    continue

            # comerciante: !vender exige pelo menos o nome do item (não pode ser vazio).
            # !vender sem args = ⚠️ já bloqueado.
            # Para venda entre jogadores, a PROPOSTA foi enviada (sucesso da ação).
            # O comprador aceitar/recusar é irrelevante para a missão.
            # Sem validação extra necessária — interceptador já cuida.

            # ditador: exige @alvo que esteja em canal de voz.
            # Sem alvo = ⚠️ já bloqueado. Valida que há alvo real:
            if chave_missao == "ditador":
                if not alvo or alvo.bot or alvo.id == ctx.author.id:
                    continue

            # blackjack/roleta: exige valor apostado como argumento.
            if chave_missao in ("blackjack", "roleta"):
                args_reais = [a for a in ctx.args if not isinstance(a, (commands.Context, disnake.Member, disnake.User))]
                if not args_reais:
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