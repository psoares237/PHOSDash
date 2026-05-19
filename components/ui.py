"""Componentes de UI reutilizáveis — KPIs, chart_block, section_header."""

import streamlit as st
import plotly.graph_objects as go

from utils.formatters import fmt_pct
from state.filters import FilterState


def metric_card(title: str, value: str, delta: float | None, delta_label: str) -> None:
    """Renderiza um card de KPI com delta opcional."""
    if delta is None:
        delta_html = '<div class="metric-delta flat">Sem base comparável</div>'
    else:
        arrow = "▲" if delta >= 0 else "▼"
        cls = "up" if delta >= 0 else "down"
        delta_html = f'<div class="metric-delta {cls}">{arrow} {fmt_pct(abs(delta))} vs. {delta_label}</div>'

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(items: list[tuple], per_row: int = 5) -> None:
    """Renderiza KPIs em linhas de N cards."""
    for idx in range(0, len(items), per_row):
        row = items[idx : idx + per_row]
        cols = st.columns(len(row), gap="medium")
        for col, item in zip(cols, row):
            with col:
                metric_card(*item)

def section_header(title: str, subtitle: str) -> None:
    """Renderiza header de seção com título e subtítulo."""
    st.markdown(
        f"""
        <div class="section-card">
            <div class="chart-title">{title}</div>
            <div class="chart-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _extract_clicked_value(result, fig: go.Figure) -> str | None:
    """Extrai o valor clicado de um gráfico Plotly de forma robusta.

    Prioridade de extração:
    1. customdata — canal prioritário, funciona para todos os tipos de gráfico
    2. labels — pie/donut/sunburst
    3. x — barras/linhas
    4. names — scatter genérico
    5. y — fallback final

    Retorna None se nenhum valor puder ser extraído.
    """
    if not result or not result.selection or not result.selection.point_indices:
        return None

    idx = result.selection.point_indices[0]
    trace = fig.data[0]

    # 1. customdata (canal prioritário — funciona para pie, bar, scatter, etc.)
    if hasattr(trace, "customdata") and trace.customdata is not None:
        try:
            val = trace.customdata[idx]
            # customdata pode ser lista (se adicionado com list) ou escalar
            if isinstance(val, (list, tuple)):
                val = val[0] if val else None
            if val is not None:
                return str(val)
        except (IndexError, TypeError):
            pass

    # 2. labels (pie/donut/sunburst)
    if hasattr(trace, "labels") and trace.labels is not None:
        try:
            return str(trace.labels[idx])
        except (IndexError, TypeError):
            pass

    # 3. x (barras/linhas)
    if hasattr(trace, "x") and trace.x is not None:
        try:
            values = list(trace.x)
            if idx < len(values):
                return str(values[idx])
        except (IndexError, TypeError):
            pass

    # 4. names (scatter com nomes)
    if hasattr(trace, "names") and trace.names is not None:
        try:
            values = list(trace.names)
            if idx < len(values):
                return str(values[idx])
        except (IndexError, TypeError):
            pass

    # 5. y (fallback final — retorna o valor do eixo y)
    if hasattr(trace, "y") and trace.y is not None:
        try:
            values = list(trace.y)
            if idx < len(values):
                return str(values[idx])
        except (IndexError, TypeError):
            pass

    return None


def chart_block(
    title: str,
    subtitle: str,
    fig: go.Figure,
    page_key: str | None = None,
    dimension: str | None = None,
    description: str = "",
) -> None:
    """Renderiza gráfico com título, subtítulo e suporte a cross-filtering via clique.

    Args:
        title: Título do gráfico.
        subtitle: Subtítulo descritivo (renderizado abaixo do título).
        fig: Figura Plotly.
        page_key: Identificador da página (ex: "overview", "receita").
        dimension: Coluna do DataFrame que será filtrada ao clicar.
        description: Objetivo estratégico do gráfico (renderizado abaixo do chart).
    """
    # Build the chart-card header with title + subtitle
    subtitle_html = f'<div class="chart-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="chart-card">
            <div class="chart-title">{title}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    config = {"displayModeBar": False}
    chart_key = f"{title}_{subtitle}".replace(" ", "_").lower()

    use_click = page_key and dimension

    if use_click:
        result = st.plotly_chart(
            fig,
            use_container_width=True,
            config=config,
            key=f"cf_{page_key}_{chart_key}",
            on_select="rerun",
            selection_mode=["points"],
        )

        # Processar clique → extrair valor → atualizar cross-filter
        clicked_value = _extract_clicked_value(result, fig)
        if clicked_value:
            FilterState(page_key).toggle(dimension, clicked_value)
    else:
        st.plotly_chart(
            fig,
            use_container_width=True,
            config=config,
            key=chart_key,
        )

    # Description/objective below the chart
    if description:
        st.markdown(
            f"""
            <div class="chart-objective">{description}</div>
            """,
            unsafe_allow_html=True,
        )