"""Formatação de valores para o dashboard PHOSDash."""

import pandas as pd


MESES_PT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
    5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
    9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}


def month_label(dt: pd.Timestamp) -> str:
    """Converte timestamp em label curto: 'Jan/2023'."""
    return f"{MESES_PT[dt.month]}/{dt.year}"


def fmt_currency(value: float) -> str:
    """Formata valor monetário: R$ 1.234,56."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_int(value: float) -> str:
    """Formata inteiro com separador: 1.234."""
    return f"{int(round(value)):,}".replace(",", ".")


def fmt_pct(value: float) -> str:
    """Formata porcentagem: 43,0%."""
    return f"{value:.1f}%".replace(".", ",")


def pct_change(current: float, previous: float):
    """Calcula variação percentual. Retorna None se não houver base."""
    if previous in (0, None) or pd.isna(previous):
        return None
    return ((current - previous) / abs(previous)) * 100