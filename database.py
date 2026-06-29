import sqlite3
from datetime import datetime, date
import pandas as pd
from dateutil.relativedelta import relativedelta
from pathlib import Path

# =====================================================
# CONFIGURAÇÃO
# =====================================================

DATABASE_FILE = Path("patentes.db")

# =====================================================
# CONEXÃO
# =====================================================

def conectar():
    return sqlite3.connect(DATABASE_FILE, check_same_thread=False)

# =====================================================
# NORMALIZAÇÃO DE DATAS (PONTO-CHAVE DA CORREÇÃO)
# =====================================================

def normalizar_data(data):
    """
    Retorna data no formato YYYY-MM-DD ou None
    Aceita: str, datetime, date, pandas.Timestamp
    """
    if data is None or data == "":
        return None

    if isinstance(data, pd.Timestamp):
        return data.date().strftime("%Y-%m-%d")

    if isinstance(data, (datetime, date)):
        return data.strftime("%Y-%m-%d")

    if isinstance(data, str):
        data = data.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(data, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass

    return None

# =====================================================
# CRIAÇÃO DO BANCO
# =====================================================

def init_database():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_patente TEXT UNIQUE NOT NULL,
            data_deposito DATE NOT NULL,
            data_concessao DATE,
            descricao TEXT,
            titular TEXT,
            gestor TEXT,
            status TEXT DEFAULT 'Ativo',
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anuidades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patente_id INTEGER NOT NULL,
            numero_anuidade INTEGER NOT NULL,
            data_inicio_ordinario DATE NOT NULL,
            data_fim_ordinario DATE NOT NULL,
            data_inicio_extraordinario DATE NOT NULL,
            data_fim_extraordinario DATE NOT NULL,
            status TEXT DEFAULT 'pendente',
            data_pagamento DATE,
            FOREIGN KEY (patente_id) REFERENCES patentes(id),
            UNIQUE(patente_id, numero_anuidade)
        )
    """)

    conn.commit()
    conn.close()

# =====================================================
# PATENTES
# =====================================================

def adicionar_patente(numero_patente, data_deposito, data_concessao=None,
                      descricao="", titular="", gestor="", status="Ativo"):

    conn = conectar()
    cursor = conn.cursor()

    try:
        data_dep = normalizar_data(data_deposito)
        data_conc = normalizar_data(data_concessao)

        cursor.execute("""
            INSERT INTO patentes
            (numero_patente, data_deposito, data_concessao, descricao, titular, gestor, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            numero_patente,
            data_dep,
            data_conc,
            descricao.strip(),
            titular.strip(),
            gestor.strip(),
            status.strip()
        ))

        patente_id = cursor.lastrowid
        data_dep_date = datetime.strptime(data_dep, "%Y-%m-%d").date()

        # Regras de não pagar
        marca_nao_pagar = False
        if gestor and gestor.upper() not in [
            "IFSC",
            "INSTITUTO FEDERAL DE SANTA CATARINA",
            "INSTITUTO FEDERAL DE EDUCAÇÃO, CIÊNCIA E TECNOLOGIA DE SANTA CATARINA"
        ]:
            marca_nao_pagar = True

        if status in ["Indeferido", "Arquivado", "Desistência"]:
            marca_nao_pagar = True

        # Criar 20 anuidades
        for anuidade in range(1, 21):
            inicio_ord = data_dep_date + relativedelta(years=3, days=(anuidade - 1) * 365)
            fim_ord = inicio_ord + relativedelta(months=3)
            inicio_ext = fim_ord + relativedelta(days=1)
            fim_ext = inicio_ext + relativedelta(months=6)

            cursor.execute("""
                INSERT INTO anuidades
                (patente_id, numero_anuidade, data_inicio_ordinario,
                 data_fim_ordinario, data_inicio_extraordinario,
                 data_fim_extraordinario, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                patente_id,
                anuidade,
                inicio_ord.strftime("%Y-%m-%d"),
                fim_ord.strftime("%Y-%m-%d"),
                inicio_ext.strftime("%Y-%m-%d"),
                fim_ext.strftime("%Y-%m-%d"),
                "nao_pagar" if marca_nao_pagar else "pendente"
            ))

        conn.commit()
        return True, "Patente adicionada com sucesso!"

    except sqlite3.IntegrityError:
        return False, "Patente já existe no banco!"
    except Exception as e:
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

# =====================================================
# CONSULTAS
# =====================================================

def obter_patentes():
    conn = conectar()
    df = pd.read_sql_query(
        "SELECT * FROM patentes ORDER BY data_deposito DESC",
        conn
    )
    conn.close()
    return df

def obter_anuidades(patente_id):
    conn = conectar()
    df = pd.read_sql_query("""
        SELECT id, numero_anuidade, data_inicio_ordinario, data_fim_ordinario,
               data_inicio_extraordinario, data_fim_extraordinario,
               status, data_pagamento
        FROM anuidades
        WHERE patente_id = ?
        ORDER BY numero_anuidade
    """, conn, params=(patente_id,))
    conn.close()
    return df

# =====================================================
# ATUALIZAÇÕES (AQUI ESTAVA O ERRO)
# =====================================================

def atualizar_status_anuidade(patente_id, numero_anuidade, status, data_pagamento=None):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE anuidades
        SET status = ?, data_pagamento = ?
        WHERE patente_id = ? AND numero_anuidade = ?
    """, (
        status,
        normalizar_data(data_pagamento),
        patente_id,
        numero_anuidade
    ))

    conn.commit()
    conn.close()
# =====================================================
# ATUALIZAÇÃO COMPLETA DA PATENTE (EDIÇÃO INLINE)
# =====================================================

def atualizar_patente(
    patente_id,
    novo_titulo=None,
    nova_data_concessao=None,
    novo_titular=None,
    novo_gestor=None,
    novo_status=None
):
    """
    Atualiza os dados principais da patente.
    Qualquer campo pode ser None (não será alterado).
    """

    conn = conectar()
    cursor = conn.cursor()

    campos = []
    valores = []

    if novo_titulo is not None:
        campos.append("descricao = ?")
        valores.append(novo_titulo.strip())

    if nova_data_concessao is not None:
        campos.append("data_concessao = ?")
        valores.append(normalizar_data(nova_data_concessao))

    if novo_titular is not None:
        campos.append("titular = ?")
        valores.append(novo_titular.strip())

    if novo_gestor is not None:
        campos.append("gestor = ?")
        valores.append(novo_gestor.strip())

    if novo_status is not None:
        campos.append("status = ?")
        valores.append(novo_status.strip())

    if not campos:
        conn.close()
        return

    valores.append(patente_id)

    query = f"""
        UPDATE patentes
        SET {', '.join(campos)}
        WHERE id = ?
    """

    cursor.execute(query, valores)
    conn.commit()
    conn.close()
