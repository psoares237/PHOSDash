"""Exportação de Relatório PDF Executivo de 1 página — PHOSDash.

Usa fpdf2 (puro Python, sem dependências de sistema) com tema dark
inspirado no design system do PHOSDash.
"""

import io
import os
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
from fpdf import FPDF
from fpdf.enums import Align, TableCellFillMode


# ── Paleta Dark Theme (consistente com theme.css) ──
BG_MAIN = (8, 20, 33)          # #081421
BG_CARD = (16, 34, 53)         # #102235
BORDER_SUBTLE = (30, 45, 65)   # rgba(255,255,255,0.06) aproximado
TEXT_PRIMARY = (247, 250, 252)  # #F7FAFC
TEXT_SECONDARY = (170, 183, 196)  # #AAB7C4
GOLD = (211, 183, 62)          # #d3b73e
BLUE = (44, 107, 150)          # #2c6b96
GREEN = (53, 117, 96)          # #357560
RED = (248, 113, 113)          # #F87171
WHITE_SOFT = (200, 210, 220)


# ── Helper para cores tuple → hex ──
def _rgb(r: int, g: int, b: int) -> tuple[int, int, int]:
    return (r, g, b)


class ExecutivePDF(FPDF):
    """PDF executivo de 1 página, layout paisagem A4, tema dark."""

    def __init__(self):
        super().__init__(orientation="L", unit="mm", format="A4")  # 297 x 210 mm
        self.set_auto_page_break(auto=False)
        self.add_page()

        # Registra fonte Unicode (suporta caracteres especiais)
        font_registered = False
        font_paths = [
            # Linux: DejaVu Sans (quase sempre disponível)
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            # Windows: Arial
            (r"C:\Windows\Fonts\arial.ttf",
             r"C:\Windows\Fonts\arialbd.ttf"),
        ]
        for regular_path, bold_path in font_paths:
            try:
                self.add_font("UniFont", "", regular_path)
                self.add_font("UniFont", "B", bold_path)
                self.font_family = "UniFont"
                font_registered = True
                break
            except Exception:
                continue
        if not font_registered:
            self.font_family = "Helvetica"

    # ── Métodos de desenho ──

    def draw_rect(self, x: float, y: float, w: float, h: float,
                  color: tuple, style: str = "F", radius: float = 0):
        """Desenha retângulo com cor sólida (F=fill, D=draw)."""
        self.set_fill_color(*color)
        self.set_draw_color(*color)
        if radius > 0:
            self.rounded_rect(x, y, w, h, radius, style, corners="all")
        else:
            self.rect(x, y, w, h, style)

    def rounded_rect(self, x: float, y: float, w: float, h: float,
                     r: float, style: str = "F", corners: str = "all"):
        """Rect with rounded corners (simplificado)."""
        # rect normal com cantos vivos (aceitável para PDF executivo)
        self.rect(x, y, w, h, style)

    def text_primary(self, x: float, y: float, text: str, size: float = 10,
                     bold: bool = False, align: str = "L", color: tuple = TEXT_PRIMARY):
        """Texto com cor primária (claro)."""
        self.set_text_color(*color)
        style = "B" if bold else ""
        self.set_font(self.font_family, style, size)
        self.set_xy(x, y)
        if align == "C":
            self.cell(0, 5, text, align="C")
        elif align == "R":
            self.cell(0, 5, text, align="R")
        else:
            self.cell(0, 5, text)

    def text_secondary(self, x: float, y: float, text: str, size: float = 8,
                       align: str = "L"):
        """Texto com cor secundária (acinzentado)."""
        self.text_primary(x, y, text, size=size, bold=False, align=align,
                          color=TEXT_SECONDARY)

    def text_gold(self, x: float, y: float, text: str, size: float = 10,
                  bold: bool = True, align: str = "L"):
        """Texto dourado destaque."""
        self.text_primary(x, y, text, size=size, bold=bold, align=align, color=GOLD)


