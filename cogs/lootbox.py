import disnake
from disnake.ext import commands
import database as db
import random
import asyncio

def formatar_moeda(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Cosméticos por raridade que podem sair nas lootboxes
COSM_COMUNS = [
    ("cor:verde",   "🟢 Cor Verde Selva",      "🟢"),
    ("cor:azul",    "🔵 Cor Azul Tropical",    "🔵"),
    ("cor:cinza",   "⚫ Cor Cinza das Pedras", "⚫"),
    ("titulo:O Intocável", "🏷️ Título: O Intocável", "🏷️"),
]

COSM_RAROS = [
    ("cor:roxo",        "🟣 Cor Roxo Místico",      "🟣"),
    ("cor:laranja",     "🟠 Cor Laranja Fogo",      "🟠"),
    ("cor:ciano",       "🩵 Cor Ciano Glacial",     "🩵"),
    ("moldura:💀",      "💀 Moldura Caveira",       "💀"),
    ("moldura:🔥",      "🔥 Moldura Chamas",        "🔥"),
    ("moldura:⚡",      "⚡ Moldura Relâmpago",     "⚡"),
    ("titulo:Fantasma", "🏷️ Título: Fantasma",      "🏷️"),
    ("titulo:Mão de Ferro", "🏷️ Título: Mão de Ferro", "🏷️"),
    ("titulo:Caçador de Sombras", "🏷️ Título: Caçador de Sombras", "🏷️"),
]

COSM_EPICOS = [
    ("cor:gold",        "🟡 Cor Dourado Real",       "🟡"),
    ("cor:vermelho",    "🔴 Cor Vermelho Sangue",    "🔴"),
    ("cor:rosa",        "🌸 Cor Rosa Flamingo",      "🌸"),
    ("moldura:🌙",      "🌙 Moldura Lua Negra",      "🌙"),
    ("moldura:👑",      "👑 Moldura Coroa Dourada",  "👑"),
    ("moldura:💎",      "💎 Moldura Diamante",       "💎"),
    ("moldura:🐍",      "🐍 Moldura Cobra Real",     "🐍"),
    ("titulo:Rei das Trevas",  "🏷️ Título: Rei das Trevas",  "🏷️"),
    ("titulo:O Invicto",       "🏷️ Título: O Invicto",       "🏷️"),
    ("titulo:Senhor do Caos",  "🏷️ Título: Senhor do Caos",  "🏷️"),
]

COSM_LENDARIOS = [
    ("moldura:🌟",   "🌟 Moldura Estrela Cadente", "🌟"),
    ("moldura:🏴‍☠️", "🏴‍☠️ Moldura Pirata",       "🏴‍☠️"),
    ("titulo:Lenda da Selva", "🏷️ Título: Lenda da Selva", "🏷️"),
]


def _sortear_cosmetico(pool: list) -> dict:
    slug, label, emoji = random.choice(pool)
    return {"tipo": "cosmetico", "slug": slug, "nome": label, "emoji": emoji}


class Lootbox(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, use as caixas no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    def sortear_comum(self):
        """Caixote de Madeira — 100% focado em itens e cosméticos comuns."""
        chance = random.randint(1, 100)
        if chance <= 30:
            return {"tipo": "item", "nome": "Casca de Banana",  "emoji": "🍌"}
        elif chance <= 60:
            return {"tipo": "item", "nome": "Energético Símio", "emoji": "🧪"}
        elif chance <= 85:
            return {"tipo": "item", "nome": "Bomba de Fumaça",  "emoji": "💨"}
        else:
            return _sortear_cosmetico(COSM_COMUNS)

    def sortear_raro(self):
        """Baú do Caçador — itens táticos + cosméticos raros."""
        chance = random.randint(1, 100)
        if chance <= 25:
            return {"tipo": "item", "nome": "Escudo",       "emoji": "🛡️"}
        elif chance <= 50:
            return {"tipo": "item", "nome": "Pé de Cabra",  "emoji": "🕵️"}
        elif chance <= 65:
            return {"tipo": "item", "nome": "Carga de C4",  "emoji": "🧨"}
        elif chance <= 80:
            return {"tipo": "item", "nome": "Seguro",       "emoji": "📄"}
        elif chance <= 95:
            return _sortear_cosmetico(COSM_RAROS)
        else:
            return _sortear_cosmetico(COSM_COMUNS)

    def sortear_lendario(self):
        chance = random.randint(1, 100)
        if chance <= 20:
            return {"tipo": "item", "nome": "Imposto do Gorila", "emoji": "🦍"}
        elif chance <= 40:
            return {"tipo": "item", "nome": "Carga de C4",       "emoji": "🧨"}
        elif chance <= 55:
            return {"tipo": "item", "nome": "Troca de Nick",       "emoji": "🪄"}
        elif chance <= 60:
            return {"tipo": "item", "nome": "Escudo Anti-Imposto", "emoji": "🏛️"}
        elif chance <= 65:
            return {"tipo": "item", "nome": "Seguro",              "emoji": "📄"}
        elif chance <= 85:
            return _sortear_cosmetico(COSM_EPICOS)
        elif chance <= 100:
            return _sortear_cosmetico(COSM_LENDARIOS)
        return _sortear_cosmetico(COSM_EPICOS)

    def sortear_gaiola(self):
        """Gaiola Misteriosa — Sorteia um dos 12 mascotes baseados na raridade."""
        chance = random.randint(1, 100)
        
        # 🟢 COMUNS (60%)
        if chance <= 20:
            return {"tipo": "mascote", "slug": "capivara", "nome": "Capivara", "emoji": "🦦", "raridade": "Comum", "cor": disnake.Color.green()}
        elif chance <= 40:
            return {"tipo": "mascote", "slug": "preguica", "nome": "Bicho-Preguiça", "emoji": "🦥", "raridade": "Comum", "cor": disnake.Color.green()}
        elif chance <= 60:
            return {"tipo": "mascote", "slug": "sapo_boi", "nome": "Sapo-Boi", "emoji": "🐸", "raridade": "Comum", "cor": disnake.Color.green()}
        
        # 🔵 RAROS (25%)
        elif chance <= 69:
            return {"tipo": "mascote", "slug": "papagaio", "nome": "Papagaio", "emoji": "🦜", "raridade": "Raro", "cor": disnake.Color.blue()}
        elif chance <= 77:
            return {"tipo": "mascote", "slug": "jiboia", "nome": "Jiboia", "emoji": "🐍", "raridade": "Raro", "cor": disnake.Color.blue()}
        elif chance <= 85:
            return {"tipo": "mascote", "slug": "gamba", "nome": "Gambá", "emoji": "🦔", "raridade": "Raro", "cor": disnake.Color.blue()}
        
        # 🟣 ÉPICOS (10%)
        elif chance <= 89:
            return {"tipo": "mascote", "slug": "macaco_prego", "nome": "Macaco-Prego", "emoji": "🐒", "raridade": "Épico", "cor": disnake.Color.purple()}
        elif chance <= 92:
            return {"tipo": "mascote", "slug": "harpia", "nome": "Harpia", "emoji": "🦅", "raridade": "Épico", "cor": disnake.Color.purple()}
        elif chance <= 95:
            return {"tipo": "mascote", "slug": "lobo_guara", "nome": "Lobo-Guará", "emoji": "🐺", "raridade": "Épico", "cor": disnake.Color.purple()}
        
        # 🌟 LENDÁRIOS (5%)
        elif chance <= 97:
            return {"tipo": "mascote", "slug": "onca", "nome": "Onça Pintada", "emoji": "🐆", "raridade": "Lendária", "cor": disnake.Color.gold()}
        elif chance <= 99:
            return {"tipo": "mascote", "slug": "gorila_prateado", "nome": "Gorila Costas-Prateadas", "emoji": "🦍", "raridade": "Lendária", "cor": disnake.Color.gold()}
        else:
            return {"tipo": "mascote", "slug": "dragao_komodo", "nome": "Dragão-de-Komodo", "emoji": "🐉", "raridade": "Lendária", "cor": disnake.Color.gold()}

    @commands.command(aliases=["lootboxes", "chances"])
    async def caixas(self, ctx):
        """Exibe o conteúdo e as porcentagens de drop de cada caixa."""
        embed = disnake.Embed(
            title="🎁 LOOTBOXES DA SELVA",
            description="As caixas contêm equipamentos, itens de sabotagem, cosméticos e até mascotes vivos!\nVeja as probabilidades de drop abaixo:",
            color=disnake.Color.dark_theme()
        )
        
        embed.add_field(
            name="🪵 Caixote de Madeira",
            value=(
                "`30%` 🍌 Casca de Banana\n"
                "`30%` 🧪 Energético Símio\n"
                "`25%` 💨 Bomba de Fumaça\n"
                "`15%` ⚪ Cosmético Comum"
            ),
            inline=True
        )
        
        embed.add_field(
            name="🪙 Baú do Caçador",
            value=(
                "`25%` 🛡️ Escudo\n"
                "`25%` 🕵️ Pé de Cabra\n"
                "`15%` 🧨 Carga de C4\n"
                "`15%` 📄 Seguro\n"
                "`15%` 🔵 Cosmético Raro\n"
                "`05%` ⚪ Cosmético Comum"
            ),
            inline=True
        )

        embed.add_field(
            name="🏺 Relíquia Ancestral",
            value=(
                "`20%` 🦍 Imposto do Gorila\n"
                "`20%` 🧨 Carga de C4\n"
                "`15%` 🪄 Troca de Nick\n"
                "`05%` 🏛️ Escudo Anti-Imposto\n"
                "`05%` 📄 Seguro\n"
                "`20%` 🟣 Cosmético Épico\n"
                "`15%` 🌟 Cosmético Lendário"
            ),
            inline=True
        )

        embed.add_field(
            name="🐾 Gaiola Misteriosa",
            value=(
                "**🟢 Comuns (60%)**\n🦦 Capivara · 🦥 Preguiça · 🐸 Sapo-Boi\n"
                "**🔵 Raros (25%)**\n🦜 Papagaio · 🐍 Jiboia · 🦔 Gambá\n"
                "**🟣 Épicos (10%)**\n🐒 Macaco-Prego · 🦅 Harpia · 🐺 Lobo-Guará\n"
                "**🌟 Lendários (5%)**\n🐆 Onça · 🦍 Gorila · 🐉 Dragão-de-Komodo"
            ),
            inline=False
        )
        
        embed.set_footer(text="Gaiolas Misteriosas só podem ser encontradas no !trabalhar ou em airdrops.")
        await ctx.send(embed=embed)

    @commands.command(aliases=["abrir"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def abrir_caixa(self, ctx, *, nome_caixa: str = None):
        if nome_caixa is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, uso: `!abrir <Caixote / Baú / Relíquia / Gaiola>`")

        nome_caixa = nome_caixa.lower()
        if "caixote" in nome_caixa or "madeira" in nome_caixa:
            caixa_alvo   = "Caixote de Madeira"
            emoji_caixa  = "🪵"
            sorteio_func = self.sortear_comum
            cor_final    = disnake.Color.from_rgb(139, 69, 19)
        elif "baú" in nome_caixa or "bau" in nome_caixa or "caçador" in nome_caixa:
            caixa_alvo   = "Baú do Caçador"
            emoji_caixa  = "🪙"
            sorteio_func = self.sortear_raro
            cor_final    = disnake.Color.blue()
        elif "relíquia" in nome_caixa or "reliquia" in nome_caixa or "ancestral" in nome_caixa:
            caixa_alvo   = "Relíquia Ancestral"
            emoji_caixa  = "🏺"
            sorteio_func = self.sortear_lendario
            cor_final    = disnake.Color.gold()
        elif "gaiola" in nome_caixa or "misteriosa" in nome_caixa:
            caixa_alvo   = "Gaiola Misteriosa"
            emoji_caixa  = "🐾"
            sorteio_func = self.sortear_gaiola
            cor_final    = disnake.Color.dark_grey() 
        else:
            return await ctx.send("❌ Caixa inválida! Escolha entre: `Caixote`, `Baú`, `Relíquia` ou `Gaiola`.")

        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Você não tem conta!")

            # ── PROTEÇÃO DA GAIOLA ──
            if caixa_alvo == "Gaiola Misteriosa":
                tipo_atual, _ = db.get_mascote(user)
                if tipo_atual:
                    return await ctx.send(
                        f"❌ {ctx.author.mention}, você já tem um mascote acompanhando-o!\n"
                        f"Use o comando `!guardar` para o enviar para a fazenda, ou `!libertar` para o soltar na selva antes de abrir uma nova gaiola."
                    )

            inv_str  = str(user["data"][5]) if len(user["data"]) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(",") if i.strip()]

            # ── VERIFICAÇÃO SE A CAIXA ESTÁ NO INVENTÁRIO E SE TEM 🔒 ──
            caixa_encontrada = None
            for item in inv_list:
                item_limpo = item.replace("🔒", "").strip()
                if item_limpo == caixa_alvo:
                    caixa_encontrada = item
                    break

            if not caixa_encontrada:
                return await ctx.send(f"❌ Você não tem nenhum(a) **{caixa_alvo}** no inventário!")

            esta_vinculada = "🔒" in caixa_encontrada

            inv_list.remove(caixa_encontrada)
            db.update_value(user["row"], 6, ", ".join(inv_list) if inv_list else "Nenhum")

            ctx._missao_ok = True  # FLAG DE SUCESSO DA MISSÃO (O jogador realmente gastou a caixa)

            premio = sorteio_func()

            msg = await ctx.send(f"🔓 {ctx.author.mention} está abrindo **{caixa_alvo}**... {emoji_caixa}")
            await asyncio.sleep(3.0)

            # ── 1. MASCOTES ──
            if premio["tipo"] == "mascote":
                db.set_mascote(user["row"], premio["slug"], 100)
                texto_premio = f"**{premio['nome']}** ({premio['raridade']})"
                cor_final = premio["cor"]
                footer = "Use !mascote para ver os atributos do seu novo companheiro!"

            # ── 2. COSMÉTICOS ──
            elif premio["tipo"] == "cosmetico":
                user_atual = db.get_user_data(str(ctx.author.id))
                inv_atual  = [i.strip() for i in str(user_atual["data"][5]).split(",") if i.strip() and i.strip() != "Nenhum"]
                chave_inv  = f"cosmético:{premio['slug']}"

                if chave_inv in inv_atual:
                    consolacao = random.randint(300, 800)
                    saldo = db.parse_float(user_atual["data"][2])
                    db.update_value(user_atual["row"], 3, round(saldo + consolacao, 2))
                    texto_premio = f"`{formatar_moeda(consolacao)} MC` *(você já tinha esse cosmético — convertido em MC)*"
                    footer = f"Cosmético duplicado! {formatar_moeda(consolacao)} MC de consolação adicionados ao seu saldo."
                else:
                    inv_atual.append(chave_inv)
                    db.update_value(user_atual["row"], 6, ", ".join(inv_atual))
                    texto_premio = f"**{premio['nome']}**"
                    footer = f"✨ Use !visuais para equipar no seu perfil!"

                if premio["slug"] in [s for s, *_ in [("moldura:🌟",), ("moldura:🏴‍☠️",), ("titulo:Lenda da Selva",)]]:
                    cor_final = disnake.Color.from_rgb(255, 215, 0)

            # ── 3. ITENS NORMAIS ──
            else:
                user_atual = db.get_user_data(str(ctx.author.id))
                inv_atual  = [i.strip() for i in str(user_atual["data"][5]).split(",") if i.strip() and i.strip() != "Nenhum"]
                
                # Aplica o cadeado ao item caso a caixa seja vinculada
                nome_item = premio["nome"]
                if esta_vinculada:
                    nome_item += " 🔒"
                
                inv_atual.append(nome_item)
                db.update_value(user_atual["row"], 6, ", ".join(inv_atual))
                
                texto_premio = f"1× **{nome_item}**"
                
                if esta_vinculada:
                    footer = "🔒 Item vinculado! Este item não pode ser negociado ou vendido."
                else:
                    DICAS_USO = {
                        "Energético Símio":  "Use !energetico para zerar o cooldown do !trabalhar.",
                        "Bomba de Fumaça":   "Use !fumaca para zerar o cooldown do !roubar.",
                        "Carga de C4":       "Use !c4 @usuario para destruir o escudo do alvo.",
                        "Imposto do Gorila": "Use !taxar @usuario para cobrar 25% dos próximos 5 trabalhos.",
                        "Troca de Nick":     "Use !apelidar @usuario <nick> para trocar o apelido do alvo.",
                        "Casca de Banana":   "Use !casca @usuario para atrapalhar o próximo trabalho do alvo.",
                        "Escudo":            "Use !escudo para ativar e proteger-se contra 3 tentativas de roubo.",
                        "Pé de Cabra":       "O Pé de Cabra é usado automaticamente no próximo !roubar.",
                        "Seguro":            "O Seguro é acionado automaticamente se você for roubado (reembolsa 60%).",
                        "Greve":             "Use !greve @usuario para reduzir o salário do alvo em 50% por 3h.",
                    }
                    footer = DICAS_USO.get(premio["nome"], "Item adicionado ao inventário. Veja !inventario.")

            # ── MONTA O EMBED FINAL ──
            embed = disnake.Embed(
                title=f"🎉 {emoji_caixa} LOOT OBTIDO!",
                description=f"A caixa foi aberta e revelou:\n\n{premio['emoji']} {texto_premio}",
                color=cor_final
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            embed.set_footer(text=footer)

            await msg.edit(content="", embed=embed)

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !abrir de {ctx.author}: {e}")
            await ctx.send(
                f"⚠️ {ctx.author.mention}, ocorreu um erro ao abrir a caixa. "
                "Seu item está seguro, tente novamente!"
            )

def setup(bot):
    bot.add_cog(Lootbox(bot))