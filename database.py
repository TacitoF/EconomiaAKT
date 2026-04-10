import os
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from disnake.ext import commands
from dotenv import load_dotenv

load_dotenv()

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

sheet_id = os.getenv("DATABASE_URL")

if not sheet_id:
    raise ValueError("❌ A variável DATABASE_URL não foi encontrada no .env ou Koyeb!")

sheet = client.open_by_key(sheet_id).sheet1
sheet_apostas = client.open_by_key(sheet_id).worksheet("Apostas_Esportivas")

# ──────────────────────────────────────────────────────────────────────────────
#  SISTEMA DE RETENTATIVA (ANTI-ERRO 503 / 429)
# ──────────────────────────────────────────────────────────────────────────────
def call_with_retry(func, *args, **kwargs):
    """
    Executa uma função da API do Google Sheets. 
    Se o Google estiver instável (erro 503, 502, 500) ou rate-limited (429), tenta de novo até 3 vezes.
    """
    for i in range(3):
        try:
            return func(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            status_code = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            # Tenta novamente em caso de erros temporários do servidor do Google
            if status_code in [429, 500, 502, 503, 504] and i < 2:
                print(f"⚠️ [Retry] Instabilidade no Google (Erro {status_code}). Tentando novamente em 2s ({i+1}/3)...")
                time.sleep(2)
                continue
            raise


def _get_or_create_config_sheet():
    try:
        return client.open_by_key(sheet_id).worksheet("Config")
    except gspread.exceptions.WorksheetNotFound:
        ws = client.open_by_key(sheet_id).add_worksheet(title="Config", rows=10, cols=2)
        call_with_retry(ws.update, "A1:B1", [["chave", "valor"]])
        return ws

sheet_config = _get_or_create_config_sheet()

def parse_float(valor, padrao=0.0):
    try:
        if valor is None or str(valor).strip() == "":
            return padrao
        s = str(valor).strip()
        if ',' in s:
            s = s.replace('.', '').replace(',', '.')
        return float(s)
    except (ValueError, TypeError):
        return padrao

def handle_db_error(e):
    print(f"❌ Erro na API do Google Sheets: {e}")
    raise commands.CommandError("⚠️ **O banco da selva está fora do ar no momento, tente novamente em 1 minuto!**")

def get_user_data(user_id):
    try:
        col_a = call_with_retry(sheet.col_values, 1)
        try:
            row_index = col_a.index(str(user_id)) + 1
        except ValueError:
            return None
        row = call_with_retry(sheet.row_values, row_index)
        return {"row": row_index, "data": row}
    except commands.CommandError:
        raise
    except Exception as e:
        handle_db_error(e)

def update_value(row, col, value):
    try:
        if isinstance(value, float):
            value = str(value).replace('.', ',')
        call_with_retry(sheet.update_cell, row, col, value)
    except Exception as e:
        handle_db_error(e)

def create_user(user_id, name):
    """
    Colunas:
      1  - user_id       | 2  - name         | 3  - saldo      | 4  - cargo
      5  - trab_ts       | 6  - inventario   | 7  - roubo_ts   | 8  - invest_ts
      9  - cripto_usos   | 10 - conquistas   | 11 - imposto/CD | 12 - escudo/CD
      13 - cosmeticos    | 14 - mascote      | 15 - greve_ts   | 16 - passivos
      17 - buff_temp     | 18 - fazenda_pet
    """
    try:
        all_rows = call_with_retry(sheet.get_all_values)
        next_row = len(all_rows) + 1
        dados = [str(user_id), str(name), "0", "Lêmure", "0", "Nenhum", "0", "", "", "", "", "", "", "", "", "", "", ""]
        call_with_retry(sheet.batch_update, [{'range': f'A{next_row}', 'values': [dados]}])
    except Exception as e:
        handle_db_error(e)

def wipe_database():
    try:
        rows = call_with_retry(sheet.get_all_values)
        if len(rows) > 1:
            call_with_retry(sheet.delete_rows, 2, len(rows))
    except Exception as e:
        handle_db_error(e)


# ──────────────────────────────────────────────────────────────────────────────
#  IMPOSTO DO GORILA
# ──────────────────────────────────────────────────────────────────────────────

def get_imposto(user_data: dict) -> tuple:
    raw = str(user_data['data'][10]) if len(user_data['data']) > 10 else ""
    raw = raw.strip()
    if not raw:
        return None, 0, 0.0
    try:
        partes = raw.split("|")
        if partes[0] == "cd":
            return None, 0, float(partes[1])
        cobrador_id = partes[0]
        cargas      = int(partes[1])
        if cargas <= 0:
            return None, 0, 0.0
        return cobrador_id, cargas, 0.0
    except (IndexError, ValueError):
        return None, 0, 0.0

def set_imposto(row: int, cobrador_id: str, cargas: int):
    try:
        valor = f"{cobrador_id}|{cargas}" if cargas > 0 else ""
        call_with_retry(sheet.update_cell, row, 11, valor)
    except Exception as e:
        handle_db_error(e)

def set_imposto_cooldown(row: int, timestamp: float):
    try:
        call_with_retry(sheet.update_cell, row, 11, f"cd|{timestamp}")
    except Exception as e:
        handle_db_error(e)

def clear_imposto(row: int):
    try:
        call_with_retry(sheet.update_cell, row, 11, "")
    except Exception as e:
        handle_db_error(e)


# ──────────────────────────────────────────────────────────────────────────────
#  ESCUDO
# ──────────────────────────────────────────────────────────────────────────────

def get_escudo_data(user_data: dict) -> tuple:
    raw = str(user_data['data'][11]) if len(user_data['data']) > 11 else ""
    raw = raw.strip()
    if not raw:
        return 0, 0.0
    try:
        if "|" in raw:
            partes = raw.split("|")
            return int(partes[0]), float(partes[1])
        else:
            return int(raw), 0.0
    except (IndexError, ValueError):
        return 0, 0.0

def set_escudo_data(row: int, cargas: int, quebra_ts: float = 0.0):
    try:
        if cargas > 0:
            valor = str(cargas)
        elif cargas == 0 and quebra_ts > 0:
            valor = f"0|{quebra_ts}"
        else:
            valor = ""
        call_with_retry(sheet.update_cell, row, 12, valor)
    except Exception as e:
        handle_db_error(e)


# ──────────────────────────────────────────────────────────────────────────────
#  CRIPTO
# ──────────────────────────────────────────────────────────────────────────────

def get_cripto_usos(user_data: dict) -> tuple[int, float]:
    raw = str(user_data['data'][8]) if len(user_data['data']) > 8 else ""
    raw = raw.strip()
    if not raw:
        return 0, 0.0
    try:
        partes = raw.split("|")
        return int(partes[0]), float(partes[1])
    except (IndexError, ValueError):
        return 0, 0.0

def set_cripto_usos(row: int, quantidade: int, timestamp_inicio: float):
    try:
        valor = f"{quantidade}|{timestamp_inicio}"
        call_with_retry(sheet.update_cell, row, 9, valor)
    except Exception as e:
        handle_db_error(e)


# ──────────────────────────────────────────────────────────────────────────────
#  COSMÉTICOS
# ──────────────────────────────────────────────────────────────────────────────

def get_cosmeticos(user_data: dict) -> dict:
    raw = str(user_data["data"][12]) if len(user_data["data"]) > 12 else ""
    raw = raw.strip()
    result = {}
    if not raw:
        return result
    for parte in raw.split("|"):
        parte = parte.strip()
        if ":" in parte:
            chave, _, valor = parte.partition(":")
            result[chave.strip()] = valor.strip()
    return result

def set_cosmetico(row: int, user_data: dict, chave: str, valor: str):
    cosm = get_cosmeticos(user_data)
    if valor:
        cosm[chave] = valor
    else:
        cosm.pop(chave, None)
    serializado = "|".join(f"{k}:{v}" for k, v in cosm.items())
    try:
        call_with_retry(sheet.update_cell, row, 13, serializado)
    except Exception as e:
        handle_db_error(e)

def clear_cosmetico(row: int, user_data: dict, chave: str):
    set_cosmetico(row, user_data, chave, "")


# ──────────────────────────────────────────────────────────────────────────────
#  MASCOTES
# ──────────────────────────────────────────────────────────────────────────────

def get_mascote(user_data: dict) -> tuple[str, int]:
    """Retorna (slug_do_mascote, nivel_de_fome). Ex: ('capivara', 100)"""
    raw = str(user_data["data"][13]) if len(user_data["data"]) > 13 else ""
    raw = raw.strip()
    if not raw:
        return None, 0
    try:
        partes = raw.split("|")
        return partes[0], int(partes[1])
    except (IndexError, ValueError):
        return None, 0

def set_mascote(row: int, slug_mascote: str, fome: int):
    try:
        valor = f"{slug_mascote}|{fome}" if slug_mascote else ""
        call_with_retry(sheet.update_cell, row, 14, valor)
    except Exception as e:
        handle_db_error(e)


# ──────────────────────────────────────────────────────────────────────────────
#  GREVE (coluna 15)
# ──────────────────────────────────────────────────────────────────────────────

def get_greve(user_data: dict) -> float:
    """Retorna o timestamp de expiração da greve. 0.0 se não houver."""
    raw = str(user_data["data"][14]) if len(user_data["data"]) > 14 else ""
    raw = raw.strip()
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0

def set_greve(row: int, timestamp_expira: float):
    """Salva o timestamp de expiração da greve na coluna 15."""
    try:
        call_with_retry(sheet.update_cell, row, 15, str(timestamp_expira) if timestamp_expira > 0 else "")
    except Exception as e:
        handle_db_error(e)


# ──────────────────────────────────────────────────────────────────────────────
#  PASSIVOS (coluna 16)
# ──────────────────────────────────────────────────────────────────────────────

MAX_PASSIVOS = 3

def get_passivos(user_data: dict) -> list[str]:
    """Retorna lista de slugs de passivos equipados."""
    raw = str(user_data["data"][15]) if len(user_data["data"]) > 15 else ""
    raw = raw.strip()
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]

