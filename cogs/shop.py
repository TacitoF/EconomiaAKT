import disnake
from disnake.ext import commands
import database as db
import time

ESCUDO_CARGAS = 3

def formatar_moeda(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

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

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, use a loja no canal {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["shop", "mercado"])
    async def loja(self, ctx):
        embed = disnake.Embed(
            title="🛒 MERCADO NEGRO DA SELVA",
            description=(
                "Bem-vindo à loja! Para adquirir algo, use o comando:\n"
                "`!comprar <nome do item>` (Ex: `!comprar Pé de Cabra`)"
            ),
            color=disnake.Color.dark_theme()
        )

        embed.add_field(
            name="📈 PROGRESSÃO (Cargos)",
            value=(
                "Suba de cargo para aumentar seu salário e limite de apostas!\n\n"
                "🐒 **Macaquinho** ─ `1.200 MC`\n"
                "🐵 **Babuíno** ─ `5.500 MC`\n"
                "🌴 **Chimpanzé** ─ `14.000 MC`\n"
                "🦧 **Orangutango** ─ `35.000 MC`\n"
                "🦍 **Gorila** ─ `85.000 MC`\n"
                "🗿 **Ancestral** ─ `210.000 MC`\n"
                "👑 **Rei Símio** ─ `600.000 MC`"
            ), inline=True
        )

        embed.add_field(name="\u200B", value="\u200B", inline=True)  # espaçador pra alinhar os campos

        embed.add_field(
            name="🛡️ EQUIPAMENTOS E DEFESA",
            value=(
                "🛡️ **Escudo** ─ `1.000 MC`\n"
                "└ *Bloqueia 3 tentativas de roubo (Limite: 1 compra/dia).*\n\n"
                "🕵️ **Pé de Cabra** ─ `1.200 MC`\n"
                "└ *Eleva a chance de roubo a 65% e fura Escudos.*\n\n"
                "📄 **Seguro** ─ `950 MC`\n"
                "└ *Garante reembolso de 60% se você for roubado.*"
            ), inline=False
        )

        embed.add_field(
            name="📦 LOOTBOXES (Contrabando)",
            value=(
                "🪵 **Caixote de Madeira** ─ `800 MC`\n"
                "└ *Contém itens de utilidade leve. (Use `!abrir caixote`)*\n\n"
                "🪙 **Baú do Caçador** ─ `3.500 MC`\n"
                "└ *Itens táticos e prêmios maiores. (Use `!abrir baú`)*\n\n"
                "🏺 **Relíquia Ancestral** ─ `15.000 MC`\n"
                "└ *Pura riqueza e tesouros de alto valor. (Use `!abrir relíquia`)*"
            ), inline=False
        )

        embed.add_field(
            name="😈 SABOTAGEM (Consumíveis)",
            value=(
                "🍌 **Casca de Banana** ─ `300 MC`\n"
                "└ *Atrasa a vítima no trabalho. (Use `!casca @user`)*\n\n"
                "🦍 **Imposto do Gorila** ─ `1.500 MC`\n"
                "└ *Rouba 25% do próximo trabalho do alvo. (Use `!taxar @user`)*\n\n"
                "🪄 **Troca de Nick** ─ `3.000 MC`\n"
                "└ *Altera o apelido do alvo no server. (Use `!apelidar @user <nick>`)*"
            ), inline=False
        )

        embed.add_field(
            name="⚡ SERVIÇOS DIRETOS",
            value=(
                "*Esses serviços não vão para o inventário, são cobrados e usados na hora!*\n\n"
                "🙊 **Maldição Símia** ─ `500 MC`\n"
                "└ *Uso direto:* `!amaldicoar @user`\n\n"
                "🎭 **Impostor** ─ `500 MC`\n"
                "└ *Uso direto:* `!impostor @user <mensagem>`"
            ), inline=False
        )

        embed.set_footer(text="🐒 Os itens consumíveis também podem ser encontrados nas lootboxes!")
        await ctx.send(embed=embed)

    @commands.command()
    async def comprar(self, ctx, *, item: str = None):
        if item is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, uso: `!comprar <nome do item>`")

        try:
            user_id = str(ctx.author.id)
            user = db.get_user_data(user_id)
            if not user:
                return await ctx.send("❌ Use `!trabalhar` primeiro para se registrar!")

            loja = {
                "macaquinho":         {"nome": "Macaquinho",        "preco": 1200.0,   "tipo": "cargo"},
                "babuíno":            {"nome": "Babuíno",           "preco": 5500.0,   "tipo": "cargo"},
                "babuino":            {"nome": "Babuíno",           "preco": 5500.0,   "tipo": "cargo"},
                "chimpanzé":          {"nome": "Chimpanzé",         "preco": 14000.0,  "tipo": "cargo"},
                "chimpanze":          {"nome": "Chimpanzé",         "preco": 14000.0,  "tipo": "cargo"},
                "orangutango":        {"nome": "Orangutango",       "preco": 35000.0,  "tipo": "cargo"},
                "gorila":             {"nome": "Gorila",            "preco": 85000.0,  "tipo": "cargo"},
                "ancestral":          {"nome": "Ancestral",         "preco": 210000.0, "tipo": "cargo"},
                "rei símio":          {"nome": "Rei Símio",         "preco": 600000.0, "tipo": "cargo"},
                "rei simio":          {"nome": "Rei Símio",         "preco": 600000.0, "tipo": "cargo"},
                "escudo":             {"nome": "Escudo",            "preco": 1000.0,   "tipo": "item"},
                "pé de cabra":        {"nome": "Pé de Cabra",       "preco": 1200.0,   "tipo": "item"},
                "pe de cabra":        {"nome": "Pé de Cabra",       "preco": 1200.0,   "tipo": "item"},
                "seguro":             {"nome": "Seguro",            "preco": 950.0,    "tipo": "item"},
                "casca de banana":    {"nome": "Casca de Banana",   "preco": 300.0,    "tipo": "item"},
                "imposto do gorila":  {"nome": "Imposto do Gorila", "preco": 1500.0,   "tipo": "item"},
                "troca de nick":      {"nome": "Troca de Nick",     "preco": 3000.0,   "tipo": "item"},
                "caixote de madeira": {"nome": "Caixote de Madeira","preco": 800.0,    "tipo": "item"},
                "caixote":            {"nome": "Caixote de Madeira","preco": 800.0,    "tipo": "item"},
                "baú do caçador":     {"nome": "Baú do Caçador",   "preco": 3500.0,   "tipo": "item"},
                "bau do cacador":     {"nome": "Baú do Caçador",   "preco": 3500.0,   "tipo": "item"},
                "baú":                {"nome": "Baú do Caçador",   "preco": 3500.0,   "tipo": "item"},
                "bau":                {"nome": "Baú do Caçador",   "preco": 3500.0,   "tipo": "item"},
                "relíquia ancestral": {"nome": "Relíquia Ancestral","preco": 15000.0,  "tipo": "item"},
                "reliquia ancestral": {"nome": "Relíquia Ancestral","preco": 15000.0,  "tipo": "item"},
                "relíquia":           {"nome": "Relíquia Ancestral","preco": 15000.0,  "tipo": "item"},
                "reliquia":           {"nome": "Relíquia Ancestral","preco": 15000.0,  "tipo": "item"},
            }

            escolha = item.lower()
            if escolha not in loja:
                return await ctx.send("❌ Item inválido! Digite exatamente como está na `!loja`.")

            item_data = loja[escolha]
            saldo = db.parse_float(user['data'][2])

            if saldo < item_data["preco"]:
                faltam = round(item_data["preco"] - saldo, 2)
                return await ctx.send(
                    f"❌ Saldo insuficiente! Você precisa de **{formatar_moeda(item_data['preco'])} MC** "
                    f"(faltam **{formatar_moeda(faltam)} MC**)."
                )

            db.update_value(user['row'], 3, round(saldo - item_data["preco"], 2))

            if item_data["tipo"] == "cargo":
                db.update_value(user['row'], 4, item_data["nome"])
                await ctx.send(f"✅ {ctx.author.mention} evoluiu para o cargo **{item_data['nome']}**! 🎉")

            else:
                inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
                inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]

                if item_data["nome"] == "Escudo":
                    agora = time.time()
                    
                    # --- SINCRONIZAÇÃO DO ESCUDO (COLUNA L) ---
                    if user_id not in self.bot.escudos_ativos and len(user['data']) > 11:
                        dado_escudo = str(user['data'][11]).strip()
                        if dado_escudo.isdigit() and int(dado_escudo) > 0:
                            self.bot.escudos_ativos[user_id] = int(dado_escudo)
                    # ------------------------------------------

                    escudo_ativo = hasattr(self.bot, 'escudos_ativos') and \
                                   self.bot.escudos_ativos.get(user_id, 0) > 0
                    if "Escudo" in inv_list or escudo_ativo:
                        db.update_value(user['row'], 3, round(saldo, 2))  # estorna o valor
                        return await ctx.send(
                            f"❌ {ctx.author.mention}, você já tem um **Escudo** "
                            f"{'ativo' if escudo_ativo else 'no inventário'}! "
                            f"Só pode ter 1 de cada vez."
                        )

                    historico        = self.bot.escudo_compras.get(user_id, (0, 0.0))
                    ultima_compra_ts = historico[1]

                    if agora - ultima_compra_ts < 86400:
                        libera_em = int(ultima_compra_ts + 86400)
                        db.update_value(user['row'], 3, round(saldo, 2))  # estorna o valor
                        return await ctx.send(
                            f"⏳ {ctx.author.mention}, você já comprou um **Escudo** hoje! "
                            f"Pode comprar outro <t:{libera_em}:R>."
                        )

                    self.bot.escudo_compras[user_id] = (1, agora)

                inv_list.append(item_data["nome"])
                db.update_value(user['row'], 6, ", ".join(inv_list))
                await ctx.send(f"🛍️ {ctx.author.mention} comprou **{item_data['nome']}** e guardou no inventário!")

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !comprar de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")

def setup(bot):
    bot.add_cog(Shop(bot))