"""Exportação de Relatório PDF Executivo de 1 página — PHOSDash.

Usa fpdf2 (puro Python, sem dependências de sistema) com tema dark
inspirado no design system do PHOSDash.
"""

import io
import os
import tempfile
from datetime import datetime

import pandas as pd
from fpdf import FPDF
from PIL import Image, ImageDraw


# ── Paleta PHOS ──
PHOS_BLUE = (44, 107, 150)        # #2c6b96
PHOS_GOLD = (211, 183, 62)        # #d3b73e
PHOS_GREEN = (53, 117, 96)        # #357560
PHOS_DARK = (8, 20, 33)           # #081421
PHOS_CARD = (16, 34, 53)          # #102235
PHOS_CARD_ALT = (22, 42, 62)      # Alternativo sutil
PHOS_TEXT = (247, 250, 252)       # #F7FAFC
PHOS_SECONDARY = (170, 183, 196)   # #AAB7C4
PHOS_RED = (248, 113, 113)        # #F87171
PHOS_PURPLE = (139, 92, 246)      # Roxo
PHOS_INDIGO = (99, 102, 241)      # Indigo


class ExecutivePDF(FPDF):
    """PDF executivo de 1 página, layout paisagem A4, tema dark PHOS."""

    def __init__(self):
        super().__init__(orientation="L", unit="mm", format="A4")  # 297 x 210 mm
        self.set_auto_page_break(auto=False)
        self.add_page()

        # Registra fonte Unicode
        font_registered = False
        font_paths = [
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
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

    def draw_rect(self, x, y, w, h, color, style="F"):
        """Desenha retângulo com cor sólida (F=fill, D=draw, DF=both)."""
        self.set_fill_color(*color)
        self.set_draw_color(*color)
        self.rect(x, y, w, h, style)

    def text_at(self, x, y, w, h, text, size=10, bold=False, color=None,
                align="L"):
        """Texto posicionado em célula com tamanho e cor."""
        c = color or PHOS_TEXT
        self.set_text_color(*c)
        style = "B" if bold else ""
        self.set_font(self.font_family, style, size)
        self.set_xy(x, y)
        if align == "C":
            self.cell(w, h, text, align="C")
        elif align == "R":
            self.cell(w, h, text, align="R")
        else:
            self.cell(w, h, text)


# ═══════════════════════════════════════════════════════════════
# SEÇÕES DE DESENHO
# ═══════════════════════════════════════════════════════════════

def _draw_header(pdf, logo_path, report_date):
    """Header com logo à esquerda, título centralizado, data à direita."""
    # Fundo do header
    pdf.draw_rect(0, 0, 297, 26, PHOS_CARD)

    # Logo à esquerda
    logo_x, logo_y = 10, 4
    if os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=logo_x, y=logo_y, h=18)
            logo_x = 28
        except Exception:
            pass

    # Título "PHOSDash" centralizado
    pdf.text_at(0, 4, 297, 10, "PHOSDash", size=16, bold=True,
                color=PHOS_GOLD, align="C")
    # Subtítulo abaixo do título
    pdf.text_at(0, 14, 297, 6, "Relatório Executivo", size=8,
                color=PHOS_SECONDARY, align="C")

    # Data à direita
    pdf.text_at(200, 8, 87, 6, report_date, size=8,
                color=PHOS_SECONDARY, align="R")

    # Linha dourada separadora
    pdf.set_draw_color(*PHOS_GOLD)
    pdf.set_line_width(0.5)
    pdf.line(10, 26, 287, 26)


