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
            faz_tipo, faz_fome = db.get_fazenda(user)
            
            if not tipo and not faz_tipo:
                if alvo.id == ctx.author.id:
                    return await ctx.send(
                        f"🐾 {ctx.author.mention}, você não tem nenhum mascote ativo nem na fazenda!\n"
                        f"Trabalhe na selva e torça para resgatar uma **Gaiola Misteriosa**."
                    )
                else:
                    return await ctx.send(f"🐾 {alvo.display_name} não possui nenhum mascote no momento.")

            embed = disnake.Embed(color=disnake.Color.dark_theme())

            if tipo:
                info = INFO_MASCOTES.get(tipo, {"nome": "Desconhecido", "imagem": "🐾", "raridade": "?", "emoji": "🐾", "buffs": "Nenhum"})
                if fome > 0:
                    status = f"✅ **Ativo e Alerta!**\nOs buffs estão aplicados."
                    embed.color = disnake.Color.green()
                else:
                    status = f"💤 **Dormindo (Fome a 0%)**\nOs buffs estão **desativados**! Alimente-o."
                    embed.color = disnake.Color.dark_grey()

                embed.title = f"{info['imagem']} Mascote Ativo de {alvo.display_name}"
                embed.add_field(name="Espécie", value=f"{info['emoji']} **{info['nome']}** ({info['raridade']})", inline=True)
                embed.add_field(name="🍗 Fome", value=self.gerar_barra_fome(fome), inline=True)
                embed.add_field(name="✨ Vantagens", value=info['buffs'], inline=False)
                embed.add_field(name="Situação", value=status, inline=False)
            else:
                embed.title = f"🐾 Mascote Ativo de {alvo.display_name}"
                embed.description = "Nenhum mascote ativo no momento. O slot principal está livre!"

            # Adiciona o status da fazenda no perfil
            if faz_tipo:
                info_faz = INFO_MASCOTES.get(faz_tipo, {"nome": "Desconhecido", "imagem": "🐾"})
                embed.add_field(
                    name="🏡 Na Fazenda", 
                    value=f"{info_faz['imagem']} **{info_faz['nome']}** (Fome: {faz_fome}%)\n*Os buffs deste mascote estão pausados.*", 
                    inline=False
                )

            if alvo.id == ctx.author.id:
                inv_str  = str(user["data"][5]) if len(user["data"]) > 5 else ""
                inv_list = [i.strip() for i in inv_str.split(",") if i.strip()]
                racoes = inv_list.count("Ração Símia")
                racoes_txt = f"{racoes}× Ração Símia no inventário" if racoes > 0 else "Sem Ração Símia — compre na !loja!"
                
                texto_dica = f"A fome diminui com o uso. Use !alimentar para restaurar.  ·  {racoes_txt}"
                if faz_tipo: texto_dica += "\nUse !trocarpet para trazer o mascote da fazenda de volta!"
                
                embed.set_footer(text=texto_dica)

            await ctx.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro no !mascote de {ctx.author}: {e}")
            await ctx.send("⚠️ Ocorreu um erro ao carregar o mascote.")

    @commands.command(aliases=["darcomida", "comida"])
    async def alimentar(self, ctx):
        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return await ctx.send("❌ Conta não encontrada!")

            tipo, fome = db.get_mascote(user)
            if not tipo:
                return await ctx.send(f"🐾 {ctx.author.mention}, você não tem nenhum mascote **ativo** para alimentar!\n*(Mascotes na fazenda não perdem fome e não precisam ser alimentados)*")

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

    # ── COMANDOS DA FAZENDA ──

    @commands.command(aliases=["farm"])
    async def fazenda(self, ctx):
        """Verifica qual mascote está guardado na fazenda."""
        user = db.get_user_data(str(ctx.author.id))
        if not user: return await ctx.send("❌ Conta não encontrada.")

        faz_tipo, faz_fome = db.get_fazenda(user)

        if not faz_tipo:
            embed = disnake.Embed(
                title="🏡 Fazenda de Mascotes",
                description=(
                    "Sua fazenda está **vazia**!\n"
                    "Use `!guardar` para enviar o seu mascote ativo para cá. "
                    "Isso deixará o seu slot principal livre para poder abrir uma nova **Gaiola Misteriosa**!"
                ),
                color=disnake.Color.green()
            )
            return await ctx.send(embed=embed)

        info = INFO_MASCOTES.get(faz_tipo, {"nome": "Desconhecido", "imagem": "🐾", "raridade": "?"})

        embed = disnake.Embed(
            title=f"🏡 Fazenda de {ctx.author.display_name}",
            description="Este mascote está a descansar tranquilamente. Ele não perde fome e os seus buffs estão pausados.",
            color=disnake.Color.green()
        )
        embed.add_field(name="Hóspede", value=f"{info.get('imagem', '🐾')} **{info.get('nome', faz_tipo)}** ({info.get('raridade', '?')})", inline=True)
        embed.add_field(name="🍗 Fome Congelada", value=self.gerar_barra_fome(faz_fome), inline=True)
        embed.set_footer(text="Use !trocarpet para trazer este mascote de volta à ação!")
        
        await ctx.send(embed=embed)

    @commands.command(aliases=["estacionar", "guardarpet"])
    async def guardar(self, ctx):
        """Envia o mascote ativo para a fazenda, desocupando o slot principal."""
        user = db.get_user_data(str(ctx.author.id))
        if not user: return await ctx.send("❌ Conta não encontrada.")

        tipo_ativo, fome_ativo = db.get_mascote(user)
        faz_tipo, _ = db.get_fazenda(user)
        
        if not tipo_ativo:
            return await ctx.send("🐾 Você não tem um mascote ativo para poder guardar!")

        if faz_tipo:
            return await ctx.send(
                "🏡 A sua fazenda já está ocupada por outro mascote!\n"
                "Use `!trocarpet` para alternar entre eles."
            )

        # Move o mascote atual para a fazenda
        db.set_fazenda(user['row'], tipo_ativo, fome_ativo)

        # Limpa o slot ativo no banco de dados
        db.set_mascote(user['row'], "", 0)

        info = INFO_MASCOTES.get(tipo_ativo, {"nome": "Mascote", "imagem": "🐾"})
        await ctx.send(
            f"🏡 {ctx.author.mention} enviou **{info['imagem']} {info['nome']}** para descansar na fazenda!\n"
            f"O seu slot principal está agora vazio. Já pode abrir uma nova **Gaiola Misteriosa**!"
        )

    @commands.command(aliases=["trocar", "resgatar"])
    async def trocarpet(self, ctx):
        """Troca o mascote da fazenda com o mascote ativo."""
        user = db.get_user_data(str(ctx.author.id))
        if not user: return await ctx.send("❌ Conta não encontrada.")

        faz_tipo, faz_fome = db.get_fazenda(user)

        if not faz_tipo:
            return await ctx.send("🏡 A sua fazenda está vazia! Não há nenhum mascote para resgatar.")

        tipo_ativo, fome_ativo = db.get_mascote(user)

        # O mascote da fazenda passa a ser o ativo
        db.set_mascote(user['row'], faz_tipo, faz_fome)

        # O mascote ativo passa para a fazenda (se houver algum)
        if tipo_ativo:
            db.set_fazenda(user['row'], tipo_ativo, fome_ativo)
            info_antigo = INFO_MASCOTES.get(tipo_ativo, {"nome": "Mascote", "imagem": "🐾"})
            msg_extra = f"e enviou **{info_antigo['imagem']} {info_antigo['nome']}** para descansar na fazenda"
        else:
            db.set_fazenda(user['row'], "", 0)
            msg_extra = "e a fazenda ficou vazia"

        info_novo = INFO_MASCOTES.get(faz_tipo, {"nome": "Mascote", "imagem": "🐾"})
        
        embed = disnake.Embed(
            title="🔄 TROCA DE MASCOTES CONCLUÍDA",
            description=f"Você resgatou **{info_novo['imagem']} {info_novo['nome']}** para o slot ativo {msg_extra}!",
            color=disnake.Color.blue()
        )
        await ctx.send(embed=embed)


    @commands.command(aliases=["abandonar"])
    async def libertar(self, ctx, confirmacao: str = None):
        """Liberta APENAS o mascote ativo na natureza."""
        try:
            user = db.get_user_data(str(ctx.author.id))
            if not user:
                return

            tipo, fome = db.get_mascote(user)
            if not tipo:
                return await ctx.send(
                    f"🐾 {ctx.author.mention}, você não tem nenhum mascote **ativo** no momento.\n"
                    f"*(Use `!fazenda` para verificar se você guardou o seu mascote)*"
                )

            # Se passou "confirmar" como argumento, executa a liberação do pet ativo
            if confirmacao and confirmacao.lower() == "confirmar":
                info = INFO_MASCOTES.get(tipo, {"nome": "Mascote", "imagem": "🐾"})
                db.set_mascote(user['row'], "", 0)
                return await ctx.send(
                    f"🌿 {ctx.author.mention} abriu a gaiola e devolveu o seu mascote ATIVO (**{info['imagem']} {info['nome']}**) para a selva.\n"
                    f"A vaga de mascote principal está livre novamente!"
                )

            # Sem argumento, mostra o aviso de confirmação
            info = INFO_MASCOTES.get(tipo, {"nome": "Mascote", "raridade": "?", "imagem": "🐾"})
            embed = disnake.Embed(
                title="🚪 Libertar Mascote Ativo?",
                description=(
                    f"Você está prestes a soltar o seu mascote **ATIVO** (**{info['imagem']} {info['nome']}**) na selva.\n\n"
                    f"⚠️ Esta ação é **irreversível**. O mascote será perdido permanentemente.\n"
                    f"*(Mascotes guardados na fazenda não serão afetados).*\n\n"
                    f"Use `!libertar confirmar` para confirmar e limpar o slot."
                ),
                color=disnake.Color.orange()
            )
            await ctx.send(embed=embed)

        except Exception as e:
            print(f"❌ Erro no !libertar de {ctx.author}: {e}")
            await ctx.send("⚠️ Ocorreu um erro ao tentar libertar o mascote.")

    # ── ENCICLOPÉDIA DE MASCOTES ──
    @commands.command(aliases=["guiamascotes", "zoologico", "listapets"])
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