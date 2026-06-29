import pandas as pd
from datetime import datetime, date, timedelta


def converter_data(data):
    if data is None:
        return None

    # pandas NaT
    if pd.isna(data):
        return None

    # pandas Timestamp
    if isinstance(data, pd.Timestamp):
        return data.date()

    # datetime ou date
    if isinstance(data, (datetime, date)):
        return data.date() if isinstance(data, datetime) else data

    # string
    if isinstance(data, str):
        data = data.strip()

        if data in ("", "-", "None"):
            return None

        # tenta YYYY-MM-DD
        try:
            return datetime.strptime(data, "%Y-%m-%d").date()
        except ValueError:
            pass

        # tenta DD/MM/YYYY
        try:
            return datetime.strptime(data, "%d/%m/%Y").date()
        except ValueError:
            return None

    return None


def calcular_status_anuidade(
    data_inicio_ord,
    data_fim_ord,
    data_inicio_extraord,
    data_fim_extraord,
    data_pagamento=None,
):
    hoje = datetime.now().date()

    if data_pagamento:
        return "pago"

    data_inicio_ord = converter_data(data_inicio_ord)
    data_fim_ord = converter_data(data_fim_ord)
    data_inicio_extraord = converter_data(data_inicio_extraord)
    data_fim_extraord = converter_data(data_fim_extraord)

    if data_fim_ord and (data_fim_ord - hoje).days > 100:
        return "futuro"

    if data_inicio_extraord and data_fim_extraord:
        if data_inicio_extraord <= hoje <= data_fim_extraord:
            return "vermelho"
        if hoje > data_fim_extraord:
            return "vermelho"

    if data_fim_ord:
        data_alerta = data_fim_ord - timedelta(days=30)
        if data_alerta <= hoje <= data_fim_ord:
            return "amarelo"

    if data_inicio_ord and hoje >= data_inicio_ord:
        return "verde"

    return "verde"


def obter_dias_restantes(data_fim_ord, data_pagamento=None):
    if data_pagamento:
        return 0

    data_fim_ord = converter_data(data_fim_ord)
    if not data_fim_ord:
        return 0

    hoje = datetime.now().date()
    return max(0, (data_fim_ord - hoje).days)


def formatar_data(data):
    data = converter_data(data)
    if not data:
        return "-"
    return data.strftime("%d/%m/%Y")


def obter_cor_status(status):
    return {
        "verde": "#00CC00",
        "amarelo": "#FFCC00",
        "vermelho": "#FF0000",
        "pago": "#0099FF",
        "futuro": "#FFCC00",
    }.get(status, "#CCCCCC")


def criar_emoji_status(status):
    return {
        "verde": "✅",
        "amarelo": "⚠️",
        "vermelho": "❌",
        "pago": "💰",
        "futuro": "⏳",
    }.get(status, "❓")


def formatar_status(status):
    return {
        "verde": "NORMAL",
        "amarelo": "ATENÇÃO",
        "vermelho": "VENCIDO",
        "pago": "PAGO",
        "futuro": "PAGAR NO FUTURO",
    }.get(status, str(status).upper())
