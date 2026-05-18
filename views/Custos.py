"""Página: Custos e Despesas.

Análise detalhada de custos: custo total, frete, desconto médio,
composição por categoria/canal/região, evolução mensal.
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
    """Renderiza a página Custos e Despesas.

    Args:
        ctx: PageContext com todos os dados preparados.
    """
    current_total = ctx.current_total
    previous_total = ctx.previous_total
    monthly = ctx.monthly
    cat = ctx.cat
    canal = ctx.canal
    regiao = ctx.regiao
    page_key = ctx.page_key

    # ── KPIs de Custo ──

    receita = current_total.get("receita", 0)
    custo = current_total.get("custo", 0)
    lucro = current_total.get("lucro", 0)
    pedidos = current_total.get("pedidos", 0)
    frete = current_total.get("frete", 0)
    desconto_medio = current_total.get("desconto_medio", 0)
    margem = (lucro / receita * 100) if receita else 0
    custo_pct = (custo / receita * 100) if receita else 0
    frete_pct = (frete / receita * 100) if receita else 0

    prev_custo = previous_total.get("custo", 0) if previous_total else 0
    prev_receita = previous_total.get("receita", 0) if previous_total else 0
    prev_frete = previous_total.get("frete", 0) if previous_total else 0
    prev_desconto_medio = previous_total.get("desconto_medio", 0) if previous_total else 0
    prev_custo_pct = (prev_custo / prev_receita * 100) if prev_receita else 0

    kpis = [
        ("Custo Total", fmt_currency(custo), pct_change(custo, prev_custo), "período anterior"),
        ("Custo/Receita", fmt_pct(custo_pct), pct_change(custo_pct, prev_custo_pct), "período anterior"),
        ("Frete Total", fmt_currency(frete), pct_change(frete, prev_frete), "período anterior"),
        ("Frete/Receita", fmt_pct(frete_pct), None, "período anterior"),
        ("Desconto Médio", fmt_pct(desconto_medio), pct_change(desconto_medio, prev_desconto_medio), "período anterior"),
    ]

    render_kpis(kpis, per_row=5)

    st.markdown("---")

    # ── Evolução Mensal: Custo e Lucro ──

    if monthly is not None and not monthly.empty:
        fig_monthly = _make_subplots_custom(monthly)

        chart_block(
            "Custo e Lucro Mensal",
            "Barras: custo mensal. Linha: lucro mensal sobre eixo secundário.",
            fig_monthly,
            page_key=page_key,
            dimension="MesLabel",
        )

    # ── Custo por Categoria (barras) ──

    col1, col2 = st.columns(2)

    with col1:
        if cat is not None and not cat.empty:
            fig_cat = px.bar(
                cat.head(8),
                x="Categoria",
                y="Custo",
                color_discrete_sequence=[CHART_COLORS[2]],
                text="Custo",
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
                yaxis_title="Custo (R$)",
            )
            fig_cat = clean_figure(fig_cat, height=340)

            chart_block(
                "Custo por Categoria",
                "Ranking de categorias por custo total.",
                fig_cat,
                page_key=page_key,
                dimension="Categoria",
            )

    # ── Composição do Custo (donut) ──

    with col2:
        if cat is not None and not cat.empty:
            fig_comp = px.pie(
                cat,
                values="Custo",
                names="Categoria",
                color_discrete_sequence=CHART_COLORS,
                hole=0.45,
            )
            fig_comp.update_traces(
                textposition="inside",
                textinfo="percent+label",
                hovertemplate="%{label}: R$ %{value:,.2f}<extra></extra>",
                customdata=cat["Categoria"].tolist(),
            )
            fig_comp = clean_figure(fig_comp, height=340)

            chart_block(
                "Composição do Custo",
                "Participação de cada categoria no custo total.",
                fig_comp,
                page_key=page_key,
                dimension="Categoria",
            )

    # ── Custo por Canal ──

    if canal is not None and not canal.empty:
        fig_canal = px.bar(
            canal,
            x="Canal_Venda",
            y="Custo",
            color_discrete_sequence=[CHART_COLORS[3]],
            text="Custo",
        )
        fig_canal.update_traces(
            texttemplate="%{text:,.2s}",
            textposition="outside",
            hovertemplate="Canal: %{x}<br>Custo: R$ %{y:,.2f}<extra></extra>",
            customdata=canal["Canal_Venda"].tolist(),
        )
        fig_canal.update_layout(
            showlegend=False,
            xaxis_title="",
            yaxis_title="Custo (R$)",
        )
        fig_canal = clean_figure(fig_canal, height=340)

        chart_block(
            "Custo por Canal de Venda",
            "Custo total por canal de venda.",
            fig_canal,
            page_key=page_key,
            dimension="Canal_Venda",
        )

    # ── Frete e Desconto por Região ──

    if regiao is not None and not regiao.empty:
        fig_regiao = _make_subplots_bars(regiao)

        chart_block(
            "Frete e Desconto por Região",
            "Barras: frete médio. Marcadores: desconto médio (%) sobre eixo secundário.",
            fig_regiao,
            page_key=page_key,
            dimension="Regiao",
        )

    # ── Leitura Executiva ──

    section_header("📋 Leitura Executiva", "Resumo automático dos custos")

    linhas = []

    # Custo/Receita
    if custo_pct > 0:
        if custo_pct >= 80:
            linhas.append(f"🔴 **Custo/Receita em {fmt_pct(custo_pct)}** — margem sob forte pressão.")
        elif custo_pct >= 60:
            linhas.append(f"🟡 **Custo/Receita em {fmt_pct(custo_pct)}** — observar com atenção.")
        else:
            linhas.append(f"🟢 **Custo/Receita em {fmt_pct(custo_pct)}** — estrutura de custo saudável.")

    # Frete
    if frete_pct > 0:
        if frete_pct >= 15:
            linhas.append(f"🚚 **Frete/Receita em {fmt_pct(frete_pct)}** — impacto significativo na margem.")
        elif frete_pct >= 8:
            linhas.append(f"🚚 **Frete/Receita em {fmt_pct(frete_pct)}** — dentro da faixa esperada.")
        else:
            linhas.append(f"🚚 **Frete/Receita em {fmt_pct(frete_pct)}** — logística eficiente.")

    # Desconto médio
    if desconto_medio > 10:
        linhas.append(f"🏷️ **Desconto médio de {fmt_pct(desconto_medio)}** — atenção à precificação.")
    elif desconto_medio > 0:
        linhas.append(f"🏷️ **Desconto médio de {fmt_pct(desconto_medio)}** — dentro da política comercial.")

    # Variação do custo
    if prev_custo > 0 and custo > 0:
        var_custo = pct_change(custo, prev_custo)
        if var_custo is not None:
            linhas.append(f"📈 **Custo {var_custo:+.1f}% vs. período anterior.**")

    leitura = "\n\n".join(linhas) if linhas else "Sem dados suficientes para leitura executiva."

    fs = FilterState(page_key)
    if fs.has_filters:
        filtros_str = ", ".join(f"{k}: {v}" for k, v in fs.filters.items())
        leitura += f"\n\n🔍 *Dados filtrados por: {filtros_str}*"

    st.markdown(leitura)


# ── Helpers: gráficos compostos ──


def _make_subplots_custom(monthly):
    """Gráfico Custo e Lucro Mensal (barras + linha)."""
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=monthly["MesLabel"],
            y=monthly["Custo"],
            name="Custo",
            marker_color=CHART_COLORS[2],
            marker_line_width=0,
            hovertemplate="Custo: R$ %{y:,.2f}<extra></extra>",
            customdata=monthly["MesLabel"].tolist(),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=monthly["MesLabel"],
            y=monthly["Lucro"],
            name="Lucro",
            mode="lines+markers",
            line=dict(color=CHART_COLORS[1], width=2.5),
            marker=dict(size=6),
            hovertemplate="Lucro: R$ %{y:,.2f}<extra></extra>",
            yaxis="y2",
            customdata=monthly["MesLabel"].tolist(),
        )
    )

    fig.update_layout(
        barmode="group",
        showlegend=True,
        yaxis=dict(title="Custo (R$)"),
        yaxis2=dict(
            title="Lucro (R$)",
            overlaying="y",
            side="right",
            gridcolor="rgba(255,255,255,0.04)",
        ),
        xaxis_title="",
    )

    return clean_figure(fig, height=380)


def _make_subplots_bars(regiao):
    """Gráfico Frete Médio e Desconto Médio por Região (barras + marcadores)."""
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=regiao["Regiao"],
            y=regiao["Frete_Medio"],
            name="Frete Médio",
            marker_color=CHART_COLORS[0],
            marker_line_width=0,
            hovertemplate="Frete Médio: R$ %{y:,.2f}<extra></extra>",
            customdata=regiao["Regiao"].tolist(),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=regiao["Regiao"],
            y=regiao["Desconto_Medio"],
            name="Desconto Médio (%)",
            mode="markers+lines",
            marker=dict(size=10, color=CHART_COLORS[6]),
            line=dict(color=CHART_COLORS[6], width=2),
            hovertemplate="Desconto: %{y:.1f}%<extra></extra>",
            yaxis="y2",
            customdata=regiao["Regiao"].tolist(),
        )
    )

    fig.update_layout(
        showlegend=True,
        yaxis=dict(title="Frete Médio (R$)"),
        yaxis2=dict(
            title="Desconto Médio (%)",
            overlaying="y",
            side="right",
            gridcolor="rgba(255,255,255,0.04)",
        ),
        xaxis_title="",
    )

    return clean_figure(fig, height=340)