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
#
#  O buff temporário do 1º lugar é armazenado como um passivo especial
#  "Troféu do Campeão" na lista de passivos do usuário, com expiração via
#  timestamp gravado no banco. O !trabalhar já lê PASSIVOS_EFEITOS —
#  basta registrar o efeito lá E checar a expiração no cog.
# ──────────────────────────────────────────────────────────────────────────────

PODIO = {
    1: {
        "mc":    500.0,
        "itens": ["Relíquia Ancestral", "Baú do Caçador", "Gaiola Misteriosa"],
        "buff":  True,   # buff temporário de +20% no !trabalhar por 7 dias
        "label": "🥇 1º lugar",
        "cor":   disnake.Color.gold(),
    },
    2: {
        "mc":    300.0,
        "itens": ["Baú do Caçador", "Gaiola Misteriosa"],
        "buff":  False,
        "label": "🥈 2º lugar",
        "cor":   disnake.Color.light_grey(),
    },
    3: {
        "mc":    150.0,
        "itens": ["Caixote de Madeira", "Gaiola Misteriosa"],
        "buff":  False,
        "label": "🥉 3º lugar",
        "cor":   disnake.Color.from_rgb(205, 127, 50),
    },
}

BUFF_DURACAO_DIAS = 7
BUFF_PASSIVO_NOME = "Troféu do Campeão"   # nome que aparece no !trabalhar


class ResetEconomia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ──────────────────────────────────────────────────────────────────────────
    #  Helpers internos
    # ──────────────────────────────────────────────────────────────────────────

    def _todos_usuarios(self) -> list[dict]:
        """Retorna todos os registros de usuário ordenados por saldo (desc)."""
        todos = db.get_all_users()          # deve retornar lista de dicts com 'data' e 'row'
        validos = [u for u in todos if u and u.get('data') and len(u['data']) > 2]
        validos.sort(key=lambda u: db.parse_float(u['data'][2]), reverse=True)
        return validos

    def _aplicar_premio(self, user: dict, posicao: int):
        """Aplica MC iniciais, itens e buff ao vencedor de determinada posição."""
        premio = PODIO[posicao]

        # MC iniciais
        db.update_value(user['row'], 3, premio['mc'])

        # Itens no inventário (começa vazio após o reset)
        itens_str = ", ".join(premio['itens'])
        db.update_value(user['row'], 6, itens_str)

        # Buff temporário de +20% no !trabalhar por 7 dias (apenas 1º lugar)
        if premio['buff']:
            expira_em = int(time.time() + BUFF_DURACAO_DIAS * 86400)
            # Guardamos o passivo especial E o timestamp de expiração
            passivos_atuais = db.get_passivos(user)
            if BUFF_PASSIVO_NOME not in passivos_atuais:
                passivos_atuais.append(BUFF_PASSIVO_NOME)
                db.set_passivos(user['row'], passivos_atuais)
            # Timestamp fica num campo auxiliar no banco (mesmo slot do buff_temp)
            db.set_buff_temp_expira(user['row'], expira_em)

    # ──────────────────────────────────────────────────────────────────────────
    #  !resetar_economia  (apenas o dono do bot)
    # ──────────────────────────────────────────────────────────────────────────

    @commands.command(name="resetar_economia", aliases=["reset_eco"])
    async def resetar_economia(self, ctx):
        if ctx.author.id != OWNER_ID:
            return  # silencioso — não expõe que o comando existe

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

        # ── 1. Coletar top 3 ANTES de zerar ──
        try:
            todos = self._todos_usuarios()
        except Exception as e:
            print(f"❌ Erro ao buscar usuários para o reset: {e}")
            return await ctx.send("❌ Erro ao buscar usuários. Reset abortado.")

        top3_ids = []
        top3_info = []   # [(posição, user_id, saldo_antigo)]

        for i, user in enumerate(todos[:3], start=1):
            uid = str(user['data'][0]) if user['data'][0] else None
            if uid:
                top3_ids.append(uid)
                top3_info.append((i, uid, db.parse_float(user['data'][2])))

        # ── 2. Zerar TODOS os usuários ──
        erros_reset = 0
        for user in todos:
            try:
                row = user['row']
                db.update_value(row, 3,  0.0)   # saldo
                db.update_value(row, 5,  0.0)   # timestamp último trabalho
                db.update_value(row, 6,  "")    # inventário
                db.update_value(row, 7,  0.0)   # timestamp último roubo / invest fixo
                db.update_value(row, 8,  0.0)   # timestamp invest fixo (bank)
                db.set_mascote(row, "", 0)       # mascote
                db.set_passivos(row, [])         # passivos
                # Zerar imposto, escudo e greve se existirem helpers no db
                try: db.set_imposto(row, "", 0)
                except Exception: pass
                try: db.set_escudo_data(row, 0)
                except Exception: pass
                try: db.set_greve(row, 0)
                except Exception: pass
                try: db.set_cripto_usos(row, 0, 0.0)
                except Exception: pass
                try: db.set_buff_temp_expira(row, 0)
                except Exception: pass
            except Exception as e:
                erros_reset += 1
                print(f"❌ Erro ao zerar usuário row={user.get('row')}: {e}")

        # Limpar bounties da memória
        if hasattr(self.bot, 'recompensas'):
            self.bot.recompensas.clear()
        if hasattr(self.bot, 'escudos_ativos'):
            self.bot.escudos_ativos.clear()
        if hasattr(self.bot, 'impostos'):
            self.bot.impostos.clear()
        if hasattr(self.bot, 'cascas'):
            self.bot.cascas.clear()

        # ── 3. Aplicar prêmios ao pódio ──
        premiados = []
        for posicao, uid, saldo_antigo in top3_info:
            user = db.get_user_data(uid)
            if not user:
                continue
            try:
                self._aplicar_premio(user, posicao)
                premiados.append((posicao, uid, saldo_antigo))
            except Exception as e:
                print(f"❌ Erro ao premiar posição {posicao} (uid={uid}): {e}")

        # ── 4. Anunciar resultado ──
        canal_id    = 1475606959247065118   # mesmo canal dos patchnotes
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
            buff_txt = f"\n✨ **Buff:** +20% no `!trabalhar` por {BUFF_DURACAO_DIAS} dias" if premio['buff'] else ""
            embed_reset.add_field(
                name=f"{medalhas[posicao]} {posicao}º lugar — {saldo_antigo:,.2f} MC acumulados",
                value=(
                    f"👤 {nome}\n"
                    f"🎁 **Itens:** {itens_fmt}\n"
                    f"💰 **MC iniciais:** `{premio['mc']:.0f} MC`"
                    f"{buff_txt}"
                ),
                inline=False
            )

        embed_reset.set_footer(text="Que a nova temporada seja épica. 🦍")
        await canal_anuncio.send(content="@everyone", embed=embed_reset)

        # Feedback privado ao owner
        aviso = f"✅ Reset concluído! {len(todos)} usuários zerados."
        if erros_reset:
            aviso += f" ⚠️ {erros_reset} erro(s) ao zerar — verifique o console."
        aviso += f"\n🏆 {len(premiados)} jogador(es) premiados."
        await ctx.author.send(aviso)

def setup(bot):
    bot.add_cog(ResetEconomia(bot))