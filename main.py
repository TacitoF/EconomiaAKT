import disnake
from disnake.ext import commands
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Gerente Conguito está online!"

def run():
    # O Koyeb usa a porta 8000 por padrão para o health check
    app.run(host='0.0.0.0', port=8000)

def keep_alive():
    t = Thread(target=run)
    t.start()

load_dotenv()

bot = commands.Bot(command_prefix="!", intents=disnake.Intents.all())

# Carrega os módulos automaticamente
for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')
        print(f"📦 Módulo carregado: {filename}")

@bot.event
async def on_ready():
    print(f"✅ {bot.user} online e modularizado!")

    
keep_alive()
bot.run(os.getenv("TOKEN"))