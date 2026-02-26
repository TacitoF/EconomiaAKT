import disnake
from disnake.ext import commands
import database as db
import random
import asyncio

# ──────────────────────────────────────────────
#  CONFIGURAÇÃO DA ECONOMIA E JOGO
# ──────────────────────────────────────────────

LINHAS       = 8
NUM_SLOTS    = LINHAS + 1   # 9 slots (0–8)
FRAME_DELAY  = 0.6
MAX_BOLINHAS = 5

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

# Multiplicadores (Baixa Volatilidade | EV ~0.97)
MULTIPLICADORES = [10,    3,   1.5,  0.8,  0.3,  0.8,  1.5,  3,   10  ]
LABELS_SLOT     = ['10x', '3x', '1.5x','0.8x','0.3x','0.8x','1.5x','3x', '10x']

W_GAP   = 3
W_PINO  = 2
W_SLOT  = W_GAP + W_PINO   
TOTAL_W = 9 * W_GAP + 8 * W_PINO 

def get_limite(cargo: str) -> int:
    return LIMITES_CARGO.get(cargo, 400)

def _fmt(m: float) -> str:
    return f"{int(m)}x" if m == int(m) else f"{m}x"

# ──────────────────────────────────────────────
#  SIMULAÇÃO
# ──────────────────────────────────────────────

def simular_queda() -> tuple[int, list[int]]:
    pos = 0
    posicoes = [0]
    for _ in range(LINHAS):
        pos += random.randint(0, 1)
        posicoes.append(pos)
    return pos, posicoes

# ──────────────────────────────────────────────
#  RENDERIZAÇÃO COM EMOJI
# ──────────────────────────────────────────────

def _fmt_slot(i: int, slots_finais: list[int] | None) -> str:
    lbl = LABELS_SLOT[i]
    if slots_finais:
        n = slots_finais.count(i)
        if n > 0:
            # Se caírem cocos nesta gaveta, troca o texto pelo número + Emoji
            lbl = f"{n}🥥"
            
            # Subtraímos 1 espaço no ljust porque o emoji ocupa o espaço visual de 2 caracteres
            if i < NUM_SLOTS - 1:
                return lbl.ljust(W_SLOT - 1)
            return lbl

    # Para gavetas vazias ou durante a animação
    if i < NUM_SLOTS - 1:
        return lbl.ljust(W_SLOT)[:W_SLOT]
    else:
        return lbl

def render_grade(frame: int, todas_pos: list[list[int]], slots_finais: list[int] | None = None) -> str:
    linhas_out = []
    
    # ── Topo: cocos ainda não entraram
    if frame == 0:
        icone = "🥥"
        centro = 4 * W_SLOT + W_GAP // 2 - 1 
        linhas_out.append(" " * centro + icone)

    # ── Linhas do triângulo
    for l in range(LINHAS):
        n_pinos     = l + 1
        n_gaps      = l + 2
        conteudo_w  = n_gaps * W_GAP + n_pinos * W_PINO
        pad         = (TOTAL_W - conteudo_w) // 2
        linha_bola  = frame - 1

        contagem: dict[int, int] = {}
        if l == linha_bola:
            for pos in todas_pos:
                g = pos[l+1] 
                contagem[g] = contagem.get(g, 0) + 1

        row = " " * pad
        for g in range(n_gaps):
            if g in contagem:
                row += "🥥 " 
            else:
                row += "   "
            
            if g < n_pinos:
                row += " *" if l < frame else " ."
        
        row += " " * pad
        linhas_out.append(row)

    linhas_out.append("─" * TOTAL_W)
    linhas_out.append("".join(_fmt_slot(i, slots_finais) for i in range(NUM_SLOTS)))

    return "\n".join(linhas_out)

# ──────────────────────────────────────────────
#  EMBEDS
# ──────────────────────────────────────────────

def _titulo_animacao(n_bolas: int) -> str:
    return "🌴 COQUEIRO — Os cocos estão caindo..." if n_bolas > 1 else "🌴 COQUEIRO — O coco está caindo..."

def embed_animando(autor: disnake.Member, aposta_unit: float, todas_pos: list[list[int]], frame: int) -> disnake.Embed:
    n     = len(todas_pos)
    total = round(aposta_unit * n, 2)
    grade = render_grade(frame, todas_pos)

    embed = disnake.Embed(
        title       = _titulo_animacao(n),
        description = f"```\n{grade}\n```",
        color       = disnake.Color.dark_green(),
    )
    embed.set_author(
        name     = f"{autor.display_name}  •  {n}x {aposta_unit:.2f} MC = {total:.2f} MC",
        icon_url = autor.display_avatar.url,
    )
    linha_atual = max(0, frame)
    embed.set_footer(text=f"🥥  linha {linha_atual} / {LINHAS}")
    return embed

