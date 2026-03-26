import disnake
from disnake.ext import commands
import database as db
import time

OWNER_ID = 757752617722970243

# ──────────────────────────────────────────────────────────────────────────────
#  PRÊMIOS DO PÓDIO
#
#  🥇 1º lugar → Relíquia Ancestral + Baú do Caçador + Gaiola Misteriosa
#                + 500 MC iniciais + buff_trabalho_temp: +20% por 7 dias
#  🥈 2º lugar → Baú do Caçador + Gaiola Misteriosa + 300 MC iniciais
#  🥉 3º lugar → Caixote de Madeira + Gaiola Misteriosa + 150 MC iniciais
# ──────────────────────────────────────────────────────────────────────────────

PODIO = {
    1: {
        "mc":       1000.0,
        "itens":    ["Relíquia Ancestral", "Baú do Caçador", "Gaiola Misteriosa"],
        "buff":     True,                        # Troféu do Campeão +20% trabalho por 7 dias
        "passivo":  None,                        # buff já é o Troféu do Campeão
        "titulo":   "cosmético:titulo:Lenda da Selva",  # título lendário exclusivo no inventário
        "conquista": "campeao_era",              # slug gravado na coluna de conquistas
        "label":    "🥇 1º lugar",
        "cor":      disnake.Color.gold(),
    },
    2: {
        "mc":       500.0,
        "itens":    ["Relíquia Ancestral", "Gaiola Misteriosa"],
        "buff":     False,
        "passivo":  "Sindicato",                 # -10min no cooldown do !trabalhar permanente
        "titulo":   None,
        "conquista": "vice_era",
        "label":    "🥈 2º lugar",
        "cor":      disnake.Color.light_grey(),
    },
    3: {
        "mc":       250.0,
        "itens":    ["Baú do Caçador", "Gaiola Misteriosa"],
        "buff":     False,
        "passivo":  "Cinto de Ferramentas",      # +4% no !trabalhar permanente
        "titulo":   None,
        "conquista": "bronze_era",
        "label":    "🥉 3º lugar",
        "cor":      disnake.Color.from_rgb(205, 127, 50),
    },
}

BUFF_DURACAO_DIAS = 7
BUFF_PASSIVO_NOME = "Troféu do Campeão"

# Valor padrão de cada coluna após o reset (índice 0 = coluna A = col 1)
# col:  1(id)  2(nome)  3(saldo)  4(cargo)    5(trab_ts)  6(inv)    7(roubo_ts)  8(invest_ts)  9(cripto)  10(conq)  11(imp)  12(escudo)  13(cosm)  14(mascote)  15(greve)  16(passivos)  17(buff_temp)
RESET_ROW_TEMPLATE = [None, None, "0", "Lêmure", "0", "Nenhum", "0", "", "", "", "", "", "", "", "", "", ""]
#                     ^col1  ^col2  col3  col4      col5  col6    col7  c8  c9  c10 c11 c12 c13 c14         c15   c16        c17
# None = mantém o valor original (user_id e nome não são zerados)


