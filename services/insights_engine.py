"""Motor de insights automáticos — formato bubble."""

import pandas as pd


def generate_insights(
    df: pd.DataFrame,
    current_total: dict,
    previous_total: dict | None = None,
) -> list[dict]:
    """Gera insights executivos a partir dos totais e DataFrame."""

    insights: list[dict] = []
    receita = current_total.get("receita", 0)
    lucro = current_total.get("lucro", 0)
    pedidos = current_total.get("pedidos", 0)
    frete = current_total.get("frete", 0)
    desconto_medio = current_total.get("desconto_medio", 0)

    margem = (lucro / receita * 100) if receita else 0
    ticket_medio = (receita / pedidos) if pedidos else 0

    # Receita em destaque
    if receita > 0:
        insights.append({
            "icon": "📈",
            "title": "Receita",
            "value": f"R$ {receita:,.0f}",
            "tag": "total do período",
            "severity": "info",
        })

    # Ticket médio
    if ticket_medio > 0:
        insights.append({
            "icon": "📊",
            "title": "Ticket Médio",
            "value": f"R$ {ticket_medio:,.2f}",
            "tag": "por pedido",
            "severity": "info",
        })

    # Margem
    if margem >= 40:
        insights.append({
            "icon": "✅",
            "title": "Margem",
            "value": f"{margem:.1f}%",
            "tag": "excelente",
            "severity": "success",
        })
    elif margem >= 25:
        insights.append({
            "icon": "📊",
            "title": "Margem",
            "value": f"{margem:.1f}%",
            "tag": "moderada",
            "severity": "info",
        })
    elif margem > 0:
        insights.append({
            "icon": "⚠️",
            "title": "Margem",
            "value": f"{margem:.1f}%",
            "tag": "sob pressão",
            "severity": "warning",
        })

    # Variação vs período anterior
    if previous_total:
        prev_receita = previous_total.get("receita", 0)
        if prev_receita > 0:
            var = ((receita - prev_receita) / prev_receita) * 100
            if var >= 10:
                insights.append({
                    "icon": "🚀",
                    "title": "Crescimento",
                    "value": f"{var:+.1f}%",
                    "tag": "vs. período anterior",
                    "severity": "success",
                })
            elif var <= -10:
                insights.append({
                    "icon": "📉",
                    "title": "Queda",
                    "value": f"{var:+.1f}%",
                    "tag": "investigar causas",
                    "severity": "danger",
                })

    # Frete proporcional
    if receita > 0 and frete > 0:
        frete_pct = frete / receita * 100
        if frete_pct > 15:
            insights.append({
                "icon": "🚚",
                "title": "Frete",
                "value": f"{frete_pct:.1f}%",
                "tag": "da receita",
                "severity": "warning",
            })

    # Desconto médio
    if desconto_medio > 10:
        insights.append({
            "icon": "🏷️",
            "title": "Descontos",
            "value": f"{desconto_medio:.1f}%",
            "tag": "médio",
            "severity": "warning",
        })

    # Ticket médio com variação
    if previous_total and previous_total.get("pedidos", 0) > 0:
        prev_ticket = previous_total.get("receita", 0) / previous_total.get("pedidos", 1)
        if prev_ticket > 0:
            var_ticket = ((ticket_medio - prev_ticket) / prev_ticket) * 100
            if abs(var_ticket) >= 5:
                insights.append({
                    "icon": "💰",
                    "title": "Ticket",
                    "value": f"{var_ticket:+.1f}%",
                    "tag": "variação",
                    "severity": "info" if var_ticket > 0 else "warning",
                })

    return insights
