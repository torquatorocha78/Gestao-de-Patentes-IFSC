import sqlite3
from dateutil.relativedelta import relativedelta


DATABASE_FILE = Path(__file__).with_name("patentes.db")
PRIMEIRA_ANUIDADE = 3
ULTIMA_ANUIDADE = 20
@@ -15,9 +14,7 @@ def get_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
from pathlib import Path

DB_PATH = Path("dados_patentes.db")

def init_database():
    with get_connection() as conn:
@@ -36,119 +33,6 @@ def init_database():
            )
            """
        )
def conectar():
    return sqlite3.connect(DB_PATH)

    migrar_anuidades_para_regra_atual()

def atualizar_patente(patente_id, data_concessao, descricao, titular):
def atualizar_patente(
    patente_id,
    novo_titulo,
    nova_data_concessao,
    novo_titular
):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE patentes
        SET
            titulo = ?,
            data_concessao = ?,
            descricao = ?,
            titular = ?
        WHERE id = ?
        """,
        (data_concessao, descricao, titular, patente_id),
        (
            novo_titulo,
            nova_data_concessao,
            novo_titular,
            patente_id,
        ),
    )

    conn.commit()
    conn.close()
def calcular_periodos_anuidade(data_deposito, numero_anuidade):
    data_dep = datetime.strptime(normalizar_data(data_deposito), "%Y-%m-%d").date()
    data_inicio_ord = data_dep + relativedelta(years=numero_anuidade - 1)
    data_fim_ord = data_inicio_ord + relativedelta(months=3)
    data_inicio_extraord = data_fim_ord + timedelta(days=1)
    data_fim_extraord = data_inicio_extraord + relativedelta(months=6)

    return (
        data_inicio_ord.strftime("%Y-%m-%d"),
        data_fim_ord.strftime("%Y-%m-%d"),
        data_inicio_extraord.strftime("%Y-%m-%d"),
        data_fim_extraord.strftime("%Y-%m-%d"),
    )


