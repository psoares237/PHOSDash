"""Motor de insights automáticos."""

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
            "title": "Receita em destaque",
            "message": f"A operação movimentou R$ {receita:,.2f}.",
        })

    # Ticket médio
    if ticket_medio > 0:
        insights.append({
            "icon": "📊",
            "title": "Ticket médio monitorado",
            "message": f"O ticket médio está em R$ {ticket_medio:,.2f} por pedido.",
        })

    # Margem
    if margem >= 40:
        insights.append({
            "icon": "📈",
            "title": "Rentabilidade excelente",
            "message": f"A margem operacional de {margem:.1f}% indica alta eficiência na conversão de receita em lucro.",
        })
    elif margem >= 25:
        insights.append({
            "icon": "📊",
            "title": "Margem moderada",
            "message": f"A margem de {margem:.1f}% está dentro da faixa esperada.",
        })
    elif margem > 0:
        insights.append({
            "icon": "⚠️",
            "title": "Margem sob pressão",
            "message": f"A margem de {margem:.1f}% requer atenção sobre custos e precificação.",
        })

    # Variação vs período anterior
    if previous_total:
        prev_receita = previous_total.get("receita", 0)
        if prev_receita > 0:
            var = ((receita - prev_receita) / prev_receita) * 100
            if var >= 10:
                insights.append({
                    "icon": "🚀",
                    "title": "Crescimento forte",
                    "message": f"Receita {var:+.1f}% vs. período anterior.",
                })
            elif var <= -10:
                insights.append({
                    "icon": "📉",
                    "title": "Queda acentuada",
                    "message": f"Receita {var:+.1f}% vs. período anterior. Investigar causas.",
                })

    # Frete proporcional
    if receita > 0 and frete > 0:
        frete_pct = frete / receita * 100
        if frete_pct > 15:
            insights.append({
                "icon": "🚚",
                "title": "Frete elevado",
                "message": f"Frete representa {frete_pct:.1f}% da receita. Avaliar alternativas logísticas.",
            })

    # Desconto médio
    if desconto_medio > 10:
        insights.append({
            "icon": "🏷️",
            "title": "Descontos acima do normal",
            "message": f"Desconto médio de {desconto_medio:.1f}% pode estar impactando margem.",
        })

    # Ticket médio com variação
    if previous_total and previous_total.get("pedidos", 0) > 0:
        prev_ticket = previous_total.get("receita", 0) / previous_total.get("pedidos", 1)
        if prev_ticket > 0:
            var_ticket = ((ticket_medio - prev_ticket) / prev_ticket) * 100
            if abs(var_ticket) >= 5:
                direction = "superior" if var_ticket > 0 else "inferior"
                insights.append({
                    "icon": "💰",
                    "title": "Variação no ticket médio",
                    "message": f"Ticket médio {var_ticket:+.1f}% ({direction} ao período anterior).",
                })

    return insights