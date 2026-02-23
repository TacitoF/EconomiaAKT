import disnake
from disnake.ext import commands
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import logging

app = Flask('')
logging.getLogger('werkzeug').setLevel(logging.ERROR)

@app.route('/')
def home():
    return "Gerente Conguito está online!"

def run():
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8000)))

def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()

google_creds = os.getenv("GOOGLE_CREDS")
if google_creds:
    with open("credentials.json", "w") as f:
        f.write(google_creds)
    print("✅ credentials.json gerado.")

load_dotenv()

bot = commands.Bot(command_prefix="!", intents=disnake.Intents.all(), help_command=None)
bot.is_locked = True

@bot.check
async def global_maintenance_check(ctx):
    if ctx.command and ctx.command.name in ['ligar', 'desligar']:
        return True
    if bot.is_locked:
        await ctx.send(f"🛠️ {ctx.author.mention}, o bot está em **manutenção**! Aguarde a gerência liberar o acesso.")
        raise commands.CheckFailure("Bot em manutenção.")
    return True

@bot.command()
async def ligar(ctx):
    if ctx.author.id != 757752617722970243:
        return await ctx.send("❌ Apenas o dono pode destravar o bot!")
    if not bot.is_locked:
        return await ctx.send("⚠️ O bot já está ligado!")
    bot.is_locked = False
    await ctx.send("✅ **BOT DESTRAVADO!** A selva está aberta!")

@bot.command()
async def desligar(ctx):
    if ctx.author.id != 757752617722970243:
        return await ctx.send("❌ Apenas o dono pode travar o bot!")
    if bot.is_locked:
        return await ctx.send("⚠️ O bot já está desligado!")
    bot.is_locked = True
    await ctx.send("🛑 **BOT TRAVADO!** Modo de manutenção ativado.")

@bot.event
async def on_ready():
    await bot.change_presence(activity=disnake.Game(name="!ajuda no AKTrovão"))
    print(f"✅ {bot.user} online! (MODO TRAVADO)")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, (commands.CheckFailure, commands.CommandNotFound)):
        return
    print(f"❌ Erro não tratado: {error}")

def load_cogs():
    if not os.path.exists('./cogs'):
        return
    for pasta_atual, _, arquivos in os.walk('./cogs'):
        if '__pycache__' in pasta_atual:
            continue
        for filename in arquivos:
            if filename.endswith('.py'):
                modulo = os.path.join(pasta_atual, filename).replace('./', '').replace('/', '.').replace('\\', '.')[:-3]
                try:
                    bot.load_extension(modulo)
                    print(f"📦 {modulo}")
                except Exception as e:
                    print(f"❌ Erro ao carregar {modulo}: {e}")

if __name__ == "__main__":
    keep_alive()
    load_cogs()
    token = os.getenv("TOKEN")
    if token:
        bot.run(token)
    else:
        print("❌ TOKEN não encontrado!")