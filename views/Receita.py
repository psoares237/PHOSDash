"""Página: Receita e Crescimento.

Análise detalhada de receita com evolução mensal, MoM, acumulado e decomposição.
Todos os visuais respondem ao cross-filtering via page_key.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from components.ui import render_kpis, section_header, chart_block
from components.charts import clean_figure, CHART_COLORS
from state.filters import FilterState
from utils.formatters import fmt_currency, fmt_int, fmt_pct, pct_change


def render(ctx):
    """Renderiza a página Receita e Crescimento.

    Args:
        ctx: PageContext com todos os dados preparados.
    """
    current_total = ctx.current_total
    previous_total = ctx.previous_total
    monthly = ctx.monthly
    cat = ctx.cat
    canal = ctx.canal
    page_key = ctx.page_key

    # ── KPIs da Receita ──

    receita = current_total.get("receita", 0)
    lucro = current_total.get("lucro", 0)
    pedidos = current_total.get("pedidos", 0)
    ticket = (receita / pedidos) if pedidos else 0
    margem = (lucro / receita * 100) if receita else 0

    prev_receita = previous_total.get("receita", 0) if previous_total else 0
    prev_pedidos = previous_total.get("pedidos", 0) if previous_total else 0

    kpis = [
        ("Receita Total", fmt_currency(receita), pct_change(receita, prev_receita), "período anterior"),
        ("Ticket Médio", fmt_currency(ticket), None, "período anterior"),
        ("Total de Pedidos", fmt_int(pedidos), pct_change(pedidos, prev_pedidos), "período anterior"),
        ("Margem", fmt_pct(margem), None, "período anterior"),
    ]

    render_kpis(kpis, per_row=4)

    st.markdown("---")

    # ── Evolução Mensal: Barras + Linha ──

    if monthly is not None and not monthly.empty:
        fig_monthly = go.Figure()

        fig_monthly.add_trace(
            go.Bar(
                x=monthly["MesLabel"],
                y=monthly["Receita"],
                name="Receita",
                marker_color=CHART_COLORS[0],
                marker_line_width=0,
                hovertemplate="Receita: R$ %{y:,.2f}<extra></extra>",
                customdata=monthly["MesLabel"].tolist(),
            )
        )

        fig_monthly.add_trace(
            go.Scatter(
                x=monthly["MesLabel"],
                y=monthly["Acumulado_Receita"],
                name="Acumulado",
                mode="lines+markers",
                line=dict(color=CHART_COLORS[1], width=2.5),
                marker=dict(size=5),
                yaxis="y2",
                hovertemplate="Acumulado: R$ %{y:,.2f}<extra></extra>",
                customdata=monthly["MesLabel"].tolist(),
            )
        )

        fig_monthly.update_layout(
            barmode="group",
            showlegend=True,
            yaxis=dict(title="Receita Mensal (R$)"),
            yaxis2=dict(
                title="Acumulado (R$)",
                overlaying="y",
                side="right",
                gridcolor="rgba(255,255,255,0.04)",
            ),
            xaxis_title="",
        )

        fig_monthly = clean_figure(fig_monthly, height=400)

        chart_block(
            "Evolução da Receita",
            "Barras: receita mensal. Linha: receita acumulada.",
            fig_monthly,
            page_key=page_key,
            dimension="MesLabel",
        )

    # ── MoM Receita ──

    if monthly is not None and not monthly.empty and "MoM_Receita" in monthly.columns:
        fig_mom = px.bar(
            monthly,
            x="MesLabel",
            y="MoM_Receita",
            color_discrete_sequence=[CHART_COLORS[2]],
        )
        fig_mom.update_traces(
            hovertemplate="Variação MoM: %{y:.1f}%<extra></extra>",
            customdata=monthly["MesLabel"].tolist(),
        )
        fig_mom.update_layout(
            showlegend=False,
            xaxis_title="",
            yaxis_title="Variação (%)",
        )
        fig_mom = clean_figure(fig_mom, height=300)

        chart_block(
            "Variação Mensal (MoM)",
            "Variação percentual da receita mês a mês.",
            fig_mom,
            page_key=page_key,
            dimension="MesLabel",
        )

    # ── Receita por Categoria ──

    if cat is not None and not cat.empty:
        fig_cat = px.bar(
            cat.head(8),
            x="Categoria",
            y="Receita",
            color_discrete_sequence=[CHART_COLORS[0]],
            text="Receita",
        )
        fig_cat.update_traces(
            texttemplate="%{text:,.2s}",
            textposition="outside",
            hovertemplate="%{x}: R$ %{y:,.2f}<extra></extra>",
            customdata=cat.head(8)["Categoria"].tolist(),
        )
        fig_cat.update_layout(
            showlegend=False,
            xaxis_title="",
            yaxis_title="Receita (R$)",
        )
        fig_cat = clean_figure(fig_cat, height=340)

        chart_block(
            "Receita por Categoria",
            "Ranking das categorias por receita.",
            fig_cat,
            page_key=page_key,
            dimension="Categoria",
        )

    # ── Receita por Canal ──

    if canal is not None and not canal.empty:
        fig_canal = px.pie(
            canal,
            values="Receita",
            names="Canal_Venda",
            color_discrete_sequence=CHART_COLORS,
            hole=0.45,
        )
        fig_canal.update_traces(
            textposition="inside",
            textinfo="percent+label",
            hovertemplate="%{label}: R$ %{value:,.2f}<extra></extra>",
            customdata=canal["Canal_Venda"].tolist(),
        )
        fig_canal = clean_figure(fig_canal, height=340)

        chart_block(
            "Receita por Canal",
            "Participação de cada canal de venda.",
            fig_canal,
            page_key=page_key,
            dimension="Canal_Venda",
        )

    # ── Leitura Executiva ──

    section_header("📋 Leitura Executiva", "Resumo automático da Receita")

    prev_rec = previous_total.get("receita", 0) if previous_total else 0
    if prev_rec > 0:
        var = pct_change(receita, prev_rec)
        crescimento_msg = f"Receita {var:+.1f}% vs. período anterior." if var is not None else "Sem base comparável."
    else:
        crescimento_msg = "Sem base comparável."

    lider_msg = ""
    if cat is not None and not cat.empty:
        top = cat.iloc[0]
        lider_msg = f"Liderando: **{top['Categoria']}** com {fmt_currency(top['Receita'])}."

    st.markdown(f"📈 **{crescimento_msg}**\n\n{lider_msg}")

    fs = FilterState(page_key)
    if fs.has_filters:
        filtros_str = ", ".join(f"{k}: {v}" for k, v in fs.filters.items())
        st.markdown(f"🔍 *Dados filtrados por: {filtros_str}*")