def _draw_kpi_section(pdf, kpis):
    """Linha de KPIs com cards elegantes — fundos alternados e borda lateral."""
    y_start = 30
    card_w = 53
    card_h = 34
    gap = 4
    x_start = 10
    n = len(kpis)
    accents = [PHOS_BLUE, PHOS_GREEN, PHOS_GOLD, PHOS_PURPLE, PHOS_INDIGO]
    icons = ["◆", "◆", "◆", "◆", "◆"]

    for i, kpi in enumerate(kpis):
        x = x_start + i * (card_w + gap)
        bg_color = PHOS_CARD if i % 2 == 0 else PHOS_CARD_ALT

        # Card background
        pdf.draw_rect(x, y_start, card_w, card_h, bg_color)

        # Borda lateral colorida (esquerda)
        accent = accents[i % len(accents)]
        pdf.set_draw_color(*accent)
        pdf.set_line_width(1.2)
        pdf.line(x, y_start, x, y_start + card_h)

        # Borda superior sutil (topo)
        pdf.set_draw_color(*accent)
        pdf.set_line_width(0.4)
        pdf.line(x, y_start, x + card_w, y_start)

        # Label com indicador (bold)
        icon = icons[i] if i < len(icons) else "◆"
        label = f"{icon} {kpi['label']}"
        pdf.text_at(x + 4, y_start + 3, card_w - 6, 5, label,
                    size=7.5, bold=True, color=PHOS_SECONDARY)

        # Valor principal (maior, bold)
        val_size = 13 if len(kpi["value"]) < 12 else 10
        pdf.text_at(x + 4, y_start + 10, card_w - 6, 6, kpi["value"],
                    size=val_size, bold=True)

        # Delta (variação)
        if kpi.get("delta") is not None:
            delta = kpi["delta"]
            delta_color = PHOS_GREEN if delta >= 0 else PHOS_RED
            arrow = "▲" if delta >= 0 else "▼"
            delta_text = f"{arrow} {abs(delta):.1f}%"
            pdf.text_at(x + 4, y_start + 19, card_w - 6, 5, delta_text,
                        size=7.5, bold=True, color=delta_color)

            if kpi.get("delta_label"):
                pdf.text_at(x + 4, y_start + 24, card_w - 6, 4,
                            kpi["delta_label"], size=6, color=PHOS_SECONDARY)


def _draw_chart_miniature(pdf, monthly_data, x, y, w, h):
    """Desenha miniatura do gráfico de evolução mensal usando PIL."""
    if monthly_data is None or monthly_data.empty or len(monthly_data) < 2:
        return

    try:
        # Prepara dados
        receita_vals = monthly_data["Receita"].values
        lucro_vals = monthly_data["Lucro"].values

        if receita_vals.max() == receita_vals.min():
            return

        # Normaliza para o tamanho da imagem
        img_w, img_h = 800, 260
        img = Image.new("RGBA", (img_w, img_h), (8, 20, 33, 255))
        draw = ImageDraw.Draw(img)

        margin_l, margin_r = 50, 20
        margin_t, margin_b = 20, 30
        plot_w = img_w - margin_l - margin_r
        plot_h = img_h - margin_t - margin_b

        r_min, r_max = 0, receita_vals.max() * 1.15
        scale_r = plot_h / (r_max - r_min) if r_max > r_min else 1

        # Normaliza lucro
        l_min = min(0, lucro_vals.min())
        l_max = lucro_vals.max() * 1.15
        l_range = l_max - l_min if l_max > l_min else 1
        scale_l = plot_h / l_range

        n = len(receita_vals)
        bar_w = max(2, (plot_w / n) * 0.6)

        # Grid horizontal sutil
        for pct in [0.25, 0.5, 0.75]:
            gy = margin_t + int(plot_h * (1 - pct))
            for gx in range(margin_l, img_w - margin_r, 4):
                draw.point((gx, gy), fill=(255, 255, 255, 20))

        # Barras de receita
        for i, rv in enumerate(receita_vals):
            bx = margin_l + int((i + 0.5) * plot_w / n - bar_w / 2)
            bar_h_px = int((rv - r_min) * scale_r)
            by = margin_t + plot_h - bar_h_px
            draw.rectangle(
                [bx, by, bx + int(bar_w), margin_t + plot_h],
                fill=(44, 107, 150, 200), outline=None
            )

        # Linha de lucro
        points = []
        for i, lv in enumerate(lucro_vals):
            lx = margin_l + int((i + 0.5) * plot_w / n)
            ly = margin_t + plot_h - int((lv - l_min) * scale_l)
            points.append((lx, ly))

        for i in range(len(points) - 1):
            draw.line([points[i], points[i + 1]],
                      fill=(211, 183, 62, 230), width=3)

        # Bolinhas nos pontos de lucro
        for pt in points:
            r = 4
            draw.ellipse([pt[0] - r, pt[1] - r, pt[0] + r, pt[1] + r],
                         fill=(211, 183, 62, 255))

        # Salva temp e insere no PDF
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            img.save(tmp.name, format="PNG")
            tmp_path = tmp.name

        try:
            pdf.image(tmp_path, x=x, y=y, w=w, h=h)
        finally:
            os.unlink(tmp_path)

    except Exception:
        # Fallback silencioso — miniatura é opcional
        pass


