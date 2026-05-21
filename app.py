"""PHOSDash — Dashboard Executivo de Performance.

Shell enxuto: sidebar → core.sidebar, dados → core.data_loader,
config → core.config. Apenas compõe os módulos e faz o roteamento.
"""

import base64, os
import streamlit as st

st.set_page_config(page_title="PHOSDash", page_icon="", layout="wide", initial_sidebar_state="expanded")

from core import Config, render_sidebar                                          # noqa: E402
from components.ui import render_kpis                                            # noqa: E402
from components.crossfilter import render_dimension_filters, render_filter_bar   # noqa: E402
from state.filters import FilterState                                            # noqa: E402
from services.page_engine import prepare_page_data                               # noqa: E402
from services.alert_engine import AlertEngine, render_active_alerts              # noqa: E402
from utils.formatters import fmt_currency, fmt_pct, fmt_int, pct_change          # noqa: E402

# ── Config ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CFG = Config(base_dir=BASE_DIR)

# ── CSS (deve vir após CFG) ──
with open(CFG.assets_css, encoding="utf-8") as _css:
    st.markdown(_css.read(), unsafe_allow_html=True)

# ── Página de Feedback (query param, não aparece na navegação) ──
if st.query_params.get("page") == "feedback":
    from views.Feedback import render as render_feedback
    render_feedback(CFG)
    st.stop()

# ── Query params para abrir páginas direto (nova aba) ──
qp = st.query_params.get("page")
if qp == "overview":
    st.session_state.nav_pagina = "📊 Visão Operacional"
elif qp == "estrategica":
    st.session_state.nav_pagina = "🎯 Visão Estratégica"
elif qp == "financeira":
    st.session_state.nav_pagina = "💰 Visão Financeira"

# ── Watermark ──
if os.path.exists(CFG.bg_watermark):
    with open(CFG.bg_watermark, "rb") as _f:
        _bg_b64 = base64.b64encode(_f.read()).decode()
    st.markdown(
        f"""<style>.stApp::before{{content:"";position:fixed;top:50%;left:50%;
transform:translate(-50%,-50%);width:80vw;height:80vh;
background-image:url("data:image/png;base64,{_bg_b64}");
background-size:contain;background-position:center;background-repeat:no-repeat;
opacity:0.02;pointer-events:none;z-index:0;}}</style>""",
        unsafe_allow_html=True,
    )

# ── Sidebar ──
with st.sidebar:
    sidebar = render_sidebar(CFG)
df, opcao_ano, pagina = sidebar["df"], sidebar["opcao_ano"], sidebar["pagina"]

# ── Filtro de ano ──
full_df = st.session_state.df
if opcao_ano != "Todos":
    df = df[df["Data"].dt.year == int(opcao_ano)]
    previous_df = full_df[full_df["Data"].dt.year == int(opcao_ano) - 1]
else:
    previous_df = full_df[full_df["Data"].dt.year == df["Data"].dt.year.max() - 1]

# ── Header ──
_nome = pagina.replace("📊 ", "").replace("🎯 ", "").replace("💰 ", "")
st.markdown(
    f"""<div class="top-header">
<div class="top-header-page">{_nome}</div>
</div>
<div class="top-header-feedback-row">
<a href="?page=feedback" class="feedback-header-btn">📋 Feedback</a>
</div>""", unsafe_allow_html=True,
)
st.markdown("---")

# ── Páginas ──
PAGE_ROUTES = {
    "📊 Visão Operacional": ("overview", "Overview"),
    "🎯 Visão Estratégica": ("receita", "Receita"),
    "💰 Visão Financeira": ("financeiro", "Financeiro"),
}
page_key, view_name = PAGE_ROUTES[pagina]

render_dimension_filters(page_key, df, CFG.dimensions_full)
render_filter_bar(page_key)

# Aplica cross-filtros antes de preparar os dados
is_filtered = FilterState(page_key).has_filters
current_df = FilterState(page_key).apply(df) if is_filtered else df
ctx = prepare_page_data(current_df, previous_df, page_key, has_filters=is_filtered)

# ══════════════════════════════════════════════════════════
# Aviso: filtros incompatíveis (dados vazios após filtrar)
# ══════════════════════════════════════════════════════════
if ctx.current_df.empty and is_filtered:
    st.markdown(
        """<div style="background: linear-gradient(135deg, rgba(16,34,53,0.97), rgba(11,22,40,0.99));
        border: 1px solid rgba(211,183,62,0.35); border-radius: 16px; padding: 36px 28px;
        text-align: center; margin: 40px 0; max-width: 680px; margin-left: auto; margin-right: auto;">
        <div style="font-size: 2.2rem; margin-bottom: 14px;">🔍</div>
        <div style="font-size: 1.1rem; font-weight: 700; color: #F4F6F8; margin-bottom: 8px;">
            Nenhum dado encontrado para esta combinação de filtros
        </div>
        <div style="font-size: 0.88rem; color: #AAB7C4; line-height: 1.6;">
            Os filtros selecionados não retornaram resultados.<br>
            Tente ajustar os critérios ou clique em <strong>Limpar filtros</strong> para redefinir.
        </div>
        </div>""",
        unsafe_allow_html=True,
    )
    if st.button("🗑️ Limpar filtros", key="clear_empty_filters"):
        FilterState(page_key).clear_all()
        st.rerun()
    st.stop()

# ── Alert Engine ──
alert_engine = AlertEngine()
alerts = alert_engine.check_all(ctx.current_df, ctx.monthly, ctx)

# Badge de alertas (ao lado do header)
if alerts:
    critical_count = sum(1 for a in alerts if a.severity == "critical")
    warning_count = sum(1 for a in alerts if a.severity == "warning")
    badge_text_parts = []
    if critical_count:
        badge_text_parts.append(f"🔴 {critical_count} crítico{'s' if critical_count > 1 else ''}")
    if warning_count:
        badge_text_parts.append(f"🟡 {warning_count} atenção")
    badge_text = " | ".join(badge_text_parts)
    st.markdown(
        f'<div class="alert-badge-header">{badge_text}</div>',
        unsafe_allow_html=True,
    )

# Seção de Alertas Ativos (no topo de cada página)
render_active_alerts(alerts)

# KPIs (apenas overview)
if page_key == "overview":
    r, l, p = ctx.current_total["receita"], ctx.current_total["lucro"], ctx.current_total["pedidos"]
    pr, pl, pp = ctx.previous_total["receita"], ctx.previous_total["lucro"], ctx.previous_total["pedidos"]
    render_kpis([
        ("Receita Total", fmt_currency(r), pct_change(r, pr), "período anterior"),
        ("Lucro Total", fmt_currency(l), pct_change(l, pl), "período anterior"),
        ("Margem de Lucro", fmt_pct((l / r * 100) if r else 0), None, "período anterior"),
        ("Ticket Médio", fmt_currency((r / p) if p else 0), None, "período anterior"),
        ("Total de Pedidos", fmt_int(p), pct_change(p, pp), "período anterior"),
    ], per_row=5)
    st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)

view_mod = __import__(f"views.{view_name}", fromlist=["render"])
view_mod.render(ctx)

# ── PDF Export ──
from services.pdf_export import generate_executive_pdf

pdf_bytes = generate_executive_pdf(ctx, CFG.logo_sidebar, opcao_ano)
st.download_button(
    label='📄 Exportar PDF',
    data=pdf_bytes,
    file_name='PHOSDash_Relatorio.pdf',
    mime='application/pdf',
)
