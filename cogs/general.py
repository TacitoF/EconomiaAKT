import disnake
from disnake.ext import commands

# ──────────────────────────────────────────────────────────────────────────────
#  Conteúdo de cada página do !ajuda
# ──────────────────────────────────────────────────────────────────────────────

def _pagina_inicio(author: disnake.Member) -> disnake.Embed:
    embed = disnake.Embed(
        title="🦍 Guia de Sobrevivência na Selva",
        description=(
            f"Olá {author.mention}, bem-vindo ao manual do servidor!\n"
            "Clique em um dos botões abaixo para ver os detalhes de cada seção.\n\n"
            "**Para começar:** use `!trabalhar` e ganhe seus primeiros MC!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=disnake.Color.green()
    )
    embed.add_field(name="📋 Seções disponíveis", inline=False, value=(
        "💵 **Economia** — trabalhar, missões, perfil, rank\n"
        "📦 **Mercado** — loja, inventário, lootboxes, airdrops\n"
        "🔰 **Passivos** — itens equipáveis e bônus permanentes\n"
        "🐾 **Mascotes** — gaiolas, buffs e cuidados\n"
        "😈 **Roubos** — assaltar, evento purge, sabotagens\n"
        "🏦 **Banco** — renda fixa e cripto\n"
        "🎲 **Jogos** — cassino, duelos e torneios\n"
        "✨ **Cosméticos** — visuais, bio, títulos\n"
        "🤐 **Castigos** — mudo, surdo, expulsar da call"
    ))
    embed.set_footer(text="Selecione uma seção abaixo")
    return embed


def _pagina_economia(author: disnake.Member) -> disnake.Embed:
    embed = disnake.Embed(title="💵 Básico & Economia", color=disnake.Color.green())
    embed.add_field(inline=False, name="💰 `!trabalhar`", value=(
        "Trabalhe a cada **1 hora** para ganhar MC e ter chance de encontrar caixas, gaiolas e passivos.\n"
        "*(O Sindicato passivo reduz o cooldown em 10 min.)*"
    ))
    embed.add_field(inline=False, name="📜 `!missoes`", value=(
        "Abre o seu Quadro de Caçadas Diárias! Complete as 3 tarefas para ganhar uma bolada em MC e um Item Aleatório (reseta à meia-noite)."
    ))
    embed.add_field(inline=False, name="👤 `!perfil [@usuario]`", value=(
        "Exibe o cartão público de qualquer jogador: cargo, bio, cosméticos e conquistas.\n"
        "No **seu próprio perfil**: botão para ver sua conta privada (saldo, cooldowns, inventário).\n"
        "No **perfil alheio**: botão para comprar o dossiê completo por **500 MC**."
    ))
    embed.add_field(inline=False, name="🏆 `!rank`  ·  🏅 `!conquistas`", value=(
        "`!rank` — Top 10 da selva por saldo.\n"
        "`!conquistas` — Seus emblemas desbloqueados."
    ))
    embed.add_field(inline=False, name="💵 `!salarios`", value=(
        "Tabela de ganhos por cargo, limites de aposta e custo de evolução."
    ))
    embed.add_field(inline=False, name="💸 `!pagar @usuario <valor>`", value=(
        "Transfere MC diretamente para outro jogador."
    ))
    embed.set_footer(text="💵 Básico & Economia  ·  Clique em Início para voltar")
    return embed


def _pagina_mercado(author: disnake.Member) -> disnake.Embed:
    embed = disnake.Embed(title="📦 Mercado & Itens", color=disnake.Color.gold())
    embed.add_field(inline=False, name="🛒 `!loja`", value=(
        "Mercado negro com **preços dinâmicos** — cada compra empurra o preço +3% (teto: +80%).\n"
        "O preço cai gradualmente se ninguém comprar (piso: -40%) e reseta todo dia.\n"
        "⚠️ **Jogadores com cargos altos pagam mais** (imposto progressivo por cargo).\n"
        "Cosméticos e upgrades de cargo têm preço fixo."
    ))
    embed.add_field(inline=False, name="🤝 `!vender @usuario <item> <preço>`", value=(
        "Vende um item do seu inventário para outro jogador.\n"
        "O comprador tem **60 segundos** para aceitar ou recusar.\n"
        "**Intransferíveis:** Escudo · Pé de Cabra · Seguro"
    ))
    embed.add_field(inline=False, name="♻️ `!vender <item>` *(sem @)* ·  `!reembolso <item>`", value=(
        "`!vender <item>` — Vende o item de volta ao sistema pelo **preço base** (100% de retorno).\n"
        "`!reembolso <item>` — Mesmo efeito, com tela de confirmação antes de executar.\n"
        "*Cosméticos, cargos e caixas não são reembolsáveis.*"
    ))
    embed.add_field(inline=False, name="🔄 `!trocar @usuario <seu item> por <item do alvo>`", value=(
        "Troca direta de itens sem MC. Anti-scam: ambos confirmam antes de finalizar.\n"
        "Suporta múltiplos itens: `!trocar @user item1 + item2 por item do alvo`"
    ))
    embed.add_field(inline=False, name="🎒 `!inventario`  ·  📊 `!caixas`  ·  🔓 `!abrir <caixa>`", value=(
        "`!inventario` — Lista seus itens e indica quais são negociáveis.\n"
        "`!caixas` — Tabela de chances e recompensas de cada tipo de caixa.\n"
        "`!abrir <caixote/baú/relíquia/gaiola>` — Abre uma caixa do inventário."
    ))
    embed.add_field(inline=False, name="✈️ Airdrops", value=(
        "Caem aleatoriamente no chat. O **primeiro a clicar em SAQUEAR** leva a caixa!\n"
        "Raridades: Caixote Comum · Baú do Caçador · Gaiola Misteriosa · Relíquia Ancestral"
    ))
    embed.set_footer(text="📦 Mercado & Itens  ·  Clique em Início para voltar")
    return embed


def _pagina_passivos(author: disnake.Member) -> disnake.Embed:
    embed = disnake.Embed(title="🔰 Passivos", color=disnake.Color.purple())
    embed.add_field(inline=False, name="O que são passivos?", value=(
        "Itens raros que caem do `!trabalhar`. Ficam no inventário e precisam ser **equipados** para ativar.\n"
        "Você pode ter até **3 passivos simultâneos**."
    ))
    embed.add_field(inline=False, name="🔰 `!equipar <item>`  ·  ❌ `!desequipar <item>`  ·  📋 `!passivos [@usuario]`", value=(
        "`!equipar` sem argumento — mostra passivos disponíveis no inventário.\n"
        "`!desequipar` — remove do slot, mas mantém no inventário.\n"
        "`!passivos` — mostra seus slots equipados e os disponíveis."
    ))
    embed.add_field(inline=False, name="⚫ Tier Comum *(~3% drop)*", value=(
        "🍀 **Amuleto da Sorte** — +3% chance de sucesso no roubo\n"
        "🔧 **Cinto de Ferramentas** — +4% ganho no trabalho\n"
        "👛 **Carteira Velha** — reduz o % máximo que podem te roubar"
    ))
    embed.add_field(inline=False, name="🔵 Tier Raro *(~1.5% drop)*", value=(
        "🔒 **Segurança Particular** — -8% chance do ladrão ter sucesso\n"
        "🧤 **Luvas de Seda** — +3% no máximo que você pode roubar\n"
        "🏛️ **Sindicato** — -10 min de cooldown no trabalho\n"
        "🐕 **Cão de Guarda** — +10% na multa do ladrão se falhar contra você"
    ))
    embed.add_field(inline=False, name="🟣 Tier Épico *(~0.5% drop)*", value=(
        "🏺 **Relíquia do Ancião** — +10% ganho no trabalho\n"
        "🩸 **Escudo de Sangue** — recupera 5% do valor roubado de você\n"
        "🌑 **Manto das Sombras** — +12% chance de sucesso no roubo\n"
        "🌟 **Talismã da Fortuna** — reduz prejuízo máximo no cripto de 25% → 15%"
    ))
    embed.set_footer(text="🔰 Passivos  ·  Clique em Início para voltar")
    return embed


def _pagina_mascotes(author: disnake.Member) -> disnake.Embed:
    embed = disnake.Embed(title="🐾 Mascotes", color=disnake.Color.teal())
    embed.add_field(inline=False, name="Como conseguir um mascote?", value=(
        "Abra uma **Gaiola Misteriosa** com `!abrir gaiola`.\n"
        "Gaiolas caem do `!trabalhar` (1,5% de chance) ou em airdrops raros."
    ))
    embed.add_field(inline=False, name="🐶 `!mascote [@usuario]`  ·  📖 `!mascotes`", value=(
        "`!mascote` — Vê o mascote atual e o nível de fome.\n"
        "`!mascotes` — Enciclopédia com todos os animais, raridades e poderes."
    ))
    embed.add_field(inline=False, name="🍗 `!alimentar`  ·  🚪 `!libertar`", value=(
        "`!alimentar` — Usa uma **Ração Símia** do inventário para restaurar +50% de fome.\n"
        "`!libertar` — Liberta o mascote para poder abrir outra gaiola.\n\n"
        "⚠️ **Mascote com fome zerada tem buffs desativados!**\n"
        "Ração Símia pode ser comprada na `!loja`."
    ))
    embed.add_field(inline=False, name="Como os mascotes ajudam?", value=(
        "Interferem no `!trabalhar` e no `!roubar` (tanto do ladrão quanto da vítima).\n"
        "Cada uso em combate ou trabalho **consome fome**. Use `!mascotes` para ver os buffs de cada animal."
    ))
    embed.set_footer(text="🐾 Mascotes  ·  Clique em Início para voltar")
    return embed


def _pagina_roubos(author: disnake.Member) -> disnake.Embed:
    embed = disnake.Embed(title="😈 Roubos & Sabotagem", color=disnake.Color.red())
    embed.add_field(inline=False, name="🥷 `!roubar @usuario`", value=(
        "Tenta roubar entre 5% e 10% do saldo da vítima. Cooldown: **2 horas**.\n"
        "Chance base de sucesso: **45%**. Se falhar, você paga uma multa à vítima.\n"
        "**Se roubar com sucesso**, um bounty é colocado automaticamente na sua cabeça.\n"
        "🔑 **Pé de Cabra** (item): aumenta a chance para 65% e perfura o escudo."
    ))
    embed.add_field(inline=False, name="🚨 Evento Global: A Hora do Purge", value=(
        "Pode acontecer aleatoriamente a qualquer momento! Durante 30 minutos de anarquia pura:\n"
        "› `!trabalhar` **não funciona**.\n"
        "› O cooldown do `!roubar` cai para apenas **5 minutos**.\n"
        "› **Não há multas** caso o roubo falhe!"
    ))
    embed.add_field(inline=False, name="🛡️ `!escudo [@usuario]`  ·  🧨 `!c4 @usuario`", value=(
        "`!escudo` — Ativa o Escudo do inventário (**3 cargas**) ou checa o status.\n"
        "Cada tentativa de roubo sofrida consome 1 carga. Com escudo ativo, o roubo é bloqueado.\n"
        "`!c4` — Usa uma **Carga de C4** para destruir todas as cargas do escudo do alvo de uma vez."
    ))
    embed.add_field(inline=False, name="🚨 `!recompensa @usuario <valor>`  ·  📜 `!recompensas`", value=(
        "Coloca a cabeça do alvo a prêmio. Quem roubar ele com sucesso leva o bounty acumulado.\n"
        "`!recompensas` — Mural de procurados com todos os alvos ativos."
    ))
    embed.add_field(inline=False, name="🍌 `!casca @usuario`  ·  🦍 `!taxar @usuario`  ·  🪧 `!greve @usuario`", value=(
        "`!casca` — Usa **Casca de Banana**: próximo trabalho do alvo não rende nada.\n"
        "`!taxar` — Usa **Imposto do Gorila**: rouba 25% dos próximos 5 trabalhos do alvo.\n"
        "*(Após as 5 cargas, o alvo fica imune a novos impostos por **24h**.)*\n"
        "`!greve` — Usa item **Greve**: salário do alvo cai 50% por **3 horas**."
    ))
    embed.add_field(inline=False, name="🪄 `!apelidar`  ·  🐒 `!amaldicoar`  ·  🎭 `!impostor`", value=(
        "`!apelidar @usuario <nick>` — Usa **Troca de Nick**: altera o apelido do alvo por 30 min. *(500 MC)*\n"
        "`!amaldicoar @usuario` — Lança a Maldição Símia: por 60s o alvo não consegue falar direito. *(500 MC)*\n"
        "`!impostor @usuario <mensagem>` — Envia uma mensagem falsa como se fosse o alvo. *(500 MC)*"
    ))
    embed.add_field(inline=False, name="🧪 `!energetico`  ·  💨 `!fumaca`", value=(
        "`!energetico` — Usa **Energético Símio**: zera o cooldown do trabalho.\n"
        "`!fumaca` — Usa **Bomba de Fumaça**: zera o cooldown do roubo."
    ))
    embed.set_footer(text="😈 Roubos & Sabotagem  ·  Clique em Início para voltar")
    return embed


def _pagina_banco(author: disnake.Member) -> disnake.Embed:
    embed = disnake.Embed(title="🏦 Banco & Investimentos", color=disnake.Color.blue())
    embed.add_field(inline=False, name="🏛️ `!investir fixo <valor>`", value=(
        "Investimento seguro: rende **+10% na hora**.\n"
        "Limite: **5.000 MC por dia**. Cooldown de 24h."
    ))
    embed.add_field(inline=False, name="📈 `!investir cripto <valor>`", value=(
        "Alto risco! Após **30 segundos**, o resultado é sorteado:\n"
        "`-25%` · `-15%` · `-5%` · `0%` · `+5%` · `+10%` · `+20%`\n"
        "Limite: **4 operações por dia**.\n"
        "*(🌟 Talismã da Fortuna passivo reduz o prejuízo máximo de 25% → 15%.)*"
    ))
    embed.set_footer(text="🏦 Banco & Investimentos  ·  Clique em Início para voltar")
    return embed


def _pagina_jogos(author: disnake.Member) -> disnake.Embed:
    embed = disnake.Embed(title="🎲 Jogos & Apostas", color=disnake.Color.orange())
    embed.add_field(inline=False, name="⚠️ Canal exclusivo: #🎰・akbet", value=(
        "Todos os jogos funcionam apenas no canal de apostas.\n"
        "Use `!jogos` lá dentro para ver as regras detalhadas de cada um."
    ))
    embed.add_field(inline=False, name="🎰 Solo", value=(
        "`!crash` · `!cassino` · `!minas` · `!corrida` · `!bicho`"
    ))
    embed.add_field(inline=False, name="⚔️ 1 vs 1", value=(
        "`!duelo` · `!cipo` · `!bang` · `!briga` · `!carta` · `!explorar`"
    ))
    embed.add_field(inline=False, name="🎮 Multiplayer", value=(
        "`!21` · `!roleta` · `!mentira` · `!torneio` · `!coco`"
    ))
    embed.add_field(inline=False, name="⚽ Futebol", value=(
        "`!futebol` — Apostar em partidas.\n"
        "`!pule` — Ver seus bilhetes ativos e cancelar apostas."
    ))
    embed.set_footer(text="🎲 Jogos & Apostas  ·  Clique em Início para voltar")
    return embed


def _pagina_cosmeticos(author: disnake.Member) -> disnake.Embed:
    embed = disnake.Embed(title="✨ Cosméticos & Perfil", color=disnake.Color.magenta())
    embed.add_field(inline=False, name="🎨 `!visuais`", value=(
        "Painel privado para equipar e remover cosméticos (cor, moldura, título).\n"
        "Cosméticos são obtidos nas caixas e têm **preço fixo** na loja."
    ))
    embed.add_field(inline=False, name="💬 `!bio <texto>`", value=(
        "Define uma frase no seu perfil público (máx. 60 caracteres).\n"
        "Use `!bio` sem texto para remover."
    ))
    embed.add_field(inline=False, name="Raridades", value=(
        "⚫ Comuns · 🔵 Raros · 🟣 Épicos · 🌟 Lendários *(só nas Relíquias Ancestrais)*"
    ))
    embed.set_footer(text="✨ Cosméticos & Perfil  ·  Clique em Início para voltar")
    return embed


def _pagina_castigos(author: disnake.Member) -> disnake.Embed:
    embed = disnake.Embed(title="🤐 Castigos de Voz", color=disnake.Color.dark_red())
    embed.add_field(inline=False, name="🔇 `!castigo <tipo> <tempo> @usuario`", value=(
        "Silencia ou ensurdece alguém em um canal de voz.\n\n"
        "**Tipos:** `mudo` · `surdo` · `surdomudo`\n"
        "**Tempos:** `1` · `5` · `10` minutos\n\n"
        "**Preços:**\n"
        "› Mudo ou Surdo: `300 MC` (1min) · `1.500 MC` (5min) · `3.000 MC` (10min)\n"
        "› Surdomudo: `600 MC` (1min) · `3.000 MC` (5min) · `6.000 MC` (10min)\n\n"
        "⚠️ O alvo precisa estar em um canal de voz."
    ))
    embed.add_field(inline=False, name="👟 `!desconectar @usuario`", value=(
        "Expulsa o alvo do canal de voz.\n"
        "Custo: **1.200 MC**. O alvo precisa estar em voz."
    ))
    embed.set_footer(text="🤐 Castigos de Voz  ·  Clique em Início para voltar")
    return embed


# ──────────────────────────────────────────────────────────────────────────────
#  Mapa de páginas
# ──────────────────────────────────────────────────────────────────────────────

PAGINAS = {
    "inicio":     ("🏠 Início",     _pagina_inicio),
    "economia":   ("💵 Economia",   _pagina_economia),
    "mercado":    ("📦 Mercado",    _pagina_mercado),
    "passivos":   ("🔰 Passivos",   _pagina_passivos),
    "mascotes":   ("🐾 Mascotes",   _pagina_mascotes),
    "roubos":     ("😈 Roubos",     _pagina_roubos),
    "banco":      ("🏦 Banco",      _pagina_banco),
    "jogos":      ("🎲 Jogos",      _pagina_jogos),
    "cosmeticos": ("✨ Cosméticos", _pagina_cosmeticos),
    "castigos":   ("🤐 Castigos",   _pagina_castigos),
}

# Ordem fixa para distribuição nas linhas de botões
ORDEM = ["inicio", "economia", "mercado", "passivos", "mascotes", "roubos", "banco", "jogos", "cosmeticos", "castigos"]


# ──────────────────────────────────────────────────────────────────────────────
#  View com um botão por tópico (2 linhas de 5)
# ──────────────────────────────────────────────────────────────────────────────

class AjudaView(disnake.ui.View):
    def __init__(self, author: disnake.Member, pagina_atual: str = "inicio"):
        super().__init__(timeout=120)
        self.author       = author
        self.pagina_atual = pagina_atual
        self.message: disnake.Message = None
        self._build_buttons()

    def _build_buttons(self):
        self.clear_items()
        for i, slug in enumerate(ORDEM):
            nome, _ = PAGINAS[slug]
            is_atual = (slug == self.pagina_atual)
            btn = disnake.ui.Button(
                label=nome,
                style=disnake.ButtonStyle.success if is_atual else disnake.ButtonStyle.primary,
                disabled=is_atual,
                custom_id=f"ajuda_{slug}",
                row=i // 5  # 5 botões por linha → linha 0 e linha 1
            )
            btn.callback = self._fazer_callback(slug)
            self.add_item(btn)

    def _fazer_callback(self, slug: str):
        async def callback(inter: disnake.MessageInteraction):
            if inter.author.id != self.author.id:
                return await inter.response.send_message(
                    "❌ Apenas quem abriu o manual pode navegar nele.", ephemeral=True
                )
            self.pagina_atual = slug
            self._build_buttons()
            _, fn_embed = PAGINAS[slug]
            await inter.response.edit_message(embed=fn_embed(self.author), view=self)
        return callback

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
#  Cog
# ──────────────────────────────────────────────────────────────────────────────

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, comandos gerais no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(name="ajuda", aliases=["comandos", "info", "help"])
    async def ajuda_comando(self, ctx):
        embed        = _pagina_inicio(ctx.author)
        view         = AjudaView(ctx.author, "inicio")
        view.message = await ctx.send(embed=embed, view=view)

    @commands.command(aliases=["ganhos", "cargos", "limites"])
    async def salarios(self, ctx):
        embed = disnake.Embed(
            title="🍌 GUIA DE PROGRESSÃO DA SELVA",
            description=(
                "Veja o salário base por hora (`!trabalhar`), custo e limite de aposta de cada cargo.\n"
                "⚠️ **Dica:** O trabalho puro não enriquece ninguém — abra caixas, ganhe minigames, roube e invista!\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.gold()
        )

        tabela = [
            ("🐒 Lêmure",      "40 – 80 MC",         "400 MC",       "—",           "1.200 MC"),
            ("🐵 Macaquinho",  "130 – 230 MC",        "1.500 MC",     "1.200 MC",    "5.500 MC"),
            ("🦍 Babuíno",     "320 – 530 MC",        "4.500 MC",     "5.500 MC",    "14.000 MC"),
            ("🦧 Chimpanzé",   "780 – 1.320 MC",      "12.000 MC",    "14.000 MC",   "35.000 MC"),
            ("🌴 Orangutango", "1.900 – 3.200 MC",    "30.000 MC",    "35.000 MC",   "85.000 MC"),
            ("🌋 Gorila",      "4.700 – 7.800 MC",    "80.000 MC",    "85.000 MC",   "210.000 MC"),
            ("🗿 Ancestral",   "11.500 – 19.000 MC",  "250.000 MC",   "210.000 MC",  "600.000 MC"),
            ("👑 Rei Símio",   "27.000 – 45.000 MC",  "1.500.000 MC", "600.000 MC",  "MÁXIMO 👑"),
        ]

        for cargo, salario, limite_aposta, custo_este, custo_prox in tabela:
            embed.add_field(
                name=cargo,
                value=(
                    f"💰 Salário: **{salario}**\n"
                    f"🎰 Aposta Máx: **`{limite_aposta}`**\n"
                    f"└ *Preço: `{custo_este}`*\n"
                    f"└ *Próximo: `{custo_prox}`*"
                ),
                inline=True
            )

        embed.set_footer(text="Evolua o seu cargo na !loja para apostar valores mais altos!")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(General(bot))