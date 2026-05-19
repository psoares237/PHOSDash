"""PHOSDash — Dashboard Executivo de Performance.

Shell principal com sidebar premium, logo PHOS, navegação simplificada
e duas páginas oficiais:
1. Visão Geral Operacional
2. Visão Estratégica
"""

import base64
import os

import numpy as np
import pandas as pd
import streamlit as st

# ── Config ──
st.set_page_config(
    page_title="PHOSDash",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──
st.markdown(open("assets/theme.css", encoding="utf-8").read(), unsafe_allow_html=True)

# ── Imports após set_page_config ──
from components.ui import render_kpis
from components.crossfilter import render_dimension_filters, render_filter_bar
from services.page_engine import prepare_page_data
from services.insights_engine import generate_insights
from utils.formatters import fmt_currency, fmt_pct, fmt_int, pct_change


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DADOS_OFICIAIS = os.path.join(BASE_DIR, "Dados_PHOSDash.xlsx")
MODELO_DOWNLOAD = os.path.join(BASE_DIR, "Modelo_dados_PHOSDash.xlsx")
LOGO_SIDEBAR = os.path.join(BASE_DIR, "assets", "logo_phos_transparent.png")

COL_MAP = {
    "Valor_Total": "Receita",
    "Custo_total": "Custo",
}


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

    categorias = [
        "Esportes",
        "Informática",
        "Eletrônicos",
        "Móveis",
        "Eletrodomésticos",
        "Celulares",
    ]

    canais = ["Site Próprio", "Marketplace", "Loja Física", "Atacado"]
    regioes = ["Sudeste", "Sul", "Nordeste", "Norte", "Centro-Oeste"]
    vendedores = ["Ana Lima", "Pedro Santos", "Carla Mendes", "João Oliveira", "Mariana Costa"]

    rows = []

    for _ in range(n):
        mes = meses[np.random.randint(0, len(meses))]
        receita = np.random.uniform(80, 8000)
        margem_pct = np.random.uniform(0.15, 0.55)
        lucro = receita * margem_pct
        custo = receita - lucro

        rows.append({
            "Mes": mes.to_period("M"),
            "Data": mes,
            "Receita": round(receita, 2),
            "Lucro": round(lucro, 2),
            "Custo": round(custo, 2),
            "ID_Pedido": f"P{np.random.randint(10000, 99999)}",
            "Quantidade": np.random.randint(1, 20),
            "Desconto_Pct": round(np.random.uniform(0, 0.25) * 100, 2),
            "Frete": round(np.random.uniform(5, 120), 2),
            "Categoria": np.random.choice(categorias),
            "Canal_Venda": np.random.choice(canais),
            "Regiao": np.random.choice(regioes),
            "Vendedor": np.random.choice(vendedores),
            "Produto": f"Produto_{np.random.randint(1, 200)}",
        })

    return pd.DataFrame(rows)


def load_data() -> pd.DataFrame:
    """Carrega dados: upload > oficiais > demo."""
    if "df" in st.session_state and st.session_state.df is not None:
        return st.session_state.df

    uploaded = st.session_state.get("uploaded_file")

    if uploaded:
        df = pd.read_excel(uploaded)
        df = standardize(df)
        st.session_state.df = df
        return df

    df = load_official_data()

    if df is not None:
        st.session_state.df = df
        return df

    df = generate_demo_data()
    st.session_state.df = df
    return df


def reset_uploaded_data() -> None:
    """Limpa o dataframe em sessão para permitir novo carregamento."""
    if "df" in st.session_state:
        del st.session_state.df


def render_sidebar_logo() -> None:
    """Renderiza o logo original da PHOS no topo da sidebar."""
    if os.path.exists(LOGO_SIDEBAR):
        with open(LOGO_SIDEBAR, "rb") as file:
            logo_b64 = base64.b64encode(file.read()).decode()

        st.markdown(
            f"""
<div class="sidebar-header">
<img src="data:image/png;base64,{logo_b64}" class="sidebar-logo-img" alt="PHOS" />
<div class="sidebar-subtitle">Dashboard Executivo</div>
</div>
""",
            unsafe_allow_html=True,
        )

    else:
        st.markdown(
            """
<div class="sidebar-header">
<div class="sidebar-logo">PHOS<span class="logo-gold">Dash</span></div>
<div class="sidebar-subtitle">Dashboard Executivo</div>
</div>
""",
            unsafe_allow_html=True,
        )


with st.sidebar:
    render_sidebar_logo()

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    df = load_data()

    st.markdown(
        """
<div class="sidebar-period">
<div class="period-label">📅 Período</div>
</div>
""",
        unsafe_allow_html=True,
    )

    anos_disponiveis = ["Todos"] + sorted(
        df["Data"].dt.year.unique().tolist(),
        reverse=True,
    )

    opcao_ano = st.selectbox(
        "Ano",
        anos_disponiveis,
        label_visibility="collapsed",
    )

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    st.markdown(
        """
<div class="sidebar-stepper">
<div class="stepper-title">📋 Passo a passo</div>
<div class="stepper-subtitle">Configure sua análise em poucos passos</div>

<div class="stepper-item completed">
<div class="stepper-number">1</div>
<div class="stepper-content">
<div class="stepper-label">Baixe o modelo padrão</div>
<div class="stepper-desc">Utilize o layout PHOSDash (.xlsx)</div>
</div>
</div>

<div class="stepper-connector"></div>

<div class="stepper-item completed">
<div class="stepper-number">2</div>
<div class="stepper-content">
<div class="stepper-label">Preencha os dados</div>
<div class="stepper-desc">Use o layout oficial do PHOSDash</div>
</div>
</div>

<div class="stepper-connector"></div>

<div class="stepper-item active">
<div class="stepper-number">3</div>
<div class="stepper-content">
<div class="stepper-label">Envie a planilha</div>
<div class="stepper-desc">O dashboard será atualizado</div>
</div>
</div>

<div class="stepper-connector"></div>

<div class="stepper-item">
<div class="stepper-number">4</div>
<div class="stepper-content">
<div class="stepper-label">Analise os indicadores</div>
<div class="stepper-desc">Navegue pelas duas visões executivas</div>
</div>
</div>
</div>
""",
        unsafe_allow_html=True,
    )

    if os.path.exists(MODELO_DOWNLOAD):
        with open(MODELO_DOWNLOAD, "rb") as file:
            st.download_button(
                "📥 Baixar modelo (.xlsx)",
                data=file,
                file_name="Modelo_dados_PHOSDash.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    uploaded_file = st.file_uploader(
        "Carregar arquivo",
        type=["xlsx"],
        key="uploaded_file",
        label_visibility="collapsed",
        on_change=reset_uploaded_data,
    )

    if uploaded_file is not None:
        file_size = len(uploaded_file.getvalue()) / 1024
        file_size_str = (
            f"{file_size:.1f} KB"
            if file_size < 1024
            else f"{file_size / 1024:.1f} MB"
        )

        st.markdown(
            f"""
<div class="file-card">
<div class="file-card-icon">✅</div>
<div class="file-card-info">
<div class="file-card-name">{uploaded_file.name}</div>
<div class="file-card-status">Importado com sucesso</div>
<div class="file-card-size">{file_size_str} • XLSX</div>
</div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    nav_labels = [
        "📊 Visão Geral Operacional",
        "🎯 Visão Estratégica",
    ]

    pagina = st.radio(
        "Página",
        nav_labels,
        label_visibility="collapsed",
        key="nav_pagina",
    )

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    st.markdown(
        """
<div class="sidebar-footer">
<div class="sidebar-footer-logo">PHOSFit Brasil</div>
<div class="sidebar-footer-slogan">Inteligência que gera resultado</div>
<div class="sidebar-footer-version">v2.0 • 2026</div>
</div>
""",
        unsafe_allow_html=True,
    )


full_df = st.session_state.df

if opcao_ano != "Todos":
    df = df[df["Data"].dt.year == int(opcao_ano)]
    previous_df = full_df[full_df["Data"].dt.year == int(opcao_ano) - 1]
else:
    previous_df = full_df[full_df["Data"].dt.year == df["Data"].dt.year.max() - 1]


st.markdown("# 📊 PHOSDash")
st.markdown("##### Painel Executivo de Performance — PHOSFit Brasil")
st.markdown("---")


DIMENSIONS_FULL = [
    ("Categoria", "Categoria"),
    ("Canal_Venda", "Canal"),
    ("Regiao", "Região"),
    ("Vendedor", "Vendedor"),
]


if pagina == "📊 Visão Geral Operacional":
    page_key = "overview"

    render_dimension_filters(page_key, df, DIMENSIONS_FULL)
    render_filter_bar(page_key)

    ctx = prepare_page_data(df, previous_df, page_key)

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

    insights = generate_insights(
        ctx.current_df,
        ctx.current_total,
        ctx.previous_total,
    )

    if insights:
        st.markdown("#### 💡 Insights Automáticos")

        for insight in insights[:3]:
            st.markdown(
                f"""
<div class="insight-card insight-info">
<div class="insight-title">
{insight.get("icon", "📊")} {insight.get("title", "")}
</div>
<div class="insight-message">
{insight.get("message", "")}
</div>
</div>
""",
                unsafe_allow_html=True,
            )

    from views.Overview import render as render_overview

    render_overview(ctx)


elif pagina == "🎯 Visão Estratégica":
    page_key = "receita"

    render_dimension_filters(page_key, df, DIMENSIONS_FULL)
    render_filter_bar(page_key)

    ctx = prepare_page_data(df, previous_df, page_key)

    from views.Receita import render as render_receita

    render_receita(ctx)