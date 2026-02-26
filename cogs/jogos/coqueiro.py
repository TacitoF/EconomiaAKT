import disnake
from disnake.ext import commands
import database as db
import random
import asyncio

# ──────────────────────────────────────────────
#  CONFIGURAÇÃO
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

# House edge ~5% | EV ~0.95 | binomial(8, 0.5)
# Probs: slot0/8=0.4%, slot1/7=3.1%, slot2/6=10.9%, slot3/5=21.9%, slot4=27.3%
MULTIPLICADORES = [25,    8,   3,    1,   0.3,   1,    3,    8,   25  ]
LABELS_SLOT     = ['25x','8x','3x', '1x','0.3x','1x', '3x', '8x','25x']


def get_limite(cargo: str) -> int:
    return LIMITES_CARGO.get(cargo, 400)


def _fmt(m: float) -> str:
    return f"{int(m)}x" if m == int(m) else f"{m}x"


# ──────────────────────────────────────────────
#  SIMULAÇÃO
# ──────────────────────────────────────────────

def simular_queda() -> tuple[int, list[int]]:
    """
    Simula 8 deflexões (0=esq, 1=dir).
    posicoes[l] = gap onde a bola está ao CHEGAR na linha l (0-indexed).
    posicoes[8] = slot final (0–8).
    """
    pos = 0
    posicoes = [0]
    for _ in range(LINHAS):
        pos += random.randint(0, 1)
        posicoes.append(pos)
    return pos, posicoes


# ──────────────────────────────────────────────
#  RENDERIZAÇÃO
# ──────────────────────────────────────────────
#
#  Layout do triângulo (monospace, dentro de ```):
#
#  Linha l tem (l+1) pinos e (l+2) gaps.
#  Cada gap ocupa 2 chars, cada pino ocupa 2 chars.
#  Centralização: pad = (LINHAS - l - 1) pares de espaços de cada lado.
#
#  Última linha (l=7): 8 pinos + 9 gaps = 34 chars de conteúdo, pad=0.
#  Gap i na última linha começa no char 4*i (exatamente onde fica o label[i]).
#
#  Labels dos slots:
#    Slots 0-7: largura 4 chars cada (gap 2 + pino 2)
#    Slot 8: largura 3 chars (último gap, sem pino à direita)
#  Total: 8*4 + 3 = 35 chars ≈ linha do triângulo (34 chars + margem).

def _fmt_slot(i: int, slots_finais: list[int] | None) -> str:
    """Formata o label do slot i com destaque se for vencedor."""
    lbl = LABELS_SLOT[i]
    if slots_finais:
        n = slots_finais.count(i)
        if n == 1:
            lbl = f"[{LABELS_SLOT[i]}]"
        elif n > 1:
            lbl = f"[{n}x]"
    largura = 4 if i < NUM_SLOTS - 1 else 3
    return lbl[:largura].ljust(largura)


def render_grade(frame: int, todas_pos: list[list[int]],
                 slots_finais: list[int] | None = None) -> str:
    """
    Monta o triângulo + linha de slots em texto monospace.

    frame:
      0            → bolinhas acima do triângulo (ainda não entraram)
      1 a LINHAS   → bolinhas na linha (frame-1)
      LINHAS+1     → frame final, sem bolinhas (só slots destacados)
    """
    linhas_out = []
    n_bolas    = len(todas_pos)

    # ── Linha de topo (frame 0): bolinhas acima do triângulo ──────────────
    if frame == 0:
        icone = "O" if n_bolas == 1 else str(n_bolas)
        # Centraliza no meio do triângulo (char 16 de 34)
        linhas_out.append(" " * 16 + icone + " " * 17)

    # ── Linhas do triângulo ───────────────────────────────────────────────
    for l in range(LINHAS):
        n_pinos   = l + 1
        n_gaps    = l + 2
        pad       = LINHAS - l - 1  # pares de espaços de cada lado

        # Linha onde a bola está neste frame
        linha_bola = frame - 1  # -1 quando frame=0 → nenhuma linha

        # Conta bolinhas nessa linha neste frame
        contagem: dict[int, int] = {}
        if l == linha_bola:
            for pos in todas_pos:
                g = pos[l]
                contagem[g] = contagem.get(g, 0) + 1

        row = "  " * pad
        for g in range(n_gaps):
            # Gap
            if g in contagem:
                qtd = contagem[g]
                row += " O" if qtd == 1 else f" {min(qtd, 9)}"
            else:
                row += "  "
            # Pino (exceto após o último gap)
            if g < n_pinos:
                row += " *" if l < frame else " ."
        row += "  " * pad

        linhas_out.append(row)

    # ── Separador e slots ─────────────────────────────────────────────────
    linhas_out.append("─" * 35)
    linhas_out.append("".join(_fmt_slot(i, slots_finais) for i in range(NUM_SLOTS)))

    return "\n".join(linhas_out)


# ──────────────────────────────────────────────
#  EMBEDS
# ──────────────────────────────────────────────

def _titulo_animacao(n_bolas: int) -> str:
    return "🌴 COQUEIRO — Os cocos estão caindo..." if n_bolas > 1 \
           else "🌴 COQUEIRO — O coco está caindo..."


