import disnake
from disnake.ext import commands
import database as db
import random
import asyncio

LIMITES_CARGO = {
    "Lêmure":      400,
    "Macaquinho":  1500,
    "Babuíno":     4500,
    "Chimpanzé":   12000,
    "Orangutango": 30000,
    "Gorila":      80000,
    "Ancestral":   250000,
    "Rei Símio":   1500000,
}

def get_limite(cargo):
    return LIMITES_CARGO.get(cargo, 250)


class LobbyView(disnake.ui.View):
    """Lobby de entrada do Blackjack com botões Entrar e Começar."""
    def __init__(self, ctx, bot, aposta: float, players: list):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bot = bot
        self.aposta = aposta
        self.players = players
        self.started = False
        self.cancelled = False
        self.msg = None

    MAX_JOGADORES = 6

    @disnake.ui.button(label="🃏 Entrar", style=disnake.ButtonStyle.success)
    async def entrar(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author in self.players:
            return await inter.response.send_message("🐒 Você já está na mesa!", ephemeral=True)
        if len(self.players) >= self.MAX_JOGADORES:
            return await inter.response.send_message(f"🚫 A mesa está cheia! Máximo de **{self.MAX_JOGADORES} jogadores**.", ephemeral=True)
        u_db = db.get_user_data(str(inter.author.id))
        if not u_db:
            return await inter.response.send_message("❌ Conta não encontrada!", ephemeral=True)
        cargo_p = u_db['data'][3] if len(u_db['data']) > 3 else "Lêmure"
        if self.aposta > get_limite(cargo_p):
            return await inter.response.send_message(f"🚫 Aposta excede seu limite de **{cargo_p}**.", ephemeral=True)
        if db.parse_float(u_db['data'][2]) < self.aposta:
            return await inter.response.send_message("❌ Saldo insuficiente!", ephemeral=True)
        db.update_value(u_db['row'], 3, round(db.parse_float(u_db['data'][2]) - self.aposta, 2))
        self.players.append(inter.author)
        await inter.response.edit_message(content=self._lobby_text())

    @disnake.ui.button(label="▶️ Começar", style=disnake.ButtonStyle.primary)
    async def comecar(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author.id != self.ctx.author.id:
            return await inter.response.send_message("❌ Só o dono da mesa pode iniciar!", ephemeral=True)
        self.started = True
        for item in self.children:
            item.disabled = True
        await inter.response.edit_message(content="✅ Mesa iniciada!", view=self)
        self.stop()

    def _lobby_text(self):
        nomes = ", ".join([p.display_name for p in self.players])
        return (
            f"🃏 **BLACKJACK!** Dono: {self.ctx.author.mention} | Aposta: `{self.aposta:.2f} MC`\n"
            f"👥 **Jogadores ({len(self.players)}):** {nomes}\n\n"
            f"Clique **Entrar** para participar ou **Começar** para iniciar!"
        )

    async def on_timeout(self):
        self.cancelled = True
        self.stop()


class BlackjackView(disnake.ui.View):
    def __init__(self, ctx, bot, aposta_base, players):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.bot = bot
        self.message = None
        self.aposta_base = round(float(aposta_base), 2)
        self.players_data = {
            p.id: {"member": p, "hand": [], "hand2": [], "status": "jogando",
                   "aposta": round(float(aposta_base), 2), "splitted": False, "current_hand": 1}
            for p in players
        }
        self.dealer_hand = []
        self.deck = self._gerar_baralho()
        self.player_ids = [p.id for p in players]
        self.current_player_idx = 0
        self.terminado = False
        self.dealer_jogando = False 

    def _gerar_baralho(self):
        naipes = ["♠️", "♥️", "♦️", "♣️"]
        valores = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        deck = [{"valor": v, "naipe": n} for v in valores for n in naipes]
        random.shuffle(deck)
        return deck

    def _calcular_pontos(self, hand):
        pontos, ases = 0, 0
        valores_map = {"A": 11, "J": 10, "Q": 10, "K": 10}
        for carta in hand:
            if carta["valor"] == "A": ases += 1
            pontos += valores_map.get(carta["valor"], int(carta["valor"]) if carta["valor"].isdigit() else 0)
        while pontos > 21 and ases > 0:
            pontos -= 10
            ases -= 1
        return pontos

    def _formatar_mao(self, hand, ocultar_primeira=False, dealer_aguardando=False):
        if not hand: return "Espere..."
        if ocultar_primeira: return f"❓, {hand[1]['valor']}{hand[1]['naipe']}"
        mao_formatada = ", ".join([f"{c['valor']}{c['naipe']}" for c in hand])
        # Mostra ❓ SOMENTE se o dealer ainda vai puxar (pontos < 17 e não estourou)
        if dealer_aguardando and self._calcular_pontos(hand) < 17:
            mao_formatada += ", ❓"
        return mao_formatada

    async def atualizar_embed(self):
        cor = disnake.Color.dark_purple() if not self.terminado else disnake.Color.gold()
        if self.dealer_jogando:
            cor = disnake.Color.blue() 

        embed = disnake.Embed(title="🃏 MESA DE BLACKJACK (21)", color=cor)

        d_p = self._calcular_pontos(self.dealer_hand)
        
        mostrar_dealer = self.dealer_jogando or self.terminado
        
        # Formata a mão do dealer com a interrogação se ele estiver jogando
        mao_dealer_str = self._formatar_mao(self.dealer_hand, not mostrar_dealer, self.dealer_jogando)

        embed.add_field(
            name="🏦 Dealer (Bot)",
            value=f"Mão: `{mao_dealer_str}`\nPontos: {d_p if mostrar_dealer else '?'}",
            inline=False
        )

        p_atual_id = self.player_ids[self.current_player_idx] if self.current_player_idx < len(self.player_ids) else None

        if p_atual_id and not self.terminado and not self.dealer_jogando:
            p_atual_data = self.players_data[p_atual_id]
            v1 = self._calcular_pontos([p_atual_data["hand"][0]])
            v2 = self._calcular_pontos([p_atual_data["hand"][1]])
            pode_split = len(p_atual_data["hand"]) == 2 and v1 == v2 and not p_atual_data["splitted"]
            
            pode_seguro = False
            if len(self.dealer_hand) > 1 and self.dealer_hand[1]['valor'] == 'A':
                if len(p_atual_data["hand"]) == 2 and not p_atual_data["splitted"]:
                    pode_seguro = True

            for child in self.children:
                if child.label == "Dividir (Split)": child.disabled = not pode_split
                if child.label == "Dobrar (Double)": child.disabled = p_atual_data["splitted"]
                if child.label == "Seguro": child.disabled = not pode_seguro

        for p_id in self.player_ids:
            p = self.players_data[p_id]
            em_turno = (not self.terminado and not self.dealer_jogando and p_atual_id == p_id)
            status_emoji = "⏳" if em_turno else ("💥" if p["status"] == "estourou" else "🛡️" if p["status"] == "seguro" else "✋" if p["status"] == "parou" else "✅")
            p_p = self._calcular_pontos(p["hand"])

            if p["splitted"]:
                p2_p = self._calcular_pontos(p["hand2"])
                ind1 = "👉 " if em_turno and p["current_hand"] == 1 else ""
                ind2 = "👉 " if em_turno and p["current_hand"] == 2 else ""
                mao_str = f"{ind1}Mão 1: `{self._formatar_mao(p['hand'])}` ({p_p})\n{ind2}Mão 2: `{self._formatar_mao(p['hand2'])}` ({p2_p})"
            else:
                mao_str = f"Mão: `{self._formatar_mao(p['hand'])}`\nPontos: `{p_p}`"

            res_txt = ""
            if self.terminado:
                def resultado_mao(pm, aposta_mao, status, dealer_pts=d_p):
                    if status == "seguro": return "🛡️ Acionou Seguro"
                    if pm > 21: return "❌ Estourou"
                    if dealer_pts > 21 or pm > dealer_pts:
                        return f"🏆 Venceu (**{(aposta_mao * 2):.2f} MC**)"
                    if pm == dealer_pts:
                        return f"🤝 Empatou (**{aposta_mao:.2f} MC**)"
                    return "💀 Perdeu"

                if p["splitted"]:
                    res_txt = (f"\nResultados:\n"
                               f"Mão 1: **{resultado_mao(p_p, p['aposta'], p['status'])}**\n"
                               f"Mão 2: **{resultado_mao(p2_p, p['aposta'], p['status'])}**")
                else:
                    res_txt = f"\nResultado: **{resultado_mao(p_p, p['aposta'], p['status'])}**"

            embed.add_field(
                name=f"{status_emoji} {p['member'].display_name}",
                value=f"{mao_str}\nAposta: `{p['aposta'] * (2 if p['splitted'] else 1):.2f} MC`{res_txt}",
                inline=True
            )

        if self.terminado:
            embed.set_footer(text="Partida finalizada! Prêmios entregues.")
        elif self.dealer_jogando:
            embed.set_footer(text="Aguarde o Dealer...")

        try:
            if self.message:
                await self.message.edit(embed=embed, view=None if (self.terminado or self.dealer_jogando) else self)
        except Exception as e:
            print(f"Erro ao atualizar embed do Blackjack: {e}")

    @disnake.ui.button(label="Pedir (Hit)", style=disnake.ButtonStyle.green)
    async def hit(self, button, inter):
        if self.terminado or self.current_player_idx >= len(self.player_ids): return
        if inter.author.id != self.player_ids[self.current_player_idx]:
            return await inter.response.send_message("❌ Não é sua vez!", ephemeral=True)
        
        await inter.response.defer()
        p = self.players_data[inter.author.id]
        mao_atual = p["hand"] if not p["splitted"] or p["current_hand"] == 1 else p["hand2"]
        mao_atual.append(self.deck.pop())
        
        if self._calcular_pontos(mao_atual) >= 21:
            if p["splitted"] and p["current_hand"] == 1: 
                p["current_hand"] = 2
                await self.atualizar_embed()
            else:
                p["status"] = "estourou" if self._calcular_pontos(mao_atual) > 21 else "parou"
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
            p["hand"].append(self.deck.pop())
            p["status"] = "estourou" if self._calcular_pontos(p["hand"]) > 21 else "parou"
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
            p["splitted"] = True
            carta_separada = p["hand"].pop()
            p["hand2"] = [carta_separada, self.deck.pop()]
            p["hand"].append(self.deck.pop())
            await self.atualizar_embed()
        except Exception as e:
            print(f"❌ Erro no Split: {e}")

    @disnake.ui.button(label="Seguro", style=disnake.ButtonStyle.secondary, disabled=True)
    async def seguro(self, button, inter):
        if self.terminado or self.current_player_idx >= len(self.player_ids): return
        p_id = inter.author.id
        if p_id != self.player_ids[self.current_player_idx]:
            return await inter.response.send_message("❌ Não é sua vez!", ephemeral=True)
        
        await inter.response.defer()
        p = self.players_data[p_id]
        try:
            u_db = db.get_user_data(str(p_id))
            if u_db:
                saldo = db.parse_float(u_db['data'][2])
                devolucao = p["aposta"] / 2
                db.update_value(u_db['row'], 3, round(saldo + devolucao, 2))
                
            p["status"] = "seguro"
            await self.atualizar_embed()
            await self._proximo_turno()
        except Exception as e:
            print(f"❌ Erro no Seguro: {e}")

    async def on_timeout(self):
        """Devolve as apostas se a partida expirar por inatividade."""
        if self.terminado:
            return
        self.terminado = True
        for item in self.children:
            item.disabled = True
        for p_id, p in self.players_data.items():
            # Só devolve quem ainda estava jogando ou parou — estourou perdeu,
            # seguro já devolveu metade na hora
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
                    title="⏰ Mesa de Blackjack encerrada por inatividade",
                    description="As apostas dos jogadores ativos foram devolvidas.",
                    color=disnake.Color.orange()
                )
                await self.message.edit(embed=embed, view=None)
        except:
            pass

    async def _proximo_turno(self):
        self.current_player_idx += 1

        # Pula jogadores que já têm status definido (21 natural, estourou, etc.)
        while (self.current_player_idx < len(self.player_ids) and
               self.players_data[self.player_ids[self.current_player_idx]]["status"] != "jogando"):
            self.current_player_idx += 1

        if self.current_player_idx >= len(self.player_ids):
            # Verifica se TODOS os jogadores na mesa estouraram ou acionaram seguro
            # Se sim, não há por que o dealer fazer a animação de puxar cartas
            precisa_animar = False
            for p in self.players_data.values():
                if p["status"] == "parou":
                    precisa_animar = True
                    break

            if precisa_animar:
                self.dealer_jogando = True

                # Revela as cartas do dealer antes de começar a puxar
                await self.atualizar_embed()
                await asyncio.sleep(1.5)

                # Puxa cartas SOMENTE enquanto o dealer ainda precisa (< 17).
                # A checagem do score acontece no while, ANTES de puxar a próxima carta.
                # Depois de puxar, só dorme se ainda for necessária mais uma carta,
                # evitando o delay desnecessário na última carta puxada.
                while self._calcular_pontos(self.dealer_hand) < 17:
                    self.dealer_hand.append(self.deck.pop())
                    await self.atualizar_embed()
                    if self._calcular_pontos(self.dealer_hand) < 17:
                        await asyncio.sleep(2.0)

                self.dealer_jogando = False
            else:
                # Se ninguém parou normalmente (todos estouraram ou pegaram seguro),
                # o dealer não precisa animar, apenas revela e encerra.
                pass

            self.terminado = True
            await self._processar_pagamentos()
            await self.atualizar_embed()

    async def _processar_pagamentos(self):
        d_p = self._calcular_pontos(self.dealer_hand)

        def lucro_mao(pontos, aposta_mao):
            if pontos > 21: return 0.0
            if d_p > 21 or pontos > d_p: return aposta_mao * 2.0
            if pontos == d_p: return aposta_mao
            return 0.0

        for p_id, p in self.players_data.items():
            if p["status"] == "seguro": 
                continue 

            try:
                u_db = db.get_user_data(str(p_id))
                if not u_db: continue
                saldo = db.parse_float(u_db['data'][2])
                ganho = lucro_mao(self._calcular_pontos(p["hand"]), p["aposta"])
                if p["splitted"]:
                    ganho += lucro_mao(self._calcular_pontos(p["hand2"]), p["aposta"])
                if ganho > 0:
                    db.update_value(u_db['row'], 3, round(saldo + ganho, 2))
            except Exception as e:
                print(f"❌ Erro ao pagar jogador {p_id}: {e}")


class BlackjackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, vai para o canal {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["bj", "21"])
    async def blackjack(self, ctx, aposta: float = None):
        if aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!blackjack <valor>` ou `!21 <valor>`")
        if aposta <= 0:
            return await ctx.send("❌ Aposta inválida!")
        aposta = round(aposta, 2)

        try:
            u_c = db.get_user_data(str(ctx.author.id))
            if not u_c:
                return await ctx.send("❌ Conta não encontrada!")

            cargo = u_c['data'][3] if len(u_c['data']) > 3 else "Lêmure"
            saldo = db.parse_float(u_c['data'][2])
            if aposta > get_limite(cargo):
                return await ctx.send(f"🚫 Como **{cargo}**, seu limite é de **{get_limite(cargo)} MC**.")
            if saldo < aposta:
                return await ctx.send("❌ Saldo insuficiente!")

            db.update_value(u_c['row'], 3, round(saldo - aposta, 2))
            players = [ctx.author]

            lobby_view = LobbyView(ctx, self.bot, aposta, players)
            msg = await ctx.send(lobby_view._lobby_text(), view=lobby_view)
            lobby_view.msg = msg

            await lobby_view.wait()

            if lobby_view.cancelled and not lobby_view.started:
                for p in players:
                    p_db = db.get_user_data(str(p.id))
                    if p_db:
                        db.update_value(p_db['row'], 3, round(db.parse_float(p_db['data'][2]) + aposta, 2))
                return await ctx.send("⏰ Mesa cancelada por inatividade. Valores devolvidos.")

            if not lobby_view.started:
                for p in players:
                    p_db = db.get_user_data(str(p.id))
                    if p_db:
                        db.update_value(p_db['row'], 3, round(db.parse_float(p_db['data'][2]) + aposta, 2))
                return await ctx.send("⏰ Mesa cancelada. Valores devolvidos.")

            # Apaga a mensagem do lobby antes de iniciar o jogo
            try:
                await lobby_view.msg.delete()
            except:
                pass

            view = BlackjackView(ctx, self.bot, aposta, players)
            view.dealer_hand = [view.deck.pop(), view.deck.pop()]
            for p_id in view.player_ids:
                view.players_data[p_id]["hand"] = [view.deck.pop(), view.deck.pop()]

            embed_loading = disnake.Embed(title="🃏 Embaralhando as cartas...", color=disnake.Color.dark_purple())
            msg = await ctx.send(embed=embed_loading)
            view.message = msg

            # Verificar Blackjack Natural (21 nas 2 primeiras cartas)
            for p_id in view.player_ids:
                if view._calcular_pontos(view.players_data[p_id]["hand"]) == 21:
                    view.players_data[p_id]["status"] = "parou"

            await view.atualizar_embed()

            # Avança o índice até o próximo jogador que ainda precisa jogar
            while (view.current_player_idx < len(view.player_ids) and
                   view.players_data[view.player_ids[view.current_player_idx]]["status"] == "parou"):
                view.current_player_idx += 1

            # Se não sobrou ninguém para jogar, vai direto para o dealer
            if view.current_player_idx >= len(view.player_ids):
                await view._proximo_turno()
                return

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !blackjack de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(BlackjackCog(bot))