"""Página: Visão Estratégica (Receita e Crescimento).

Análise focada em tendências, crescimento e rentabilidade comparada:
1. Leitura Executiva com narrativa contextual (crescimento, margem, alertas)
2. MoM / YoY unificado com toggle (coloração positiva/negativa)
3. Região com receita e margem
4. Lucro Líquido por Canal

Todos os visuais respondem ao cross-filtering via page_key.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

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
    # MoM / YoY — Variação (Toggle Unificado)
    # ═══════════════════════════════════════

    view_mode = st.radio(
        "Variação",
        ["MoM", "YoY"],
        horizontal=True,
        key=f"var_toggle_{page_key}",
    )

    if monthly is not None and not monthly.empty:

        if view_mode == "MoM" and "MoM_Receita" in monthly.columns:
            mom_data = monthly.dropna(subset=["MoM_Receita"]).copy()

            if not mom_data.empty:
                mom_colors = [
                    CHART_COLORS[2] if v >= 0 else CHART_COLORS[6]
                    for v in mom_data["MoM_Receita"]
                ]

                fig_var = go.Figure()
                fig_var.add_trace(
                    go.Bar(
                        x=mom_data["MesLabel"],
                        y=mom_data["MoM_Receita"],
                        marker_color=mom_colors,
                        marker_line_width=0,
                        customdata=mom_data["MesLabel"].tolist(),
                        hovertemplate="%{x}: %{y:+.1f}%<extra></extra>",
                    )
                )
                fig_var.add_hline(
                    y=0, line_dash="solid", line_color="rgba(255,255,255,0.15)",
                    line_width=1,
                )
                fig_var.update_layout(
                    showlegend=False,
                    xaxis_title="",
                    yaxis_title="Variação MoM (%)",
                )
                fig_var = clean_figure(fig_var, height=380)

                avg_var = mom_data["MoM_Receita"].mean()
                pos_var = (mom_data["MoM_Receita"] > 0).sum()
                total_var = len(mom_data)

                chart_block(
                    "Variação Mês a Mês (MoM)",
                    f"Média: {avg_var:+.1f}% | {pos_var}/{total_var} meses positivos",
                    fig_var,
                    page_key=page_key,
                    dimension="MesLabel",
                    description=(
                        "Barras verdes = crescimento, vermelhas = retração. "
                        "A linha tracejada marca o zero. Detecte aceleração, "
                        "desaceleração ou reversão de tendência."
                    ),
                )

        elif view_mode == "YoY" and "Receita_YoY_Pct" in monthly.columns:
            yoy_data = monthly.dropna(subset=["Receita_YoY_Pct"]).copy()

            if not yoy_data.empty:
                yoy_colors = [
                    CHART_COLORS[2] if v >= 0 else CHART_COLORS[6]
                    for v in yoy_data["Receita_YoY_Pct"]
                ]

                fig_var = go.Figure()
                fig_var.add_trace(
                    go.Bar(
                        x=yoy_data["MesLabel"],
                        y=yoy_data["Receita_YoY_Pct"],
                        marker_color=yoy_colors,
                        marker_line_width=0,
                        customdata=yoy_data["MesLabel"].tolist(),
                        hovertemplate="%{x}: %{y:+.1f}%<extra></extra>",
                    )
                )
                fig_var.add_hline(
                    y=0, line_dash="solid", line_color="rgba(255,255,255,0.15)",
                    line_width=1,
                )
                fig_var.update_layout(
                    showlegend=False,
                    xaxis_title="",
                    yaxis_title="Variação YoY (%)",
                )
                fig_var = clean_figure(fig_var, height=380)

                avg_var = yoy_data["Receita_YoY_Pct"].mean()
                pos_var = (yoy_data["Receita_YoY_Pct"] > 0).sum()
                total_var = len(yoy_data)

                chart_block(
                    "Variação Ano a Ano (YoY)",
                    f"Média: {avg_var:+.1f}% | {pos_var}/{total_var} meses positivos",
                    fig_var,
                    page_key=page_key,
                    dimension="MesLabel",
                    description=(
                        "Comparação com o mesmo mês do ano anterior. "
                        "Barras verdes = crescimento YoY, vermelhas = retração. "
                        "Identifique tendências de longo prazo e sazonalidade."
                    ),
                )

    st.markdown("<div style='height: 24px'></div>", unsafe_allow_html=True)

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
    """Renderiza leitura executiva em formato narrativo (2-3 frases)."""

    fs = FilterState(page_key)

    # ── Constrói frases narrativas ──
    frases = []

    # 1. Crescimento da receita e canal mais lucrativo
    if prev_receita and prev_receita > 0:
        var = ((receita - prev_receita) / prev_receita) * 100
        direcao = "cresceu" if var >= 0 else "recuou"

        canal_nome = ""
        if canal is not None and not canal.empty:
            top_canal = canal.sort_values("Lucro_Liquido", ascending=False).iloc[0]
            canal_nome = top_canal["Canal_Venda"]

        if canal_nome:
            frases.append(
                f"Receita {direcao} <b>{var:+.1f}%</b> vs. período anterior, "
                f"puxada pelo canal <b>{canal_nome}</b>."
            )
        else:
            frases.append(
                f"Receita {direcao} <b>{var:+.1f}%</b> vs. período anterior."
            )
    else:
        frases.append("Receita sem base comparável no período.")

    # 2. Margem e região de destaque
    regiao_nome = ""
    regiao_margem = 0
    if regiao is not None and not regiao.empty:
        top_reg = regiao.sort_values("Margem", ascending=False).iloc[0]
        regiao_nome = top_reg["Regiao"]
        regiao_margem = top_reg["Margem"]

    margem_status = (
        "saudável" if margem >= 35
        else "sob pressão" if margem >= 25
        else "crítica"
    )

    if regiao_nome:
        frases.append(
            f"Margem de <b>{margem:.1f}%</b> ({margem_status}) — "
            f"<b>{regiao_nome}</b> lidera com {regiao_margem:.1f}%."
        )
    else:
        frases.append(
            f"Margem de <b>{margem:.1f}%</b> — situação {margem_status}."
        )

    # 3. Alerta contextual (receita subindo com margem baixa)
    if prev_receita and prev_receita > 0:
        var = ((receita - prev_receita) / prev_receita) * 100
        if var > 5 and margem < 30:
            frases.append(
                "⚠️ Atenção: receita subindo com margem comprimida — "
                "investigar frete, descontos ou mix de canais."
            )

    # ── Renderiza HTML ──
    html = '<div class="exec-card">'

    html += '<div class="exec-header">'
    html += '<span class="exec-header-icon">📋</span>'
    html += '<span class="exec-header-title">Leitura Executiva</span>'
    html += '<span class="exec-header-badge">Narrativa</span>'
    html += '</div>'

    html += '<div class="exec-narrative">'
    for frase in frases:
        html += f"<p>{frase}</p>"
    html += '</div>'

    if fs.has_filters:
        filtros_str = ", ".join(f"{k}: {v}" for k, v in fs.filters.items())
        html += f'<div class="exec-footer">🔍 Dados filtrados por: {filtros_str}</div>'

    html += '</div>'

    st.markdown(html, unsafe_allow_html=True)
