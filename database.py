import gspread
from oauth2client.service_account import ServiceAccountCredentials
from disnake.ext import commands

# Configuração Google
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Discord_Economy").sheet1

def handle_db_error(e):
    """Amortecedor de quedas da API do Google"""
    print(f"❌ Erro na API do Google Sheets: {e}")
    # Dispara um erro amigável que o Discord vai mostrar para o usuário em vez de crashar
    raise commands.CommandError("⚠️ **O banco da selva está fora do ar no momento, tente novamente em 1 minuto!**")

def get_user_data(user_id):
    try:
        cell = sheet.find(str(user_id))
        row = sheet.row_values(cell.row)
        # Retorna um dicionário para facilitar o acesso nos Cogs
        return {"row": cell.row, "data": row}
    except gspread.exceptions.CellNotFound:
        # Se o usuário não existir, é normal, retorna None para a conta ser criada
        return None
    except Exception as e:
        # Se for qualquer outro erro (Google caiu, timeout, etc), aciona o amortecedor
        handle_db_error(e)

def update_value(row, col, value):
    try:
        sheet.update_cell(row, col, value)
    except Exception as e:
        handle_db_error(e)

def create_user(user_id, name):
    try:
        # Novo cargo inicial da V4.4: Lêmure
        sheet.append_row([user_id, name, 0, "Lêmure", 0, "Nenhum"])
    except Exception as e:
        handle_db_error(e)

def wipe_database():
    """Apaga todos os dados da planilha, preservando o cabeçalho."""
    try:
        # Obtém todas as linhas
        rows = sheet.get_all_values()
        
        # Se houver mais de uma linha (além do cabeçalho)
        if len(rows) > 1:
            # Apaga da linha 2 até a última
            sheet.delete_rows(2, len(rows))
    except Exception as e:
        handle_db_error(e)