def set_passivos(row: int, passivos: list[str]):
    """Salva a lista de passivos equipados na coluna 16."""
    try:
        valor = ", ".join(passivos[:MAX_PASSIVOS]) if passivos else ""
        call_with_retry(sheet.update_cell, row, 16, valor)
    except Exception as e:
        handle_db_error(e)


# ──────────────────────────────────────────────────────────────────────────────
#  BUFF TEMPORÁRIO (coluna 17 — timestamp de expiração do Troféu do Campeão)
# ──────────────────────────────────────────────────────────────────────────────

def get_buff_temp_expira(user_data: dict) -> float:
    """Retorna o timestamp de expiração do buff temporário. 0.0 se não houver."""
    raw = str(user_data["data"][16]) if len(user_data["data"]) > 16 else ""
    raw = raw.strip()
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0

def set_buff_temp_expira(row: int, timestamp_expira: float):
    """Salva o timestamp de expiração do buff temporário na coluna 17."""
    try:
        valor = str(timestamp_expira) if timestamp_expira > 0 else ""
        call_with_retry(sheet.update_cell, row, 17, valor)
    except Exception as e:
        handle_db_error(e)


# ──────────────────────────────────────────────────────────────────────────────
#  FAZENDA DE MASCOTES (coluna 18)
# ──────────────────────────────────────────────────────────────────────────────

