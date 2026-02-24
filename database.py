import gspread
from oauth2client.service_account import ServiceAccountCredentials
from disnake.ext import commands

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

sheet = client.open("Discord_Economy").sheet1
sheet_apostas = client.open("Discord_Economy").worksheet("Apostas_Esportivas")

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
        # Busca manual pela coluna A para evitar dependência de exceção específica do gspread
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

# =====================================================================
# FUNÇÕES DE APOSTAS ESPORTIVAS (NOVO)
# =====================================================================

def registrar_aposta_esportiva(user_id, match_id, palpite, valor, odd):
    """Salva um novo palpite na aba Apostas_Esportivas."""
    try:
        # Substitui ponto por vírgula para manter o padrão financeiro da planilha
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
        
        # Começa do index 1 para pular o cabeçalho
        for i, row in enumerate(rows):
            if i == 0: continue 
            
            # Verifica se a linha tem as 6 colunas e o status é Pendente
            if len(row) >= 6 and row[5] == "Pendente":
                apostas.append({
                    "row": i + 1, # +1 porque a API do Sheets não começa no 0
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