def _draw_chart_section(pdf, monthly_data):
    """Seção do gráfico de evolução mensal com miniatura."""
    x, y = 10, 68
    w, h = 165, 80

    # Card background
    pdf.draw_rect(x - 2, y - 6, w + 4, h + 15, PHOS_CARD)

    # Título da seção
    pdf.text_at(x, y - 4, w, 5, "Evolucao Mensal", size=10, bold=True,
                color=PHOS_GOLD)
    pdf.text_at(x, y + 1, w, 4, "Receita, Lucro e Margem", size=7,
                color=PHOS_SECONDARY)

    # Miniatura do gráfico (PIL)
    _draw_chart_miniature(pdf, monthly_data, x, y + 9, w - 4, h - 12)


def _draw_top_categories(pdf, cat_df):
    """Tabela de Top 5 categorias com estilo aprimorado."""
    x, y = 178, 68
    w = 110
    table_h = 85

    # Card background
    pdf.draw_rect(x - 2, y - 6, w + 4, table_h + 15, PHOS_CARD)

    # Título da seção
    pdf.text_at(x, y - 4, w, 5, "Top 5 Categorias", size=10, bold=True,
                color=PHOS_GOLD)
    pdf.text_at(x, y + 1, w, 4, "Por receita e margem", size=7,
                color=PHOS_SECONDARY)

    if cat_df is None or cat_df.empty:
        pdf.text_at(x, y + 15, w, 5, "Sem dados disponíveis.", size=8,
                    color=PHOS_SECONDARY)
        return

    top5 = cat_df.head(5)
    col_w = [52, 30, 28]  # Categoria, Receita, Margem
    headers = ["Categoria", "Receita", "Margem"]
    header_y = y + 8

    # Cabeçalho com fundo azul
    for j, (header, cw) in enumerate(zip(headers, col_w)):
        cx = x + sum(col_w[:j])
        pdf.set_fill_color(*PHOS_BLUE)
        pdf.set_text_color(*PHOS_TEXT)
        pdf.set_font(pdf.font_family, "B", 7.5)
        pdf.set_xy(cx, header_y)
        pdf.cell(cw, 5.5, header, border=0, fill=True,
                 align="C" if j > 0 else "L")

    # Linhas
    from utils.formatters import fmt_currency, fmt_pct

    for i, (_, row) in enumerate(top5.iterrows()):
        row_y = header_y + 5.8 + i * 6.5
        cat_name = str(row.get("Categoria", ""))[:24]
        receita = row.get("Receita", 0)
        margem = row.get("Margem", 0)
        receita_str = fmt_currency(receita)
        margem_str = fmt_pct(margem)

        # Fundo alternado
        bg = PHOS_DARK if i % 2 == 0 else PHOS_CARD_ALT
        pdf.set_fill_color(*bg)

        for j, (val, cw) in enumerate(
            zip([cat_name, receita_str, margem_str], col_w)
        ):
            cx = x + sum(col_w[:j])
            pdf.set_text_color(*PHOS_TEXT)
            pdf.set_font(pdf.font_family, "", 7)
            pdf.set_xy(cx, row_y)
            pdf.cell(cw, 5.8, val, border=0, fill=True,
                     align="C" if j > 0 else "L")

    # Linha de totais
    total_y = header_y + 5.8 + 5 * 6.5 + 2
    pdf.set_draw_color(*PHOS_GOLD)
    pdf.set_line_width(0.3)
    pdf.line(x, total_y, x + sum(col_w), total_y)

    total_receita = top5["Receita"].sum()
    total_margem = (
        top5["Lucro"].sum() / total_receita * 100
        if total_receita else 0
    )
    pdf.set_fill_color(*PHOS_CARD)
    pdf.set_text_color(*PHOS_GOLD)
    pdf.set_font(pdf.font_family, "B", 7)
    pdf.set_xy(x, total_y + 0.5)
    pdf.cell(col_w[0], 5, "Total (Top 5)", border=0, fill=True)
    pdf.cell(col_w[1], 5, fmt_currency(total_receita), border=0, fill=True,
             align="C")
    pdf.cell(col_w[2], 5, fmt_pct(total_margem), border=0, fill=True,
             align="C")


def _sanitize_text(text):
    """Remove emojis e caracteres nao suportados pela fonte DejaVu Sans."""
    import re
    cleaned = re.sub(r'[\U0001F300-\U0001F9FF\u2600-\u27BF\u2702-\u27B0'
                     r'\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF'
                     r'\U0001F600-\U0001F64F\U0001F680-\U0001F6FF'
                     r'\u200D\uFE0F\u20E3]+', '', text)
    return cleaned.strip()


