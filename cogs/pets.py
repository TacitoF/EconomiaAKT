import disnake
from disnake.ext import commands
import database as db

# Registro central de atributos de cada mascote
INFO_MASCOTES = {
    # 🟢 COMUNS
    "capivara": {
        "nome": "Capivara", "emoji": "🟢", "imagem": "🦦", "raridade": "Comum",
        "buffs": "📈 **+10%** de lucro no `!trabalhar`"
    },
    "preguica": {
        "nome": "Bicho-Preguiça", "emoji": "🟢", "imagem": "🦥", "raridade": "Comum",
        "buffs": "📈 **+15%** no `!trabalhar`\n⚠️ Gasta **15%** de fome por turno"
    },
    "sapo_boi": {
        "nome": "Sapo-Boi", "emoji": "🟢", "imagem": "🐸", "raridade": "Comum",
        "buffs": "📈 **+8%** no `!trabalhar`\n✨ **20%** de chance de NÃO gastar fome"
    },

    # 🔵 RAROS
    "papagaio": {
        "nome": "Papagaio", "emoji": "🔵", "imagem": "🦜", "raridade": "Raro",
        "buffs": "🛡️ **-15%** de chance de você ser roubado"
    },
    "jiboia": {
        "nome": "Jiboia", "emoji": "🔵", "imagem": "🐍", "raridade": "Raro",
        "buffs": "🛡️ **-10%** chance de ser roubado\n💸 Ladrão paga **+50%** de multa se falhar"
    },
    "gamba": {
        "nome": "Gambá", "emoji": "🔵", "imagem": "🦔", "raridade": "Raro",
        "buffs": "🛡️ **-20%** chance de ser roubado\n⚠️ Gasta **20%** de fome ao te defender"
    },

    # 🟣 ÉPICOS
    "macaco_prego": {
        "nome": "Macaco-Prego", "emoji": "🟣", "imagem": "🐒", "raridade": "Épico",
        "buffs": "🥷 **+15%** de chance de sucesso ao roubar"
    },
    "harpia": {
        "nome": "Harpia", "emoji": "🟣", "imagem": "🦅", "raridade": "Épico",
        "buffs": "🥷 **+10%** sucesso ao roubar\n💰 Rouba uma porcentagem **maior** da vítima"
    },
    "lobo_guara": {
        "nome": "Lobo-Guará", "emoji": "🟣", "imagem": "🐺", "raridade": "Épico",
        "buffs": "📈 **+10%** Trabalho\n🥷 **+10%** Sucesso de Roubo"
    },

    # 🌟 LENDÁRIOS
    "onca": {
        "nome": "Onça Pintada", "emoji": "🌟", "imagem": "🐆", "raridade": "Lendária",
        "buffs": "📈 **+15%** Trabalho\n🥷 **+15%** Sucesso Roubo\n🛡️ **-15%** Chance ser roubado"
    },
    "gorila_prateado": {
        "nome": "Gorila Costas-Prateadas", "emoji": "🌟", "imagem": "🦍", "raridade": "Lendária",
        "buffs": "📈 **+25%** Trabalho\n🥷 **+20%** Sucesso Roubo"
    },
    "dragao_komodo": {
        "nome": "Dragão-de-Komodo", "emoji": "🌟", "imagem": "🐉", "raridade": "Lendária",
        "buffs": "🥷 **+25%** Sucesso Roubo\n🛡️ **-25%** Chance ser roubado"
    }
}