def embed_resultado(autor: disnake.Member, aposta_unit: float, todas_pos: list[list[int]], slots_finais: list[int]) -> disnake.Embed:
    n_bolas      = len(slots_finais)
    total_aposta = round(aposta_unit * n_bolas, 2)
    total_ganho  = round(sum(aposta_unit * MULTIPLICADORES[s] for s in slots_finais), 2)
    lucro        = round(total_ganho - total_aposta, 2)
    melhor       = max(MULTIPLICADORES[s] for s in slots_finais)

    grade = render_grade(LINHAS + 1, todas_pos, slots_finais=slots_finais)

    if melhor >= 15:
        cor    = disnake.Color.gold()
        titulo = "🌴 JACKPOT! UM COCO CHEGOU NA BORDA! 🌴"
    elif lucro > 0:
        cor    = disnake.Color.green()
        titulo = f"🥥 Boa queda!  +{lucro:.2f} MC"
    elif lucro == 0:
        cor    = disnake.Color.teal()
        titulo = "🌿 Empatou — apostado devolvido"
    else:
        cor    = disnake.Color.red()
        titulo = f"🪨 Queda ruim  {lucro:.2f} MC"

    embed = disnake.Embed(
        title       = titulo,
        description = f"```\n{grade}\n```",
        color       = cor,
    )
    embed.set_author(
        name     = f"{autor.display_name}  •  {n_bolas}x {aposta_unit:.2f} MC = {total_aposta:.2f} MC",
        icon_url = autor.display_avatar.url,
    )

    if n_bolas > 1:
        det = "\n".join(
            f"Bola {i+1}: slot {s} → **{_fmt(MULTIPLICADORES[s])}** → `{aposta_unit * MULTIPLICADORES[s]:.2f} MC`"
            for i, s in enumerate(slots_finais)
        )
        embed.add_field(name="🎯 Resultado por bola", value=det, inline=False)

    embed.add_field(name="💸 Total apostado", value=f"`{total_aposta:.2f} MC`", inline=True)
    embed.add_field(name="💰 Total retorno",  value=f"`{total_ganho:.2f} MC`",  inline=True)

    if lucro > 0:   embed.add_field(name="📈 Lucro",   value=f"**+{lucro:.2f} MC**", inline=True)
    elif lucro < 0: embed.add_field(name="📉 Perda",   value=f"**{lucro:.2f} MC**",  inline=True)
    else:           embed.add_field(name="➡️ Empate",  value="Devolvido",             inline=True)

    embed.set_footer(text="!coqueiro <valor> [bolinhas]  •  Borda: 15x  |  Centro: 0.2x")
    return embed

# ──────────────────────────────────────────────
#  COG
# ──────────────────────────────────────────────

class Coqueiro(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != "🎰・akbet":
            canal  = disnake.utils.get(ctx.guild.channels, name="🎰・akbet")
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🌴 {ctx.author.mention}, o Coqueiro fica no {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["plinko", "palmeira"])
    async def coqueiro(self, ctx, aposta: float = None, bolinhas: int = 1):
        """🌴 Joga cocos pela palmeira e torça pelo jackpot nas bordas!"""

        if aposta is None:
            embed = disnake.Embed(
                title="🌴 COMO JOGAR COQUEIRO (PLINKO)",
                description=(
                    "**Comando:** `!coqueiro <valor> [quantidade_de_cocos]`\n"
                    "*(Ex: `!coqueiro 100 5` jogará 5 cocos de 100 MC cada)*\n\n"
                    "🥥 Máximo de **5 cocos** por jogada.\n"
                    "🎯 O objetivo é que os cocos caiam nas **bordas** (15x)."
                ),
                color=disnake.Color.dark_green()
            )
            return await ctx.send(embed=embed)

        if bolinhas > MAX_BOLINHAS:
            return await ctx.send(f"❌ {ctx.author.mention}, você só pode jogar no máximo **{MAX_BOLINHAS} cocos** de uma vez!")
        if bolinhas < 1:
            return await ctx.send(f"❌ {ctx.author.mention}, você precisa jogar pelo menos **1 coco**!")

        if aposta <= 0:
            return await ctx.send("❌ A aposta precisa ser maior que zero!")

        aposta      = round(aposta, 2)
        total_gasto = round(aposta * bolinhas, 2)

        try:
            u = db.get_user_data(str(ctx.author.id))
            if not u:
                return await ctx.send("❌ Conta não encontrada! Use `!trabalhar` para criar sua conta.")

            cargo  = u["data"][3] if len(u["data"]) > 3 and u["data"][3] else "Lêmure"
            saldo  = db.parse_float(u["data"][2])
            limite = get_limite(cargo)

            if aposta > limite:
                return await ctx.send(f"🚫 Como **{cargo}**, seu limite por bolinha é **{limite} MC**.")
            if saldo < total_gasto:
                return await ctx.send(f"❌ Saldo insuficiente! Você tem **{saldo:.2f} MC** e precisa de **{total_gasto:.2f} MC**.")

            db.update_value(u["row"], 3, round(saldo - total_gasto, 2))

            todas_pos  = []
            slots_finais = []
            for _ in range(bolinhas):
                slot, posicoes = simular_queda()
                todas_pos.append(posicoes)
                slots_finais.append(slot)

            total_ganho = round(sum(aposta * MULTIPLICADORES[s] for s in slots_finais), 2)

            msg = await ctx.send(embed=embed_animando(ctx.author, aposta, todas_pos, 0))

            for frame in range(1, LINHAS + 1):
                await asyncio.sleep(FRAME_DELAY)
                try: await msg.edit(embed=embed_animando(ctx.author, aposta, todas_pos, frame))
                except Exception: break

            if total_ganho > 0:
                u2 = db.get_user_data(str(ctx.author.id))
                if u2:
                    db.update_value(u2["row"], 3, round(db.parse_float(u2["data"][2]) + total_ganho, 2))

            await asyncio.sleep(0.3)
            try: await msg.edit(embed=embed_resultado(ctx.author, aposta, todas_pos, slots_finais))
            except Exception: pass

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !coqueiro de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, erro inesperado.")

def setup(bot):
    bot.add_cog(Coqueiro(bot))