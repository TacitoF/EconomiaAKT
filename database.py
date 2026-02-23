import gspread
from oauth2client.service_account import ServiceAccountCredentials
from disnake.ext import commands

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Discord_Economy").sheet1

def parse_float(valor, padrao=0.0):
    """Converte qualquer valor da planilha para float com segurança."""
    try:
        if valor is None or str(valor).strip() == "":
            return padrao
        return float(str(valor).replace(',', '.').strip())
    except (ValueError, TypeError):
        return padrao

def handle_db_error(e):
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

def update_value(row, col, value):
    try:
        if isinstance(value, float):
            value = str(value).replace('.', ',')
        sheet.update_cell(row, col, value)
    except Exception as e:
        handle_db_error(e)

def create_user(user_id, name):
    try:
        sheet.append_row([str(user_id), str(name), "0", "Lêmure", "0", "Nenhum", "0", "", "", ""])
    except Exception as e:
        handle_db_error(e)

def wipe_database():
    """Apaga todas as linhas da planilha preservando o cabeçalho."""
    try:
        rows = sheet.get_all_values()
        if len(rows) > 1:
            sheet.delete_rows(2, len(rows))
    except Exception as e:
        handle_db_error(e)