def embed_animando(autor: disnake.Member, aposta_unit: float,
                   todas_pos: list[list[int]], frame: int) -> disnake.Embed:
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


def embed_resultado(autor: disnake.Member, aposta_unit: float,
                    todas_pos: list[list[int]],
                    slots_finais: list[int]) -> disnake.Embed:
    n_bolas      = len(slots_finais)
    total_aposta = round(aposta_unit * n_bolas, 2)
    total_ganho  = round(sum(aposta_unit * MULTIPLICADORES[s] for s in slots_finais), 2)
    lucro        = round(total_ganho - total_aposta, 2)
    melhor       = max(MULTIPLICADORES[s] for s in slots_finais)

    # Grade sem bolinhas visíveis (frame LINHAS+1) com slots destacados
    grade = render_grade(LINHAS + 1, todas_pos, slots_finais=slots_finais)

    if melhor >= 25:
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

    # Detalhes por bolinha (só quando há mais de uma)
    if n_bolas > 1:
        det = "\n".join(
            f"Bola {i+1}: slot {s} → **{_fmt(MULTIPLICADORES[s])}** → `{aposta_unit * MULTIPLICADORES[s]:.2f} MC`"
            for i, s in enumerate(slots_finais)
        )
        embed.add_field(name="🎯 Resultado por bola", value=det, inline=False)

    embed.add_field(name="💸 Total apostado", value=f"`{total_aposta:.2f} MC`", inline=True)
    embed.add_field(name="💰 Total retorno",  value=f"`{total_ganho:.2f} MC`",  inline=True)

    if lucro > 0:
        embed.add_field(name="📈 Lucro",   value=f"**+{lucro:.2f} MC**", inline=True)
    elif lucro < 0:
        embed.add_field(name="📉 Perda",   value=f"**{lucro:.2f} MC**",  inline=True)
    else:
        embed.add_field(name="➡️ Empate",  value="Devolvido",             inline=True)

    embed.set_footer(text="!coqueiro <valor> [bolinhas]  •  Borda: 25x  |  Centro: 0.3x")
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
            return await ctx.send(
                "🌴 **COQUEIRO** — O Plinko da Selva!\n"
                f"**Uso:** `!coqueiro <valor>` ou `!coqueiro <valor> <bolinhas>` (máx {MAX_BOLINHAS})\n\n"
                "O coco cai por **8 fileiras** de pinos. Cada pino o desvia para um lado.\n"
                "Bordas = jackpot raro 🌴 | Centro = resultado mais comum 🪨\n"
                "```\n"
                "25x 8x  3x  1x  0.3x1x  3x  8x  25x\n"
                "```"
            )

        bolinhas = max(1, min(bolinhas, MAX_BOLINHAS))

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
                return await ctx.send(
                    f"🚫 Como **{cargo}**, seu limite por bolinha é **{limite} MC**."
                )
            if saldo < total_gasto:
                return await ctx.send(
                    f"❌ Saldo insuficiente! Você tem **{saldo:.2f} MC** "
                    f"e precisa de **{total_gasto:.2f} MC** ({bolinhas}x `{aposta:.2f} MC`)."
                )

            # Debita antes de animar
            db.update_value(u["row"], 3, round(saldo - total_gasto, 2))

            # Calcula trajetórias completas antecipadamente
            todas_pos  = []
            slots_finais = []
            for _ in range(bolinhas):
                slot, posicoes = simular_queda()
                todas_pos.append(posicoes)
                slots_finais.append(slot)

            total_ganho = round(
                sum(aposta * MULTIPLICADORES[s] for s in slots_finais), 2
            )

            # Frame 0: bolinhas acima do triângulo
            msg = await ctx.send(embed=embed_animando(ctx.author, aposta, todas_pos, 0))

            # Frames 1..LINHAS: bolinhas descendo
            for frame in range(1, LINHAS + 1):
                await asyncio.sleep(FRAME_DELAY)
                try:
                    await msg.edit(embed=embed_animando(ctx.author, aposta, todas_pos, frame))
                except Exception as e:
                    print(f"❌ Coqueiro erro frame {frame}: {e}")
                    break

            # Credita ganho
            if total_ganho > 0:
                u2 = db.get_user_data(str(ctx.author.id))
                if u2:
                    db.update_value(
                        u2["row"], 3,
                        round(db.parse_float(u2["data"][2]) + total_ganho, 2)
                    )

            # Frame final: triângulo limpo + slots destacados
            await asyncio.sleep(0.3)
            try:
                await msg.edit(embed=embed_resultado(ctx.author, aposta, todas_pos, slots_finais))
            except Exception as e:
                print(f"❌ Coqueiro erro resultado: {e}")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !coqueiro de {ctx.author}: {e}")
            try:
                u_err = db.get_user_data(str(ctx.author.id))
                if u_err:
                    db.update_value(
                        u_err["row"], 3,
                        round(db.parse_float(u_err["data"][2]) + total_gasto, 2)
                    )
            except Exception:
                pass
            await ctx.send(f"⚠️ {ctx.author.mention}, erro inesperado. Aposta devolvida!")


def setup(bot):
    bot.add_cog(Coqueiro(bot))