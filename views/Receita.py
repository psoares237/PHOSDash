"""Página: Visão Estratégica (Receita e Crescimento).

Análise focada em tendências, crescimento e rentabilidade comparada:
1. Evolução (receita + acumulado + margem)
2. MoM com coloração positiva/negativa
3. Região com receita e margem
4. Lucro Líquido por Canal

Todos os visuais respondem ao cross-filtering via page_key.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from components.ui import render_kpis, chart_block
from components.charts import clean_figure, CHART_COLORS
from state.filters import FilterState
from utils.formatters import fmt_currency, fmt_int, fmt_pct, pct_change


def render(ctx):
    """Renderiza a página Visão Estratégica."""

    current_total = ctx.current_total
    previous_total = ctx.previous_total
    monthly = ctx.monthly
    regiao = ctx.regiao
    canal = ctx.canal
    page_key = ctx.page_key

    receita = current_total.get("receita", 0)
    lucro = current_total.get("lucro", 0)
    pedidos = current_total.get("pedidos", 0)
    ticket = (receita / pedidos) if pedidos else 0
    margem = (lucro / receita * 100) if receita else 0

    prev_receita = previous_total.get("receita", 0) if previous_total else 0
    prev_lucro = previous_total.get("lucro", 0) if previous_total else 0
    prev_pedidos = previous_total.get("pedidos", 0) if previous_total else 0

    # ── KPIs ──
    kpis = [
        ("Receita Total", fmt_currency(receita), pct_change(receita, prev_receita),
         "período anterior"),
        ("Lucro Total", fmt_currency(lucro), pct_change(lucro, prev_lucro),
         "período anterior"),
        ("Margem", fmt_pct(margem), None,
         "período anterior"),
        ("Ticket Médio", fmt_currency(ticket), None,
         "período anterior"),
        ("Total de Pedidos", fmt_int(pedidos), pct_change(pedidos, prev_pedidos),
         "período anterior"),
    ]

    render_kpis(kpis, per_row=5)

    st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)

    # ── Leitura Executiva ──
    _render_leitura(ctx, receita, prev_receita, lucro, margem, canal, regiao, page_key)

    st.markdown("<div style='height: 24px'></div>", unsafe_allow_html=True)

    # ═══════════════════════════════════════
    # LINHA 1 — Evolução + MoM (2 colunas)
    # ═══════════════════════════════════════

    col1, col2 = st.columns(2)

    with col1:
        if monthly is not None and not monthly.empty:
            fig_monthly = go.Figure()

            # Barras: Receita mensal
            fig_monthly.add_trace(
                go.Bar(
                    x=monthly["MesLabel"],
                    y=monthly["Receita"],
                    name="Receita Mensal",
                    marker_color=CHART_COLORS[0],
                    marker_line_width=0,
                    customdata=monthly["MesLabel"].tolist(),
                    hovertemplate="Receita: R$ %{y:,.2f}<extra></extra>",
                )
            )

            # Linha: Acumulado
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

            # Linha tracejada: Margem %
            fig_monthly.add_trace(
                go.Scatter(
                    x=monthly["MesLabel"],
                    y=monthly["Margem"],
                    name="Margem %",
                    mode="lines",
                    line=dict(color=CHART_COLORS[5], width=1.5, dash="dot"),
                    yaxis="y2",
                    customdata=monthly["MesLabel"].tolist(),
                    hovertemplate="Margem: %{y:.1f}%<extra></extra>",
                )
            )

            fig_monthly.update_layout(
                barmode="group",
                showlegend=True,
                yaxis=dict(title="Receita Mensal"),
                yaxis2=dict(
                    title="Acumulado / Margem",
                    overlaying="y",
                    side="right",
                    gridcolor="rgba(255,255,255,0.04)",
                ),
                xaxis_title="",
                legend=dict(
                    orientation="h",
                    yanchor="bottom", y=1.02,
                    xanchor="right", x=1,
                    font=dict(size=11, color="#AAB7C4"),
                ),
            )

            fig_monthly = clean_figure(fig_monthly, height=380)

            chart_block(
                "Evolução da Receita",
                "Receita mensal, acumulado e margem.",
                fig_monthly,
                page_key=page_key,
                dimension="MesLabel",
                description=(
                    "Visão completa da trajetória: receita (barras), acumulado no ano "
                    "(linha contínua) e margem (tracejada). Alerta: margem caindo com "
                    "receita subindo indica desconto ou custo subindo."
                ),
            )

    with col2:
        if monthly is not None and not monthly.empty and "MoM_Receita" in monthly.columns:
            mom_data = monthly.dropna(subset=["MoM_Receita"]).copy()

            if not mom_data.empty:
                # Cores por valor positivo/negativo
                mom_colors = [
                    CHART_COLORS[2] if v >= 0 else CHART_COLORS[6]
                    for v in mom_data["MoM_Receita"]
                ]

                fig_mom = go.Figure()

                fig_mom.add_trace(
                    go.Bar(
                        x=mom_data["MesLabel"],
                        y=mom_data["MoM_Receita"],
                        marker_color=mom_colors,
                        marker_line_width=0,
                        customdata=mom_data["MesLabel"].tolist(),
                        hovertemplate="%{x}: %{y:+.1f}%<extra></extra>",
                    )
                )

                # Linha de referência zero
                fig_mom.add_hline(
                    y=0, line_dash="solid", line_color="rgba(255,255,255,0.15)",
                    line_width=1,
                )

                fig_mom.update_layout(
                    showlegend=False,
                    xaxis_title="",
                    yaxis_title="Variação MoM (%)",
                )

                fig_mom = clean_figure(fig_mom, height=380)

                # Estatísticas
                avg_mom = mom_data["MoM_Receita"].mean()
                pos_months = (mom_data["MoM_Receita"] > 0).sum()
                total_months = len(mom_data)

                chart_block(
                    "Variação Mês a Mês (MoM)",
                    f"Média: {avg_mom:+.1f}% | {pos_months}/{total_months} meses positivos",
                    fig_mom,
                    page_key=page_key,
                    dimension="MesLabel",
                    description=(
                        "Barras verdes = crescimento, vermelhas = retração. "
                        "A linha tracejada marca o zero. Detecte aceleração, "
                        "desaceleração ou reversão de tendência."
                    ),
                )

    # ═══════════════════════════════════════
    # YoY — Variação Year-over-Year
    # ═══════════════════════════════════════

    if monthly is not None and not monthly.empty and "Receita_YoY_Pct" in monthly.columns:
        yoy_data = monthly.dropna(subset=["Receita_YoY_Pct"]).copy()

        if not yoy_data.empty:
            yoy_colors = [
                CHART_COLORS[2] if v >= 0 else CHART_COLORS[6]
                for v in yoy_data["Receita_YoY_Pct"]
            ]

            fig_yoy = go.Figure()

            fig_yoy.add_trace(
                go.Bar(
                    x=yoy_data["MesLabel"],
                    y=yoy_data["Receita_YoY_Pct"],
                    marker_color=yoy_colors,
                    marker_line_width=0,
                    customdata=yoy_data["MesLabel"].tolist(),
                    hovertemplate="%{x}: %{y:+.1f}%<extra></extra>",
                )
            )

            fig_yoy.add_hline(
                y=0, line_dash="solid", line_color="rgba(255,255,255,0.15)",
                line_width=1,
            )

            fig_yoy.update_layout(
                showlegend=False,
                xaxis_title="",
                yaxis_title="Variação YoY (%)",
            )

            fig_yoy = clean_figure(fig_yoy, height=380)

            avg_yoy = yoy_data["Receita_YoY_Pct"].mean()
            pos_yoy = (yoy_data["Receita_YoY_Pct"] > 0).sum()
            total_yoy = len(yoy_data)

            chart_block(
                "Variação Ano a Ano (YoY)",
                f"Média: {avg_yoy:+.1f}% | {pos_yoy}/{total_yoy} meses positivos",
                fig_yoy,
                page_key=page_key,
                dimension="MesLabel",
                description=(
                    "Comparação com o mesmo mês do ano anterior. "
                    "Barras verdes = crescimento YoY, vermelhas = retração. "
                    "Identifique tendências de longo prazo e sazonalidade."
                ),
            )

    # ═══════════════════════════════════════
    # LINHA 2 — Região + Lucro Líquido por Canal (2 colunas)
    # ═══════════════════════════════════════

    col3, col4 = st.columns(2)

    with col3:
        if regiao is not None and not regiao.empty:
            fig_reg = px.bar(
                regiao,
                x="Regiao",
                y="Receita",
                color="Margem",
                color_continuous_scale=[
                    "#F87171",
                    "#d3b73e",
                    "#357560",
                ],
                text="Receita",
            )

            fig_reg.update_traces(
                texttemplate="R$ %{text:,.2s}",
                textposition="outside",
                customdata=regiao["Regiao"].tolist(),
                hovertemplate=(
                    "%{x}<br>Receita: R$ %{y:,.2f}<br>"
                    "Margem: %{marker.color:.1f}%<extra></extra>"
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

            fig_reg.update_layout(
                showlegend=False,
                xaxis_title="",
                yaxis_title="Receita (R$)",
            )

            fig_reg = clean_figure(fig_reg, height=380)

            # Top região
            top_reg = regiao.iloc[0]["Regiao"] if not regiao.empty else "—"

            chart_block(
                "Receita e Margem por Região",
                f"Destaque: {top_reg} — cor indica rentabilidade.",
                fig_reg,
                page_key=page_key,
                dimension="Regiao",
                description=(
                    "Receita (tamanho da barra) × Margem (cor). "
                    "Regiões com muita receita e margem baixa indicam "
                    "pressão de custo ou frete elevado na operação local."
                ),
            )

    with col4:
        if canal is not None and not canal.empty:
            # Ordenar por Lucro Líquido (mais relevante que receita bruta)
            canal_ll = canal.sort_values("Lucro_Liquido", ascending=False)

            fig_ll = px.bar(
                canal_ll,
                x="Canal_Venda",
                y="Lucro_Liquido",
                color="Margem",
                color_continuous_scale=[
                    "#F87171",
                    "#d3b73e",
                    "#357560",
                ],
                text="Lucro_Liquido",
            )

            fig_ll.update_traces(
                texttemplate="R$ %{text:,.2s}",
                textposition="outside",
                customdata=canal_ll["Canal_Venda"].tolist(),
                hovertemplate=(
                    "%{x}<br>Lucro Líquido: R$ %{y:,.2f}<br>"
                    "Margem: %{marker.color:.1f}%<extra></extra>"
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

            fig_ll.update_layout(
                showlegend=False,
                xaxis_title="",
                yaxis_title="Lucro Líquido (R$)",
            )

            fig_ll = clean_figure(fig_ll, height=380)

            top_canal_ll = canal_ll.iloc[0]["Canal_Venda"] if not canal_ll.empty else "—"
            top_ll_val = canal_ll.iloc[0]["Lucro_Liquido"] if not canal_ll.empty else 0

            chart_block(
                "Lucro Líquido por Canal",
                f"Destaque: {top_canal_ll} — {fmt_currency(top_ll_val)} líquido.",
                fig_ll,
                page_key=page_key,
                dimension="Canal_Venda",
                description=(
                    "Lucro após frete por canal. Canais com pouco lucro líquido "
                    "apesar de alta receita têm frete ou custo elevado — candidatos "
                    "a renegociação logística ou revisão de preço."
                ),
            )


def _render_leitura(ctx, receita, prev_receita, lucro, margem, canal, regiao, page_key):
    """Renderiza leitura executiva aprimorada da página Estratégica."""

    fs = FilterState(page_key)

    # Crescimento
    crescimento_dot = "info"
    crescimento_label = "Sem base comparável"
    if prev_receita > 0:
        var = pct_change(receita, prev_receita)
        if var is not None:
            if var >= 10:
                crescimento_dot = "good"
            elif var >= 0:
                crescimento_dot = "info"
            elif var >= -10:
                crescimento_dot = "warn"
            else:
                crescimento_dot = "bad"
            crescimento_label = f"Receita {var:+.1f}% vs. anterior"

    # Margem status
    margem_dot = "good" if margem >= 35 else "warn" if margem >= 25 else "bad"
    margem_label = f"Margem {margem:.1f}%"

    # Canal mais lucrativo
    canal_msg = "—"
    if canal is not None and not canal.empty:
        top_canal = canal.sort_values("Lucro_Liquido", ascending=False).iloc[0]
        canal_msg = (
            f"{top_canal['Canal_Venda']} — "
            f"{fmt_currency(top_canal['Lucro_Liquido'])} líquido"
        )

    # Região com maior margem
    regiao_msg = "—"
    if regiao is not None and not regiao.empty:
        top_margem_reg = regiao.sort_values("Margem", ascending=False).iloc[0]
        regiao_msg = (
            f"{top_margem_reg['Regiao']} — "
            f"margem {top_margem_reg['Margem']:.1f}%"
        )

    html = '<div class="exec-card">'

    html += '<div class="exec-header">'
    html += '<span class="exec-header-icon">📋</span>'
    html += '<span class="exec-header-title">Leitura Executiva</span>'
    html += '<span class="exec-header-badge">Crescimento</span>'
    html += '</div>'

    html += '<div class="exec-metric">'
    html += f'<span class="exec-dot {crescimento_dot}"></span>'
    html += f'<span class="exec-metric-label">Crescimento vs. anterior</span>'
    html += f'<span class="exec-metric-value">{crescimento_label}</span>'
    html += '</div>'

    html += '<div class="exec-metric">'
    html += f'<span class="exec-dot {margem_dot}"></span>'
    html += f'<span class="exec-metric-label">Rentabilidade</span>'
    html += f'<span class="exec-metric-value">{margem_label}</span>'
    html += '</div>'

    html += '<div class="exec-metric">'
    html += '<span class="exec-dot info"></span>'
    html += '<span class="exec-metric-label">Canal mais lucrativo</span>'
    html += f'<span class="exec-metric-value">{canal_msg}</span>'
    html += '</div>'

    html += '<div class="exec-metric">'
    html += '<span class="exec-dot info"></span>'
    html += '<span class="exec-metric-label">Região de maior margem</span>'
    html += f'<span class="exec-metric-value">{regiao_msg}</span>'
    html += '</div>'

    if fs.has_filters:
        filtros_str = ", ".join(f"{k}: {v}" for k, v in fs.filters.items())
        html += f'<div class="exec-footer">🔍 Dados filtrados por: {filtros_str}</div>'

    html += '</div>'

    st.markdown(html, unsafe_allow_html=True)
