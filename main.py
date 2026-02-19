import disnake
from disnake.ext import commands
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# --- CONFIGURAÇÃO PARA O KOYEB (KEEP ALIVE) ---
app = Flask('')

@app.route('/')
def home():
    return "Gerente Conguito está online!"

def run():
    # O Koyeb exige resposta na porta 8000 para o Health Check
    app.run(host='0.0.0.0', port=8000)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ---------------------------------------------

# Carrega variáveis localmente (não afeta o Koyeb)
load_dotenv()

# Configuração do Bot com intents completas
bot = commands.Bot(
    command_prefix="!", 
    intents=disnake.Intents.all(),
    help_command=None
)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} online no AKTrovão!")

# Carregamento modular dos comandos
if __name__ == "__main__":
    # Garante que a pasta cogs existe para evitar erro de diretório no servidor
    if os.path.exists('./cogs'):
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    bot.load_extension(f'cogs.{filename[:-3]}')
                    print(f"📦 Módulo carregado: {filename}")
                except Exception as e:
                    print(f"❌ Erro ao carregar {filename}: {e}")
    
    # Inicia o servidor fantasma para o Koyeb não reiniciar o bot
    keep_alive()
    
    # Puxa o Token das variáveis configuradas no painel do Koyeb
    token = os.getenv("TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ ERRO: Variável 'TOKEN' não encontrada!")