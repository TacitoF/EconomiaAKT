import disnake
from disnake.ext import commands
import database as db
import random
import asyncio

LIMITES_CARGO = {
    "Lêmure": 250, "Macaquinho": 800, "Babuíno": 2000, "Chimpanzé": 6000,
    "Orangutango": 15000, "Gorila": 45000, "Ancestral": 150000, "Rei Símio": 1500000
}

def get_limite(cargo):
    return LIMITES_CARGO.get(cargo, 250)

class BlackjackView(disnake.ui.View):
    def __init__(self, ctx, bot, aposta_base, players):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.bot = bot
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

    def _formatar_mao(self, hand, ocultar_primeira=False):
        if not hand: return "Espere..."
        if ocultar_primeira: return f"❓, {hand[1]['valor']}{hand[1]['naipe']}"
        return ", ".join([f"{c['valor']}{c['naipe']}" for c in hand])

    async def atualizar_embed(self, inter=None):
        cor = disnake.Color.dark_purple() if not self.terminado else disnake.Color.gold()
        embed = disnake.Embed(title="🃏 MESA DE BLACKJACK (21)", color=cor)

        d_p = self._calcular_pontos(self.dealer_hand)
        embed.add_field(
            name="🏦 Dealer (Bot)",
            value=f"Mão: `{self._formatar_mao(self.dealer_hand, not self.terminado)}`\nPontos: {d_p if self.terminado else '?'}",
            inline=False
        )

        p_atual_id = self.player_ids[self.current_player_idx] if self.current_player_idx < len(self.player_ids) else None

        if p_atual_id and not self.terminado:
            p_atual_data = self.players_data[p_atual_id]
            v1 = self._calcular_pontos([p_atual_data["hand"][0]])
            v2 = self._calcular_pontos([p_atual_data["hand"][1]])
            pode_split = len(p_atual_data["hand"]) == 2 and v1 == v2 and not p_atual_data["splitted"]
            for child in self.children:
                if child.label == "Dividir (Split)": child.disabled = not pode_split
                if child.label == "Dobrar (Double)": child.disabled = p_atual_data["splitted"]

        for p_id in self.player_ids:
            p = self.players_data[p_id]
            em_turno = (not self.terminado and p_atual_id == p_id)
            status_emoji = "⏳" if em_turno else ("💥" if p["status"] == "estourou" else "✋" if p["status"] == "parou" else "✅")
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
                def resultado_mao(pm):
                    if pm > 21: return "❌ Estourou"
                    if d_p > 21 or pm > d_p: return "🏆 Venceu"
                    if pm == d_p: return "🤝 Empatou (Devolvido)"
                    return "💀 Perdeu"
                res_txt = f"\nMão 1: **{resultado_mao(p_p)}**\nMão 2: **{resultado_mao(p2_p)}**" if p["splitted"] else f"\nResultado: **{resultado_mao(p_p)}**"

            embed.add_field(
                name=f"{status_emoji} {p['member'].display_name}",
                value=f"{mao_str}\nAposta: `{p['aposta'] * (2 if p['splitted'] else 1):.2f} C`{res_txt}",
                inline=True
            )

        if self.terminado:
            embed.set_footer(text="Partida finalizada! Prêmios entregues.")

        if inter:
            await inter.response.edit_message(embed=embed, view=None if self.terminado else self)
        else:
            return embed

    @disnake.ui.button(label="Pedir (Hit)", style=disnake.ButtonStyle.green)
    async def hit(self, button, inter):
        if self.terminado or self.current_player_idx >= len(self.player_ids): return
        if inter.author.id != self.player_ids[self.current_player_idx]:
            return await inter.send("❌ Não é sua vez!", ephemeral=True)
        p = self.players_data[inter.author.id]
        mao_atual = p["hand"] if not p["splitted"] or p["current_hand"] == 1 else p["hand2"]
        mao_atual.append(self.deck.pop())
        if self._calcular_pontos(mao_atual) >= 21:
            if p["splitted"] and p["current_hand"] == 1: p["current_hand"] = 2
            else:
                p["status"] = "parou"
                await self._proximo_turno()
        await self.atualizar_embed(inter)

    @disnake.ui.button(label="Parar (Stand)", style=disnake.ButtonStyle.grey)
    async def stand(self, button, inter):
        if self.terminado or self.current_player_idx >= len(self.player_ids): return
        if inter.author.id != self.player_ids[self.current_player_idx]:
            return await inter.send("❌ Não é sua vez!", ephemeral=True)
        p = self.players_data[inter.author.id]
        if p["splitted"] and p["current_hand"] == 1: p["current_hand"] = 2
        else:
            p["status"] = "parou"
            await self._proximo_turno()
        await self.atualizar_embed(inter)

    @disnake.ui.button(label="Dobrar (Double)", style=disnake.ButtonStyle.blurple)
    async def double(self, button, inter):
        if self.terminado or self.current_player_idx >= len(self.player_ids): return
        p_id = inter.author.id
        if p_id != self.player_ids[self.current_player_idx]:
            return await inter.send("❌ Não é sua vez!", ephemeral=True)
        p = self.players_data[p_id]
        try:
            u_db = db.get_user_data(str(p_id))
            if not u_db or db.parse_float(u_db['data'][2]) < p["aposta"]:
                return await inter.send("❌ Saldo insuficiente para dobrar!", ephemeral=True)
            db.update_value(u_db['row'], 3, round(db.parse_float(u_db['data'][2]) - p["aposta"], 2))
            p["aposta"] *= 2
            p["hand"].append(self.deck.pop())
            p["status"] = "parou"
            await self._proximo_turno()
            await self.atualizar_embed(inter)
        except Exception as e:
            print(f"❌ Erro no Double: {e}")

    @disnake.ui.button(label="Dividir (Split)", style=disnake.ButtonStyle.danger, disabled=True)
    async def split(self, button, inter):
        if self.terminado or self.current_player_idx >= len(self.player_ids): return
        p_id = inter.author.id
        if p_id != self.player_ids[self.current_player_idx]:
            return await inter.send("❌ Não é sua vez!", ephemeral=True)
        p = self.players_data[p_id]
        try:
            u_db = db.get_user_data(str(p_id))
            if not u_db or db.parse_float(u_db['data'][2]) < p["aposta"]:
                return await inter.send("❌ Saldo insuficiente para o Split!", ephemeral=True)
            db.update_value(u_db['row'], 3, round(db.parse_float(u_db['data'][2]) - p["aposta"], 2))
            p["splitted"] = True
            carta_separada = p["hand"].pop()
            p["hand2"] = [carta_separada, self.deck.pop()]
            p["hand"].append(self.deck.pop())
            await self.atualizar_embed(inter)
        except Exception as e:
            print(f"❌ Erro no Split: {e}")

    async def _proximo_turno(self):
        self.current_player_idx += 1
        if self.current_player_idx >= len(self.player_ids):
            self.terminado = True
            while self._calcular_pontos(self.dealer_hand) < 17:
                self.dealer_hand.append(self.deck.pop())
            await self._processar_pagamentos()

    async def _processar_pagamentos(self):
        d_p = self._calcular_pontos(self.dealer_hand)

        def lucro_mao(pontos, aposta_mao):
            if pontos > 21: return 0.0
            if d_p > 21 or pontos > d_p: return aposta_mao * 2.0
            if pontos == d_p: return aposta_mao
            return 0.0

        for p_id, p in self.players_data.items():
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
                return await ctx.send(f"🚫 Como **{cargo}**, seu limite é de **{get_limite(cargo)} C**.")
            if saldo < aposta:
                return await ctx.send("❌ Saldo insuficiente!")

            db.update_value(u_c['row'], 3, round(saldo - aposta, 2))
            players = [ctx.author]

            def gerar_texto_lobby(lista):
                nomes = ", ".join([p.display_name for p in lista])
                return (f"🃏 **BLACKJACK!** Dono: {ctx.author.mention} | Aposta: `{aposta:.2f} C`\n"
                        f"👥 **Jogadores ({len(lista)}):** {nomes}\n\nDigite `!entrar` para participar ou **`começar`** para iniciar!")

            msg = await ctx.send(gerar_texto_lobby(players))

            def check(m):
                return m.channel == ctx.channel and (
                    m.content.lower() == '!entrar' or
                    (m.author == ctx.author and m.content.lower() == 'começar')
                )

            start = False
            while True:
                try:
                    m = await self.bot.wait_for('message', check=check, timeout=60.0)
                    if m.content.lower() == 'começar':
                        start = True
                        break
                    if m.content.lower() == '!entrar' and m.author not in players:
                        u_db = db.get_user_data(str(m.author.id))
                        if not u_db: continue
                        cargo_p = u_db['data'][3] if len(u_db['data']) > 3 else "Lêmure"
                        if aposta > get_limite(cargo_p):
                            await ctx.send(f"🚫 {m.author.mention}, aposta excede seu limite de **{cargo_p}**.", delete_after=6)
                            continue
                        if db.parse_float(u_db['data'][2]) >= aposta:
                            db.update_value(u_db['row'], 3, round(db.parse_float(u_db['data'][2]) - aposta, 2))
                            players.append(m.author)
                            await msg.edit(content=gerar_texto_lobby(players))
                        else:
                            await ctx.send(f"❌ {m.author.mention}, saldo insuficiente!", delete_after=6)
                except asyncio.TimeoutError:
                    break

            if not start:
                for p in players:
                    p_db = db.get_user_data(str(p.id))
                    if p_db:
                        db.update_value(p_db['row'], 3, round(db.parse_float(p_db['data'][2]) + aposta, 2))
                return await ctx.send("⏰ Mesa cancelada. Valores devolvidos.")

            view = BlackjackView(ctx, self.bot, aposta, players)
            view.dealer_hand = [view.deck.pop(), view.deck.pop()]
            for p_id in view.player_ids:
                view.players_data[p_id]["hand"] = [view.deck.pop(), view.deck.pop()]
            await ctx.send(embed=await view.atualizar_embed(), view=view)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !blackjack de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(BlackjackCog(bot))