def _draw_header(pdf: ExecutivePDF, logo_path: str, report_date: str):
    """Desenha o header: logo/nome + data + linha divisória."""
    # Background do header
    pdf.draw_rect(0, 0, 297, 22, BG_CARD)

    # Logo (se existir)
    logo_x, logo_y = 8, 3
    if os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=logo_x, y=logo_y, h=16)
            logo_x = 30  # Espaço após logo
        except Exception:
            pass

    # Nome + subtítulo
    pdf.text_gold(logo_x, logo_y + 1, "PHOS", size=14)
    pdf.text_primary(logo_x + 14, logo_y + 1, "Dash", size=14, bold=True)
    pdf.text_secondary(logo_x, logo_y + 7, "Dashboard Executivo", size=7)

    # Data
    pdf.text_secondary(240, logo_y + 4, report_date, size=8, align="R")

    # Linha dourada
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.4)
    pdf.line(8, 22, 289, 22)


def _draw_kpi_section(pdf: ExecutivePDF, kpis: list[dict]):
    """Desenha a linha de KPIs (5 cards horizontais)."""
    y_start = 26
    card_w = 53
    card_h = 30
    gap = 4
    x_start = 8

    for i, kpi in enumerate(kpis):
        x = x_start + i * (card_w + gap)

        # Card background
        pdf.draw_rect(x, y_start, card_w, card_h, BG_CARD)

        # Borda superior colorida (varia por posição)
        accents = [BLUE, GREEN, GOLD, (139, 92, 246), (99, 102, 241)]  # purple, indigo
        accent = accents[i % len(accents)]
        pdf.set_draw_color(*accent)
        pdf.set_line_width(1.0)
        pdf.line(x, y_start, x + card_w, y_start)

        # Título (ícone + nome) — centralizado
        icon_map = {0: "💰", 1: "💵", 2: "🎫", 3: "📊", 4: "📦"}
        title = f"{icon_map.get(i, '📊')} {kpi['label']}"
        pdf.text_secondary(x + 3, y_start + 3, title, size=7)

        # Valor principal
        value_text = kpi["value"]
        val_size = 12 if len(value_text) < 12 else 10
        pdf.text_primary(x + 3, y_start + 9, value_text, size=val_size, bold=True)

        # Delta (variação)
        if kpi.get("delta"):
            delta = kpi["delta"]
            color = GREEN if (isinstance(delta, (int, float)) and delta >= 0) else RED
            arrow = "▲" if (isinstance(delta, (int, float)) and delta >= 0) else "▼"
            delta_text = f"{arrow} {abs(delta):.1f}%"
            pdf.text_primary(x + 3, y_start + 20, delta_text, size=8, bold=False, color=color)

            # Label do delta
            if kpi.get("delta_label"):
                pdf.text_secondary(x + 3, y_start + 24, kpi["delta_label"], size=6)


def _draw_chart_section(pdf: ExecutivePDF, fig: go.Figure):
    """Converte gráfico Plotly para imagem e insere no PDF."""
    if fig is None:
        return

    try:
        img_bytes = fig.to_image(format="png", width=1200, height=500, scale=1.5)
    except Exception:
        return

    # Área do gráfico: lado esquerdo (metade inferior)
    x, y = 8, 60
    w, h = 160, 70

    # Card background
    pdf.draw_rect(x - 2, y - 6, w + 4, h + 12, BG_CARD)
    pdf.text_primary(x, y - 4, "📈 Evolução Mensal — Receita, Lucro e Margem", size=9, bold=True)

    # Salva imagem temporária
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(img_bytes)
        tmp_path = tmp.name

    try:
        pdf.image(tmp_path, x=x, y=y + 2, w=w, h=h)
    finally:
        os.unlink(tmp_path)