def get_fazenda(user_data: dict) -> tuple[str, int]:
    """Retorna o mascote guardado na fazenda: (slug_fazenda, nivel_fome)."""
    raw = str(user_data["data"][17]) if len(user_data["data"]) > 17 else ""
    raw = raw.strip()
    if not raw:
        return None, 0
    try:
        partes = raw.split("|")
        return partes[0], int(partes[1])
    except (IndexError, ValueError):
        return None, 0

def set_fazenda(row: int, slug_mascote: str, fome: int):
    """Salva o mascote guardado na fazenda na coluna 18."""
    try:
        valor = f"{slug_mascote}|{fome}" if slug_mascote else ""
        call_with_retry(sheet.update_cell, row, 18, valor)
    except Exception as e:
        handle_db_error(e)


# ──────────────────────────────────────────────────────────────────────────────
#  SEGURO DE CARGAS (coluna 19)
# ──────────────────────────────────────────────────────────────────────────────

def get_seguro_cargas(user_data: dict) -> int:
    """Retorna o número de cargas restantes do seguro. 0 se não houver."""
    raw = str(user_data["data"][18]) if len(user_data["data"]) > 18 else ""
    raw = raw.strip()
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError:
        return 0

def set_seguro_cargas(row: int, cargas: int):
    """Salva o número de cargas do seguro na coluna 19."""
    try:
        valor = str(cargas) if cargas > 0 else ""
        call_with_retry(sheet.update_cell, row, 19, valor)
    except Exception as e:
        handle_db_error(e)


