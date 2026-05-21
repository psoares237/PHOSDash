"""Página: Visão Financeira (FinOps).

KPIs de segunda linha, análise de rentabilidade, concentração,
correlação desconto-margem e projeções. Visão de CFO.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from components.ui import render_kpis, chart_block, section_header
from components.charts import clean_figure, CHART_COLORS
from state.filters import FilterState
from utils.formatters import fmt_currency, fmt_int, fmt_pct, pct_change
from services.kpi_service import (
    hhi_by_dimensions, desconto_margem_correlation,
    run_rate_projection, forma_pagamento_analysis,
    sazonalidade_analysis, margem_contribuicao,
    produto_margem_analysis,
)
from services.analytics_service import grouped_sales


def render(ctx):
    """Renderiza a página Visão Financeira."""

    current_total = ctx.current_total
    previous_total = ctx.previous_total
    monthly = ctx.monthly
    df = ctx.current_df
    page_key = ctx.page_key

    receita = current_total.get("receita", 0)
    lucro = current_total.get("lucro", 0)
    custo = current_total.get("custo", 0)
    frete_total = current_total.get("frete", 0)
    pedidos = current_total.get("pedidos", 0)
    desconto_medio = current_total.get("desconto_medio", 0)

    prev_receita = previous_total.get("receita", 0) if previous_total else 0

    # Margem de Contribuição
    margem_contrib = lucro - frete_total
    margem_contrib_pct = (margem_contrib / receita * 100) if receita else 0
    frete_pct = (frete_total / receita * 100) if receita else 0

    # Run Rate — com e sem ajuste sazonal
    saz = sazonalidade_analysis(monthly)
    proj = run_rate_projection(monthly, saz)
    tendencia_icon = {"crescimento": "📈", "queda": "📉", "estável": "➡️"}.get(
        proj["tendencia"], "➡️"
    )

    # ── KPIs ──
    kpis = [
        ("Margem Contribuição", fmt_currency(margem_contrib), None,
         "após frete"),
        ("Margem Contrib. %", fmt_pct(margem_contrib_pct), None,
         "da receita"),
        ("Run Rate (12m)", fmt_currency(proj["run_rate_12m"]), None,
         f"tendência: {proj['tendencia']}"),
        ("Frete % Receita", fmt_pct(frete_pct), None,
         "custo logístico"),
        ("Desconto Médio", fmt_pct(desconto_medio), None,
         "sobre vendas"),
    ]

    render_kpis(kpis, per_row=5)
    st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)

    # ── Leitura Executiva ──
    _render_leitura_financeira(ctx, receita, prev_receita, margem_contrib_pct,
                                frete_pct, desconto_medio, proj, page_key)

    st.markdown("<div style='height: 24px'></div>", unsafe_allow_html=True)

    # ═══════════════════════════════════════
    # LINHA 1 — Margem por Categoria + Forma de Pagamento
    # ═══════════════════════════════════════

    col1, col2 = st.columns(2)

    with col1:
        if df is not None and not df.empty and "Categoria" in df.columns:
            mc_data = margem_contribuicao(df)
            mc_agg = (
                mc_data.groupby("Categoria", as_index=False)
                .agg(
                    Margem_Contrib=("Margem_Contrib", "sum"),
                    Receita=("Receita", "sum"),
                )
                .sort_values("Margem_Contrib", ascending=False)
            )
            mc_agg["Margem_Contrib_Pct"] = (
                mc_agg["Margem_Contrib"] / mc_agg["Receita"] * 100
            )

            fig_mc = px.bar(
                mc_agg.head(8),
                x="Categoria",
                y="Margem_Contrib_Pct",
                color_discrete_sequence=[CHART_COLORS[2]],
                text="Margem_Contrib_Pct",
            )

            fig_mc.update_traces(
                texttemplate="%{text:.1f}%",
                textposition="outside",
                customdata=mc_agg.head(8)["Categoria"].tolist(),
                hovertemplate="%{x}: %{y:.2f}% de margem<br>Receita: R$ %{customdata[0]}<extra></extra>",
            )

            fig_mc.update_layout(
                showlegend=False,
                xaxis_title="",
                yaxis_title="Margem Contrib. (%)",
            )

            fig_mc = clean_figure(fig_mc, height=380)

            chart_block(
                "Margem de Contribuição por Categoria",
                f"Média geral: {margem_contrib_pct:.1f}% — após frete.",
                fig_mc,
                page_key=page_key,
                dimension="Categoria",
                description=(
                    "Mostra quais categorias entregam maior retorno operacional, "
                    "considerando custo do produto e frete. Categorias com margem "
                    "baixa são candidatas a revisão de preço ou renegociação de frete."
                ),
            )

    with col2:
        if df is not None and not df.empty:
            pag_df = forma_pagamento_analysis(df)

            if not pag_df.empty:
                fig_pag = px.pie(
                    pag_df,
                    values="Receita",
                    names="Forma_Pagamento",
                    color_discrete_sequence=CHART_COLORS,
                    hole=0.45,
                )

                fig_pag.update_traces(
                    textposition="inside",
                    textinfo="percent+label",
                    customdata=pag_df["Forma_Pagamento"].tolist(),
                    hovertemplate=(
                        "%{label}: R$ %{value:,.2f}<br>"
                        "Margem: %{customdata[0]}<extra></extra>"
                    ),
                )

                fig_pag = clean_figure(fig_pag, height=380)

                chart_block(
                    "Receita por Forma de Pagamento",
                    "Distribuição e margem por meio de pagamento.",
                    fig_pag,
                    page_key=page_key,
                    dimension="Forma_Pagamento",
                    description=(
                        "Permite avaliar se há diferença de rentabilidade entre "
                        "formas de pagamento (ex: Pix vs Cartão) e se a política "
                        "de descontos por modalidade afeta a margem."
                    ),
                )

    # ═══════════════════════════════════════
    # LINHA 2 — Correlação + Frete por Canal
    # ═══════════════════════════════════════

    col3, col4 = st.columns(2)

    with col3:
        if df is not None and not df.empty:
            corr = desconto_margem_correlation(df)
            canais_df = corr["canais"]

            if not canais_df.empty:
                fig_corr = px.scatter(
                    canais_df,
                    x="Desconto_Medio",
                    y="Margem_Media",
                    size="Receita",
                    text=canais_df.index,
                    color_discrete_sequence=[CHART_COLORS[0]],
                )

                fig_corr.update_traces(
                    textposition="top center",
                    marker=dict(opacity=0.75, line=dict(width=1, color="#2c3e50")),
                    hovertemplate=(
                        "Desconto Médio: %{x:.2f}%<br>"
                        "Margem: %{y:.2f}%<br>"
                        "Receita: R$ %{marker.size:,.2f}<extra></extra>"
                    ),
                )

                fig_corr.update_layout(
                    showlegend=False,
                    xaxis_title="Desconto Médio (%)",
                    yaxis_title="Margem Média (%)",
                )

                fig_corr = clean_figure(fig_corr, height=380)

                chart_block(
                    "Correlação: Desconto × Margem",
                    f"r = {corr['global_r']:.2f} — {corr['insight'][:80]}...",
                    fig_corr,
                    description=(
                        "Cada ponto = 1 pedido. Correlação negativa sugere que "
                        "descontos maiores reduzem a margem. Bolhas à direita "
                        "e abaixo indicam canais com alto desconto e baixa margem — "
                        "candidatos a otimização comercial."
                    ),
                )

    with col4:
        if df is not None and not df.empty and "Canal_Venda" in df.columns:
            canal_agg = grouped_sales(df, "Canal_Venda")

            if not canal_agg.empty:
                canal_agg["Frete_Pct"] = (
                    canal_agg["Frete"] / canal_agg["Receita"] * 100
                )

                fig_frete = px.bar(
                    canal_agg.sort_values("Frete_Pct", ascending=False).head(8),
                    x="Canal_Venda",
                    y="Frete_Pct",
                    color_discrete_sequence=[CHART_COLORS[3]],
                    text="Frete_Pct",
                )

                fig_frete.update_traces(
                    texttemplate="%{text:.1f}%",
                    textposition="outside",
                    customdata=canal_agg.head(8)["Canal_Venda"].tolist(),
                    hovertemplate="%{x}: %{y:.2f}% da receita em frete<extra></extra>",
                )

                fig_frete.update_layout(
                    showlegend=False,
                    xaxis_title="",
                    yaxis_title="Frete (% da Receita)",
                )

                fig_frete = clean_figure(fig_frete, height=380)

                chart_block(
                    "Frete como % da Receita por Canal",
                    f"Média geral: {frete_pct:.1f}% da receita.",
                    fig_frete,
                    page_key=page_key,
                    dimension="Canal_Venda",
                    description=(
                        "Canais com frete acima de 10% da receita merecem atenção. "
                        "Avalie renegociação com transportadoras ou repasse ao cliente."
                    ),
                )

    # ═══════════════════════════════════════
    # LINHA 3 — HHI Concentração + Sazonalidade
    # ═══════════════════════════════════════

    col5, col6 = st.columns(2)

    with col5:
        if df is not None and not df.empty:
            hhi_dims = ["Categoria", "Canal_Venda", "Regiao", "Vendedor"]
            hhi = hhi_by_dimensions(df, hhi_dims)

            if hhi:
                hhi_df = (
                    pd.DataFrame(
                        [(k, v) for k, v in hhi.items()],
                        columns=["Dimensão", "HHI"],
                    )
                    .sort_values("HHI", ascending=True)
                )

                # Cores por faixa
                colors = []
                for v in hhi_df["HHI"]:
                    if v > 2500:
                        colors.append("#F87171")  # Vermelho — alta concentração
                    elif v > 1500:
                        colors.append("#d3b73e")  # Dourado — moderada
                    else:
                        colors.append("#357560")  # Verde — saudável

                fig_hhi = px.bar(
                    hhi_df,
                    x="HHI",
                    y="Dimensão",
                    orientation="h",
                    color_discrete_sequence=[CHART_COLORS[0]],
                )

                fig_hhi.update_traces(
                    marker_color=colors,
                    text=[f"{v:.0f}" for v in hhi_df["HHI"]],
                    textposition="outside",
                    hovertemplate="HHI: %{x:.0f}<extra></extra>",
                )

                fig_hhi.add_vline(
                    x=1500, line_dash="dash", line_color="#d3b73e",
                    annotation_text="moderado",
                )
                fig_hhi.add_vline(
                    x=2500, line_dash="dash", line_color="#F87171",
                    annotation_text="alto",
                )

                fig_hhi.update_layout(
                    showlegend=False,
                    xaxis_title="Índice HHI",
                    yaxis_title="",
                )

                fig_hhi = clean_figure(fig_hhi, height=380)

                chart_block(
                    "Concentração de Receita (HHI)",
                    "Índice Herfindahl-Hirschman por dimensão.",
                    fig_hhi,
                    description=(
                        "HHI < 1500: diversificado (verde). "
                        "1500-2500: moderado (amarelo). "
                        "> 2500: concentrado (vermelho) — risco de dependência. "
                        "Priorize ações para reduzir concentração nas dimensões em vermelho."
                    ),
                )

    with col6:
        if monthly is not None and not monthly.empty and saz is not None and not saz.empty:
                fig_saz = go.Figure()

                fig_saz.add_trace(
                    go.Scatter(
                        x=saz["MesNome"],
                        y=saz["Receita_Media"],
                        mode="lines+markers",
                        name="Média",
                        line=dict(color=CHART_COLORS[0], width=2.5),
                        marker=dict(size=8),
                        customdata=saz["MesNome"].tolist(),
                        hovertemplate="Mês: %{x} | Receita Média: R$ %{y:,.2f}<extra></extra>",
                    )
                )

                fig_saz.add_trace(
                    go.Scatter(
                        x=saz["MesNome"],
                        y=saz["Receita_Media"] + saz["Desvio_Padrao"],
                        mode="lines",
                        name="+1 desvio",
                        line=dict(color=CHART_COLORS[5], width=1, dash="dot"),
                        hovertemplate="+1σ: R$ %{y:,.2f}<extra></extra>",
                    )
                )

                fig_saz.add_trace(
                    go.Scatter(
                        x=saz["MesNome"],
                        y=saz["Receita_Media"] - saz["Desvio_Padrao"],
                        mode="lines",
                        name="-1 desvio",
                        line=dict(color=CHART_COLORS[5], width=1, dash="dot"),
                        fill="tonexty",
                        fillcolor="rgba(96,165,250,0.1)",
                        hovertemplate="-1σ: R$ %{y:,.2f}<extra></extra>",
                    )
                )

                fig_saz.update_layout(
                    showlegend=False,
                    xaxis_title="",
                    yaxis_title="Receita Média (R$)",
                )

                fig_saz = clean_figure(fig_saz, height=380)

                chart_block(
                    "Sazonalidade da Receita",
                    "Padrão mensal com desvio padrão.",
                    fig_saz,
                    description=(
                        "Identifica meses de pico e vale ao longo do ano. "
                        "Use para planejar estoque, campanhas e metas mensais. "
                        "A faixa mostra a dispersão histórica (±1 desvio padrão)."
                    ),
                )

    # ═══════════════════════════════════════
    # LINHA 3.5 — Run Rate: Simples vs Ajustado
    # ═══════════════════════════════════════

    if proj.get("tem_sazonalidade"):
        st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)

        rr_df = pd.DataFrame({
            "Período": ["3 meses", "6 meses", "12 meses"],
            "Projeção Simples": [
                proj["run_rate_3m"],
                proj["run_rate_6m"],
                proj["run_rate_12m"],
            ],
            "Projeção Ajustada": [
                proj["run_rate_3m_ajustado"],
                proj["run_rate_6m_ajustado"],
                proj["run_rate_12m_ajustado"],
            ],
        })

        fig_rr = go.Figure()

        fig_rr.add_trace(
            go.Scatter(
                x=rr_df["Período"],
                y=rr_df["Projeção Simples"],
                mode="lines+markers",
                name="Projeção Simples",
                line=dict(color=CHART_COLORS[0], width=3),
                marker=dict(size=10, symbol="circle"),
                hovertemplate="Simples (%{x}): %{y:$,.2f}<extra></extra>",
            )
        )

        fig_rr.add_trace(
            go.Scatter(
                x=rr_df["Período"],
                y=rr_df["Projeção Ajustada"],
                mode="lines+markers",
                name="Projeção Ajustada",
                line=dict(color=CHART_COLORS[6], width=3, dash="dash"),
                marker=dict(size=10, symbol="diamond"),
                hovertemplate="Ajustada (%{x}): %{y:$,.2f}<extra></extra>",
            )
        )

        # Diferença percentual anotada em cada ponto
        for i, row in rr_df.iterrows():
            diff = (
                (row["Projeção Ajustada"] - row["Projeção Simples"])
                / row["Projeção Simples"] * 100
                if row["Projeção Simples"]
                else 0
            )
            fig_rr.add_annotation(
                x=row["Período"],
                y=max(row["Projeção Simples"], row["Projeção Ajustada"]),
                text=f"{diff:+.1f}%",
                showarrow=False,
                yshift=25,
                font=dict(
                    size=11,
                    color="#357560" if diff > 0 else "#F87171" if diff < 0 else "#AAB7C4",
                ),
            )

        fig_rr.update_layout(
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
            ),
            xaxis_title="",
            yaxis_title="Receita Anual Projetada (R$)",
            hovermode="x unified",
        )

        fig_rr = clean_figure(fig_rr, height=380)

        st.caption(
            "Run Rate Projetado: média diária × dias restantes. "
            "Run Rate Ajustado: projeção com sazonalidade "
            "(receita dessazonalizada antes da projeção)."
        )

        chart_block(
            "Run Rate: Simples vs Ajustado (Sazonal)",
            (
                proj.get("insight", "")
                if proj.get("insight")
                else "Comparação entre projeção com média simples e com ajuste sazonal."
            ),
            fig_rr,
            description=(
                "A projeção simples usa a média móvel dos últimos meses. "
                "A projeção ajustada remove o efeito sazonal de cada mês "
                "(divide a receita pelo fator sazonal do mês) antes de projetar. "
                "Diferenças significativas indicam que a sazonalidade está "
                "distorcendo a projeção baseada em média simples."
            ),
        )

    # ═══════════════════════════════════════
    # LINHA 4 — Pareto de Produtos (80/20)
    # ═══════════════════════════════════════

    if df is not None and not df.empty and "Produto" in df.columns:
        pareto_df = grouped_sales(df, "Produto").head(30)

        if not pareto_df.empty:
            total_receita = pareto_df["Receita"].sum()
            pareto_df["Pct_Receita"] = pareto_df["Receita"] / total_receita * 100
            pareto_df["Cumulativo"] = pareto_df["Pct_Receita"].cumsum()
            pareto_df["Pareto_80"] = pareto_df["Cumulativo"] <= 80

            top_80_count = int(pareto_df["Pareto_80"].sum())
            top_20_count = max(int(len(pareto_df) * 0.2), 1)
            top_20_pct = pareto_df.head(top_20_count)["Pct_Receita"].sum()

            fig_pareto = go.Figure()

            # Barras com destaque para produtos dentro da faixa 80%
            bar_colors = [
                CHART_COLORS[0] if v else "#4a6a85"
                for v in pareto_df["Pareto_80"]
            ]

            fig_pareto.add_trace(
                go.Bar(
                    x=pareto_df["Produto"],
                    y=pareto_df["Receita"],
                    name="Receita",
                    marker_color=bar_colors,
                    customdata=pareto_df["Pct_Receita"],
                    hovertemplate=(
                        "%{x}: R$ %{y:,.2f}<br>"
                        "%{customdata:.2f}% da receita<extra></extra>"
                    ),
                )
            )

            # Linha acumulada no eixo secundário
            fig_pareto.add_trace(
                go.Scatter(
                    x=pareto_df["Produto"],
                    y=pareto_df["Cumulativo"],
                    name="% Acumulado",
                    mode="lines+markers",
                    line=dict(color=CHART_COLORS[6], width=2.2),
                    marker=dict(size=5, color=CHART_COLORS[6]),
                    yaxis="y2",
                    hovertemplate="%{x}: %{y:.2f}% acumulado<extra></extra>",
                )
            )

            # Linha de referência 80%
            fig_pareto.add_hline(
                y=80,
                line_dash="dash",
                line_color=CHART_COLORS[1],
                annotation_text="80%",
                annotation_position="right",
            )

            # Anotação do percentual exato dos top 20%
            fig_pareto.add_annotation(
                x=0.98,
                y=0.95,
                xref="paper",
                yref="paper",
                text=f"Top 20% produtos = {top_20_pct:.1f}% da receita",
                showarrow=False,
                font=dict(color=CHART_COLORS[1], size=12),
                bgcolor="rgba(15,23,42,0.85)",
                bordercolor=CHART_COLORS[1],
                borderwidth=1,
                borderpad=8,
            )

            fig_pareto.update_layout(
                showlegend=False,
                xaxis_title="",
                yaxis_title="Receita (R$)",
                yaxis2=dict(
                    title="% Acumulado",
                    overlaying="y",
                    side="right",
                    range=[0, 105],
                    tickfont=dict(color="#AAB7C4"),
                    gridcolor="rgba(255,255,255,0.03)",
                ),
                hovermode="x unified",
            )

            fig_pareto = clean_figure(fig_pareto, height=440)

            chart_block(
                "Pareto de Produtos — Regra 80/20",
                f"{top_80_count} produtos concentram 80% da receita ({len(pareto_df)} analisados).",
                fig_pareto,
                page_key=page_key,
                dimension="Produto",
                description=(
                    "O Princípio de Pareto revela que poucos produtos geram a maior "
                    "parte da receita. Produtos em azul compõem os 80% acumulados — "
                    "priorize estoque, marketing e negociação para este grupo. Produtos "
                    "à direita da linha de 80% são candidatos a revisão de sortimento "
                    "ou descontinuação."
                ),
            )

    # ═══════════════════════════════════════
    # LINHA 5 — Margem Unitária por Produto (Preço × Custo)
    # ═══════════════════════════════════════

    if df is not None and not df.empty and "Produto" in df.columns:
        prod_margem = produto_margem_analysis(df)

        if not prod_margem.empty:
            col7, col8 = st.columns(2)

            # ── Top 10 menor margem (risco) ──
            risco_df = prod_margem.tail(10).sort_values("Margem_Pct", ascending=True)
            n_neg = int((risco_df["Margem_Pct"] < 0).sum())

            with col7:
                risco_colors = [
                    "#F87171" if v < 0 else "#d3b73e"
                    for v in risco_df["Margem_Pct"]
                ]

                fig_risco = px.bar(
                    risco_df,
                    x="Margem_Pct",
                    y="Produto",
                    orientation="h",
                    color_discrete_sequence=[CHART_COLORS[6]],
                )

                fig_risco.update_traces(
                    marker_color=risco_colors,
                    text=[f"{v:.1f}%" for v in risco_df["Margem_Pct"]],
                    textposition="outside",
                    customdata=risco_df[["Preco_Medio", "Custo_Medio", "Receita_Total"]].values.tolist(),
                    hovertemplate=(
                        "%{y}<br>"
                        "Margem: %{x:.1f}%<br>"
                        "Preço Médio: R$ %{customdata[0]:,.2f}<br>"
                        "Custo Médio: R$ %{customdata[1]:,.2f}<br>"
                        "Receita Total: R$ %{customdata[2]:,.2f}<extra></extra>"
                    ),
                )

                fig_risco.add_vline(
                    x=0, line_dash="solid", line_color="#F87171",
                    line_width=2, annotation_text="break-even",
                )

                fig_risco.update_layout(
                    showlegend=False,
                    xaxis_title="Margem Unitaria (%)",
                    yaxis_title="",
                )

                fig_risco = clean_figure(fig_risco, height=380)

                risco_subtitle = (
                    f"{n_neg} produto(s) com margem negativa ⚠️"
                    if n_neg > 0
                    else "Nenhum produto com margem negativa ✅"
                )

                chart_block(
                    "Top 10 — Menor Margem (Risco)",
                    risco_subtitle,
                    fig_risco,
                    page_key=page_key,
                    dimension="Produto",
                    description=(
                        "Produtos com menor margem unitária percentual. "
                        "Margens negativas (abaixo de 0%) indicam prejuízo "
                        "por unidade — candidatos urgentes a revisão de preço, "
                        "redução de custo ou descontinuação."
                    ),
                )

            # ── Top 10 maior margem (destaque) ──
            destaque_df = prod_margem.head(10)

            with col8:
                destaque_colors = [
                    CHART_COLORS[2] if v >= 50 else CHART_COLORS[0]
                    for v in destaque_df["Margem_Pct"]
                ]

                fig_destaque = px.bar(
                    destaque_df,
                    x="Margem_Pct",
                    y="Produto",
                    orientation="h",
                    color_discrete_sequence=[CHART_COLORS[2]],
                )

                fig_destaque.update_traces(
                    marker_color=destaque_colors,
                    text=[f"{v:.1f}%" for v in destaque_df["Margem_Pct"]],
                    textposition="outside",
                    customdata=destaque_df[["Preco_Medio", "Custo_Medio", "Receita_Total"]].values.tolist(),
                    hovertemplate=(
                        "%{y}<br>"
                        "Margem: %{x:.1f}%<br>"
                        "Preço Médio: R$ %{customdata[0]:,.2f}<br>"
                        "Custo Médio: R$ %{customdata[1]:,.2f}<br>"
                        "Receita Total: R$ %{customdata[2]:,.2f}<extra></extra>"
                    ),
                )

                fig_destaque.add_vline(
                    x=50, line_dash="dash", line_color="#357560",
                    annotation_text="50%",
                )

                fig_destaque.update_layout(
                    showlegend=False,
                    xaxis_title="Margem Unitaria (%)",
                    yaxis_title="",
                )

                fig_destaque = clean_figure(fig_destaque, height=380)

                high_margin_count = int((destaque_df["Margem_Pct"] >= 50).sum())
                destaque_subtitle = (
                    f"{high_margin_count} produto(s) com margem ≥ 50% 🌟"
                    if high_margin_count > 0
                    else "Produtos com melhor margem do portfólio"
                )

                chart_block(
                    "Top 10 — Maior Margem (Destaque)",
                    destaque_subtitle,
                    fig_destaque,
                    page_key=page_key,
                    dimension="Produto",
                    description=(
                        "Produtos com maior margem unitária percentual. "
                        "Margens acima de 50% representam alta rentabilidade "
                        "por unidade — candidatos a investimento em marketing, "
                        "estoque e expansão de canais."
                    ),
                )


def _render_leitura_financeira(ctx, receita, prev_receita, margem_contrib_pct,
                                frete_pct, desconto_medio, proj, page_key):
    """Renderiza leitura executiva premium da página Financeira."""

    fs = FilterState(page_key)

    # Crescimento vs anterior
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
    margem_dot = "good" if margem_contrib_pct >= 25 else "warn" if margem_contrib_pct >= 15 else "bad"
    margem_label = f"Margem Contrib. {margem_contrib_pct:.1f}%"

    # Frete alerta
    frete_dot = "bad" if frete_pct > 15 else "warn" if frete_pct > 10 else "good"
    frete_label = f"Frete {frete_pct:.1f}% da receita"

    # Desconto alerta
    desc_dot = "warn" if desconto_medio > 12 else "info"
    desc_label = f"Desconto médio {desconto_medio:.1f}%"

    html = '<div class="exec-card">'

    html += '<div class="exec-header">'
    html += '<span class="exec-header-icon">📋</span>'
    html += '<span class="exec-header-title">Diagnóstico Financeiro</span>'
    html += '<span class="exec-header-badge">FinOps</span>'
    html += '</div>'

    html += '<div class="exec-metric">'
    html += f'<span class="exec-dot {crescimento_dot}"></span>'
    html += f'<span class="exec-metric-label">Crescimento</span>'
    html += f'<span class="exec-metric-value">{crescimento_label}</span>'
    html += '</div>'

    html += '<div class="exec-metric">'
    html += f'<span class="exec-dot {margem_dot}"></span>'
    html += f'<span class="exec-metric-label">Rentabilidade Operacional</span>'
    html += f'<span class="exec-metric-value">{margem_label}</span>'
    html += '</div>'

    html += '<div class="exec-metric">'
    html += f'<span class="exec-dot {frete_dot}"></span>'
    html += f'<span class="exec-metric-label">Eficiência Logística</span>'
    html += f'<span class="exec-metric-value">{frete_label}</span>'
    html += '</div>'

    html += '<div class="exec-metric">'
    html += f'<span class="exec-dot {desc_dot}"></span>'
    html += f'<span class="exec-metric-label">Política de Desconto</span>'
    html += f'<span class="exec-metric-value">{desc_label}</span>'
    html += '</div>'

    html += '<div class="exec-metric">'
    html += f'<span class="exec-dot info"></span>'
    html += f'<span class="exec-metric-label">Run Rate Projetado (12m)</span>'
    html += f'<span class="exec-metric-value">{fmt_currency(proj["run_rate_12m"])}</span>'
    html += '</div>'

    if proj.get("tem_sazonalidade"):
        diff_pct = (
            (proj["run_rate_12m_ajustado"] - proj["run_rate_12m"])
            / proj["run_rate_12m"] * 100
            if proj["run_rate_12m"]
            else 0
        )
        saz_dot = "good" if diff_pct > 5 else "warn" if diff_pct < -5 else "info"
        html += '<div class="exec-metric">'
        html += f'<span class="exec-dot {saz_dot}"></span>'
        html += f'<span class="exec-metric-label">Run Rate Ajustado (12m)</span>'
        html += f'<span class="exec-metric-value">{fmt_currency(proj["run_rate_12m_ajustado"])} ({diff_pct:+.1f}%)</span>'
        html += '</div>'

    if fs.has_filters:
        filtros_str = ", ".join(f"{k}: {v}" for k, v in fs.filters.items())
        html += f'<div class="exec-footer">🔍 Dados filtrados por: {filtros_str}</div>'

    html += '</div>'

    st.markdown(html, unsafe_allow_html=True)


# Import para compatibilidade com _render_leitura_financeira
import pandas as pd
