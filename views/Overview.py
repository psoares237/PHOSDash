"""Página: Visão Geral (Overview).

Layout executivo em grid, inspirado em dashboards premium:
3 colunas, cards com título/subtítulo/descrição e leitura executiva compacta.
Todos os visuais respondem ao cross-filtering via page_key.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from components.ui import section_header, chart_block
from components.charts import clean_figure, CHART_COLORS
from state.filters import FilterState
from utils.formatters import pct_change


def render(ctx):
    """Renderiza a página Visão Geral."""

    current_total = ctx.current_total
    previous_total = ctx.previous_total
    monthly = ctx.monthly
    cat = ctx.cat
    regiao = ctx.regiao
    canal = ctx.canal
    top_channel_name = ctx.top_channel_name
    top_channel_share = ctx.top_channel_share
    page_key = ctx.page_key

    # ═══════════════════════════════════════
    # LINHA 1 — visão financeira, categoria e região
    # ═══════════════════════════════════════

    col1, col2, col3 = st.columns(3)

    with col1:
        if monthly is not None and not monthly.empty:
            fig = make_subplots(
                rows=1,
                cols=1,
                specs=[[{"secondary_y": True}]],
            )

            fig.add_trace(
                go.Bar(
                    x=monthly["MesLabel"],
                    y=monthly["Receita"],
                    name="Receita",
                    marker_color=CHART_COLORS[0],
                    marker_line_width=0,
                    customdata=monthly["MesLabel"].tolist(),
                    hovertemplate="Receita: R$ %{y:,.2f}<extra></extra>",
                ),
                secondary_y=False,
            )

            fig.add_trace(
                go.Scatter(
                    x=monthly["MesLabel"],
                    y=monthly["Lucro"],
                    name="Lucro",
                    mode="lines+markers",
                    line=dict(color=CHART_COLORS[1], width=2.4),
                    marker=dict(size=5),
                    customdata=monthly["MesLabel"].tolist(),
                    hovertemplate="Lucro: R$ %{y:,.2f}<extra></extra>",
                ),
                secondary_y=True,
            )

            fig.update_layout(
                barmode="group",
                showlegend=True,
                xaxis_title="",
                yaxis_title="",
                yaxis2_title="",
            )

            fig = clean_figure(fig, height=320)

            chart_block(
                "Receita e Lucro Mensal",
                "Comparativo financeiro mensal.",
                fig,
                page_key=page_key,
                dimension="MesLabel",
                description=(
                    "Permite avaliar a evolução conjunta da receita e do lucro, "
                    "identificando meses de maior rentabilidade e possíveis sazonalidades."
                ),
            )

    with col2:
        if cat is not None and not cat.empty:
            fig_cat = px.pie(
                cat,
                values="Receita",
                names="Categoria",
                color_discrete_sequence=CHART_COLORS,
                hole=0.50,
            )

            fig_cat.update_traces(
                textposition="inside",
                textinfo="percent",
                customdata=cat["Categoria"].tolist(),
                hovertemplate="%{label}: R$ %{value:,.2f}<extra></extra>",
            )

            fig_cat = clean_figure(fig_cat, height=320)

            chart_block(
                "Receita por Categoria",
                "Participação das categorias no faturamento.",
                fig_cat,
                page_key=page_key,
                dimension="Categoria",
                description=(
                    "Ajuda a identificar concentração de receita, dependência de categorias "
                    "e oportunidades de diversificação comercial."
                ),
            )

    with col3:
        if regiao is not None and not regiao.empty:
            fig_reg = px.pie(
                regiao,
                values="Receita",
                names="Regiao",
                color_discrete_sequence=CHART_COLORS,
                hole=0.50,
            )

            fig_reg.update_traces(
                textposition="inside",
                textinfo="percent",
                customdata=regiao["Regiao"].tolist(),
                hovertemplate="%{label}: R$ %{value:,.2f}<extra></extra>",
            )

            fig_reg = clean_figure(fig_reg, height=320)

            chart_block(
                "Receita por Região",
                "Distribuição geográfica da receita.",
                fig_reg,
                page_key=page_key,
                dimension="Regiao",
                description=(
                    "Mostra quais regiões sustentam o faturamento e onde existem "
                    "oportunidades de expansão ou risco de concentração."
                ),
            )

    # ═══════════════════════════════════════
    # LINHA 2 — canal e leitura executiva
    # ═══════════════════════════════════════

    col4, col5 = st.columns([2, 1])

    with col4:
        if canal is not None and not canal.empty:
            fig_canal = px.bar(
                canal.head(8),
                x="Canal_Venda",
                y="Receita",
                color_discrete_sequence=[CHART_COLORS[0]],
                text="Receita",
            )

            fig_canal.update_traces(
                texttemplate="%{text:,.2s}",
                textposition="outside",
                customdata=canal.head(8)["Canal_Venda"].tolist(),
                hovertemplate="Canal: %{x}<br>Receita: R$ %{y:,.2f}<extra></extra>",
            )

            fig_canal.update_layout(
                showlegend=False,
                xaxis_title="",
                yaxis_title="Receita (R$)",
            )

            fig_canal = clean_figure(fig_canal, height=320)

            chart_block(
                "Receita por Canal de Venda",
                f"Destaque: {top_channel_name} com {top_channel_share:.1f}% da receita.",
                fig_canal,
                page_key=page_key,
                dimension="Canal_Venda",
                description=(
                    "Permite avaliar dependência de canais, eficiência comercial "
                    "e oportunidades de fortalecimento ou diversificação de vendas."
                ),
            )

    with col5:
        _render_leitura_executiva(ctx)


def _render_leitura_executiva(ctx):
    """Renderiza leitura executiva compacta em card."""

    current_total = ctx.current_total
    previous_total = ctx.previous_total
    cat = ctx.cat
    regiao = ctx.regiao
    canal = ctx.canal
    page_key = ctx.page_key

    receita = current_total.get("receita", 0)
    lucro = current_total.get("lucro", 0)
    margem = (lucro / receita * 100) if receita else 0

    if margem >= 40:
        margem_msg = f"Margem forte ({margem:.1f}%)."
    elif margem >= 25:
        margem_msg = f"Margem moderada ({margem:.1f}%)."
    elif margem > 0:
        margem_msg = f"Margem sob pressão ({margem:.1f}%)."
    else:
        margem_msg = "Margem não calculável."

    prev_receita = previous_total.get("receita", 0) if previous_total else 0

    if prev_receita > 0:
        var = pct_change(receita, prev_receita)
        crescimento_msg = (
            f"Receita {var:+.1f}% vs. período anterior."
            if var is not None
            else "Sem base comparável."
        )
    else:
        crescimento_msg = "Sem base comparável."

    alertas = []

    if cat is not None and not cat.empty:
        top_cat_share = cat.iloc[0]["Receita"] / cat["Receita"].sum() * 100
        if top_cat_share >= 40:
            alertas.append(
                f"Categoria dominante: {cat.iloc[0]['Categoria']} ({top_cat_share:.1f}%)."
            )

    if regiao is not None and not regiao.empty:
        top_reg_share = regiao.iloc[0]["Receita"] / regiao["Receita"].sum() * 100
        if top_reg_share >= 50:
            alertas.append(
                f"Concentração regional: {regiao.iloc[0]['Regiao']} ({top_reg_share:.1f}%)."
            )

    if canal is not None and not canal.empty:
        top_canal_share = canal.iloc[0]["Receita"] / canal["Receita"].sum() * 100
        if top_canal_share >= 60:
            alertas.append(
                f"Dependência de canal: {canal.iloc[0]['Canal_Venda']} ({top_canal_share:.1f}%)."
            )

    fs = FilterState(page_key)

    st.markdown(
        """
<div class="chart-card">
    <div class="chart-title">Leitura Executiva</div>
    <div class="chart-subtitle">Resumo automático dos principais sinais da operação.</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(f"📊 **{margem_msg}**")
    st.markdown(f"📈 **{crescimento_msg}**")

    for alerta in alertas:
        st.markdown(f"⚠️ {alerta}")

    if fs.has_filters:
        filtros_str = ", ".join(f"{k}: {v}" for k, v in fs.filters.items())
        st.markdown(f"🔍 *Dados filtrados por: {filtros_str}*")

    st.markdown("</div>", unsafe_allow_html=True)
