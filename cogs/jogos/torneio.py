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
    return LIMITES_CARGO.get(cargo, 400)

def formatar_moeda(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def save_achievement(user_data, slug):
    conquistas = str(user_data['data'][9]) if len(user_data['data']) > 9 else ""
    lista = [c.strip() for c in conquistas.split(',') if c.strip()]
    if slug not in lista:
        lista.append(slug)
        db.update_value(user_data['row'], 10, ", ".join(lista))

# ──────────────────────────────────────────────
#  VIEW DA LUTA (JOKENPÔ)
# ──────────────────────────────────────────────
class TorneioMatchView(disnake.ui.View):
    def __init__(self, p1: disnake.Member, p2: disnake.Member):
        super().__init__(timeout=30) # 30 segundos para jogar
        self.p1 = p1
        self.p2 = p2
        self.choices = {p1.id: None, p2.id: None}
        self.winner = None
        self.loser = None
        self.empate = False
        self.motivo = ""

    async def registrar_escolha(self, inter: disnake.MessageInteraction, escolha: str, emoji: str):
        if inter.author.id not in self.choices:
            return await inter.response.send_message("🐒 Você não está nesta luta! Afaste-se da arena.", ephemeral=True)
            
        if self.choices[inter.author.id] is not None:
            return await inter.response.send_message("⚠️ Você já fez a sua escolha! Aguarde o seu adversário.", ephemeral=True)

        self.choices[inter.author.id] = escolha
        await inter.response.send_message(f"Você fez a sua jogada: {emoji} **{escolha.capitalize()}**!", ephemeral=True)

        if all(c is not None for c in self.choices.values()):
            self.stop()
            self.resolver()

    @disnake.ui.button(label="Gorila", emoji="🦍", style=disnake.ButtonStyle.primary)
    async def btn_gorila(self, button, inter): await self.registrar_escolha(inter, "gorila", "🦍")

    @disnake.ui.button(label="Caçador", emoji="🤠", style=disnake.ButtonStyle.danger)
    async def btn_cacador(self, button, inter): await self.registrar_escolha(inter, "cacador", "🤠")

    @disnake.ui.button(label="Casca", emoji="🍌", style=disnake.ButtonStyle.success)
    async def btn_casca(self, button, inter): await self.registrar_escolha(inter, "casca", "🍌")

    def resolver(self):
        c1, c2 = self.choices[self.p1.id], self.choices[self.p2.id]
        if c1 == c2:
            self.empate = True
            self.motivo = "Empate técnico! Ambos escolheram a mesma coisa."
            return

        regras = {"gorila": "cacador", "cacador": "casca", "casca": "gorila"}
        msgs = {
            "gorila": "🦍 O Gorila amassou o Caçador!",
            "cacador": "🤠 O Caçador atirou e destruiu a Casca!",
            "casca": "🍌 O Gorila escorregou na Casca e quebrou a cabeça!"
        }

        if regras[c1] == c2:
            self.winner, self.loser = self.p1, self.p2
            self.motivo = msgs[c1]
        else:
            self.winner, self.loser = self.p2, self.p1
            self.motivo = msgs[c2]

    async def on_timeout(self):
        c1, c2 = self.choices[self.p1.id], self.choices[self.p2.id]
        
        if c1 is None and c2 is not None:
            self.winner, self.loser = self.p2, self.p1
            self.motivo = f"💤 {self.p1.display_name} dormiu na árvore e perdeu por W.O.!"
        elif c2 is None and c1 is not None:
            self.winner, self.loser = self.p1, self.p2
            self.motivo = f"💤 {self.p2.display_name} dormiu na árvore e perdeu por W.O.!"
        else:
            # Ambos não jogaram, o juiz decide por sorteio
            self.winner = random.choice([self.p1, self.p2])
            self.loser = self.p2 if self.winner == self.p1 else self.p1
            self.motivo = "💤 Ambos dormiram! O juiz jogou uma moeda para cima para decidir."


# ──────────────────────────────────────────────
#  VIEW DO LOBBY (INSCRIÇÕES)
# ──────────────────────────────────────────────
class TorneioLobbyView(disnake.ui.View):
    def __init__(self, ctx, aposta: float):
        super().__init__(timeout=120) # 2 Minutos para a galera entrar
        self.ctx = ctx
        self.aposta = aposta
        self.players = [ctx.author]
        self.msg = None

    @disnake.ui.button(label="Entrar no Torneio", style=disnake.ButtonStyle.success, emoji="🎟️")
    async def btn_entrar(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.author in self.players:
            return await inter.response.send_message("🐒 Você já está inscrito no torneio!", ephemeral=True)
            
        if len(self.players) >= 8:
            return await inter.response.send_message("🚫 O torneio já atingiu o limite máximo de 8 jogadores!", ephemeral=True)

        try:
            user = db.get_user_data(str(inter.author.id))
            if not user:
                return await inter.response.send_message("❌ Você não tem conta na selva!", ephemeral=True)

            saldo = db.parse_float(user['data'][2])
            cargo = user['data'][3] if len(user['data']) > 3 else "Lêmure"

            if saldo < self.aposta:
                return await inter.response.send_message(f"❌ Saldo insuficiente! Você precisa de **{formatar_moeda(self.aposta)} MC**.", ephemeral=True)
            if self.aposta > get_limite(cargo):
                return await inter.response.send_message(f"🚫 O limite para o seu cargo é de **{formatar_moeda(get_limite(cargo))} MC**.", ephemeral=True)

            # Debita a entrada
            db.update_value(user['row'], 3, round(saldo - self.aposta, 2))
            self.players.append(inter.author)

            embed = self.msg.embeds[0]
            embed.description = f"💰 **Entrada:** `{formatar_moeda(self.aposta)} MC`\n🏆 **Pote Atual:** `{formatar_moeda(self.aposta * len(self.players))} MC`\n👥 **Participantes ({len(self.players)}/8):**"
            embed.clear_fields()
            
            nomes = "\n".join([f"🥊 {p.mention}" for p in self.players])
            embed.add_field(name="Lutadores na Arena:", value=nomes, inline=False)

            if len(self.players) == 8:
                self.stop()
                embed.color = disnake.Color.red()
                embed.set_footer(text="A arena fechou! O torneio vai começar.")
                await inter.response.edit_message(embed=embed, view=None)
            else:
                await inter.response.edit_message(embed=embed, view=self)

        except Exception as e:
            print(f"Erro ao entrar no torneio: {e}")
            await inter.response.send_message("Ocorreu um erro no banco de dados.", ephemeral=True)

    async def on_timeout(self):
        self.stop()
        if len(self.players) < 3:
            # Reembolsa todos
            for p in self.players:
                try:
                    u_db = db.get_user_data(str(p.id))
                    if u_db:
                        db.update_value(u_db['row'], 3, round(db.parse_float(u_db['data'][2]) + self.aposta, 2))
                except: pass
            
            embed = self.msg.embeds[0]
            embed.title = "🚩 TORNEIO CANCELADO"
            embed.description = "Não houve jogadores suficientes (Mínimo: 3). As inscrições foram devolvidas."
            embed.color = disnake.Color.dark_grey()
            embed.clear_fields()
            await self.msg.edit(embed=embed, view=None)


# ──────────────────────────────────────────────
#  SISTEMA CENTRAL DO TORNEIO (LÓGICA MATA-MATA EXTREMO)
# ──────────────────────────────────────────────
class TorneioSimio(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name not in ['🎰・akbet', '🐒・conguitos']:
            canal = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"⚠️ {ctx.author.mention}, organize os seus torneios no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["campeonato", "cup"])
    async def torneio(self, ctx, aposta: float = None):
        """Abre as inscrições para um Torneio de Jokenpô (Máx 8 jogadores)."""
        if aposta is None or aposta < 100:
            embed = disnake.Embed(
                title="🏆 TORNEIO DO REI SÍMIO — Como funciona",
                description=(
                    "Um torneio mata-mata de **Jokenpô da Selva** com até **8 jogadores**!\n\n"
                    "**Regras do Jokenpô:**\n"
                    "🦍 **Gorila** derrota o 🤠 **Caçador**\n"
                    "🤠 **Caçador** destrói a 🍌 **Casca**\n"
                    "🍌 **Casca** derruba o 🦍 **Gorila**\n\n"
                    "**Formato:** Os jogadores se enfrentam em duelos via botões. "
                    "Em caso de 3 empates seguidos, o juiz decide na moeda.\n\n"
                    "**Prêmios:** 🥇 1º lugar recebe **80%** do pote · 🥈 2º lugar recebe **20%**\n"
                    "**Entrada mínima:** 100 MC\n\n"
                    "**Uso:** `!torneio <valor>`"
                ),
                color=disnake.Color.gold()
            )
            return await ctx.send(embed=embed)
        aposta = round(aposta, 2)

        try:
            u_criador = db.get_user_data(str(ctx.author.id))
            if not u_criador: return await ctx.send("❌ Você não tem conta na selva!")
            
            s_criador = db.parse_float(u_criador['data'][2])
            cargo = u_criador['data'][3] if len(u_criador['data']) > 3 else "Lêmure"
            
            if s_criador < aposta:
                return await ctx.send("❌ Você não tem saldo suficiente para bancar a sua própria entrada.")
            if aposta > get_limite(cargo):
                return await ctx.send(f"🚫 O seu limite de aposta é de **{formatar_moeda(get_limite(cargo))} MC**.")

            # Debita a entrada do criador
            db.update_value(u_criador['row'], 3, round(s_criador - aposta, 2))

            embed = disnake.Embed(
                title="🏆 TORNEIO DO REI SÍMIO ABERTO!",
                description=f"💰 **Entrada:** `{formatar_moeda(aposta)} MC`\n🏆 **Pote Atual:** `{formatar_moeda(aposta)} MC`\n👥 **Participantes (1/8):**",
                color=disnake.Color.gold()
            )
            embed.add_field(name="Lutadores na Arena:", value=f"🥊 {ctx.author.mention}", inline=False)
            embed.set_footer(text="As inscrições encerram em 2 minutos! O torneio avança com 3 a 8 jogadores.")

            view = TorneioLobbyView(ctx, aposta)
            msg = await ctx.send(embed=embed, view=view)
            view.msg = msg

            await view.wait()

            if len(view.players) >= 3:
                await self.iniciar_torneio(ctx, view.players, aposta)

        except Exception as e:
            print(f"❌ Erro ao criar torneio: {e}")

    async def iniciar_torneio(self, ctx, players, aposta):
        total_pote = round(len(players) * aposta, 2)
        premio_1 = round(total_pote * 0.80, 2)
        premio_2 = round(total_pote * 0.20, 2)

        await ctx.send(f"🔥 **A ARENA ESTÁ FECHADA!** O torneio vai começar com **{len(players)} jogadores**.\n💰 **Pote Total:** `{formatar_moeda(total_pote)} MC`\n🥇 1º Lugar: **{formatar_moeda(premio_1)}** | 🥈 2º Lugar: **{formatar_moeda(premio_2)}**")
        await asyncio.sleep(3)

        # Sorteia a ordem inicial dos jogadores
        random.shuffle(players)
        lutadores_ativos = players.copy()
        vice_campeao = None
        fase_num = 1

        # Loop das Fases (Lógica de Máximo de Embates)
        while len(lutadores_ativos) > 1:
            # Se for ímpar (ex: 5 ou 3), 1 pessoa descansa. Se for par, 0 pessoas descansam.
            byes = len(lutadores_ativos) % 2
            
            avancam = lutadores_ativos[:byes]       # O(s) sortudo(s) que passa(m) direto
            vao_lutar = lutadores_ativos[byes:]     # Os que vão sair no soco
            
            matches = [(vao_lutar[i], vao_lutar[i+1]) for i in range(0, len(vao_lutar), 2)]
            
            if len(lutadores_ativos) == 2:
                fase_nome = "A GRANDE FINAL 🏆"
                cor_fase = disnake.Color.gold()
            elif len(lutadores_ativos) <= 4:
                fase_nome = "SEMIFINAIS 🥊"
                cor_fase = disnake.Color.orange()
            else:
                fase_nome = f"FASE {fase_num} ⚔️"
                cor_fase = disnake.Color.blue()

            msg_fase = f"📢 **{fase_nome}** VAI COMEÇAR!"
            if byes > 0:
                nomes_byes = ", ".join([p.display_name for p in avancam])
                msg_fase += f"\n🍀 *Sorteio: {nomes_byes} avança direto para a próxima rodada!*"
            
            embed_fase = disnake.Embed(title=fase_nome, description=msg_fase, color=cor_fase)
            await ctx.send(embed=embed_fase)
            await asyncio.sleep(3)

            for m in matches:
                p1, p2 = m[0], m[1]
                
                tentativas = 0
                while tentativas < 3:
                    view_luta = TorneioMatchView(p1, p2)
                    embed_luta = disnake.Embed(
                        title=f"{fase_nome} — LUTA!",
                        description=f"{p1.mention} **VS** {p2.mention}\n\nUsem os botões abaixo! Têm 30 segundos.",
                        color=cor_fase
                    )
                    
                    msg_luta = await ctx.send(content=f"{p1.mention} {p2.mention}", embed=embed_luta, view=view_luta)
                    await view_luta.wait()

                    for item in view_luta.children: item.disabled = True

                    if view_luta.empate:
                        tentativas += 1
                        embed_luta.description = f"🤝 **EMPATE!** Ambos escolheram igual. Vamos repetir! (Tentativa {tentativas}/3)"
                        embed_luta.color = disnake.Color.yellow()
                        await msg_luta.edit(embed=embed_luta, view=None)
                        await asyncio.sleep(2)
                        continue
                    else:
                        break

                if view_luta.empate:
                    view_luta.winner = random.choice([p1, p2])
                    view_luta.loser = p2 if view_luta.winner == p1 else p1
                    view_luta.motivo = "A luta demorou demais e o juiz decidiu na moeda!"

                avancam.append(view_luta.winner)
                if len(lutadores_ativos) == 2:
                    vice_campeao = view_luta.loser # Guarda o vice para o pagamento final

                embed_res = disnake.Embed(
                    title="💥 FIM DO COMBATE!",
                    description=f"{view_luta.motivo}\n\n🏆 **{view_luta.winner.mention}** avança na chave!",
                    color=disnake.Color.green()
                )
                await msg_luta.edit(embed=embed_res, view=None)
                await asyncio.sleep(3)

            # Prepara a lista para a próxima fase e mistura tudo de novo para não favorecer o W.O.
            lutadores_ativos = avancam
            random.shuffle(lutadores_ativos)
            fase_num += 1

        campeao = lutadores_ativos[0]

        # ── PAGAMENTOS ──
        try:
            u_camp = db.get_user_data(str(campeao.id))
            if u_camp:
                db.update_value(u_camp['row'], 3, round(db.parse_float(u_camp['data'][2]) + premio_1, 2))
                save_achievement(u_camp, "rei_da_arena")
            
            if vice_campeao:
                u_vice = db.get_user_data(str(vice_campeao.id))
                if u_vice:
                    db.update_value(u_vice['row'], 3, round(db.parse_float(u_vice['data'][2]) + premio_2, 2))
        except Exception as e:
            print(f"Erro ao pagar prêmios do torneio: {e}")

        # ── PÓDIO FINAL ──
        embed_final = disnake.Embed(
            title="👑 O NOVO REI SÍMIO!",
            description=f"A poeira baixou e temos o vencedor definitivo.\n\n🥇 **CAMPEÃO:** {campeao.mention}\n└ Prêmio: `{formatar_moeda(premio_1)} MC`\n\n🥈 **VICE-CAMPEÃO:** {vice_campeao.mention if vice_campeao else 'Ninguém'}\n└ Prêmio: `{formatar_moeda(premio_2)} MC`",
            color=disnake.Color.gold()
        )
        embed_final.set_image(url="https://i.imgur.com/kS944e8.png")
        await ctx.send(content=f"🎉 Parabéns {campeao.mention}!", embed=embed_final)


def setup(bot):
    bot.add_cog(TorneioSimio(bot))