def _draw_top_categories(pdf: ExecutivePDF, cat_df: pd.DataFrame):
    """Tabela de Top 5 categorias (lado direito, metade inferior)."""
    x, y = 174, 60
    w = 116
    table_h = 70

    # Card background
    pdf.draw_rect(x - 2, y - 6, w + 4, table_h + 12, BG_CARD)
    pdf.text_primary(x, y - 4, "🏆 Top 5 Categorias", size=9, bold=True)

    if cat_df is None or cat_df.empty:
        pdf.text_secondary(x, y + 10, "Sem dados de categorias disponíveis.", size=8)
        return

    top5 = cat_df.head(5)

    # Cabeçalho da tabela
    col_w = [44, 36, 36]  # Categoria, Receita, Margem
    headers = ["Categoria", "Receita", "Margem"]
    header_y = y + 2

    for j, (header, cw) in enumerate(zip(headers, col_w)):
        cx = x + sum(col_w[:j])
        pdf.set_fill_color(*BLUE)
        pdf.set_text_color(*TEXT_PRIMARY)
        pdf.set_font(pdf.font_family, "B", 7)
        pdf.set_xy(cx, header_y)
        pdf.cell(cw, 5, header, border=0, fill=True, align="C")

    # Linhas de dados
    for i, (_, row) in enumerate(top5.iterrows()):
        row_y = header_y + 5 + i * 5.5
        cat_name = str(row.get("Categoria", ""))[:20]
        receita = row.get("Receita", 0)
        margem = row.get("Margem", 0)

        from utils.formatters import fmt_currency, fmt_pct
        receita_str = fmt_currency(receita)
        margem_str = fmt_pct(margem)

        # Alterna cor de fundo das linhas
        if i % 2 == 0:
            pdf.set_fill_color(*BG_MAIN)
        else:
            pdf.set_fill_color(*(20, 30, 45))

        for j, (val, cw) in enumerate(zip([cat_name, receita_str, margem_str], col_w)):
            cx = x + sum(col_w[:j])
            pdf.set_text_color(*TEXT_PRIMARY)
            pdf.set_font(pdf.font_family, "", 7)
            pdf.set_xy(cx, row_y)
            pdf.cell(cw, 5, val, border=0, fill=(i % 2 == 0), align="C" if j > 0 else "L")


def _draw_insights(pdf: ExecutivePDF, insights: list[dict]):
    """Seção de insights automáticos na parte inferior."""
    x, y = 8, 136
    w = 282

    pdf.draw_rect(x - 2, y - 4, w + 4, 18, BG_CARD)
    pdf.text_primary(x, y - 2, "💡 Insights Automáticos", size=9, bold=True)

    if not insights:
        pdf.text_secondary(x, y + 5, "Nenhum insight disponível para o período.", size=8)
        return

    # Renderiza até 6 insights
    max_insights = min(len(insights), 6)
    bubble_w = (w - 10) / max_insights - 4
    bubble_h = 12
    bubble_y = y + 4

    severity_colors = {
        "success": GREEN,
        "info": BLUE,
        "warning": GOLD,
        "danger": RED,
    }

    for i, ins in enumerate(insights[:max_insights]):
        bx = x + i * (bubble_w + 4)
        sev = ins.get("severity", "info")
        color = severity_colors.get(sev, BLUE)

        # Bubble background
        pdf.draw_rect(bx, bubble_y, bubble_w, bubble_h, BG_MAIN)
        # Borda colorida
        pdf.set_draw_color(*color)
        pdf.set_line_width(0.3)
        pdf.rect(bx, bubble_y, bubble_w, bubble_h, "D")

        # Ícone + Título + Valor (em uma linha compacta)
        icon = ins.get("icon", "📊")
        title = ins.get("title", "")[:12]
        value = ins.get("value", "")[:14]
        text = f"{icon} {title}: {value}"
        pdf.text_primary(bx + 1, bubble_y + 1.5, text, size=6.5, bold=True)

        # Tag (linha abaixo)
        tag = ins.get("tag", "")[:30]
        if tag:
            pdf.text_secondary(bx + 1, bubble_y + 6.5, tag, size=5.5)


def _draw_footer(pdf: ExecutivePDF):
    """Rodapé com branding PHOS."""
    y = 200
    pdf.text_secondary(8, y, "PHOSFit Brasil • Inteligência que gera resultado", size=6)
    pdf.text_secondary(200, y, "Relatório gerado automaticamente pelo PHOSDash v2.0", size=6, align="R")