def _draw_insights(pdf, insights):
    """Seção de insights automáticos — estilo bubble cards."""
    x, y = 10, 155
    w = 278

    # Fundo do card
    pdf.draw_rect(x - 2, y - 5, w + 4, 24, PHOS_CARD)

    # Título
    pdf.text_at(x, y - 3, w, 5, "Insights Automaticos", size=10,
                bold=True, color=PHOS_GOLD)

    if not insights:
        pdf.text_at(x, y + 5, w, 5, "Nenhum insight disponível para o período.",
                    size=8, color=PHOS_SECONDARY)
        return

    max_insights = min(len(insights), 6)
    bubble_w = (w - 10) / max_insights - 4
    bubble_h = 15
    bubble_y = y + 5

    severity_colors = {
        "success": PHOS_GREEN,
        "info": PHOS_BLUE,
        "warning": PHOS_GOLD,
        "danger": PHOS_RED,
    }

    for i, ins in enumerate(insights[:max_insights]):
        bx = x + i * (bubble_w + 4)
        sev = ins.get("severity", "info")
        color = severity_colors.get(sev, PHOS_BLUE)

        # Bubble background + borda colorida
        pdf.set_fill_color(*PHOS_DARK)
        pdf.set_draw_color(*color)
        pdf.set_line_width(0.4)
        pdf.rect(bx, bubble_y, bubble_w, bubble_h, "DF")

        # Ícone + Título + Valor
        icon = _sanitize_text(ins.get("icon", "•"))
        title = _sanitize_text(ins.get("title", ""))[:13]
        value = _sanitize_text(ins.get("value", ""))[:14]
        text = f"{icon} {title}: {value}"
        pdf.text_at(bx + 1.5, bubble_y + 1.5, bubble_w - 3, 4.5, text,
                    size=6.5, bold=True)

        # Tag
        tag = _sanitize_text(ins.get("tag", ""))[:30]
        if tag:
            pdf.text_at(bx + 1.5, bubble_y + 7, bubble_w - 3, 4, tag,
                        size=5.5, color=PHOS_SECONDARY)


def _draw_footer(pdf):
    """Rodapé com branding PHOS centralizado."""
    y = 202
    # Linha dourada
    pdf.set_draw_color(*PHOS_GOLD)
    pdf.set_line_width(0.3)
    pdf.line(10, y - 3, 287, y - 3)

    # Texto centralizado
    pdf.text_at(0, y, 297, 5,
                "Gerado por PHOSDash — phosconsultoria.com.br",
                size=7, color=PHOS_SECONDARY, align="C")


# ═══════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def generate_executive_pdf(
    ctx,
    logo_path: str,
    opcao_ano: str = "Todos",
    extra_insights: list[dict] | None = None,
) -> bytes:
    """Gera relatório PDF executivo de 1 página.

    Args:
        ctx: PageContext com dados atuais.
        logo_path: Caminho para o logo PHOS.
        opcao_ano: Ano selecionado para exibir no header.
        extra_insights: Lista de insights (opcional).

    Returns:
        bytes do PDF pronto para download.
    """
    pdf = ExecutivePDF()

    # Fundo escuro da página
    pdf.draw_rect(0, 0, 297, 210, PHOS_DARK)

    # Header
    now = datetime.now().strftime("%d/%m/%Y às %H:%M")
    periodo = f"{opcao_ano}  •  {now}"
    _draw_header(pdf, logo_path, periodo)

    # KPIs
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

    # Gráfico de evolução mensal (miniatura PIL)
    monthly = ctx.monthly
    _draw_chart_section(pdf, monthly)

    # Top 5 Categorias
    cat_df = (
        ctx.cat
        if hasattr(ctx, "cat") and ctx.cat is not None and not ctx.cat.empty
        else None
    )
    _draw_top_categories(pdf, cat_df)

    # Insights
    insights = extra_insights or []
    if not insights:
        from services.insights_engine import generate_insights

        df_for_insights = (
            ctx.current_df
            if hasattr(ctx, "current_df") and ctx.current_df is not None
            else pd.DataFrame()
        )
        insights = generate_insights(df_for_insights, ct, pt)

    _draw_insights(pdf, insights)

    # Rodapé
    _draw_footer(pdf)

    return bytes(pdf.output())
