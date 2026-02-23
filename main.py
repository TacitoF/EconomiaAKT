import disnake
from disnake.ext import commands
import os
import json
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import logging

# --- CONFIGURAÇÃO PARA O KOYEB (KEEP ALIVE) ---
app = Flask('')

# Desativa os logs chatos do Flask no console
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def home():
    return "Gerente Conguito está online!"

def run():
    # O Koyeb usa a porta 8000 por padrão conforme suas configurações
    port = int(os.getenv("PORT", 8000)) 
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True 
    t.start()

# --- GERAÇÃO DINÂMICA DAS CREDENCIAIS DO GOOGLE ---
google_creds = os.getenv("GOOGLE_CREDS")
if google_creds:
    with open("credentials.json", "w") as f:
        f.write(google_creds)
    print("✅ Arquivo credentials.json gerado.")

load_dotenv()

# Configuração do Bot
bot = commands.Bot(
    command_prefix="!", 
    intents=disnake.Intents.all(),
    help_command=None
)

# --- SISTEMA DE MANUTENÇÃO GLOBAL ---
# O bot já inicia com a trava ativada!
bot.is_locked = True 

@bot.check
async def global_maintenance_check(ctx):
    # Permite sempre que os comandos de ligar/desligar sejam usados
    if ctx.command and ctx.command.name in ['ligar', 'desligar']:
        return True
    
    # Se estiver travado, avisa o membro e bloqueia a execução de qualquer outro comando
    if bot.is_locked:
        await ctx.send(f"🛠️ {ctx.author.mention}, o bot acabou de ser reiniciado ou está **desligado para manutenção**! Aguarde até que a gerência libere o acesso.")
        raise commands.CheckFailure("Bot em manutenção.")
    
    return True

@bot.command()
async def ligar(ctx):
    """Destrava o bot para o público (Apenas Dono)"""
    if ctx.author.id != 757752617722970243: 
        return await ctx.send("❌ Apenas o dono pode destravar o bot!")
        
    if not bot.is_locked:
        return await ctx.send("⚠️ O bot já está ligado!")
        
    bot.is_locked = False
    await ctx.send("✅ **BOT DESTRAVADO!** A selva está oficialmente aberta para negócios e jogos!")

@bot.command()
async def desligar(ctx):
    """Trava o bot para o público (Apenas Dono)"""
    if ctx.author.id != 757752617722970243:
        return await ctx.send("❌ Apenas o dono pode travar o bot!")
        
    if bot.is_locked:
        return await ctx.send("⚠️ O bot já está desligado!")
        
    bot.is_locked = True
    await ctx.send("🛑 **BOT TRAVADO!** Modo de manutenção ativado. Apenas comandos administrativos estão a funcionar agora.")

@bot.event
async def on_ready():
    await bot.change_presence(activity=disnake.Game(name="!ajuda no AKTrovão"))
    print(f"✅ {bot.user} online no AKTrovão! (Iniciando em MODO TRAVADO)")

def load_cogs():
    if os.path.exists('./cogs'):
        # os.walk varre a pasta cogs e todas as subpastas dentro dela
        for pasta_atual, subpastas, arquivos in os.walk('./cogs'):
            # Ignora as pastas invisíveis de cache do Python para não dar erro
            if '__pycache__' in pasta_atual:
                continue
                
            for filename in arquivos:
                if filename.endswith('.py'):
                    # Pega o caminho do arquivo (ex: ./cogs/jogos/minas.py)
                    caminho_completo = os.path.join(pasta_atual, filename)
                    
                    # Transforma no formato que o disnake entende (ex: cogs.jogos.minas)
                    modulo = caminho_completo.replace('./', '').replace('/', '.').replace('\\', '.')[:-3]
                    
                    try:
                        bot.load_extension(modulo)
                        print(f"📦 Módulo carregado: {modulo}")
                    except Exception as e:
                        print(f"❌ Erro ao carregar módulo {modulo}: {e}")

# Silencia erros normais no terminal para não poluir o Log
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure) and bot.is_locked:
        return # Se falhou pela trava de manutenção, ignora o log
    elif isinstance(error, commands.CommandNotFound):
        return # Ignora comandos que não existem
    else:
        # Repassa o erro se for algo mais grave
        pass

if __name__ == "__main__":
    print("🌐 Iniciando servidor Keep Alive na porta 8000...")
    keep_alive()
    
    load_cogs()
    
    token = os.getenv("TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ ERRO: TOKEN não encontrado!")