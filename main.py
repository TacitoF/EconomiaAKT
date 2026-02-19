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
    # O Koyeb exige que a aplicação responda na porta 8000
    app.run(host='0.0.0.0', port=8000)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ---------------------------------------------

# Carrega variáveis do arquivo .env (apenas para teste local)
load_dotenv()

# Configuração do Bot
bot = commands.Bot(
    command_prefix="!", 
    intents=disnake.Intents.all(),
    help_command=None # Remove o help padrão para não dar conflito com o seu
)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} está online no AKTrovão!")
    print("-------------------------------")

# Carrega os módulos da pasta /cogs
if __name__ == "__main__":
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                bot.load_extension(f'cogs.{filename[:-3]}')
                print(f"📦 Módulo carregado: {filename}")
            except Exception as e:
                print(f"❌ Falha ao carregar módulo {filename}: {e}")

    # Inicia o servidor web para o Health Check do Koyeb
    keep_alive()
    
    # Puxa o TOKEN da variável de ambiente (configurada no painel do Koyeb)
    token = os.getenv("TOKEN")
    
    if token:
        bot.run(token)
    else:
        print("❌ ERRO: O TOKEN não foi encontrado nas variáveis de ambiente!")