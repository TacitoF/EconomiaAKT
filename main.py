import disnake
from disnake.ext import commands
import os
from dotenv import load_dotenv

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

bot.run(os.getenv("TOKEN"))