def generate_executive_pdf(
    ctx,
    logo_path: str,
    opcao_ano: str = "Todos",
    extra_insights: list[dict] | None = None,
) -> bytes:
    """Gera relatório PDF executivo de 1 página.

    Args:
        ctx: PageContext com dados atuais (current_total, monthly, cat, etc.).
        logo_path: Caminho para o logo PHOS.
        opcao_ano: Ano selecionado (para exibir no header).
        extra_insights: Lista de insights (opcional, gerados pelo insight engine).

    Returns:
        bytes do PDF pronto para download.
    """
    pdf = ExecutivePDF()

    # ── Fundo escuro da página inteira ──
    pdf.draw_rect(0, 0, 297, 210, BG_MAIN)

    # ── Header ──
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    periodo = f"Período: {opcao_ano}  •  {now}"
    _draw_header(pdf, logo_path, periodo)

    # ── KPIs ──
    from utils.formatters import fmt_currency, fmt_pct, fmt_int, pct_change

    ct = ctx.current_total
    pt = ctx.previous_total

    receita = ct.get("receita", 0)
    lucro = ct.get("lucro", 0)
    pedidos = ct.get("pedidos", 0)
    margem_val = (lucro / receita * 100) if receita else 0
    ticket_medio = (receita / pedidos) if pedidos else 0

    kpis = [
        {
            "label": "Receita Total",
            "value": fmt_currency(receita),
            "delta": pct_change(receita, pt.get("receita", 0)) if pt else None,
            "delta_label": "período anterior",
        },
        {
            "label": "Lucro Total",
            "value": fmt_currency(lucro),
            "delta": pct_change(lucro, pt.get("lucro", 0)) if pt else None,
            "delta_label": "período anterior",
        },
        {
            "label": "Margem",
            "value": fmt_pct(margem_val),
            "delta": None,
            "delta_label": "",
        },
        {
            "label": "Ticket Médio",
            "value": fmt_currency(ticket_medio),
            "delta": None,
            "delta_label": "",
        },
        {
            "label": "Pedidos",
            "value": fmt_int(pedidos),
            "delta": pct_change(pedidos, pt.get("pedidos", 0)) if pt else None,
            "delta_label": "período anterior",
        },
    ]
    _draw_kpi_section(pdf, kpis)

    # ── Gráfico de evolução mensal ──
    monthly = ctx.monthly
    fig = None
    if monthly is not None and not monthly.empty:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(
            go.Bar(
                x=monthly["MesLabel"],
                y=monthly["Receita"],
                name="Receita",
                marker_color="#2c6b96",
                marker_line_width=0,
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
                line=dict(color="#d3b73e", width=2),
                marker=dict(size=4),
                hovertemplate="Lucro: R$ %{y:,.2f}<extra></extra>",
            ),
            secondary_y=True,
        )
        fig.add_trace(
            go.Scatter(
                x=monthly["MesLabel"],
                y=monthly["Margem"],
                name="Margem %",
                mode="lines",
                line=dict(color="#8B5CF6", width=1.5, dash="dot"),
                hovertemplate="Margem: %{y:.1f}%<extra></extra>",
            ),
            secondary_y=True,
        )

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#F7FAFC", size=10),
            margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02,
                xanchor="right", x=1, font=dict(size=9, color="#AAB7C4"),
            ),
            xaxis=dict(gridcolor="rgba(255,255,255,0.06)", tickfont=dict(color="#AAB7C4")),
            yaxis=dict(gridcolor="rgba(255,255,255,0.06)", tickfont=dict(color="#AAB7C4")),
            yaxis2=dict(gridcolor="rgba(255,255,255,0.06)", tickfont=dict(color="#AAB7C4")),
            height=350,
        )

    _draw_chart_section(pdf, fig)

    # ── Top 5 Categorias ──
    cat_df = ctx.cat if hasattr(ctx, "cat") and ctx.cat is not None and not ctx.cat.empty else None
    _draw_top_categories(pdf, cat_df)

    # ── Insights ──
    insights = extra_insights or []
    if not insights:
        # Gera insights básicos a partir dos totais
        from services.insights_engine import generate_insights
        df_for_insights = ctx.current_df if hasattr(ctx, "current_df") and ctx.current_df is not None else pd.DataFrame()
        insights = generate_insights(df_for_insights, ct, pt)

    _draw_insights(pdf, insights)

    # ── Rodapé ──
    _draw_footer(pdf)

    return bytes(pdf.output())
