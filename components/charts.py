"""Utilitários de formatação para gráficos Plotly."""

import plotly.graph_objects as go

from core.config import CHART_COLORS  # noqa: F401 — re-exportado por compatibilidade


def clean_figure(fig: go.Figure, height: int = 380) -> go.Figure:
    """Aplica tema dark padrão do PHOSDash a uma figura Plotly."""
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#F7FAFC", family="Inter, system-ui, sans-serif"),
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color="#AAB7C4"),
        ),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            tickfont=dict(color="#AAB7C4"),
            title_font=dict(color="#AAB7C4"),
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            tickfont=dict(color="#AAB7C4"),
            title_font=dict(color="#AAB7C4"),
        ),
    )
    return fig