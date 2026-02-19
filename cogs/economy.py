import disnake
from disnake.ext import commands
import database as db
import time
import random

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def trabalhar(self, ctx):
        user_id = str(ctx.author.id)
        user = db.get_user_data(user_id)
        
        if not user:
            db.create_user(user_id, ctx.author.name)
            user = db.get_user_data(user_id)

        agora = time.time()
        # Verifica se a coluna de tempo (índice 4) existe e tem valor
        ultimo_work = float(user['data'][4]) if len(user['data']) > 4 and user['data'][4] else 0

        if agora - ultimo_work < 3600:
            restante = int((3600 - (agora - ultimo_work)) / 60)
            return await ctx.send(f"⏳ Você está exausto! Volte em **{restante} minutos**.")

        cargo = user['data'][3]
        # Multiplicadores baseados no cargo
        mults = {"Estagiário": 1, "Desenvolvedor": 1.5, "Sênior": 2.5, "Diretor": 4.0}
        ganho = int(random.randint(100, 300) * mults.get(cargo, 1))
        
        novo_saldo = int(user['data'][2]) + ganho
        
        db.update_value(user['row'], 3, novo_saldo)
        db.update_value(user['row'], 5, agora)
        
        await ctx.send(f"✅ Como **{cargo}**, você ganhou **{ganho} Conguitos**!")

    @commands.command()
    async def perfil(self, ctx, membro: disnake.Member = None):
        """Mostra o saldo, cargo e inventário."""
        membro = membro or ctx.author
        user_id = str(membro.id)
        user = db.get_user_data(user_id)

        if not user:
            return await ctx.send(f"❌ **{membro.display_name}** não tem conta! Use `!trabalhar`.")

        saldo = user['data'][2]
        cargo = user['data'][3]
        # Verifica inventário na coluna 6 (índice 5)
        inventario = user['data'][5] if len(user['data']) > 5 and user['data'][5] != "" else "Vazio"

        embed = disnake.Embed(
            title=f"🐒 Perfil AKTrovão - {membro.display_name}",
            color=disnake.Color.gold()
        )
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.add_field(name="💰 Saldo", value=f"{saldo} Conguitos", inline=True)
        embed.add_field(name="💼 Cargo", value=cargo, inline=True)
        embed.add_field(name="🎒 Inventário", value=f"`{inventario}`", inline=False)
        embed.set_footer(text="Use !loja para gastar seus Conguitos!")
        
        await ctx.send(embed=embed)

    @commands.command()
    async def loja(self, ctx):
        """Lista os itens disponíveis."""
        embed = disnake.Embed(title="🛒 Loja de Itens AKTrovão", color=disnake.Color.blue())
        embed.add_field(name="✨ Desenvolvedor", value="5.000 C | Bônus 1.5x", inline=False)
        embed.add_field(name="🔥 Sênior", value="15.000 C | Bônus 2.5x", inline=False)
        embed.add_field(name="🛡️ Escudo", value="2.000 C | Proteção contra roubo", inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def comprar(self, ctx, *, item: str):
        """Lógica de compra."""
        user_id = str(ctx.author.id)
        user = db.get_user_data(user_id)
        if not user: return await ctx.send("❌ Use `!trabalhar` primeiro!")

        loja = {
            "desenvolvedor": {"preco": 5000, "tipo": "cargo"},
            "sênior": {"preco": 15000, "tipo": "cargo"},
            "escudo": {"preco": 2000, "tipo": "item"}
        }

        escolha = item.lower()
        if escolha not in loja: return await ctx.send("❌ Item inválido!")

        saldo = int(user['data'][2])
        if saldo < loja[escolha]["preco"]:
            return await ctx.send(f"❌ Saldo insuficiente! Falta {loja[escolha]['preco'] - saldo} C.")

        db.update_value(user['row'], 3, saldo - loja[escolha]["preco"])

        if loja[escolha]["tipo"] == "cargo":
            db.update_value(user['row'], 4, escolha.capitalize())
            await ctx.send(f"🎉 Você agora é **{escolha.capitalize()}**!")
        else:
            db.update_value(user['row'], 6, escolha.capitalize())
            await ctx.send(f"🛡️ Você comprou um **{escolha.capitalize()}**!")

    @commands.command(name="wipe")
    async def wipe_planilha(self, ctx):
        """Limpa toda a planilha (Dono apenas)."""
        MEU_ID = 757752617722970243
        
        if ctx.author.id != MEU_ID:
            return await ctx.send("❌ Você não tem permissão para usar este comando de mestre! 🍌")

        await ctx.send("🧹 Iniciando limpeza total da planilha de economia...")

        try:
            # Pega todos os registros da planilha
            records = db.sheet.get_all_records()
            
            if len(records) > 0:
                # Apaga da linha 2 até a última (preserva o cabeçalho na linha 1)
                db.sheet.delete_rows(2, len(records) + 1)
                await ctx.send("✅ **RESET TOTAL CONCLUÍDO!** A economia do AKTrovão voltou ao zero.")
            else:
                await ctx.send("🤔 A planilha já está vazia (apenas o cabeçalho existe).")
                
        except Exception as e:
            await ctx.send(f"⚠️ Ocorreu um erro ao tentar limpar a planilha: {e}")

def setup(bot):
    bot.add_cog(Economy(bot))