class Pets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🐒・conguitos':
            canal = disnake.utils.get(ctx.guild.channels, name='🐒・conguitos')
            mencao = canal.mention if canal else "#🐒・conguitos"
            await ctx.send(f"⚠️ {ctx.author.mention}, use os comandos de mascote no {mencao}!")
            raise commands.CommandError("Canal incorreto.")

    def gerar_barra_fome(self, fome: int):
        tamanho = 10
        cheios = int((fome / 100) * tamanho)
        vazios = tamanho - cheios
        
        if fome <= 20:
            barra = "🟥" * cheios + "⬛" * vazios
        elif fome <= 50:
            barra = "🟨" * cheios + "⬛" * vazios
        else:
            barra = "🟩" * cheios + "⬛" * vazios
            
        return f"[{barra}] {fome}%"

    @commands.command(aliases=["pet", "bichinho", "animal"])
    async def mascote(self, ctx, membro: disnake.Member = None):
        alvo = membro or ctx.author
        
        try:
            user = db.get_user_data(str(alvo.id))
            if not user:
                return await ctx.send(f"❌ Conta não encontrada!")

            tipo, fome = db.get_mascote(user)
            
            if not tipo or tipo not in INFO_MASCOTES:
                if alvo.id == ctx.author.id:
                    return await ctx.send(
                        f"🐾 {ctx.author.mention}, você não tem nenhum mascote!\n"
                        f"Trabalhe na selva e torça para resgatar uma **Gaiola Misteriosa**."
                    )
                else:
                    return await ctx.send(f"🐾 {alvo.display_name} não possui nenhum mascote no momento.")

            info = INFO_MASCOTES[tipo]

            if fome > 0:
                status = f"✅ **Ativo e Alerta!**\nOs buffs estão aplicados."
                cor = disnake.Color.green()
            else:
                status = f"💤 **Dormindo (Fome a 0%)**\nOs buffs estão **desativados**! Alimente-o."
                cor = disnake.Color.dark_grey()

            embed = disnake.Embed(
                title=f"{info['imagem']} Mascote de {alvo.display_name}",
                color=cor
            )
            embed.add_field(name="Espécie", value=f"{info['emoji']} **{info['nome']}** ({info['raridade']})", inline=True)
            embed.add_field(name="🍗 Fome", value=self.gerar_barra_fome(fome), inline=True)
            embed.add_field(name="✨ Vantagens", value=info['buffs'], inline=False)
            embed.add_field(name="Situação", value=status, inline=False)

            if alvo.id == ctx.author.id:
                embed.set_footer(text="A fome diminui com o uso. Use !alimentar para restaurar.")

            await ctx.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro no !mascote de {ctx.author}: {e}")
            await ctx.send("⚠️ Ocorreu um erro ao carregar o mascote.")

    @commands.command(aliases=["dar_comida"])
    async def alimentar(self, ctx):
        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Conta não encontrada!")

            tipo, fome = db.get_mascote(user)
            if not tipo:
                return await ctx.send(f"🐾 {ctx.author.mention}, você não tem nenhum mascote para alimentar!")

            if fome >= 100:
                return await ctx.send(f"🍗 {ctx.author.mention}, o seu mascote já está de barriga cheia!")

            inv_str  = str(user['data'][5]) if len(user['data']) > 5 else ""
            inv_list = [i.strip() for i in inv_str.split(',') if i.strip()]

            if "Ração Símia" not in inv_list:
                return await ctx.send(
                    f"❌ {ctx.author.mention}, você não tem **Ração Símia** no inventário!\n"
                    f"Compre na `!loja` na categoria de Sabotagem & Consumíveis."
                )

            inv_list.remove("Ração Símia")
            db.update_value(user['row'], 6, ", ".join(inv_list))

            nova_fome = min(fome + 50, 100)
            db.set_mascote(user['row'], tipo, nova_fome)

            info = INFO_MASCOTES.get(tipo, {"imagem": "🐾"})
            await ctx.send(f"🍗 {ctx.author.mention} deu Ração Símia para o mascote {info['imagem']}!\nFome restaurada: **{fome}% ➔ {nova_fome}%**.")

        except Exception as e:
            print(f"❌ Erro no !alimentar de {ctx.author}: {e}")
            await ctx.send("⚠️ Ocorreu um erro ao tentar alimentar o mascote.")

    @commands.command(aliases=["abandonar"])
    async def libertar(self, ctx):
        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return

            tipo, _ = db.get_mascote(user)
            if not tipo:
                return await ctx.send(f"🐾 {ctx.author.mention}, você não tem mascote.")

            info = INFO_MASCOTES.get(tipo, {"nome": "Mascote"})
            db.set_mascote(user['row'], "", 0)
            
            await ctx.send(f"🌿 {ctx.author.mention} abriu a gaiola e devolveu a sua **{info['nome']}** para a selva.\nA vaga de mascote está livre novamente!")
            
        except Exception as e:
            print(f"❌ Erro no !libertar de {ctx.author}: {e}")
            await ctx.send("⚠️ Ocorreu um erro ao tentar libertar o mascote.")

    # ── NOVO COMANDO: ENCICLOPÉDIA DE MASCOTES ──
    @commands.command(aliases=["guia_mascotes", "zoologico", "lista_pets"])
    async def mascotes(self, ctx):
        embed = disnake.Embed(
            title="🐾 GUIA DE MASCOTES DA SELVA",
            description="Conheça todos os companheiros disponíveis na **Gaiola Misteriosa** e as suas habilidades únicas!",
            color=disnake.Color.gold()
        )

        comuns = []
        raros = []
        epicos = []
        lendarios = []

        for slug, info in INFO_MASCOTES.items():
            texto = f"{info['imagem']} **{info['nome']}**\n{info['buffs']}\n"
            if info['raridade'] == "Comum":
                comuns.append(texto)
            elif info['raridade'] == "Raro":
                raros.append(texto)
            elif info['raridade'] == "Épico":
                epicos.append(texto)
            elif info['raridade'] == "Lendária":
                lendarios.append(texto)

        embed.add_field(name="🟢 COMUNS (60% de chance na Gaiola)", value="\n".join(comuns), inline=False)
        embed.add_field(name="🔵 RAROS (25% de chance na Gaiola)", value="\n".join(raros), inline=False)
        embed.add_field(name="🟣 ÉPICOS (10% de chance na Gaiola)", value="\n".join(epicos), inline=False)
        embed.add_field(name="🌟 LENDÁRIOS (5% de chance na Gaiola)", value="\n".join(lendarios), inline=False)

        embed.set_footer(text="Trabalhe arduamente na selva para ter a chance de encontrar uma gaiola!")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Pets(bot))