import pandas as pd
from datetime import datetime, timedelta


def converter_data(data):
    if not data:
        return None
    if isinstance(data, str):
        return datetime.strptime(data, "%Y-%m-%d").date()
    return data


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

    # Anuidade muito futura
    if data_fim_ord and (data_fim_ord - hoje).days > 100:
        return "futuro"

    # Período extraordinário ou vencido
    if data_inicio_extraord and data_fim_extraord:
        if data_inicio_extraord <= hoje <= data_fim_extraord:
            return "vermelho"
        if hoje > data_fim_extraord:
            return "vermelho"

    # Alerta (30 dias antes do vencimento)
    if data_fim_ord:
        data_alerta = data_fim_ord - timedelta(days=30)
        if data_alerta <= hoje <= data_fim_ord:
            return "amarelo"

    # Normal
    if data_inicio_ord and hoje >= data_inicio_ord:
        return "verde"

    return "verde"


def obter_dias_restantes(data_fim_ord, data_pagamento=None):
    if data_pagamento:
        return 0

    hoje = datetime.now().date()
    data_fim_ord = converter_data(data_fim_ord)

    if not data_fim_ord:
        return 0

    dias = (data_fim_ord - hoje).days
    return max(0, dias)


def formatar_data(data):
    data = converter_data(data)
    return data.strftime("%d/%m/%Y") if data else "-"


def obter_cor_status(status):
    cores = {
        "verde": "#00CC00",
        "amarelo": "#FFCC00",
        "vermelho": "#FF0000",
        "pago": "#0099FF",
        "futuro": "#FFCC00",
    }
    return cores.get(status, "#CCCCCC")


def criar_emoji_status(status):
    emojis = {
        "verde": "✅",
        "amarelo": "⚠️",
        "vermelho": "❌",
        "pago": "💰",
        "futuro": "⏳",
    }
    return emojis.get(status, "❓")


def formatar_status(status):
    rotulos = {
        "verde": "NORMAL",
        "amarelo": "ATENÇÃO",
        "vermelho": "VENCIDO",
        "pago": "PAGO",
        "futuro": "PAGAR NO FUTURO",
    }
    return rotulos.get(status, str(status).upper())
