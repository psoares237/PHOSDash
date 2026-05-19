"""Página: Receita e Crescimento.

Análise detalhada de receita com evolução mensal, variação, categoria e canal.
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
    """Renderiza a página Receita e Crescimento."""

    current_total = ctx.current_total
    previous_total = ctx.previous_total
    monthly = ctx.monthly
    cat = ctx.cat
    canal = ctx.canal
    page_key = ctx.page_key

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

    st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if monthly is not None and not monthly.empty:
            fig_monthly = go.Figure()

            fig_monthly.add_trace(
                go.Bar(
                    x=monthly["MesLabel"],
                    y=monthly["Receita"],
                    name="Receita",
                    marker_color=CHART_COLORS[0],
                    marker_line_width=0,
                    customdata=monthly["MesLabel"].tolist(),
                    hovertemplate="Receita: R$ %{y:,.2f}<extra></extra>",
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
                    customdata=monthly["MesLabel"].tolist(),
                    hovertemplate="Acumulado: R$ %{y:,.2f}<extra></extra>",
                )
            )

            fig_monthly.update_layout(
                barmode="group",
                showlegend=True,
                yaxis=dict(title="Receita Mensal"),
                yaxis2=dict(
                    title="Acumulado",
                    overlaying="y",
                    side="right",
                    gridcolor="rgba(255,255,255,0.04)",
                ),
                xaxis_title="",
            )

            fig_monthly = clean_figure(fig_monthly, height=340)

            chart_block(
                "Evolução da Receita",
                "Receita mensal e acumulada.",
                fig_monthly,
                page_key=page_key,
                dimension="MesLabel",
                description=(
                    "Permite avaliar crescimento, sazonalidade e velocidade "
                    "de formação do faturamento ao longo do tempo."
                ),
            )

    with col2:
        if monthly is not None and not monthly.empty and "MoM_Receita" in monthly.columns:
            fig_mom = px.bar(
                monthly,
                x="MesLabel",
                y="MoM_Receita",
                color_discrete_sequence=[CHART_COLORS[2]],
            )

            fig_mom.update_traces(
                customdata=monthly["MesLabel"].tolist(),
                hovertemplate="Variação MoM: %{y:.1f}%<extra></extra>",
            )

            fig_mom.update_layout(
                showlegend=False,
                xaxis_title="",
                yaxis_title="Variação (%)",
            )

            fig_mom = clean_figure(fig_mom, height=340)

            chart_block(
                "Variação Mensal",
                "Crescimento mês a mês da receita.",
                fig_mom,
                page_key=page_key,
                dimension="MesLabel",
                description=(
                    "Mostra aceleração ou retração comercial, ajudando a detectar "
                    "picos de campanha, sazonalidade e mudanças de demanda."
                ),
            )

    col3, col4 = st.columns(2)

    with col3:
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
                customdata=cat.head(8)["Categoria"].tolist(),
                hovertemplate="%{x}: R$ %{y:,.2f}<extra></extra>",
            )

            fig_cat.update_layout(
                showlegend=False,
                xaxis_title="",
                yaxis_title="Receita (R$)",
            )

            fig_cat = clean_figure(fig_cat, height=340)

            chart_block(
                "Receita por Categoria",
                "Categorias com maior faturamento.",
                fig_cat,
                page_key=page_key,
                dimension="Categoria",
                description=(
                    "Identifica quais categorias sustentam a receita e onde "
                    "existe risco de concentração comercial."
                ),
            )

    with col4:
        if canal is not None and not canal.empty:
            fig_canal = px.pie(
                canal,
                values="Receita",
                names="Canal_Venda",
                color_discrete_sequence=CHART_COLORS,
                hole=0.50,
            )

            fig_canal.update_traces(
                textposition="inside",
                textinfo="percent",
                customdata=canal["Canal_Venda"].tolist(),
                hovertemplate="%{label}: R$ %{value:,.2f}<extra></extra>",
            )

            fig_canal = clean_figure(fig_canal, height=340)

            chart_block(
                "Receita por Canal",
                "Participação dos canais de venda.",
                fig_canal,
                page_key=page_key,
                dimension="Canal_Venda",
                description=(
                    "Avalia dependência de canais e oportunidades de diversificação "
                    "da origem da receita."
                ),
            )

    _render_leitura(ctx, receita, previous_total, cat, page_key)


def _render_leitura(ctx, receita, previous_total, cat, page_key):
    """Renderiza leitura executiva da página."""

    section_header("📋 Leitura Executiva", "Resumo automático da Receita")

    prev_rec = previous_total.get("receita", 0) if previous_total else 0

    if prev_rec > 0:
        var = pct_change(receita, prev_rec)
        crescimento_msg = (
            f"Receita {var:+.1f}% vs. período anterior."
            if var is not None
            else "Sem base comparável."
        )
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
