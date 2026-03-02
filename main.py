import disnake
from disnake.ext import commands
import os
import time
import uuid
import signal
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import logging

# Gera um ID único para esta instância toda vez que o código roda
INSTANCE_ID = str(uuid.uuid4())[:8]

app = Flask('')
logging.getLogger('werkzeug').setLevel(logging.ERROR)

@app.route('/')
def home():
    return f"Koba está online! Instância: {INSTANCE_ID}"

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
bot.is_locked = True # Inicia travado até carregar tudo

# ──────────────────────────────────────────────
#  ANTI-SPAM GLOBAL (TRAVA INTELIGENTE)
# ──────────────────────────────────────────────
ANTI_SPAM_COOLDOWN = 2.5 
_spam_tracker: dict = {}
_spam_warning_tracker: dict = {} 

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
        ultimo_aviso = _spam_warning_tracker.get(chave, 0)
        if agora - ultimo_aviso > 5.0:
            try:
                aviso = await ctx.send(
                    f"⏱️ {ctx.author.mention}, a selva tem limites! Aguarde **{restante:.1f}s** antes de usar outro comando."
                )
                await aviso.delete(delay=3)
                _spam_warning_tracker[chave] = agora 
            except Exception:
                pass
        raise commands.CheckFailure("Anti-spam ativado.")

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

        agora = disnake.utils.utcnow()

        if online:
            embed = disnake.Embed(
                title="<:online:1> KOBA OPERACIONAL",
                description=(
                    "```ansi\n"
                    "\u001b[1;32m● SISTEMA ATIVO\u001b[0m\n"
                    "```\n"
                    "Todos os módulos foram inicializados com sucesso.\n"
                    "A economia da selva está operando normalmente.\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "📋 **MÓDULOS ATIVOS**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "✅  Economia & Trabalho\n"
                    "✅  Cassino & Apostas\n"
                    "✅  Jogos PvP\n"
                    "✅  Apostas Esportivas\n"
                    "✅  Loja & Inventário\n"
                    "✅  Banco & Transferências\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "💬 Use `!ajuda` para ver todos os comandos disponíveis."
                ),
                color=0x2ecc71
            )
            embed.set_author(name="Koba — Sistema de Economia", icon_url=guild.me.display_avatar.url)
            embed.set_footer(text=f"🟢 Online desde | Instância: {INSTANCE_ID}")
            embed.timestamp = agora

        else:
            embed = disnake.Embed(
                title="🔴 KOBA OFFLINE — MANUTENÇÃO",
                description=(
                    "```ansi\n"
                    "\u001b[1;31m● SISTEMA INDISPONÍVEL\u001b[0m\n"
                    "```\n"
                    "O sistema está temporariamente fora do ar para\n"
                    "realização de manutenção e melhorias.\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "📋 **STATUS DOS MÓDULOS**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🔴  Economia & Trabalho\n"
                    "🔴  Cassino & Apostas\n"
                    "🔴  Jogos PvP\n"
                    "🔴  Apostas Esportivas\n"
                    "🔴  Loja & Inventário\n"
                    "🔴  Banco & Transferências\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🔧 Os comandos estão bloqueados durante este período.\n"
                    "⏳ O sistema voltará em breve. Obrigado pela paciência!"
                ),
                color=0xe74c3c
            )
            embed.set_author(name="Koba — Sistema de Economia", icon_url=guild.me.display_avatar.url)
            embed.set_footer(text=f"🔴 Offline desde | Instância: {INSTANCE_ID}")
            embed.timestamp = agora

        try:
            await canal.send(embed=embed)
        except Exception as e:
            print(f"⚠️ Erro ao enviar status em {guild.name}: {e}")

# COMANDOS DE CONTROLE MANUAL (Ainda funcionam caso queira travar sem desligar o bot)
@bot.command()
async def ligar(ctx):
    try: await ctx.message.delete()
    except: pass
    if ctx.author.id != 757752617722970243: return
    bot.is_locked = False
    await ctx.send("✅ SISTEMAS ATIVOS: Koba assumiu o controle!", delete_after=5)
    await atualizar_canal_status(online=True)

@bot.command()
async def desligar(ctx):
    try: await ctx.message.delete()
    except: pass
    if ctx.author.id != 757752617722970243: return
    bot.is_locked = True
    await ctx.send("🛠️ MANUTENÇÃO: Koba entrou em modo de suspensão.", delete_after=5)
    await atualizar_canal_status(online=False)

# ──────────────────────────────────────────────
#  SISTEMA DE DESLIGAMENTO GRACIOSO E AUTO-KILL
# ──────────────────────────────────────────────
async def shutdown_task():
    """Roda automaticamente quando o Koyeb pede para a máquina desligar."""
    print(f"🛑 Instância {INSTANCE_ID} recebendo ordem de desligamento (SIGTERM)...")
    if not bot.is_locked:
        bot.is_locked = True
        await atualizar_canal_status(online=False)
    await bot.close()

@bot.listen('on_message')
async def auto_kill_old_instance(message):
    """Lê o canal de status. Se um bot NOVO mandar mensagem, o bot VELHO se desliga na hora."""
    if message.author.id != bot.user.id or message.channel.name != NOME_CANAL_STATUS:
        return

    if message.embeds:
        embed = message.embeds[0]
        if embed.footer and embed.footer.text and "Instância:" in embed.footer.text:
            id_na_mensagem = embed.footer.text.split("Instância: ")[-1].strip()
            
            # Se o ID da mensagem for diferente do meu ID atual, significa que sou a instância velha!
            if id_na_mensagem != INSTANCE_ID and "Online" in embed.footer.text:
                print(f"⚠️ Nova instância ({id_na_mensagem}) detectada! Encerrando a antiga ({INSTANCE_ID}) para evitar duplicidade.")
                bot.is_locked = True # Trava para não mandar a mensagem vermelha por cima da verde
                await bot.close()


# EVENTOS
@bot.event
async def on_ready():
    await bot.change_presence(activity=disnake.Game(name="!trabalhar para começar!"))
    
    # Prepara o bot para ouvir a ordem de desligamento do servidor Koyeb
    try:
        bot.loop.add_signal_handler(signal.SIGTERM, lambda: bot.loop.create_task(shutdown_task()))
    except NotImplementedError:
        pass # Ignora no Windows (ambiente de teste local)

    # Liga o bot automaticamente! Você não precisa mais digitar !ligar
    bot.is_locked = False
    print(f"✅ {bot.user} (Koba) online! (Instância: {INSTANCE_ID})")
    await atualizar_canal_status(online=True)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, (commands.CheckFailure, commands.CommandNotFound)):
        return
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
            modulo = pasta_atual.replace('./', '').replace('/', '.').replace('\\', '.')
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