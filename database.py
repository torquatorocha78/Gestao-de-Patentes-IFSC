from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import sqlite3
from dateutil.relativedelta import relativedelta

DATABASE_FILE = Path(__file__).with_name("patentes.db")
PRIMEIRA_ANUIDADE = 3
ULTIMA_ANUIDADE = 20


def get_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS patentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_patente TEXT UNIQUE NOT NULL,
                data_deposito DATE NOT NULL,
                data_concessao DATE,
                descricao TEXT,
                titular TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS anuidades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patente_id INTEGER NOT NULL,
                numero_anuidade INTEGER NOT NULL,
                data_inicio_ordinario DATE NOT NULL,
                data_fim_ordinario DATE NOT NULL,
                data_inicio_extraordinario DATE NOT NULL,
                data_fim_extraordinario DATE NOT NULL,
                status TEXT,
                data_pagamento DATE,
                FOREIGN KEY (patente_id) REFERENCES patentes(id) ON DELETE CASCADE,
                UNIQUE(patente_id, numero_anuidade)
            )
            """
        )


def normalizar_data(valor):
    if valor is None or pd.isna(valor):
        return None

    if isinstance(valor, datetime):
        return valor.date().strftime("%Y-%m-%d")

    if isinstance(valor, date):
        return valor.strftime("%Y-%m-%d")

    texto = str(valor).strip()
    if not texto:
        return None

    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, formato).date().strftime("%Y-%m-%d")
        except ValueError:
            pass

    data_parseada = pd.to_datetime(texto, dayfirst=True, errors="raise")
    return data_parseada.date().strftime("%Y-%m-%d")


def calcular_periodos_anuidade(data_deposito, numero_anuidade):
    data_dep = datetime.strptime(normalizar_data(data_deposito), "%Y-%m-%d").date()

    inicio_ord = data_dep + relativedelta(years=numero_anuidade - 1)
    fim_ord = inicio_ord + relativedelta(months=3)

    inicio_ext = fim_ord + timedelta(days=1)
    fim_ext = inicio_ext + relativedelta(months=6)

    return (
        inicio_ord.strftime("%Y-%m-%d"),
        fim_ord.strftime("%Y-%m-%d"),
        inicio_ext.strftime("%Y-%m-%d"),
        fim_ext.strftime("%Y-%m-%d"),
    )


def inserir_anuidades(cursor, patente_id, data_deposito, pagamentos=None):
    pagamentos = pagamentos or {}

    for numero in range(PRIMEIRA_ANUIDADE, ULTIMA_ANUIDADE + 1):
        datas = calcular_periodos_anuidade(data_deposito, numero)
        pagamento = pagamentos.get(numero, {})

        cursor.execute(
            """
            INSERT OR IGNORE INTO anuidades
            (patente_id, numero_anuidade, data_inicio_ordinario, data_fim_ordinario,
             data_inicio_extraordinario, data_fim_extraordinario, status, data_pagamento)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patente_id,
                numero,
                *datas,
                pagamento.get("status", "pendente"),
                pagamento.get("data_pagamento"),
            ),
        )


def adicionar_patente(numero_patente, data_deposito, data_concessao=None, descricao="", titular=""):
    numero_patente = str(numero_patente).strip()
    data_deposito = normalizar_data(data_deposito)
    data_concessao = normalizar_data(data_concessao)

    if not numero_patente or not data_deposito:
        return False, "Número da patente e data de depósito são obrigatórios."

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO patentes
                (numero_patente, data_deposito, data_concessao, descricao, titular)
                VALUES (?, ?, ?, ?, ?)
                """,
                (numero_patente, data_deposito, data_concessao, descricao, titular),
            )

            inserir_anuidades(cursor, cursor.lastrowid, data_deposito)

        return True, "Patente adicionada com sucesso!"

    except sqlite3.IntegrityError:
        return False, "Patente já existe."


def obter_patentes():
    with get_connection() as conn:
        return pd.read_sql(
            """
            SELECT id, numero_patente, data_deposito, data_concessao, descricao, titular
            FROM patentes
            ORDER BY data_deposito DESC
            """,
            conn,
        )


def obter_anuidades(patente_id):
    with get_connection() as conn:
        return pd.read_sql(
            """
            SELECT numero_anuidade, data_inicio_ordinario, data_fim_ordinario,
                   data_inicio_extraordinario, data_fim_extraordinario,
                   status, data_pagamento
            FROM anuidades
            WHERE patente_id = ?
            ORDER BY numero_anuidade
            """,
            conn,
            params=(int(patente_id),),
        )


def atualizar_status_anuidade(patente_id, numero_anuidade, status, data_pagamento=None):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE anuidades
            SET status = ?, data_pagamento = ?
            WHERE patente_id = ? AND numero_anuidade = ?
            """,
            (status, normalizar_data(data_pagamento), patente_id, numero_anuidade),
        )


def deletar_patente(patente_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM patentes WHERE id = ?", (int(patente_id),))


def importar_excel(caminho):
    df = pd.read_excel(caminho)
    resultados = []

    for _, row in df.iterrows():
        sucesso, msg = adicionar_patente(
            row.get("numero_patente"),
            row.get("data_deposito"),
            row.get("data_concessao"),
            row.get("descricao", ""),
            row.get("titular", ""),
        )
        resultados.append((row.get("numero_patente"), sucesso, msg))

    return resultados