# ──────────────────────────────────────────────────────────────────────────────
#  BUSCA EM MASSA (usado pelo reset de economia)
# ──────────────────────────────────────────────────────────────────────────────

def get_all_users() -> list[dict]:
    """
    Retorna todos os usuários cadastrados na planilha principal.
    Cada item é um dict {'row': int, 'data': list} — mesmo formato de get_user_data().
    Pula a linha 1 caso ela seja um cabeçalho (célula A1 não numérica).
    """
    try:
        all_rows = call_with_retry(sheet.get_all_values)
        usuarios = []
        for i, row in enumerate(all_rows):
            # Pula linhas vazias ou cabeçalho
            if not row or not str(row[0]).strip():
                continue
            if i == 0 and not str(row[0]).strip().isdigit():
                continue  # linha de cabeçalho
            usuarios.append({"row": i + 1, "data": row})
        return usuarios
    except Exception as e:
        handle_db_error(e)
        return []


# ──────────────────────────────────────────────────────────────────────────────
#  FUNÇÕES DE APOSTAS ESPORTIVAS E OUTROS
# ──────────────────────────────────────────────────────────────────────────────

def registrar_aposta_esportiva(user_id, match_id, palpite, valor, odd, time_casa="", time_fora="", liga="", horario=""):
    try:
        valor_str = str(valor).replace('.', ',')
        odd_str = str(odd).replace('.', ',')
        dados = [
            str(user_id), str(match_id), palpite, valor_str, odd_str, "Pendente",
            str(time_casa), str(time_fora), str(liga), str(horario)
        ]
        all_rows = call_with_retry(sheet_apostas.get_all_values)
        next_row = len(all_rows) + 1
        call_with_retry(sheet_apostas.batch_update, [{'range': f'A{next_row}', 'values': [dados]}])
    except Exception as e:
        handle_db_error(e)

def obter_apostas_pendentes():
    try:
        rows = call_with_retry(sheet_apostas.get_all_values)
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
                    "status": row[5],
                    "time_casa": row[6] if len(row) > 6 else "",
                    "time_fora": row[7] if len(row) > 7 else "",
                    "liga": row[8] if len(row) > 8 else "",
                    "horario": row[9] if len(row) > 9 else "",
                })
        return apostas
    except Exception as e:
        handle_db_error(e)
        return []

def atualizar_status_aposta(row, status):
    try:
        call_with_retry(sheet_apostas.update_cell, row, 6, status)
    except Exception as e:
        handle_db_error(e)

def atualizar_valor_aposta(row: int, novo_valor: float):
    try:
        call_with_retry(sheet_apostas.update_cell, row, 4, str(round(novo_valor, 2)).replace('.', ','))
    except Exception as e:
        handle_db_error(e)

def get_apostas_pendentes_usuario(user_id: str) -> list:
    todas = obter_apostas_pendentes()
    return [a for a in todas if str(a["user_id"]) == str(user_id)]

