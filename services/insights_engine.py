"""Motor de insights automáticos — formato bubble."""

import numpy as np
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

    # Concentração de produtos — Princípio de Pareto 80/20
    if df is not None and not df.empty and "Produto" in df.columns:
        prod_receita = df.groupby("Produto")["Receita"].sum().sort_values(ascending=False)
        total = prod_receita.sum()
        if total > 0:
            cumsum_pct = prod_receita.cumsum() / total * 100
            top_80_count = int((cumsum_pct <= 80).sum())
            total_prods = len(prod_receita)
            top_20_count = max(int(total_prods * 0.2), 1)
            top_20_receita = prod_receita.head(top_20_count).sum() / total * 100

            concentration_severity = "warning" if top_20_receita >= 80 else "info"
            insights.append({
                "icon": "🎯",
                "title": "Pareto",
                "value": f"{top_20_receita:.0f}%",
                "tag": f"{top_80_count}/{total_prods} produtos = 80% da receita",
                "severity": concentration_severity,
            })

    # Margem unitária por produto — alerta de margem negativa ou baixa
    if df is not None and not df.empty and "Produto" in df.columns:
        cols_lower = {c.lower(): c for c in df.columns}
        preco_col = cols_lower.get("preco_unitario")
        custo_col = cols_lower.get("custo_unitario")

        if preco_col is not None and custo_col is not None:
            prod_margem = (
                df.groupby("Produto")
                .agg(
                    Preco_Medio=(preco_col, "mean"),
                    Custo_Medio=(custo_col, "mean"),
                    Receita=("Receita", "sum"),
                )
            )
            prod_margem["Margem_Pct"] = (
                (prod_margem["Preco_Medio"] - prod_margem["Custo_Medio"])
                / prod_margem["Preco_Medio"].replace(0, np.nan)
            ) * 100

            neg_margin = prod_margem[prod_margem["Margem_Pct"] < 0]
            low_margin = prod_margem[
                (prod_margem["Margem_Pct"] >= 0) & (prod_margem["Margem_Pct"] < 15)
            ]

            if len(neg_margin) > 0:
                nomes = ", ".join(neg_margin.head(3).index.tolist())
                insights.append({
                    "icon": "🚨",
                    "title": "Margem Negativa",
                    "value": f"{len(neg_margin)} produtos",
                    "tag": f"Prejuízo unitário: {nomes}",
                    "severity": "danger",
                })
            elif len(low_margin) > 0:
                nomes = ", ".join(low_margin.head(3).index.tolist())
                insights.append({
                    "icon": "⚠️",
                    "title": "Margem Baixa",
                    "value": f"{len(low_margin)} produtos",
                    "tag": f"Margem < 15%: {nomes}",
                    "severity": "warning",
                })

    return insights