def inserir_anuidades(cursor, patente_id, data_deposito, pagamentos=None):
    pagamentos = pagamentos or {}

    for numero_anuidade in range(PRIMEIRA_ANUIDADE, ULTIMA_ANUIDADE + 1):
        datas = calcular_periodos_anuidade(data_deposito, numero_anuidade)
        pagamento = pagamentos.get(numero_anuidade, {})
        data_pagamento = pagamento.get("data_pagamento")
        status = "pago" if data_pagamento else pagamento.get("status", "pendente")

        cursor.execute(
            """
            INSERT INTO anuidades
            (patente_id, numero_anuidade, data_inicio_ordinario, data_fim_ordinario,
             data_inicio_extraordinario, data_fim_extraordinario, status, data_pagamento)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(patente_id),
                numero_anuidade,
                *datas,
                status,
                data_pagamento,
            ),
        )


def migrar_anuidades_para_regra_atual():
    with get_connection() as conn:
        cursor = conn.cursor()
        patentes = cursor.execute("SELECT id, data_deposito FROM patentes").fetchall()

        for patente_id, data_deposito in patentes:
            anuidades = cursor.execute(
                """
                SELECT numero_anuidade, data_inicio_ordinario, status, data_pagamento
                FROM anuidades
                WHERE patente_id = ?
                ORDER BY numero_anuidade
                """,
                (patente_id,),
            ).fetchall()

            esperado_inicio, _, _, _ = calcular_periodos_anuidade(data_deposito, PRIMEIRA_ANUIDADE)
            numeros = [linha[0] for linha in anuidades]
            precisa_migrar = numeros != list(range(PRIMEIRA_ANUIDADE, ULTIMA_ANUIDADE + 1))
            if anuidades and numeros and min(numeros) == PRIMEIRA_ANUIDADE:
                precisa_migrar = precisa_migrar or anuidades[0][1] != esperado_inicio

            if not precisa_migrar:
                continue

            pagamentos = {}
            for numero, _, status, data_pagamento in anuidades:
                numero_atual = numero if numero >= PRIMEIRA_ANUIDADE else numero + 2
                if PRIMEIRA_ANUIDADE <= numero_atual <= ULTIMA_ANUIDADE:
                    pagamentos[numero_atual] = {
                        "status": status or "pendente",
                        "data_pagamento": data_pagamento,
                    }

            cursor.execute("DELETE FROM anuidades WHERE patente_id = ?", (patente_id,))
            inserir_anuidades(cursor, patente_id, data_deposito, pagamentos)

        cursor.execute(
            """
@@ -172,8 +56,10 @@ def migrar_anuidades_para_regra_atual():
def normalizar_data(valor):
    if valor is None or pd.isna(valor):
        return None

    if isinstance(valor, datetime):
        return valor.date().strftime("%Y-%m-%d")

    if isinstance(valor, date):
        return valor.strftime("%Y-%m-%d")

@@ -191,98 +77,133 @@ def normalizar_data(valor):
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

    if not numero_patente:
        return False, "Numero da patente e obrigatorio."
    if not data_deposito:
        return False, "Data de deposito e obrigatoria."
    if not numero_patente or not data_deposito:
        return False, "Número da patente e data de depósito são obrigatórios."

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO patentes (numero_patente, data_deposito, data_concessao, descricao, titular)
                INSERT INTO patentes
                (numero_patente, data_deposito, data_concessao, descricao, titular)
                VALUES (?, ?, ?, ?, ?)
                """,
                (numero_patente, data_deposito, data_concessao, descricao or "", titular or ""),
                (numero_patente, data_deposito, data_concessao, descricao, titular),
            )

            patente_id = cursor.lastrowid
            inserir_anuidades(cursor, patente_id, data_deposito)
            inserir_anuidades(cursor, cursor.lastrowid, data_deposito)

        return True, "Patente adicionada com sucesso!"

    except sqlite3.IntegrityError:
        return False, "Patente ja existe no banco de dados!"
    except Exception as e:
        return False, f"Erro ao adicionar patente: {str(e)}"
        return False, "Patente já existe."


def obter_patentes():
    with get_connection() as conn:
        query = """
        return pd.read_sql(
            """
            SELECT id, numero_patente, data_deposito, data_concessao, descricao, titular
            FROM patentes
            ORDER BY data_deposito DESC
        """
        return pd.read_sql_query(query, conn)
            """,
            conn,
        )


def obter_anuidades(patente_id):
    patente_id = int(patente_id)
    with get_connection() as conn:
        query = """
        return pd.read_sql(
            """
            SELECT numero_anuidade, data_inicio_ordinario, data_fim_ordinario,
                   data_inicio_extraordinario, data_fim_extraordinario, status, data_pagamento
                   data_inicio_extraordinario, data_fim_extraordinario,
                   status, data_pagamento
            FROM anuidades
            WHERE patente_id = ?
            ORDER BY numero_anuidade
        """
        return pd.read_sql_query(query, conn, params=(patente_id,))
            """,
            conn,
            params=(int(patente_id),),
        )


def atualizar_status_anuidade(patente_id, numero_anuidade, status, data_pagamento=None):
    patente_id = int(patente_id)
    numero_anuidade = int(numero_anuidade)
    data_pagamento = normalizar_data(data_pagamento)
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE anuidades
            SET status = ?, data_pagamento = ?
            WHERE patente_id = ? AND numero_anuidade = ?
            """,
            (status, data_pagamento, patente_id, numero_anuidade),
            (status, normalizar_data(data_pagamento), patente_id, numero_anuidade),
        )


def deletar_patente(patente_id):
    patente_id = int(patente_id)
    with get_connection() as conn:
        conn.execute("DELETE FROM patentes WHERE id = ?", (patente_id,))
        conn.execute("DELETE FROM patentes WHERE id = ?", (int(patente_id),))


def importar_excel(caminho_arquivo):
    try:
        df = pd.read_excel(caminho_arquivo)
        resultados = []

        for _, row in df.iterrows():
            numero = str(row["numero_patente"]).strip() if "numero_patente" in df.columns else str(row.iloc[0]).strip()
            data_dep = row["data_deposito"] if "data_deposito" in df.columns else row.iloc[1]
            data_conc = row.get("data_concessao", None)
            descricao = row.get("descricao", "")
            titular = row.get("titular", "")

            sucesso, mensagem = adicionar_patente(numero, data_dep, data_conc, descricao, titular)
            resultados.append((numero, sucesso, mensagem))

        return resultados
    except Exception as e:
        return [("Erro", False, f"Erro ao importar: {str(e)}")]
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
