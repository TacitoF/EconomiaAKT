import disnake
from disnake.ext import commands
import os
import time
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import logging

app = Flask('')
logging.getLogger('werkzeug').setLevel(logging.ERROR)

@app.route('/')
def home():
    return "Koba está online e operando a economia!"

def run():
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8000)))

def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()

google_creds = os.getenv("GOOGLE_CREDS")
if google_creds:
    with open("credentials.json", "w") as f:
        f.write(google_creds)
    print("✅ credentials.json gerado pelo ambiente.")

load_dotenv()

bot = commands.Bot(command_prefix="!", intents=disnake.Intents.all(), help_command=None)
bot.is_locked = True

# ──────────────────────────────────────────────
#  ANTI-SPAM GLOBAL (TRAVA INTELIGENTE)
# ──────────────────────────────────────────────
ANTI_SPAM_COOLDOWN = 2.5 # Tempo de espera entre qualquer comando
_spam_tracker: dict = {}
_spam_warning_tracker: dict = {} # Controla quando avisamos o usuário para não floodarmos de volta

@bot.check
async def global_check(ctx):
    if ctx.command and ctx.command.name in ['ligar', 'desligar']:
        return True

    if bot.is_locked:
        raise commands.CheckFailure("Bot em manutenção.")

    chave = str(ctx.author.id)
    agora = time.time()
    ultimo = _spam_tracker.get(chave, 0)
    restante = ANTI_SPAM_COOLDOWN - (agora - ultimo)

    if restante > 0:
        # Só enviamos a mensagem de aviso se não tivermos avisado nos últimos 5 segundos
        ultimo_aviso = _spam_warning_tracker.get(chave, 0)
        
        if agora - ultimo_aviso > 5.0:
            try:
                aviso = await ctx.send(
                    f"⏱️ {ctx.author.mention}, a selva tem limites! Aguarde **{restante:.1f}s** antes de usar outro comando."
                )
                await aviso.delete(delay=3)
                _spam_warning_tracker[chave] = agora # Registra que acabamos de avisar
            except Exception:
                pass
                
        # Bloqueia a execução do comando de qualquer forma
        raise commands.CheckFailure("Anti-spam ativado.")

    # Se o comando passou, atualizamos o tempo do último uso
    _spam_tracker[chave] = agora
    return True

# CANAL DE STATUS
NOME_CANAL_STATUS = "📡・status-bot"
ALLOWED_GUILDS = [1474556702861819967, 1438279770386206882]

@bot.check
async def restrict_servers(ctx):
    if os.getenv("ENVIRONMENT") == "DEV":
        return ctx.guild.id in ALLOWED_GUILDS
    return True

async def atualizar_canal_status(online: bool):
    """Limpa o canal de status completamente e envia o novo embed."""
    for guild in bot.guilds:
        canal = disnake.utils.get(guild.text_channels, name=NOME_CANAL_STATUS)
        if not canal:
            continue
        try:
            await canal.purge(limit=100)
        except Exception as e:
            print(f"⚠️ Erro ao limpar canal de status em {guild.name}: {e}")

        if online:
            embed = disnake.Embed(
                title="🟢 SISTEMA ONLINE",
                description=(
                    "**Koba** está ativo e pronto para uso!\n\n"
                    "A economia da selva está operando normalmente.\n"
                    "Use `!ajuda` para acessar o painel de investimentos e jogos."
                ),
                color=disnake.Color.green()
            )
        else:
            embed = disnake.Embed(
                title="🔴 SISTEMA EM MANUTENÇÃO",
                description=(
                    "**Koba** está temporariamente offline para auditoria e melhorias no sistema.\n\n"
                    "Os comandos estão bloqueados durante este período.\n"
                    "Retornaremos em breve! 🔧"
                ),
                color=disnake.Color.red()
            )

        embed.set_footer(text="Última atualização")
        embed.timestamp = disnake.utils.utcnow()

        try:
            await canal.send(embed=embed)
        except Exception as e:
            print(f"⚠️ Erro ao enviar status em {guild.name}: {e}")

# COMANDOS DE CONTROLE
@bot.command()
async def ligar(ctx):
    try: await ctx.message.delete()
    except: pass
    if ctx.author.id != 757752617722970243:
        return await ctx.send("❌ Acesso restrito! Apenas a gerência pode destravar o bot.")
    if not bot.is_locked:
        return await ctx.send("⚠️ O bot já está ligado!")
    bot.is_locked = False
    await ctx.send("✅ SISTEMAS ATIVOS: Koba assumiu o controle!", delete_after=5)
    await atualizar_canal_status(online=True)

@bot.command()
async def desligar(ctx):
    try: await ctx.message.delete()
    except: pass
    if ctx.author.id != 757752617722970243:
        return await ctx.send("❌ Acesso restrito! Apenas a gerência pode travar o bot.")
    if bot.is_locked:
        return await ctx.send("⚠️ O bot já está desligado!")
    bot.is_locked = True
    await ctx.send("🛠️ MANUTENÇÃO: Koba entrou em modo de suspensão.", delete_after=5)
    await atualizar_canal_status(online=False)

# EVENTOS
@bot.event
async def on_ready():
    await bot.change_presence(activity=disnake.Game(name="!trabalhar para começar ou !ajuda para o manual!"))
    print(f"✅ {bot.user} (Koba) online! (MODO TRAVADO)")
    await atualizar_canal_status(online=not bot.is_locked)

@bot.event
async def on_command_error(ctx, error):
    # Ignora falhas de check (como o anti-spam) e comandos inexistentes
    if isinstance(error, (commands.CheckFailure, commands.CommandNotFound)):
        return
        
    # SILENCIA OS ERROS DE COOLDOWN NO CONSOLE E AVISA O USUÁRIO
    if isinstance(error, commands.CommandOnCooldown):
        try:
            aviso = await ctx.send(f"⏳ Comando em recarga! Tente novamente em **{error.retry_after:.1f}s**.")
            await aviso.delete(delay=4)
        except:
            pass
        return

    print(f"❌ Erro não tratado: {error}")

# ──────────────────────────────────────────────
#  CARREGAMENTO DE COGS
# ──────────────────────────────────────────────
def load_cogs():
    if not os.path.exists('./cogs'):
        return

    for pasta_atual, subdirs, arquivos in os.walk('./cogs'):
        if '__pycache__' in pasta_atual:
            continue

        if '__init__.py' in arquivos:
            modulo = (
                pasta_atual
                .replace('./', '').replace('/', '.').replace('\\', '.')
            )
            try:
                bot.load_extension(modulo)
                print(f"📦 {modulo} (pacote)")
            except Exception as e:
                print(f"❌ Erro ao carregar pacote {modulo}: {e}")
            subdirs.clear()
            continue

        for filename in arquivos:
            if not filename.endswith('.py') or filename == '__init__.py':
                continue
            modulo = (
                os.path.join(pasta_atual, filename)
                .replace('./', '').replace('/', '.').replace('\\', '.')[:-3]
            )
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