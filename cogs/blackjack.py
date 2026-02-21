import disnake
from disnake.ext import commands
import database as db
import random
import asyncio

def get_limite_bj(cargo):
    """Função auxiliar para retornar o limite de aposta baseado no cargo."""
    limites = {
        "Macaquinho": 500,
        "Chimpanzé": 2000,
        "Orangutango": 10000,
        "Gorila": 50000
    }
    return limites.get(cargo, 500)

class BlackjackView(disnake.ui.View):
    def __init__(self, ctx, bot, aposta_base, players):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.bot = bot
        self.players_data = {p.id: {"member": p, "hand": [], "status": "jogando", "aposta": aposta_base, "splitted": False} for p in players}
        self.dealer_hand = []
        self.deck = self.gerar_baralho()
        self.player_ids = [p.id for p in players]
        self.current_player_idx = 0
        self.terminado = False

    def gerar_baralho(self):
        naipes = ["♠️", "♥️", "♦️", "♣️"]
        valores = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        deck = [{"valor": v, "naipe": n} for v in valores for n in naipes]
        random.shuffle(deck)
        return deck

    def calcular_pontos(self, hand):
        pontos = 0
        ases = 0
        valores_map = {"A": 11, "J": 10, "Q": 10, "K": 10}
        for carta in hand:
            if carta["valor"] == "A": ases += 1
            pontos += valores_map.get(carta["valor"], 0) or int(carta["valor"] if carta["valor"].isdigit() else 0)
        while pontos > 21 and ases > 0:
            pontos -= 10
            ases -= 1
        return pontos

    def formatar_mao(self, hand, ocultar_primeira=False):
        if not hand: return "Espere..."
        if ocultar_primeira: return f"❓, {hand[1]['valor']}{hand[1]['naipe']}"
        return ", ".join([f"{c['valor']}{c['naipe']}" for c in hand])

    async def atualizar_embed(self, inter=None):
        cor = disnake.Color.dark_purple() if not self.terminado else disnake.Color.gold()
        embed = disnake.Embed(title="🃏 MESA DE BLACKJACK (21)", color=cor)
        
        d_p = self.calcular_pontos(self.dealer_hand)
        status_dealer = f"Pontos: {d_p}" if self.terminado else "Pontos: ?"
        embed.add_field(name="🏦 Dealer (Bot)", value=f"Mão: `{self.formatar_mao(self.dealer_hand, not self.terminado)}`\n{status_dealer}", inline=False)
            # Pega o ID do jogador do turno atual
        p_atual_id = self.player_ids[self.current_player_idx] if self.current_player_idx < len(self.player_ids) else None
        
        if p_atual_id and not self.terminado:
            p_atual_data = self.players_data[p_atual_id]
            
            # --- NOVA LÓGICA DE SPLIT POR VALOR ---
            # Calculamos o valor individual de cada uma das duas cartas
            v1 = self.calcular_pontos([p_atual_data["hand"][0]])
            v2 = self.calcular_pontos([p_atual_data["hand"][1]])
            
            # Agora ele permite split se os PONTOS forem iguais (ex: 10 e J)
            pode_split = len(p_atual_data["hand"]) == 2 and v1 == v2 and not p_atual_data["splitted"]
            # --------------------------------------

            for child in self.children:
                if child.label == "Dividir (Split)":
                    child.disabled = not pode_split

        for p_id in self.player_ids:
            p = self.players_data[p_id]
            em_turno = (not self.terminado and p_atual_id == p_id)
            status_emoji = "⏳" if em_turno else "✅"
            if p["status"] == "estourou": status_emoji = "💥"
            if p["status"] == "parou": status_emoji = "✋"
            
            p_p = self.calcular_pontos(p["hand"])
            res_txt = ""
            
            if self.terminado:
                if p_p > 21 and d_p > 21: 
                    res_txt = "\n🤝 **EMPATE (Ambos Estouraram)**"
                elif p_p > 21: 
                    res_txt = "\n❌ **ESTOUROU**"
                elif d_p > 21 or p_p > d_p: 
                    lucro_bruto = p["aposta"]
                    taxa = int(lucro_bruto * 0.15)
                    lucro_liquido = lucro_bruto - taxa
                    ganho_total = p["aposta"] + lucro_liquido
                    res_txt = f"\n🏆 **VENCEU! (+{ganho_total} C)**\n*(Cassino reteve {taxa} C)*"
                elif p_p == d_p: 
                    res_txt = "\n🤝 **EMPATE**"
                else: 
                    res_txt = "\n💀 **PERDEU**"

            embed.add_field(
                name=f"{status_emoji} {p['member'].display_name}", 
                value=f"Mão: `{self.formatar_mao(p['hand'])}`\nPontos: `{p_p}` | Aposta: `{p['aposta']} C`{res_txt}", 
                inline=True
            )
            
        if self.terminado:
            embed.set_footer(text="Partida finalizada! Prêmios e impostos aplicados.")

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
        p["hand"].append(self.deck.pop())
        
        if self.calcular_pontos(p["hand"]) >= 21:
            p["status"] = "parou" if self.calcular_pontos(p["hand"]) == 21 else "estourou"
            await self.proximo_turno()
        
        await self.atualizar_embed(inter)

    @disnake.ui.button(label="Parar (Stand)", style=disnake.ButtonStyle.grey)
    async def stand(self, button, inter):
        if self.terminado or self.current_player_idx >= len(self.player_ids): return
        if inter.author.id != self.player_ids[self.current_player_idx]:
            return await inter.send("❌ Não é sua vez!", ephemeral=True)
        
        self.players_data[inter.author.id]["status"] = "parou"
        await self.proximo_turno()
        await self.atualizar_embed(inter)

    @disnake.ui.button(label="Dobrar (Double)", style=disnake.ButtonStyle.blurple)
    async def double(self, button, inter):
        if self.terminado or self.current_player_idx >= len(self.player_ids): return
        p_id = inter.author.id
        if p_id != self.player_ids[self.current_player_idx]:
            return await inter.send("❌ Não é sua vez!", ephemeral=True)
        
        p = self.players_data[p_id]
        u_db = db.get_user_data(str(p_id))
        
        if int(u_db['data'][2]) < p["aposta"]:
            return await inter.send("❌ Saldo insuficiente para dobrar!", ephemeral=True)
        
        db.update_value(u_db['row'], 3, int(u_db['data'][2]) - p["aposta"])
        p["aposta"] *= 2
        p["hand"].append(self.deck.pop())
        p["status"] = "parou" if self.calcular_pontos(p["hand"]) <= 21 else "estourou"
        
        await self.proximo_turno()
        await self.atualizar_embed(inter)

    @disnake.ui.button(label="Dividir (Split)", style=disnake.ButtonStyle.danger, disabled=True)
    async def split(self, button, inter):
        if self.terminado or self.current_player_idx >= len(self.player_ids): return
        p_id = inter.author.id
        if p_id != self.player_ids[self.current_player_idx]:
            return await inter.send("❌ Não é sua vez!", ephemeral=True)
        
        p = self.players_data[p_id]
        u_db = db.get_user_data(str(p_id))
        
        if int(u_db['data'][2]) < p["aposta"]:
            return await inter.send("❌ Saldo insuficiente para o Split!", ephemeral=True)
        
        db.update_value(u_db['row'], 3, int(u_db['data'][2]) - p["aposta"])
        p["aposta"] *= 2
        p["splitted"] = True
        
        p["hand"].pop()
        p["hand"].append(self.deck.pop())
        
        await self.atualizar_embed(inter)

    async def proximo_turno(self):
        self.current_player_idx += 1
        if self.current_player_idx >= len(self.player_ids):
            self.terminado = True
            while self.calcular_pontos(self.dealer_hand) < 17:
                self.dealer_hand.append(self.deck.pop())
            await self.processar_pagamentos_db()

    async def processar_pagamentos_db(self):
        d_p = self.calcular_pontos(self.dealer_hand)
        for p_id, p in self.players_data.items():
            p_p = self.calcular_pontos(p["hand"])
            u_db = db.get_user_data(str(p_id))
            saldo_atual = int(u_db['data'][2])
            
            if p_p > 21 and d_p > 21: # Ambos estouraram
                db.update_value(u_db['row'], 3, saldo_atual + p["aposta"])
            elif p_p <= 21:
                if d_p > 21 or p_p > d_p: # Ganhou
                    lucro_bruto = p["aposta"]
                    taxa = int(lucro_bruto * 0.15)
                    lucro_liquido = lucro_bruto - taxa
                    db.update_value(u_db['row'], 3, saldo_atual + p["aposta"] + lucro_liquido)
                elif p_p == d_p: # Empatou
                    db.update_value(u_db['row'], 3, saldo_atual + p["aposta"])


class BlackjackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, macaco esperto joga no lugar certo! Vai para o canal {mencao}.")
            raise commands.CommandError("Canal de apostas incorreto.")

    @commands.command(aliases=["bj", "21"])
    async def blackjack(self, ctx, aposta: int):
        """Inicia uma mesa de Blackjack multiplayer."""
        if aposta <= 0: return await ctx.send("❌ Aposta inválida!")
        
        u_c = db.get_user_data(str(ctx.author.id))
        if not u_c: return await ctx.send("❌ Conta não encontrada!")

        cargo = u_c['data'][3]
        limite = get_limite_bj(cargo)

        if aposta > limite:
            return await ctx.send(f"🚫 **LIMITE DE CARGO!** Como **{cargo}**, seu limite para abrir ou entrar em mesas é de **{limite} C**.")

        if int(u_c['data'][2]) < aposta: return await ctx.send("❌ Saldo insuficiente!")
        
        db.update_value(u_c['row'], 3, int(u_c['data'][2]) - aposta)
        players = [ctx.author]

        def gerar_texto_lobby(lista_jogadores):
            nomes = ", ".join([p.display_name for p in lista_jogadores])
            qtd = len(lista_jogadores)
            return (f"🃏 **BLACKJACK!** Dono: {ctx.author.mention} | Aposta: `{aposta} C`\n"
                    f"👥 **Jogadores ({qtd}):** {nomes}\n\n"
                    f"Digite `!entrar` para participar!\n"
                    f"{ctx.author.mention}, digite **`começar`** para iniciar o jogo!")
        
        msg = await ctx.send(gerar_texto_lobby(players))

        def check(m): return m.channel == ctx.channel and (m.content.lower() == '!entrar' or (m.author == ctx.author and m.content.lower() == 'começar'))
        
        start = False
        while True:
            try:
                m = await self.bot.wait_for('message', check=check, timeout=60.0)
                if m.content.lower() == 'começar':
                    start = True
                    break
                if m.content.lower() == '!entrar' and m.author not in players:
                    u_db = db.get_user_data(str(m.author.id))
                    if u_db:
                        cargo_p = u_db['data'][3]
                        limite_p = get_limite_bj(cargo_p)
                        if aposta > limite_p:
                            await ctx.send(f"🚫 {m.author.mention}, a aposta da mesa excede seu limite de **{cargo_p}** ({limite_p} C).", delete_after=6)
                            continue
                            
                        if int(u_db['data'][2]) >= aposta:
                            db.update_value(u_db['row'], 3, int(u_db['data'][2]) - aposta)
                            players.append(m.author)
                            await msg.edit(content=gerar_texto_lobby(players))
                        else:
                            await ctx.send(f"❌ {m.author.mention}, saldo insuficiente para entrar!", delete_after=6)
            except asyncio.TimeoutError: break

        if not start:
            for p in players:
                p_db = db.get_user_data(str(p.id))
                db.update_value(p_db['row'], 3, int(p_db['data'][2]) + aposta)
            return await ctx.send("⏰ Mesa cancelada. Valores devolvidos.")

        # --- CORREÇÃO DO BUG DAS DUAS MESAS (CHAMADA ÚNICA AQUI) ---
        view = BlackjackView(ctx, self.bot, aposta, players)
        view.dealer_hand = [view.deck.pop(), view.deck.pop()]
        for p_id in view.player_ids: 
            view.players_data[p_id]["hand"] = [view.deck.pop(), view.deck.pop()]
        await ctx.send(embed=await view.atualizar_embed(), view=view)


def setup(bot):
    bot.add_cog(BlackjackCog(bot))