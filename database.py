import sqlite3
from pathlib import Path

DB_PATH = Path("dados_patentes.db")


def conectar():
    return sqlite3.connect(DB_PATH)


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
            titular = ?
        WHERE id = ?
        """,
        (
            novo_titulo,
            nova_data_concessao,
            novo_titular,
            patente_id,
        ),
    )

    conn.commit()
    conn.close()
