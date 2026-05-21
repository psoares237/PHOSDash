"""Página: Visão Geral (Overview).

Layout executivo aprimorado:
1. Receita/Lucro com margem + Categoria com top highlight
2. Vendedor Top 5 + Canal de Venda com margem por canal

Todos os visuais respondem ao cross-filtering via page_key.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from components.ui import chart_block
from components.charts import clean_figure, CHART_COLORS
from utils.formatters import fmt_currency, fmt_pct


def render(ctx):
    """Renderiza a página Visão Geral."""

    monthly = ctx.monthly
    cat = ctx.cat
    canal = ctx.canal
    vendedor = ctx.vendedor
    top_channel_name = ctx.top_channel_name
    top_channel_share = ctx.top_channel_share
    page_key = ctx.page_key

    # Top category info for subtitle
    top_cat_name = cat.iloc[0]["Categoria"] if not cat.empty else "N/A"
    top_cat_share = (
        cat.iloc[0]["Receita"] / cat["Receita"].sum() * 100
    ) if not cat.empty else 0

    # ═══════════════════════════════════════
    # LINHA 1 — Receita+Lucro+Margem + Categoria (2 colunas)
    # ═══════════════════════════════════════

    col1, col2 = st.columns(2)

    with col1:
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
                    customdata=monthly["MesLabel"].tolist(),
                    hovertemplate="Receita: R$ %{y:,.2f}<extra></extra>",
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
                    line=dict(color=CHART_COLORS[1], width=2.4),
                    marker=dict(size=5),
                    customdata=monthly["MesLabel"].tolist(),
                    hovertemplate="Lucro: R$ %{y:,.2f}<extra></extra>",
                ),
                secondary_y=True,
            )

            # Linha tracejada: Margem % (sobre secondary y)
            fig.add_trace(
                go.Scatter(
                    x=monthly["MesLabel"],
                    y=monthly["Margem"],
                    name="Margem %",
                    mode="lines",
                    line=dict(color=CHART_COLORS[5], width=1.5, dash="dot"),
                    customdata=monthly["MesLabel"].tolist(),
                    hovertemplate="Margem: %{y:.2f}%<extra></extra>",
                ),
                secondary_y=True,
            )

            fig.update_layout(
                barmode="group",
                showlegend=True,
                xaxis_title="",
                yaxis_title="Receita (R$)",
                yaxis2_title="Lucro / Margem",
                legend=dict(
                    orientation="h",
                    yanchor="bottom", y=1.02,
                    xanchor="right", x=1,
                    font=dict(size=11, color="#AAB7C4"),
                ),
            )

            fig = clean_figure(fig, height=420)

            chart_block(
                "Receita, Lucro e Margem",
                "Evolução mensal com indicador de rentabilidade.",
                fig,
                page_key=page_key,
                dimension="MesLabel",
                description=(
                    "Visão integrada: barras mostram receita, linha contínua o lucro "
                    "e linha tracejada a margem %. Identifique meses de alta receita "
"com baixa margem, sinal de custo ou desconto excessivo."
                ),
            )

    with col2:
        if cat is not None and not cat.empty:
            # Agrupar categorias pequenas como "Outros" para legibilidade
            cat_top = cat.head(7).copy()
            outros_receita = cat.iloc[7:]["Receita"].sum() if len(cat) > 7 else 0
            if outros_receita > 0:
                cat_top = pd.concat([
                    cat_top,
                    pd.DataFrame([{"Categoria": "Outros", "Receita": outros_receita}]),
                ])

            fig_cat = px.pie(
                cat_top,
                values="Receita",
                names="Categoria",
                color_discrete_sequence=CHART_COLORS,
                hole=0.50,
            )

            fig_cat.update_traces(
                textposition="inside",
                textinfo="percent+label",
                textfont_size=11,
                customdata=cat_top["Categoria"].tolist(),
                hovertemplate="%{label}: R$ %{value:,.2f} (%{percent})<extra></extra>",
                sort=False,
            )

            fig_cat = clean_figure(fig_cat, height=420)

            chart_block(
                "Receita por Categoria",
                f"Destaque: {top_cat_name} com {top_cat_share:.1f}% da receita.",
                fig_cat,
                page_key=page_key,
                dimension="Categoria",
                description=(
                    "Concentração de receita por categoria. Se uma categoria representa "
                    "mais de 30%, há risco de dependência. Categorias pequenas agrupadas "
                    "em 'Outros' para legibilidade."
                ),
            )

    # ═══════════════════════════════════════
    # LINHA 2 — Vendedor Top 5 + Canal com Margem (2 colunas)
    # ═══════════════════════════════════════

    col3, col4 = st.columns(2)

    with col3:
        if vendedor is not None and not vendedor.empty:
            vend_top = vendedor.head(5)

            fig_vend = px.bar(
                vend_top,
                x="Vendedor",
                y="Receita",
                color="Margem",
                color_continuous_scale=[
                    "#F87171",  # baixa margem
                    "#d3b73e",  # média
                    "#357560",  # alta
                ],
                text="Receita",
            )

            fig_vend.update_traces(
                texttemplate="R$ %{text:,.2s}",
                textposition="outside",
                customdata=vend_top["Vendedor"].tolist(),
                hovertemplate=(
                    "%{x}<br>Receita: R$ %{y:,.2f}<br>"
                    "Margem: %{marker.color:.2f}%<extra></extra>"
                ),
                marker=dict(
                    line=dict(width=0),
                    colorbar=dict(
                        title="Margem %",
                        tickfont=dict(color="#AAB7C4"),
                        title_font=dict(color="#AAB7C4"),
                    ),
                ),
            )

            fig_vend.update_layout(
                showlegend=False,
                xaxis_title="",
                yaxis_title="Receita (R$)",
            )

            fig_vend = clean_figure(fig_vend, height=420)

            chart_block(
                "Top 5 Vendedores",
"Performance por vendedor, cor indica margem.",
                fig_vend,
                page_key=page_key,
                dimension="Vendedor",
                description=(
                    "Receita (tamanho da barra) vs Margem (cor: verde=alta, "
                    "vermelho=baixa). Vendedores com alta receita e baixa margem "
                    "podem estar usando desconto excessivo para vender."
                ),
            )

    with col4:
        if canal is not None and not canal.empty:
            # Canal com duplo eixo: Receita (barra) + Margem % (bolinha)
            fig_canal = make_subplots(specs=[[{"secondary_y": True}]])

            fig_canal.add_trace(
                go.Bar(
                    x=canal["Canal_Venda"],
                    y=canal["Receita"],
                    name="Receita",
                    marker_color=CHART_COLORS[0],
                    marker_line_width=0,
                    customdata=canal["Canal_Venda"].tolist(),
                    hovertemplate="%{x}: R$ %{y:,.2f}<extra></extra>",
                ),
                secondary_y=False,
            )

            fig_canal.add_trace(
                go.Scatter(
                    x=canal["Canal_Venda"],
                    y=canal["Margem"],
                    name="Margem %",
                    mode="markers+text",
                    marker=dict(
                        size=canal["Margem"] * 1.2 + 8,
                        color=canal["Margem"].apply(
                            lambda m: "#357560" if m >= 35
                            else "#d3b73e" if m >= 25
                            else "#F87171"
                        ),
                        line=dict(width=1.5, color="#1a2a3a"),
                    ),
                    text=[f"{m:.1f}%" for m in canal["Margem"]],
                    textposition="top center",
                    textfont=dict(size=11, color="#F7FAFC"),
                    customdata=canal["Canal_Venda"].tolist(),
                    hovertemplate="%{x}: Margem %{y:.2f}%<extra></extra>",
                ),
                secondary_y=True,
            )

            fig_canal.update_layout(
                barmode="group",
                showlegend=True,
                xaxis_title="",
                yaxis_title="Receita (R$)",
                yaxis2_title="Margem (%)",
                legend=dict(
                    orientation="h",
                    yanchor="bottom", y=1.02,
                    xanchor="right", x=1,
                    font=dict(size=11, color="#AAB7C4"),
                ),
            )

            fig_canal = clean_figure(fig_canal, height=420)

            chart_block(
                "Receita e Margem por Canal",
                f"Destaque: {top_channel_name}, {top_channel_share:.1f}% da receita.",
                fig_canal,
                page_key=page_key,
                dimension="Canal_Venda",
                description=(
                    "Barras mostram volume de receita. Bolas mostram margem % "
                    "(verde ≥35%, amarelo ≥25%, vermelho <25%). Canais com muita "
                    "receita e margem baixa precisam de revisão de precificação."
                ),
            )


# Import local para compatibilidade
import pandas as pd
