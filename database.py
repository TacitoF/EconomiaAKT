import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from disnake.ext import commands
from dotenv import load_dotenv

# Carrega as variáveis de ambiente (para garantir leitura local do .env)
load_dotenv()

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

sheet_id = os.getenv("DATABASE_URL")

if not sheet_id:
    raise ValueError("❌ A variável DATABASE_URL não foi encontrada no .env ou Koyeb!")

sheet = client.open_by_key(sheet_id).sheet1
sheet_apostas = client.open_by_key(sheet_id).worksheet("Apostas_Esportivas")

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
        col_a = sheet.col_values(1)
        try:
            row_index = col_a.index(str(user_id)) + 1 
        except ValueError:
            return None

        row = sheet.row_values(row_index)
        return {"row": row_index, "data": row}
    except commands.CommandError:
        raise
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
    """Apaga todas as linhas da planilha de economia preservando o cabeçalho."""
    try:
        rows = sheet.get_all_values()
        if len(rows) > 1:
            sheet.delete_rows(2, len(rows))
    except Exception as e:
        handle_db_error(e)

# FUNÇÕES DE APOSTAS ESPORTIVAS

def registrar_aposta_esportiva(user_id, match_id, palpite, valor, odd):
    """Salva um novo palpite na aba Apostas_Esportivas."""
    try:
        valor_str = str(valor).replace('.', ',')
        odd_str = str(odd).replace('.', ',')
        
        sheet_apostas.append_row([str(user_id), str(match_id), palpite, valor_str, odd_str, "Pendente"])
    except Exception as e:
        handle_db_error(e)

def obter_apostas_pendentes():
    """Lê a planilha e retorna apenas as apostas que ainda não finalizaram."""
    try:
        rows = sheet_apostas.get_all_values()
        apostas = []
        
        for i, row in enumerate(rows):
            if i == 0: continue 
            
            if len(row) >= 6 and row[5] == "Pendente":
                apostas.append({
                    "row": i + 1,
                    "user_id": row[0],
                    "match_id": int(row[1]),
                    "palpite": row[2],
                    "valor": parse_float(row[3]),
                    "odd": parse_float(row[4]),
                    "status": row[5]
                })
        return apostas
    except Exception as e:
        handle_db_error(e)
        return []

def atualizar_status_aposta(row, status):
    """Atualiza o status (Venceu/Perdeu) de uma aposta específica na planilha."""
    try:
        sheet_apostas.update_cell(row, 6, status)
    except Exception as e:
        handle_db_error(e)