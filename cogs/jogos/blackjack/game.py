import disnake
import asyncio
import database as db
from .constantes import NOME_PT
from .sapato import Sapato
from .side_bets import avaliar_21_3, avaliar_perfect_pairs


class BlackjackView(disnake.ui.View):
    def __init__(self, ctx, bot, aposta_base, players, sapato: Sapato,
                 side_bets: dict | None = None):
        super().__init__(timeout=120)
        self.ctx         = ctx
        self.bot         = bot
        self.message     = None
        self.aposta_base = round(float(aposta_base), 2)
        self.sapato      = sapato
        self.side_bets   = side_bets or {}

        self.players_data = {
            p.id: {
                "member": p, "hand": [], "hand2": [], "status": "jogando",
                "aposta": round(float(aposta_base), 2), "splitted": False, "current_hand": 1,
                "hand_ases_iniciais": 0,
                "hand2_ases_iniciais": 0,
                "sb_21_3_resultado": None,
                "sb_pp_resultado":   None,
            }
            for p in players
        }
        self.dealer_hand          = []
        self.player_ids           = [p.id for p in players]
        self.current_player_idx   = 0
        self.terminado            = False
        self.dealer_jogando       = False
        self._insurance_resolvido = False

    # ── Helpers de carta ──────────────────────────────────────────────────

    def _puxar_carta(self) -> dict:
        return self.sapato.puxar()

    def _calcular_pontos(self, hand: list, ases_iniciais: int = None) -> int:
        pontos = 0
        ases_flexiveis = 0

        for i, carta in enumerate(hand):
            if carta["valor"] == "A":
                if ases_iniciais is not None:
                    if ases_flexiveis + (pontos // 11) < ases_iniciais:
                        pontos += 11
                        ases_flexiveis += 1
                    else:
                        pontos += 1
                else:
                    if i < 2:
                        pontos += 11
                        ases_flexiveis += 1
                    else:
                        pontos += 1
            else:
                valores_map = {"J": 10, "Q": 10, "K": 10}
                pontos += valores_map.get(
                    carta["valor"],
                    int(carta["valor"]) if carta["valor"].isdigit() else 0
                )

        while pontos > 21 and ases_flexiveis > 0:
            pontos -= 10
            ases_flexiveis -= 1

        return pontos

    def _get_pontos_mao(self, p_id: int, mao: int = 1) -> int:
        p = self.players_data[p_id]
        if mao == 1:
            return self._calcular_pontos(p["hand"], p["hand_ases_iniciais"])
        return self._calcular_pontos(p["hand2"], p["hand2_ases_iniciais"])

    def _formatar_mao(self, hand: list, ocultar_primeira=False, dealer_aguardando=False) -> str:
        if not hand:
            return "Espere..."
        if ocultar_primeira:
            return f"❓, {hand[1]['valor']}{hand[1]['naipe']}"
        mao_str = ", ".join(f"{c['valor']}{c['naipe']}" for c in hand)
        if dealer_aguardando and self._calcular_pontos(hand) < 17:
            mao_str += ", ❓"
        return mao_str

    def _sapato_info(self) -> str:
        r = self.sapato.cartas_restantes
        t = self.sapato.total_inicial
        return f"🃏 Sapato: {r}/{t} cartas ({r/t*100:.0f}%)"

    def _dealer_mostra_as(self) -> bool:
        return len(self.dealer_hand) > 1 and self.dealer_hand[1]["valor"] == "A"

    # ── Side bets ─────────────────────────────────────────────────────────

    def _resolver_side_bets_iniciais(self) -> list[str]:
        msgs = []
        carta_dealer_aberta = self.dealer_hand[1]

        for p_id, p in self.players_data.items():
            sb = self.side_bets.get(p_id, {})
            c1, c2 = p["hand"][0], p["hand"][1]

            val_pp = sb.get("pp")
            if val_pp:
                nome_pp, mult_pp = avaliar_perfect_pairs(c1, c2)
                if nome_pp:
                    ganho_pp = round(val_pp * mult_pp, 2)
                    u_db = db.get_user_data(str(p_id))
                    if u_db:
                        db.update_value(u_db['row'], 3, round(db.parse_float(u_db['data'][2]) + ganho_pp, 2))
                    p["sb_pp_resultado"] = f"✅ {NOME_PT[nome_pp]} ({mult_pp}x) → +**{ganho_pp:.2f} MC**"
                    msgs.append(f"💎 **{p['member'].display_name}** — Perfect Pairs: {NOME_PT[nome_pp]} → **+{ganho_pp:.2f} MC**!")
                else:
                    p["sb_pp_resultado"] = f"❌ Sem par (perdeu {val_pp:.2f} MC)"

            val_21 = sb.get("21_3")
            if val_21:
                nome_21, mult_21 = avaliar_21_3(c1, c2, carta_dealer_aberta)
                if nome_21:
                    ganho_21 = round(val_21 * mult_21, 2)
                    u_db = db.get_user_data(str(p_id))
                    if u_db:
                        db.update_value(u_db['row'], 3, round(db.parse_float(u_db['data'][2]) + ganho_21, 2))
                    p["sb_21_3_resultado"] = f"✅ {NOME_PT[nome_21]} ({mult_21}x) → +**{ganho_21:.2f} MC**"
                    msgs.append(f"🃏 **{p['member'].display_name}** — 21+3: {NOME_PT[nome_21]} → **+{ganho_21:.2f} MC**!")
                else:
                    p["sb_21_3_resultado"] = f"❌ Sem combinação (perdeu {val_21:.2f} MC)"

        return msgs

    # ── Embed ─────────────────────────────────────────────────────────────

    async def atualizar_embed(self):
        if self.terminado:
            cor = disnake.Color.gold()
        elif self.dealer_jogando:
            cor = disnake.Color.blue()
        else:
            cor = disnake.Color.dark_purple()

        embed = disnake.Embed(title="🃏 MESA DE BLACKJACK (21)", color=cor)

        d_p = self._calcular_pontos(self.dealer_hand)
        mostrar_dealer = self.dealer_jogando or self.terminado
        embed.add_field(
            name   = "🏦 Dealer (Bot)",
            value  = f"Mão: `{self._formatar_mao(self.dealer_hand, not mostrar_dealer, self.dealer_jogando)}`\nPontos: {d_p if mostrar_dealer else '?'}",
            inline = False
        )

        p_atual_id = (
            self.player_ids[self.current_player_idx]
            if self.current_player_idx < len(self.player_ids) else None
        )

        # Habilita/desabilita botões do jogador atual
        if p_atual_id and not self.terminado and not self.dealer_jogando:
            p_atual = self.players_data[p_atual_id]
            v1 = self._calcular_pontos([p_atual["hand"][0]])
            v2 = self._calcular_pontos([p_atual["hand"][1]])
            pode_split  = len(p_atual["hand"]) == 2 and v1 == v2 and not p_atual["splitted"]
            pode_seguro = (
                self._dealer_mostra_as()
                and len(p_atual["hand"]) == 2
                and not p_atual["splitted"]
                and not self._insurance_resolvido
            )
            for child in self.children:
                if child.label == "Dividir (Split)":    child.disabled = not pode_split
                if child.label == "Dobrar (Double)":    child.disabled = p_atual["splitted"]
                if child.label == "Seguro (Insurance)": child.disabled = not pode_seguro

        # Campo de cada jogador
        for p_id in self.player_ids:
            p       = self.players_data[p_id]
            em_turno = (not self.terminado and not self.dealer_jogando and p_atual_id == p_id)
            p_p     = self._get_pontos_mao(p_id, 1)

            status_emoji = (
                "⏳" if em_turno           else
                "💥" if p["status"] == "estourou" else
                "🏳️" if p["status"] == "seguro"   else
                "✋" if p["status"] == "parou"     else "✅"
            )

            if p["splitted"]:
                p2_p = self._get_pontos_mao(p_id, 2)
                ind1 = "👉 " if em_turno and p["current_hand"] == 1 else ""
                ind2 = "👉 " if em_turno and p["current_hand"] == 2 else ""
                mao_str = (
                    f"{ind1}Mão 1: `{self._formatar_mao(p['hand'])}` ({p_p})\n"
                    f"{ind2}Mão 2: `{self._formatar_mao(p['hand2'])}` ({p2_p})"
                )
            else:
                mao_str = f"Mão: `{self._formatar_mao(p['hand'])}`\nPontos: `{p_p}`"

            res_txt = self._montar_resultado_jogador(p, p_id, p_p, d_p) if self.terminado else ""
            sb_txt  = self._montar_sb_txt(p)

            embed.add_field(
                name   = f"{status_emoji} {p['member'].display_name}",
                value  = f"{mao_str}\nAposta: `{p['aposta'] * (2 if p['splitted'] else 1):.2f} MC`{res_txt}{sb_txt}",
                inline = True
            )

        if self.terminado:
            footer = f"Partida finalizada! Prêmios entregues. • {self._sapato_info()}"
        elif self.dealer_jogando:
            footer = f"Aguarde o Dealer... • {self._sapato_info()}"
        else:
            footer = self._sapato_info()

        embed.set_footer(text=footer)

        try:
            if self.message:
                await self.message.edit(
                    embed=embed,
                    view=None if (self.terminado or self.dealer_jogando) else self
                )
        except Exception as e:
            print(f"Erro ao atualizar embed do Blackjack: {e}")

    def _montar_resultado_jogador(self, p: dict, p_id: int, p_p: int, d_p: int) -> str:
        def label_mao(pm, aposta_mao, status):
            if status == "seguro":              return f"🛡️ Acionou Seguro (devolvido: **{aposta_mao * 0.5:.2f} MC**)"
            if pm > 21:                         return "❌ Estourou"
            if d_p > 21 or pm > d_p:           return f"🏆 Venceu (**{aposta_mao * 2:.2f} MC**)"
            if pm == d_p:                       return f"🤝 Empatou (**{aposta_mao:.2f} MC**)"
            return "💀 Perdeu"

        if p["splitted"]:
            p2_p = self._get_pontos_mao(p_id, 2)
            return (
                f"\nResultados:\n"
                f"Mão 1: **{label_mao(p_p,  p['aposta'], p['status'])}**\n"
                f"Mão 2: **{label_mao(p2_p, p['aposta'], p['status'])}**"
            )
        return f"\nResultado: **{label_mao(p_p, p['aposta'], p['status'])}**"

    def _montar_sb_txt(self, p: dict) -> str:
        txt = ""
        if p.get("sb_pp_resultado"):  txt += f"\n💎 PP: {p['sb_pp_resultado']}"
        if p.get("sb_21_3_resultado"): txt += f"\n🃏 21+3: {p['sb_21_3_resultado']}"
        return txt

    # ── Botões ────────────────────────────────────────────────────────────

    @disnake.ui.button(label="Pedir (Hit)", style=disnake.ButtonStyle.green)
    async def hit(self, button, inter):
        if self.terminado or self.current_player_idx >= len(self.player_ids): return
        if inter.author.id != self.player_ids[self.current_player_idx]:
            return await inter.response.send_message("❌ Não é sua vez!", ephemeral=True)

        await inter.response.defer()
        p         = self.players_data[inter.author.id]
        nova_carta = self._puxar_carta()

        if p["splitted"] and p["current_hand"] == 2:
            p["hand2"].append(nova_carta)
            pontos_mao = self._get_pontos_mao(inter.author.id, 2)
        else:
            p["hand"].append(nova_carta)
            pontos_mao = self._get_pontos_mao(inter.author.id, 1)

        if pontos_mao >= 21:
            if p["splitted"] and p["current_hand"] == 1:
                p["current_hand"] = 2
                await self.atualizar_embed()
            else:
                p["status"] = "estourou" if pontos_mao > 21 else "parou"
                await self.atualizar_embed()
                await self._proximo_turno()
        else:
            await self.atualizar_embed()

    @disnake.ui.button(label="Parar (Stand)", style=disnake.ButtonStyle.grey)
    async def stand(self, button, inter):
        if self.terminado or self.current_player_idx >= len(self.player_ids): return
        if inter.author.id != self.player_ids[self.current_player_idx]:
            return await inter.response.send_message("❌ Não é sua vez!", ephemeral=True)

        await inter.response.defer()
        p = self.players_data[inter.author.id]
        if p["splitted"] and p["current_hand"] == 1:
            p["current_hand"] = 2
            await self.atualizar_embed()
        else:
            p["status"] = "parou"
            await self.atualizar_embed()
            await self._proximo_turno()

    @disnake.ui.button(label="Dobrar (Double)", style=disnake.ButtonStyle.blurple)
    async def double(self, button, inter):
        if self.terminado or self.current_player_idx >= len(self.player_ids): return
        p_id = inter.author.id
        if p_id != self.player_ids[self.current_player_idx]:
            return await inter.response.send_message("❌ Não é sua vez!", ephemeral=True)

        await inter.response.defer()
        p = self.players_data[p_id]
        try:
            u_db = db.get_user_data(str(p_id))
            if not u_db or db.parse_float(u_db['data'][2]) < p["aposta"]:
                return await inter.followup.send("❌ Saldo insuficiente para dobrar!", ephemeral=True)
            db.update_value(u_db['row'], 3, round(db.parse_float(u_db['data'][2]) - p["aposta"], 2))
            p["aposta"] *= 2
            p["hand"].append(self._puxar_carta())
            pontos = self._get_pontos_mao(p_id, 1)
            p["status"] = "estourou" if pontos > 21 else "parou"
            await self.atualizar_embed()
            await self._proximo_turno()
        except Exception as e:
            print(f"❌ Erro no Double: {e}")

    @disnake.ui.button(label="Dividir (Split)", style=disnake.ButtonStyle.danger, disabled=True)
    async def split(self, button, inter):
        if self.terminado or self.current_player_idx >= len(self.player_ids): return
        p_id = inter.author.id
        if p_id != self.player_ids[self.current_player_idx]:
            return await inter.response.send_message("❌ Não é sua vez!", ephemeral=True)

        await inter.response.defer()
        p = self.players_data[p_id]
        try:
            u_db = db.get_user_data(str(p_id))
            if not u_db or db.parse_float(u_db['data'][2]) < p["aposta"]:
                return await inter.followup.send("❌ Saldo insuficiente para o Split!", ephemeral=True)
            db.update_value(u_db['row'], 3, round(db.parse_float(u_db['data'][2]) - p["aposta"], 2))
            p["splitted"]      = True
            carta_separada     = p["hand"].pop()
            p["hand"].append(self._puxar_carta())
            p["hand2"]         = [carta_separada, self._puxar_carta()]
            p["hand_ases_iniciais"]  = sum(1 for c in p["hand"][:2]  if c["valor"] == "A")
            p["hand2_ases_iniciais"] = sum(1 for c in p["hand2"][:2] if c["valor"] == "A")
            await self.atualizar_embed()
        except Exception as e:
            print(f"❌ Erro no Split: {e}")

    @disnake.ui.button(label="Seguro (Insurance)", style=disnake.ButtonStyle.secondary, disabled=True, row=1)
    async def insurance(self, button, inter):
        if self.terminado or self.current_player_idx >= len(self.player_ids): return
        p_id = inter.author.id
        if p_id != self.player_ids[self.current_player_idx]:
            return await inter.response.send_message("❌ Não é sua vez!", ephemeral=True)

        await inter.response.defer()
        p = self.players_data[p_id]
        try:
            u_db = db.get_user_data(str(p_id))
            if not u_db:
                return await inter.followup.send("❌ Conta não encontrada!", ephemeral=True)
            saldo = db.parse_float(u_db['data'][2])
            db.update_value(u_db['row'], 3, round(saldo + p["aposta"] * 0.5, 2))
            p["status"] = "seguro"
            self._insurance_resolvido = True
            await self.atualizar_embed()
            await self._proximo_turno()
        except Exception as e:
            print(f"❌ Erro no Seguro: {e}")

    # ── Timeout ───────────────────────────────────────────────────────────

    async def on_timeout(self):
        if self.terminado:
            return
        self.terminado = True
        for item in self.children:
            item.disabled = True

        for p_id, p in self.players_data.items():
            if p["status"] not in ("jogando", "parou"):
                continue
            try:
                u_db = db.get_user_data(str(p_id))
                if u_db:
                    saldo = db.parse_float(u_db['data'][2])
                    db.update_value(u_db['row'], 3, round(saldo + p["aposta"], 2))
            except Exception as e:
                print(f"❌ Erro ao devolver aposta no timeout: {e}")

        try:
            if self.message:
                embed = disnake.Embed(
                    title       = "⏰ Mesa de Blackjack encerrada por inatividade",
                    description = "As apostas dos jogadores ativos foram devolvidas.",
                    color       = disnake.Color.orange()
                )
                await self.message.edit(embed=embed, view=None)
        except Exception:
            pass

    # ── Fluxo do jogo ─────────────────────────────────────────────────────

    async def _proximo_turno(self):
        self.current_player_idx += 1
        while (
            self.current_player_idx < len(self.player_ids) and
            self.players_data[self.player_ids[self.current_player_idx]]["status"] != "jogando"
        ):
            self.current_player_idx += 1

        if self.current_player_idx >= len(self.player_ids):
            precisa_animar = any(p["status"] == "parou" for p in self.players_data.values())

            if precisa_animar:
                self.dealer_jogando = True
                await self.atualizar_embed()
                await asyncio.sleep(1.5)
                while self._calcular_pontos(self.dealer_hand) < 17:
                    self.dealer_hand.append(self._puxar_carta())
                    await self.atualizar_embed()
                    if self._calcular_pontos(self.dealer_hand) < 17:
                        await asyncio.sleep(2.0)
                self.dealer_jogando = False

            self.terminado = True
            await self._processar_pagamentos()
            await self.atualizar_embed()

    async def _processar_pagamentos(self):
        d_p = self._calcular_pontos(self.dealer_hand)

        def lucro_mao(pontos: int, aposta_mao: float) -> float:
            if pontos > 21:               return 0.0
            if d_p > 21 or pontos > d_p: return aposta_mao * 2.0
            if pontos == d_p:             return aposta_mao
            return 0.0

        for p_id, p in self.players_data.items():
            if p["status"] == "seguro":
                continue
            try:
                u_db = db.get_user_data(str(p_id))
                if not u_db:
                    continue
                saldo = db.parse_float(u_db['data'][2])
                ganho = lucro_mao(self._get_pontos_mao(p_id, 1), p["aposta"])
                if p["splitted"]:
                    ganho += lucro_mao(self._get_pontos_mao(p_id, 2), p["aposta"])
                if ganho > 0:
                    db.update_value(u_db['row'], 3, round(saldo + ganho, 2))
            except Exception as e:
                print(f"❌ Erro ao pagar jogador {p_id}: {e}")