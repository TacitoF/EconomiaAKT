import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Configuração Google
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Discord_Economy").sheet1

def get_user_data(user_id):
    try:
        cell = sheet.find(str(user_id))
        row = sheet.row_values(cell.row)
        # Retorna um dicionário para facilitar o acesso nos Cogs
        return {"row": cell.row, "data": row}
    except:
        return None

def update_value(row, col, value):
    sheet.update_cell(row, col, value)

def create_user(user_id, name):
    # ID, Nome, Saldo, Cargo, LastWork, Inventário
    sheet.append_row([user_id, name, 0, "Estagiário", 0, "Nenhum"])