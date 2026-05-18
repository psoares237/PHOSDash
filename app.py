"""PHOSDash — Dashboard Executivo de Performance.

Shell principal: sidebar com navegação, hero com KPIs filtráveis, páginas por radio.
Cross-filtering como cidadão de primeira classe — todos os visuais respondem.
"""

import streamlit as st
import pandas as pd
import numpy as np
import os

# ── Config ──
st.set_page_config(
    page_title="PHOSDash",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──
st.markdown(open("assets/theme.css", encoding="utf-8").read(), unsafe_allow_html=True)

# ── Imports (após set_page_config) ──
from components.ui import render_kpis, section_header
from components.crossfilter import render_dimension_filters, render_filter_bar
from services.page_engine import prepare_page_data
from services.insights_engine import generate_insights
from utils.formatters import fmt_currency, fmt_pct, fmt_int, pct_change


# ── Constantes ──

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DADOS_OFICIAIS = os.path.join(BASE_DIR, "Dados_PHOSDash.xlsx")
MODELO_DOWNLOAD = os.path.join(BASE_DIR, "Modelo_dados_PHOSDash.xlsx")

COL_MAP = {
    "Valor_Total": "Receita",
    "Custo_total": "Custo",
}

COL_NAMES_PT = {
    "Receita": "Receita",
    "Custo": "Custo",
    "Lucro": "Lucro",
    "Frete": "Frete",
    "Quantidade": "Quantidade",
    "Desconto_Pct": "Desconto (%)",
    "Canal_Venda": "Canal de Venda",
    "Regiao": "Região",
}


# ── Funções de dados ──

def load_official_data() -> pd.DataFrame | None:
    """Carrega a planilha oficial Dados_PHOSDash.xlsx."""
    if not os.path.exists(DADOS_OFICIAIS):
        return None
    try:
        df = pd.read_excel(DADOS_OFICIAIS)
        if df.empty:
            return None
        return standardize(df)
    except Exception:
        return None


def standardize(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza colunas do DataFrame para o formato interno do PHOSDash."""
    df = df.rename(columns=COL_MAP)
    if "Mes" not in df.columns and "Data" in df.columns:
        df["Data"] = pd.to_datetime(df["Data"])
        df["Mes"] = df["Data"].dt.to_period("M")
    return df


def generate_demo_data() -> pd.DataFrame:
    """Gera dados fictícios para demonstração quando não há dados oficiais."""
    np.random.seed(42)
    n = 2400
    meses = pd.date_range("2020-01-01", "2025-12-01", freq="MS")
    categorias = ["Esportes", "Informática", "Eletrônicos", "Móveis", "Eletrodomésticos", "Celulares"]
    canais = ["Site Próprio", "Marketplace", "Loja Física", "Atacado"]
    regioes = ["Sudeste", "Sul", "Nordeste", "Norte", "Centro-Oeste"]
    vendedores = ["Ana Lima", "Pedro Santos", "Carla Mendes", "João Oliveira", "Mariana Costa"]

    rows = []
    for i in range(n):
        mes = meses[np.random.randint(0, len(meses))]
        cat = np.random.choice(categorias)
        canal = np.random.choice(canais)
        regiao = np.random.choice(regioes)
        vendedor = np.random.choice(vendedores)
        receita = np.random.uniform(80, 8000)
        margem_pct = np.random.uniform(0.15, 0.55)
        lucro = receita * margem_pct
        custo = receita - lucro
        qtd = np.random.randint(1, 20)
        desconto = np.random.uniform(0, 0.25)
        frete = np.random.uniform(5, 120)

        rows.append({
            "Mes": mes.to_period("M"),
            "Data": mes,
            "Receita": round(receita, 2),
            "Lucro": round(lucro, 2),
            "Custo": round(custo, 2),
            "ID_Pedido": f"P{np.random.randint(10000, 99999)}",
            "Quantidade": qtd,
            "Desconto_Pct": round(desconto * 100, 2),
            "Frete": round(frete, 2),
            "Categoria": cat,
            "Canal_Venda": canal,
            "Regiao": regiao,
            "Vendedor": vendedor,
            "Produto": f"Produto_{np.random.randint(1, 200)}",
        })

    return pd.DataFrame(rows)


def load_data() -> pd.DataFrame:
    """Carrega dados: upload > oficiais > demo."""
    if "df" in st.session_state and st.session_state.df is not None:
        return st.session_state.df

    # 1. Upload do usuário
    uploaded = st.session_state.get("uploaded_file")
    if uploaded:
        df = pd.read_excel(uploaded)
        df = standardize(df)
        st.session_state.df = df
        return df

    # 2. Dados oficiais
    df = load_official_data()
    if df is not None:
        st.session_state.df = df
        return df

    # 3. Demo data
    df = generate_demo_data()
    st.session_state.df = df
    return df


# ── Sidebar Premium ──

with st.sidebar:
    # ── Header ──
    st.markdown(
        '<div class="sidebar-header">'
        '<div class="sidebar-logo">'
        '<span class="logo-icon">💎</span> PHOS<span class="logo-gold">Dash</span>'
        '</div>'
        '<div class="sidebar-subtitle">Dashboard Executivo</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # ── Stepper: Passo a passo ──
    st.markdown(
        '<div class="sidebar-stepper">'
        '<div class="stepper-title">📋 Passo a passo</div>'
        '<div class="stepper-subtitle">Configure sua análise em poucos passos</div>'
        '<div class="stepper-item completed">'
        '<div class="stepper-number">1</div>'
        '<div class="stepper-content">'
        '<div class="stepper-label">Baixe o modelo padrão</div>'
        '<div class="stepper-desc">Utilize o layout PHOSDash (.xlsx)</div>'
        '</div></div>'
        '<div class="stepper-connector"></div>'
        '<div class="stepper-item active">'
        '<div class="stepper-number">2</div>'
        '<div class="stepper-content">'
        '<div class="stepper-label">Preencha os dados</div>'
        '<div class="stepper-desc">Use o layout padrão do PHOSDash</div>'
        '</div></div>'
        '<div class="stepper-connector"></div>'
        '<div class="stepper-item">'
        '<div class="stepper-number">3</div>'
        '<div class="stepper-content">'
        '<div class="stepper-label">Envie a planilha</div>'
        '<div class="stepper-desc">O dashboard será atualizado</div>'
        '</div></div>'
        '<div class="stepper-connector"></div>'
        '<div class="stepper-item">'
        '<div class="stepper-number">4</div>'
        '<div class="stepper-content">'
        '<div class="stepper-label">Analise os indicadores</div>'
        '<div class="stepper-desc">Dashboards atualizados automaticamente</div>'
        '</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Download modelo ──
    with open(MODELO_DOWNLOAD, "rb") as f:
        st.download_button(
            "📥 Baixar modelo (.xlsx)",
            data=f,
            file_name="Modelo_dados_PHOSDash.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # ── Upload ──
    uploaded_file = st.file_uploader(
        "Carregar arquivo", type=["xlsx"], key="uploaded_file",
        label_visibility="collapsed",
    )

    # ── Card de arquivo importado ──
    if uploaded_file is not None:
        file_size = len(uploaded_file.getvalue()) / 1024
        file_size_str = f"{file_size:.1f} KB" if file_size < 1024 else f"{file_size/1024:.1f} MB"
        st.markdown(
            f'<div class="file-card">'
            f'<div class="file-card-icon">✅</div>'
            f'<div class="file-card-info">'
            f'<div class="file-card-name">{uploaded_file.name}</div>'
            f'<div class="file-card-status">Importado com sucesso</div>'
            f'<div class="file-card-size">{file_size_str} • XLSX</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # ── Período ──
    df = load_data()
    st.markdown(
        '<div class="sidebar-period">'
        '<div class="period-label">📅 Período</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    anos_disponiveis = ["Todos"] + sorted(
        df["Data"].dt.year.unique().tolist(), reverse=True
    )
    opcao_ano = st.selectbox("Ano", anos_disponiveis, label_visibility="collapsed")

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # ── Navegação executiva ──
    NAV_ITEMS = [
        ("📊", "Visão Geral"),
        ("📈", "Receita e Crescimento"),
        ("💰", "Custos e Despesas"),
        ("📉", "Margem e Rentabilidade"),
        ("🛒", "Comercial"),
        ("🌎", "Geografia"),
        ("📦", "Produtos"),
        ("🏦", "Finanças"),
        ("🧠", "Insights & BI Avançado"),
    ]

    nav_labels = [f"{icon} {name}" for icon, name in NAV_ITEMS]
    pagina = st.radio("Página", nav_labels, label_visibility="collapsed", key="nav_pagina")

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # ── Ações rápidas ──
    st.markdown(
        '<div class="sidebar-actions">'
        '<div class="action-btn" onclick="document.querySelector(\'[data-testid=stSidebar] details summary\').click();">'
        '<span class="action-icon">🗑️</span> Limpar filtros'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # ── Espaçamento para empurrar rodapé ──
    st.markdown("<div style='flex:1; min-height:2rem;'></div>", unsafe_allow_html=True)

    # ── Rodapé executivo ──
    st.markdown(
        '<div class="sidebar-footer">'
        '<div class="sidebar-footer-logo">PHOSFit Brasil</div>'
        '<div class="sidebar-footer-slogan">Inteligência que gera resultado</div>'
        '<div class="sidebar-footer-version">v2.0 • 2026</div>'
        '</div>',
        unsafe_allow_html=True,
    )

# ── Filtrar por ano (sidebar) ──

if opcao_ano != "Todos":
    df = df[df["Data"].dt.year == int(opcao_ano)]

# Período anterior (mesmo intervalo, ano anterior)
if opcao_ano != "Todos":
    previous_df = load_data()
    previous_df = previous_df[previous_df["Data"].dt.year == int(opcao_ano) - 1]
else:
    previous_df = load_data()
    previous_df = previous_df[previous_df["Data"].dt.year == df["Data"].dt.year.max() - 1]

# ── Cabeçalho ──

st.markdown("# 📊 PHOSDash")
st.markdown("##### Painel Executivo de Performance — PHOSFit Brasil")
st.markdown("---")

# ── Navegação por página ──

DIMENSIONS_FULL = [
    ("Categoria", "Categoria"),
    ("Canal_Venda", "Canal"),
    ("Regiao", "Região"),
    ("Vendedor", "Vendedor"),
]

# ═══════════════════════════════════════
# Página: Visão Geral
# ═══════════════════════════════════════

if pagina == "📊 Visão Geral":
    page_key = "overview"

    render_dimension_filters(page_key, df, DIMENSIONS_FULL)
    render_filter_bar(page_key)

    ctx = prepare_page_data(df, previous_df, page_key)

    # ── Hero KPIs ──

    receita = ctx.current_total["receita"]
    lucro = ctx.current_total["lucro"]
    pedidos = ctx.current_total["pedidos"]
    margem = (lucro / receita * 100) if receita else 0
    ticket = (receita / pedidos) if pedidos else 0

    prev_receita = ctx.previous_total["receita"]
    prev_lucro = ctx.previous_total["lucro"]
    prev_pedidos = ctx.previous_total["pedidos"]

    kpis = [
        ("Receita Total", fmt_currency(receita), pct_change(receita, prev_receita), "período anterior"),
        ("Lucro Total", fmt_currency(lucro), pct_change(lucro, prev_lucro), "período anterior"),
        ("Margem de Lucro", fmt_pct(margem), None, "período anterior"),
        ("Ticket Médio", fmt_currency(ticket), None, "período anterior"),
        ("Total de Pedidos", fmt_int(pedidos), pct_change(pedidos, prev_pedidos), "período anterior"),
    ]

    render_kpis(kpis, per_row=5)

    # ── Insights ──

    insights = generate_insights(ctx.current_df, ctx.current_total, ctx.previous_total)
    if insights:
        st.markdown("#### 💡 Insights Automáticos")
        for ins in insights[:3]:
            st.markdown(
                f"""
                <div class="insight-card insight-info">
                    <div class="insight-title">{ins['icon']} {ins['title']}</div>
                    <div class="insight-message">{ins['message']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Gráficos Overview ──

    from views.Overview import render as render_overview

    render_overview(ctx)

# ═══════════════════════════════════════
# Página: Receita e Crescimento
# ═══════════════════════════════════════

elif pagina == "📈 Receita e Crescimento":
    page_key = "receita"

    render_dimension_filters(page_key, df, DIMENSIONS_FULL)
    render_filter_bar(page_key)

    ctx = prepare_page_data(df, previous_df, page_key)

    from views.Receita import render as render_receita

    render_receita(ctx)

# ═══════════════════════════════════════
# Página: Custos e Despesas
# ═══════════════════════════════════════

elif pagina == "💰 Custos e Despesas":
    page_key = "custos"

    render_dimension_filters(page_key, df, DIMENSIONS_FULL)
    render_filter_bar(page_key)

    ctx = prepare_page_data(df, previous_df, page_key)

    from views.Custos import render as render_custos

    render_custos(ctx)

# ═══════════════════════════════════════
# Páginas ainda não implementadas
# ═══════════════════════════════════════

elif pagina == "📉 Margem e Rentabilidade":
    st.info("🚧 Página **Margem e Rentabilidade** — em breve disponível.")

elif pagina == "🛒 Comercial":
    st.info("🚧 Página **Comercial** — em breve disponível.")

elif pagina == "🌎 Geografia":
    st.info("🚧 Página **Geografia** — em breve disponível.")

elif pagina == "📦 Produtos":
    st.info("🚧 Página **Produtos** — em breve disponível.")

elif pagina == "🏦 Finanças":
    st.info("🚧 Página **Finanças** — em breve disponível.")

elif pagina == "🧠 Insights & BI Avançado":
    st.info("🚧 Página **Insights & BI Avançado** — em breve disponível.")