def limpar_apostas_finalizadas() -> int:
    try:
        all_rows = call_with_retry(sheet_apostas.get_all_values)
        if len(all_rows) <= 1:
            return 0
        header = all_rows[0]
        data_rows = all_rows[1:]
        status_finalizados = {"Venceu", "Perdeu", "Reembolso"}
        max_cols = max(len(header), max((len(r) for r in data_rows), default=0))
        if len(header) < max_cols:
            header.extend([""] * (max_cols - len(header)))
        rows_to_keep = []
        for row in data_rows:
            if len(row) < 6 or row[5] not in status_finalizados:
                if len(row) < max_cols:
                    row.extend([""] * (max_cols - len(row)))
                rows_to_keep.append(row)
        deleted_count = len(data_rows) - len(rows_to_keep)
        if deleted_count > 0:
            call_with_retry(sheet_apostas.clear)
            nova_planilha = [header] + rows_to_keep
            call_with_retry(sheet_apostas.batch_update, [{'range': 'A1', 'values': nova_planilha}])
        return deleted_count
    except Exception as e:
        handle_db_error(e)
        return 0


# ──────────────────────────────────────────────────────────────────────────────
#  INSTÂNCIA ATIVA
# ──────────────────────────────────────────────────────────────────────────────

def _config_row(chave: str) -> int | None:
    try:
        col = call_with_retry(sheet_config.col_values, 1)
        idx = col.index(chave)
        return idx + 1
    except ValueError:
        return None

def set_instancia_ativa(instance_id: str):
    try:
        row = _config_row("instancia_ativa")
        if row:
            call_with_retry(sheet_config.update_cell, row, 2, instance_id)
        else:
            col_vals = call_with_retry(sheet_config.col_values, 1)
            next_row = len(col_vals) + 1
            call_with_retry(sheet_config.update, f"A{next_row}:B{next_row}", [["instancia_ativa", instance_id]])
    except Exception as e:
        handle_db_error(e)

def get_instancia_ativa() -> str | None:
    try:
        row = _config_row("instancia_ativa")
        if not row:
            return None
        celula = call_with_retry(sheet_config.cell, row, 2)
        return celula.value
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
#  MERCADO DINÂMICO
# ──────────────────────────────────────────────────────────────────────────────

def _get_or_create_mercado_sheet():
    try:
        return client.open_by_key(sheet_id).worksheet("Mercado")
    except gspread.exceptions.WorksheetNotFound:
        ws = client.open_by_key(sheet_id).add_worksheet(title="Mercado", rows=50, cols=3)
        call_with_retry(ws.update, "A1:C1", [["item_id", "compras_hoje", "ultimo_reset"]])
        return ws

sheet_mercado = _get_or_create_mercado_sheet()

def _mercado_row(item_id: str) -> int | None:
    try:
        col = call_with_retry(sheet_mercado.col_values, 1)
        idx = col.index(item_id)
        return idx + 1
    except ValueError:
        return None

def get_compras_item(item_id: str) -> int:
    try:
        row = _mercado_row(item_id)
        if not row:
            return 0
        valores = call_with_retry(sheet_mercado.row_values, row)
        compras = int(valores[1]) if len(valores) > 1 and valores[1] else 0
        ultimo_reset = float(valores[2]) if len(valores) > 2 and valores[2] else 0.0
        if time.time() - ultimo_reset >= 86400:
            call_with_retry(sheet_mercado.update, f"B{row}:C{row}", [[0, time.time()]])
            return 0
        return compras
    except Exception:
        return 0

def incrementar_compras(item_id: str, quantidade: int = 1):
    try:
        row = _mercado_row(item_id)
        agora = time.time()
        if not row:
            col_vals = call_with_retry(sheet_mercado.col_values, 1)
            next_row = len(col_vals) + 1
            call_with_retry(sheet_mercado.update, f"A{next_row}:C{next_row}", [[item_id, quantidade, agora]])
        else:
            valores = call_with_retry(sheet_mercado.row_values, row)
            compras_atuais = int(valores[1]) if len(valores) > 1 and valores[1] else 0
            ultimo_reset = float(valores[2]) if len(valores) > 2 and valores[2] else 0.0
            if agora - ultimo_reset >= 86400:
                compras_atuais = 0
                ultimo_reset = agora
            call_with_retry(sheet_mercado.update, f"B{row}:C{row}", [[compras_atuais + quantidade, ultimo_reset]])
    except Exception as e:
        print(f"⚠️ Erro ao incrementar compras de {item_id}: {e}")