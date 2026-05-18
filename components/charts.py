"""Utilitários de formatação para gráficos Plotly."""

import plotly.graph_objects as go


# Cores oficiais do PHOSDash (dark theme)
CHART_COLORS = [
    "#2c6b96",  # Azul principal
    "#d3b73e",  # Dourado
    "#357560",  # Verde
    "#cabdaf",  # Areia
    "#384727",  # Verde escuro
    "#8B5CF6",  # Roxo
    "#F87171",  # Vermelho suave
    "#60A5FA",  # Azul claro
]


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