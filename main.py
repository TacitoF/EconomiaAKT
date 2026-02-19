import disnake
from disnake.ext import commands
import os
import json
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# --- CONFIGURAÇÃO PARA O KOYEB (KEEP ALIVE) ---
app = Flask('')

@app.route('/')
def home():
    return "Gerente Conguito está online!"

def run():
    app.run(host='0.0.0.0', port=8000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- GERAÇÃO DINÂMICA DAS CREDENCIAIS DO GOOGLE ---
google_creds = os.getenv("GOOGLE_CREDS")
if google_creds:
    # Se estivermos no servidor, cria o arquivo físico que as libs esperam
    with open("credentials.json", "w") as f:
        f.write(google_creds)
    print("✅ Arquivo credentials.json gerado a partir das variáveis de ambiente.")

# Carrega variáveis do .env (local)
load_dotenv()

# Configuração do Bot
bot = commands.Bot(
    command_prefix="!", 
    intents=disnake.Intents.all(),
    help_command=None
)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} online no AKTrovão!")
    print("-------------------------------")

# Carrega os módulos da pasta /cogs
if __name__ == "__main__":
    # Garante que o arquivo de credenciais existe antes de carregar os módulos
    if os.path.exists('./cogs'):
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    bot.load_extension(f'cogs.{filename[:-3]}')
                    print(f"📦 Módulo carregado: {filename}")
                except Exception as e:
                    print(f"❌ Erro ao carregar módulo {filename}: {e}")

    keep_alive()
    
    token = os.getenv("TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ ERRO: O TOKEN não foi encontrado!")