class ResetEconomia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ──────────────────────────────────────────────────────────────────────────
    #  Helpers internos
    # ──────────────────────────────────────────────────────────────────────────

    def _todos_usuarios(self) -> list[dict]:
        """Retorna todos os registros de usuário ordenados por saldo (desc)."""
        todos = db.get_all_users()
        validos = [u for u in todos if u and u.get('data') and len(u['data']) > 2]
        validos.sort(key=lambda u: db.parse_float(u['data'][2]), reverse=True)
        return validos

    def _linha_zerada(self, user: dict) -> list:
        """
        Monta a linha completa após reset, preservando user_id (col1) e nome (col2).
        Garante que a linha tenha pelo menos 17 colunas.
        """
        dados_originais = user['data']
        # Garante tamanho mínimo
        while len(dados_originais) < 17:
            dados_originais.append("")

        linha = []
        for i, val_padrao in enumerate(RESET_ROW_TEMPLATE):
            if val_padrao is None:
                # Preserva o valor original (user_id e nome)
                linha.append(dados_originais[i])
            else:
                linha.append(val_padrao)
        return linha

    # ──────────────────────────────────────────────────────────────────────────
    #  !resetar_economia  (apenas o dono do bot)
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command(name="resetar_economia", aliases=["reset_eco"])
    async def resetar_economia(self, ctx):
        if ctx.author.id != OWNER_ID:
            return  # silencioso

        # ── Confirmação de segurança ──
        embed_conf = disnake.Embed(
            title="⚠️ RESET TOTAL DA ECONOMIA",
            description=(
                "Você está prestes a:\n\n"
                "• **Zerar** saldo, inventário e mascote de **todos** os usuários\n"
                "• **Premiar** os top 3 com itens e MC iniciais\n"
                "• **Remover** bounties e passivos de todos\n\n"
                "Esta ação é **irreversível**.\n\n"
                "Responda `CONFIRMAR RESET` em até 30 segundos para prosseguir."
            ),
            color=disnake.Color.red()
        )
        await ctx.send(embed=embed_conf)

        def check(m):
            return (
                m.author.id == OWNER_ID
                and m.channel.id == ctx.channel.id
                and m.content.strip().upper() == "CONFIRMAR RESET"
            )

        try:
            await self.bot.wait_for("message", check=check, timeout=30.0)
        except Exception:
            return await ctx.send("❌ Reset cancelado por timeout.")

        await ctx.send("⏳ Iniciando reset... aguarde.")

        # ── 1. Coletar todos os usuários ANTES de zerar ──
        try:
            todos = self._todos_usuarios()
        except Exception as e:
            print(f"❌ Erro ao buscar usuários para o reset: {e}")
            return await ctx.send("❌ Erro ao buscar usuários. Reset abortado.")

        if not todos:
            return await ctx.send("❌ Nenhum usuário encontrado na planilha. Reset abortado.")

        # ── 2. Guardar top 3 ANTES de zerar ──
        top3_info = []  # [(posição, user_dict, saldo_antigo)]
        for i, user in enumerate(todos[:3], start=1):
            saldo_antigo = db.parse_float(user['data'][2])
            top3_info.append((i, user, saldo_antigo))

        # ── 3. Zerar TODOS via batch_update (uma única chamada à API) ──
        try:
            batch_data = []
            for user in todos:
                linha = self._linha_zerada(user)
                row_num = user['row']
                # Converte a range para notação A1 (ex: linha 2 → A2:Q2)
                col_fim = chr(ord('A') + len(linha) - 1)  # ex: Q para 17 colunas
                batch_data.append({
                    'range': f'A{row_num}:{col_fim}{row_num}',
                    'values': [linha]
                })

            # Divide em lotes de 50 para evitar erro 429
            LOTE = 50
            for inicio in range(0, len(batch_data), LOTE):
                db.call_with_retry(db.sheet.batch_update, batch_data[inicio:inicio + LOTE])
                if inicio + LOTE < len(batch_data):
                    time.sleep(1)  # pausa entre lotes

            erros_reset = 0
        except Exception as e:
            print(f"❌ Erro no batch reset: {e}")
            return await ctx.send(f"❌ Falha ao zerar a planilha: `{e}`\nReset abortado.")

        # Limpar dicts de memória do bot
        for attr in ('recompensas', 'escudos_ativos', 'impostos', 'cascas'):
            if hasattr(self.bot, attr):
                getattr(self.bot, attr).clear()

        # ── 4. Aplicar prêmios ao pódio (após o reset em massa) ──
        premiados = []
        expira_buff = int(time.time() + BUFF_DURACAO_DIAS * 86400)

        for posicao, user_antigo, saldo_antigo in top3_info:
            uid = str(user_antigo['data'][0])
            user = db.get_user_data(uid)
            if not user:
                continue
            try:
                premio = PODIO[posicao]
                row = user['row']

                # MC iniciais (coluna 3)
                db.update_value(row, 3, premio['mc'])

                # Monta inventário: itens funcionais + título cosmético (se houver)
                itens_inv = list(premio['itens'])
                if premio.get('titulo'):
                    itens_inv.append(premio['titulo'])
                db.update_value(row, 6, ", ".join(itens_inv))

                # Passivos: Troféu do Campeão (1º) ou passivo permanente (2º/3º)
                passivos_novos = []
                if premio['buff']:
                    passivos_novos.append(BUFF_PASSIVO_NOME)
                    db.set_buff_temp_expira(row, expira_buff)
                if premio.get('passivo'):
                    passivos_novos.append(premio['passivo'])
                if passivos_novos:
                    db.set_passivos(row, passivos_novos)

                # Conquista permanente (coluna 10)
                if premio.get('conquista'):
                    conquistas_raw = str(user['data'][9]) if len(user['data']) > 9 else ""
                    slugs = [c.strip() for c in conquistas_raw.split(',') if c.strip()]
                    if premio['conquista'] not in slugs:
                        slugs.append(premio['conquista'])
                        db.update_value(row, 10, ", ".join(slugs))

                premiados.append((posicao, uid, saldo_antigo))
            except Exception as e:
                print(f"❌ Erro ao premiar posição {posicao} (uid={uid}): {e}")

        # ── 5. Anunciar resultado ──
        canal_id = 1475606959247065118
        canal_anuncio = self.bot.get_channel(canal_id) or ctx.channel

        embed_reset = disnake.Embed(
            title="🔄 RESET DA ECONOMIA — NOVA ERA COMEÇA!",
            description=(
                "A selva foi varrida. Saldos, inventários e mascotes foram zerados.\n"
                "Uma nova disputa pelo topo começa agora. Boa sorte a todos! 🍀\n\n"
                "**Os maiores acumuladores da era anterior foram imortalizados:**"
            ),
            color=disnake.Color.dark_gold()
        )

        medalhas = {1: "🥇", 2: "🥈", 3: "🥉"}
        for posicao, uid, saldo_antigo in premiados:
            discord_user = self.bot.get_user(int(uid))
            nome = discord_user.mention if discord_user else f"ID {uid}"
            premio = PODIO[posicao]
            itens_fmt = " · ".join(f"`{it}`" for it in premio['itens'])

            extras = []
            if premio['buff']:
                extras.append(f"👑 **Troféu do Campeão** (+20% `!trabalhar` por {BUFF_DURACAO_DIAS} dias)")
            if premio.get('passivo'):
                descricoes_passivo = {
                    "Sindicato":           "**Sindicato** (-10min no cooldown do `!trabalhar`)",
                    "Cinto de Ferramentas": "**Cinto de Ferramentas** (+4% no `!trabalhar`)",
                }
                extras.append(f"🔰 {descricoes_passivo.get(premio['passivo'], premio['passivo'])}")
            if premio.get('titulo'):
                extras.append("✨ **Título: Lenda da Selva** (exclusivo de campeão)")
            if premio.get('conquista'):
                nomes_conquista = {
                    "campeao_era": "👑 Conquista permanente: **Campeão da Era**",
                    "vice_era":    "🥈 Conquista permanente: **Vice da Era**",
                    "bronze_era":  "🥉 Conquista permanente: **Bronze da Era**",
                }
                extras.append(nomes_conquista.get(premio['conquista'], ""))

            extras_txt = "\n".join(f"└ {e}" for e in extras if e)

            embed_reset.add_field(
                name=f"{medalhas[posicao]} {posicao}º lugar — {saldo_antigo:,.2f} MC acumulados",
                value=(
                    f"👤 {nome}\n"
                    f"🎁 **Itens:** {itens_fmt}\n"
                    f"💰 **MC iniciais:** `{premio['mc']:.0f} MC`\n"
                    f"{extras_txt}"
                ),
                inline=False
            )

        embed_reset.set_footer(text="Que a nova temporada seja épica. 🦍")
        await canal_anuncio.send(content="@everyone", embed=embed_reset)

        # Feedback privado ao owner
        aviso = f"✅ Reset concluído! {len(todos)} usuário(s) zerado(s)."
        aviso += f"\n🏆 {len(premiados)} jogador(es) premiado(s)."
        await ctx.author.send(aviso)


def setup(bot):
    bot.add_cog(ResetEconomia(bot))