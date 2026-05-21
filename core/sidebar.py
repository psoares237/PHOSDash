"""Renderização da sidebar premium do PHOSDash.

Contém logo, seletor de período, stepper de configuração,
upload/download de planilhas e navegação entre páginas.
"""

import base64
import os
from typing import Any

import streamlit as st

from core.config import Config
from core.data_loader import load_data, reset_uploaded_data


def _render_sidebar_logo(logo_path: str) -> None:
    """Renderiza o logo original da PHOS no topo da sidebar."""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as file:
            logo_b64 = base64.b64encode(file.read()).decode()

        st.markdown(
            f"""<div class="sidebar-header">
<img src="data:image/png;base64,{logo_b64}" class="sidebar-logo-img" alt="PHOS" />
<div class="sidebar-subtitle">Dashboard Executivo</div>
</div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """<div class="sidebar-header">
<div class="sidebar-logo">PHOS<span class="logo-gold">Dash</span></div>
<div class="sidebar-subtitle">Dashboard Executivo</div>
</div>""",
            unsafe_allow_html=True,
        )


def _render_stepper() -> None:
    """Renderiza o passo a passo visual na sidebar."""
    st.markdown(
        """<div class="sidebar-stepper">
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
</div>""",
        unsafe_allow_html=True,
    )


def _render_footer() -> None:
    """Renderiza o rodapé da sidebar."""
    st.markdown(
        """<div class="sidebar-footer">
<div class="sidebar-footer-logo">PHOSFit Brasil</div>
<div class="sidebar-footer-slogan">Inteligência que gera resultado</div>
<div class="sidebar-footer-version">v2.0 • 2026</div>
</div>""",
        unsafe_allow_html=True,
    )


def render_sidebar(config: Config) -> dict[str, Any]:
    """Renderiza a sidebar completa e retorna os dados selecionados.

    Args:
        config: Instância de Config com os paths do projeto.

    Returns:
        Dicionário com:
            - df: DataFrame carregado (do ano selecionado).
            - opcao_ano: Ano selecionado (str "Todos" ou ano como str).
            - pagina: Página de navegação selecionada.
    """
    _render_sidebar_logo(config.logo_sidebar)

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # ── Navegação (bloco no topo) ──
    st.markdown(
        """<div class="sidebar-period">
<div class="period-label">🧭 Navegação</div>
</div>""",
        unsafe_allow_html=True,
    )

    nav_labels = [
        "📊 Visão Operacional",
        "🎯 Visão Estratégica",
        "💰 Visão Financeira",
    ]

    pagina = st.selectbox(
        "Página",
        nav_labels,
        label_visibility="collapsed",
        key="nav_pagina",
    )

    # Links para abrir em nova aba
    page_links = {
        "📊 Visão Operacional": "?page=overview",
        "🎯 Visão Estratégica": "?page=estrategica",
        "💰 Visão Financeira": "?page=financeira",
    }
    st.markdown(
        f"""<div style="margin-top:6px;font-size:0.65rem;color:#5A6F86;text-align:center;">
        🔗 <a href="{page_links[pagina]}" target="_blank" style="color:#7B8FA8;text-decoration:none;">
        Abrir em nova aba</a></div>""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # ── Carregamento de dados ──
    df = load_data(config.dados_oficiais)

    # ── Seletor de período ──
    st.markdown(
        """<div class="sidebar-period">
<div class="period-label">📅 Período</div>
</div>""",
        unsafe_allow_html=True,
    )

    anos_disponiveis = ["Todos"] + sorted(
        df["Data"].dt.year.unique().tolist(), reverse=True
    )

    opcao_ano = st.selectbox(
        "Ano",
        anos_disponiveis,
        label_visibility="collapsed",
    )

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # ── Stepper ──
    _render_stepper()

    # ── Download do modelo ──
    if os.path.exists(config.modelo_download):
        with open(config.modelo_download, "rb") as file:
            st.download_button(
                "📥 Baixar modelo (.xlsx)",
                data=file,
                file_name="Modelo_dados_PHOSDash.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    # ── Upload de planilha ──
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
            f"{file_size:.1f} KB" if file_size < 1024 else f"{file_size / 1024:.1f} MB"
        )

        st.markdown(
            f"""<div class="file-card">
<div class="file-card-icon">✅</div>
<div class="file-card-info">
<div class="file-card-name">{uploaded_file.name}</div>
<div class="file-card-status">Importado com sucesso</div>
<div class="file-card-size">{file_size_str} • XLSX</div>
</div>
</div>""",
            unsafe_allow_html=True,
        )

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # ── Rodapé ──
    _render_footer()

    return {
        "df": df,
        "opcao_ano": opcao_ano,
        "pagina": pagina,
    }
