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

@bot.event
async def on_ready():
    await bot.change_presence(activity=disnake.Game(name="!ajuda no AKTrovão"))
    print(f"✅ {bot.user} online no AKTrovão!")

def load_cogs():
    if os.path.exists('./cogs'):
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    bot.load_extension(f'cogs.{filename[:-3]}')
                    print(f"📦 Módulo carregado: {filename}")
                except Exception as e:
                    print(f"❌ Erro ao carregar módulo {filename}: {e}")

if __name__ == "__main__":
    print("🌐 Iniciando servidor Keep Alive na porta 8000...")
    keep_alive()
    
    load_cogs()
    
    token = os.getenv("TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ ERRO: TOKEN não encontrado!")