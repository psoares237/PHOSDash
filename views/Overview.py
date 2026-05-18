"""Página: Visão Geral (Overview).

KPIs no topo (renderizados pelo app.py), gráficos-síntese e leitura executiva.
Todos os visuais respondem ao cross-filtering via page_key.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from components.ui import render_kpis, section_header, chart_block
from components.charts import clean_figure, CHART_COLORS
from state.filters import FilterState
from utils.formatters import fmt_currency, fmt_int, fmt_pct, pct_change


def render(ctx):
    """Renderiza a página Visão Geral.

    Args:
        ctx: PageContext com todos os dados preparados.
    """
    current_df = ctx.current_df
    current_total = ctx.current_total
    previous_total = ctx.previous_total
    monthly = ctx.monthly
    cat = ctx.cat
    regiao = ctx.regiao
    canal = ctx.canal
    top_channel_name = ctx.top_channel_name
    top_channel_share = ctx.top_channel_share
    page_key = ctx.page_key

    # ── Seção: Receita e Lucro Mensal ──

    if monthly is not None and not monthly.empty:
        fig = make_subplots(
            rows=1, cols=1,
            specs=[[{"secondary_y": True}]],
        )

        # Barras: Receita
        fig.add_trace(
            go.Bar(
                x=monthly["MesLabel"],
                y=monthly["Receita"],
                name="Receita",
                marker_color=CHART_COLORS[0],
                marker_line_width=0,
                hovertemplate="Receita: R$ %{y:,.2f}<extra></extra>",
                customdata=monthly["MesLabel"].tolist(),
            ),
            secondary_y=False,
        )

        # Linha: Lucro
        fig.add_trace(
            go.Scatter(
                x=monthly["MesLabel"],
                y=monthly["Lucro"],
                name="Lucro",
                mode="lines+markers",
                line=dict(color=CHART_COLORS[1], width=2.5),
                marker=dict(size=6),
                hovertemplate="Lucro: R$ %{y:,.2f}<extra></extra>",
                customdata=monthly["MesLabel"].tolist(),
            ),
            secondary_y=True,
        )

        fig.update_layout(
            barmode="group",
            showlegend=True,
            xaxis_title="",
            yaxis_title="Receita (R$)",
            yaxis2_title="Lucro (R$)",
        )

        fig = clean_figure(fig, height=380)
        chart_block(
            "Receita e Lucro Mensal",
            "Barras: receita mensal. Linha: lucro mensal sobre eixo secundário.",
            fig,
            page_key=page_key,
            dimension="MesLabel",
        )

    # ── Seção: Categoria + Região (lado a lado) ──

    col1, col2 = st.columns(2)

    with col1:
        if cat is not None and not cat.empty:
            fig_cat = px.pie(
                cat,
                values="Receita",
                names="Categoria",
                color_discrete_sequence=CHART_COLORS,
                hole=0.45,
            )
            fig_cat.update_traces(
                textposition="inside",
                textinfo="percent+label",
                hovertemplate="%{label}: R$ %{value:,.2f}<extra></extra>",
                customdata=cat["Categoria"].tolist(),
            )
            fig_cat = clean_figure(fig_cat, height=340)
            chart_block(
                "Receita por Categoria",
                "Participação percentual de cada categoria no total.",
                fig_cat,
                page_key=page_key,
                dimension="Categoria",
            )

    with col2:
        if regiao is not None and not regiao.empty:
            fig_reg = px.pie(
                regiao,
                values="Receita",
                names="Regiao",
                color_discrete_sequence=CHART_COLORS,
                hole=0.45,
            )
            fig_reg.update_traces(
                textposition="inside",
                textinfo="percent+label",
                hovertemplate="%{label}: R$ %{value:,.2f}<extra></extra>",
                customdata=regiao["Regiao"].tolist(),
            )
            fig_reg = clean_figure(fig_reg, height=340)
            chart_block(
                "Receita por Região",
                "Distribuição geográfica da receita.",
                fig_reg,
                page_key=page_key,
                dimension="Regiao",
            )

    # ── Seção: Canal de Venda ──

    if canal is not None and not canal.empty:
        fig_canal = px.bar(
            canal.head(6),
            x="Canal_Venda",
            y="Receita",
            color_discrete_sequence=[CHART_COLORS[0]],
            text="Receita",
        )
        fig_canal.update_traces(
            texttemplate="%{text:,.2s}",
            textposition="outside",
            hovertemplate="Canal: %{x}<br>Receita: R$ %{y:,.2f}<extra></extra>",
            customdata=canal.head(6)["Canal_Venda"].tolist(),
        )
        fig_canal.update_layout(showlegend=False, xaxis_title="", yaxis_title="Receita (R$)")
        fig_canal = clean_figure(fig_canal, height=340)
        chart_block(
            "Receita por Canal de Venda",
            f"Top canais. Destaque: {top_channel_name} com {top_channel_share:.1f}% da receita.",
            fig_canal,
            page_key=page_key,
            dimension="Canal_Venda",
        )

    # ── Leitura Executiva ──

    receita = current_total.get("receita", 0)
    lucro = current_total.get("lucro", 0)
    pedidos = current_total.get("pedidos", 0)
    margem = (lucro / receita * 100) if receita else 0

    # Classificação de margem
    if margem >= 40:
        margem_msg = f"Margem forte ({margem:.1f}%) — operação saudável."
    elif margem >= 25:
        margem_msg = f"Margem moderada ({margem:.1f}%) — observar custos."
    elif margem > 0:
        margem_msg = f"Margem sob pressão ({margem:.1f}%) — ação necessária."
    else:
        margem_msg = "Margem não calculável."

    # Crescimento
    prev_receita = previous_total.get("receita", 0) if previous_total else 0
    if prev_receita > 0:
        var = pct_change(receita, prev_receita)
        if var is not None:
            crescimento_msg = f"Receita {var:+.1f}% vs. período anterior."
        else:
            crescimento_msg = "Sem base comparável."
    else:
        crescimento_msg = "Sem base comparável."

    # Concentração
    alertas = []
    if cat is not None and not cat.empty and len(cat) > 0:
        top_cat_share = cat.iloc[0]["Receita"] / cat["Receita"].sum() * 100
        if top_cat_share >= 40:
            alertas.append(f"Concentração por categoria: {cat.iloc[0]['Categoria']} ({top_cat_share:.1f}%).")

    if regiao is not None and not regiao.empty and len(regiao) > 0:
        top_reg_share = regiao.iloc[0]["Receita"] / regiao["Receita"].sum() * 100
        if top_reg_share >= 50:
            alertas.append(f"Concentração regional: {regiao.iloc[0]['Regiao']} ({top_reg_share:.1f}%).")

    if canal is not None and not canal.empty and len(canal) > 0:
        top_canal_share = canal.iloc[0]["Receita"] / canal["Receita"].sum() * 100
        if top_canal_share >= 60:
            alertas.append(f"Dependência de canal: {canal.iloc[0]['Canal_Venda']} ({top_canal_share:.1f}%).")

    # Montar leitura
    linha_margem = f"📊 **{margem_msg}**"
    linha_crescimento = f"📈 **{crescimento_msg}**"
    linhas_alerta = ""
    if alertas:
        linhas_alerta = "\n\n".join(f"⚠️ {a}" for a in alertas)

    leitura = f"{linha_margem}\n\n{linha_crescimento}"
    if linhas_alerta:
        leitura += f"\n\n{linhas_alerta}"

    fs = FilterState(page_key)
    if fs.has_filters:
        filtros_str = ", ".join(f"{k}: {v}" for k, v in fs.filters.items())
        leitura += f"\n\n🔍 *Dados filtrados por: {filtros_str}*"

    section_header("📋 Leitura Executiva", "Resumo automático dos indicadores principais")
    st.markdown(leitura)