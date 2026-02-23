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
    raise commands.CommandError("⚠️ **O banco da selva está fora do ar no momento, tente novamente em 1 minuto!**")

def get_user_data(user_id):
    try:
        cell = sheet.find(str(user_id))
        row = sheet.row_values(cell.row)
        return {"row": cell.row, "data": row}
    except gspread.exceptions.CellNotFound:
        return None
    except Exception as e:
        handle_db_error(e)

def get_all_records_safe():
    """Retorna todos os registros da planilha como strings puras, evitando bugs de conversão."""
    try:
        all_values = sheet.get_all_values()
        if not all_values:
            return []
        headers = all_values[0]
        # Monta a lista de dicionários manualmente para garantir que tudo seja lido como string
        return [dict(zip(headers, row)) for row in all_values[1:]]
    except Exception as e:
        handle_db_error(e)

def update_value(row, col, value):
    # Se o valor for um número, garante que salve com vírgula para o Google Sheets PT-BR reconhecer
    if isinstance(value, float):
        value = str(value).replace('.', ',')
    try:
        sheet.update_cell(row, col, value)
    except Exception as e:
        handle_db_error(e)

def create_user(user_id, name):
    try:
        sheet.append_row([user_id, name, "0", "Lêmure", "0", "Nenhum"])
    except Exception as e:
        handle_db_error(e)

def wipe_database():
    """Apaga todos os dados da planilha, preservando o cabeçalho."""
    try:
        rows = sheet.get_all_values()
        if len(rows) > 1:
            sheet.delete_rows(2, len(rows))
    except Exception as e:
        handle_db_error(e)