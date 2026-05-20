"""Serviço de KPIs Financeiros — indicadores de 2ª linha para FinOps.

Fornece métricas de concentração, correlação, projeção e rentabilidade
que complementam o analytics_service com visão de CFO.
"""

import numpy as np
import pandas as pd
import streamlit as st


@st.cache_data(ttl=300, show_spinner=False)
def margem_contribuicao(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula margem de contribuição por pedido e agrega por dimensão.

    Margem de Contribuição = Receita - Custo - Frete
    (Lucro Operacional aproximado com dados disponíveis)

    Returns:
        DataFrame com colunas: Receita, Custo, Frete, Margem_Contrib,
        Margem_Contrib_Pct para cada registro.
    """
    result = df.copy()
    result["Margem_Contrib"] = result["Receita"] - result["Custo"] - result["Frete"]
    result["Margem_Contrib_Pct"] = np.where(
        result["Receita"] != 0,
        result["Margem_Contrib"] / result["Receita"] * 100,
        0,
    )
    return result


@st.cache_data(ttl=300, show_spinner=False)
def hhi_index(df: pd.DataFrame, column: str) -> float:
    """Herfindahl-Hirschman Index — medida de concentração de mercado.

    HHI = Σ(sᵢ²) × 10000, onde sᵢ é a participação percentual.

    Interpretação (escala 0-10000):
        < 1500: Não concentrado (saudável)
        1500-2500: Moderadamente concentrado
        > 2500: Altamente concentrado (risco)

    Args:
        df: DataFrame com coluna 'Receita'.
        column: Coluna de segmentação (ex: 'Categoria', 'Canal_Venda').

    Returns:
        Índice HHI (float).
    """
    if df.empty or column not in df.columns:
        return 0

    total = df["Receita"].sum()
    if total == 0:
        return 0

    shares = df.groupby(column)["Receita"].sum() / total
    return float((shares**2).sum() * 10000)


@st.cache_data(ttl=300, show_spinner=False)
def hhi_by_dimensions(df: pd.DataFrame, dimensions: list[str]) -> dict[str, float]:
    """Calcula HHI para múltiplas dimensões.

    Returns:
        Dict {dimensão: índice_hhi}.
    """
    return {dim: hhi_index(df, dim) for dim in dimensions if dim in df.columns}


@st.cache_data(ttl=300, show_spinner=False)
def desconto_margem_correlation(df: pd.DataFrame) -> dict:
    """Analisa correlação entre desconto médio e margem por categoria e canal.

    Returns:
        Dict com:
            - categorias: DataFrame com Desconto_Medio, Margem, Correlação por categoria
            - canais: idem por canal
            - global_r: coeficiente de Pearson global
            - insight: texto descritivo do achado
    """
    if df.empty:
        return {"categorias": pd.DataFrame(), "canais": pd.DataFrame(),
                "global_r": 0.0, "insight": "Sem dados"}

    # Correlação global
    global_r = float(df["Desconto_Pct"].corr(df["Lucro"] / df["Receita"].replace(0, np.nan)))

    # Por categoria
    cat_agg = (
        df.groupby("Categoria")
        .agg(
            Desconto_Medio=("Desconto_Pct", "mean"),
            Margem_Media=("Lucro", lambda x: x.sum() / df.loc[x.index, "Receita"].sum() * 100
                           if df.loc[x.index, "Receita"].sum() != 0 else 0),
            Receita=("Receita", "sum"),
        )
        .sort_values("Receita", ascending=False)
    )

    # Por canal
    canal_agg = (
        df.groupby("Canal_Venda")
        .agg(
            Desconto_Medio=("Desconto_Pct", "mean"),
            Margem_Media=("Lucro", lambda x: x.sum() / df.loc[x.index, "Receita"].sum() * 100
                           if df.loc[x.index, "Receita"].sum() != 0 else 0),
            Receita=("Receita", "sum"),
        )
        .sort_values("Receita", ascending=False)
    )

    # Insight automático
    if global_r < -0.3:
        insight = (
            f"Correlação negativa significativa (r={global_r:.2f}): "
            "canais/categorias com maior desconto tendem a ter margens menores. "
            "Recomendação: revisar política de desconto."
        )
    elif global_r < -0.1:
        insight = (
            f"Correlação negativa leve (r={global_r:.2f}): "
            "desconto impacta margem de forma moderada."
        )
    elif global_r > 0.1:
        insight = (
            f"Correlação positiva (r={global_r:.2f}): "
            "desconto NÃO está corroendo margem — precificação saudável."
        )
    else:
        insight = (
            f"Sem correlação significativa (r={global_r:.2f}): "
            "política de desconto não é o principal driver de margem."
        )

    return {
        "categorias": cat_agg,
        "canais": canal_agg,
        "global_r": global_r,
        "insight": insight,
    }


@st.cache_data(ttl=300, show_spinner=False)
def run_rate_projection(monthly: pd.DataFrame) -> dict:
    """Projeta receita anualizada com base nos últimos meses.

    Usa média móvel dos últimos 3, 6 e 12 meses.

    Returns:
        Dict com projeções e confiança.
    """
    if monthly.empty or "Receita" not in monthly.columns:
        return {"run_rate_3m": 0, "run_rate_6m": 0, "run_rate_12m": 0,
                "tendencia": "estável", "confianca": "baixa"}

    receita = monthly["Receita"].tail(12)

    if len(receita) < 3:
        return {"run_rate_3m": 0, "run_rate_6m": 0, "run_rate_12m": 0,
                "tendencia": "estável", "confianca": "baixa"}

    rr3 = float(receita.tail(3).mean() * 12)
    rr6 = float(receita.tail(6).mean() * 12)
    rr12 = float(receita.tail(12).mean() * 12) if len(receita) >= 12 else rr6

    # Tendência: compara médias
    media_recente = receita.tail(3).mean()
    media_anterior = receita.head(len(receita) - 3).mean() if len(receita) > 3 else media_recente

    if media_anterior > 0:
        var = (media_recente - media_anterior) / media_anterior
        if var > 0.05:
            tendencia = "crescimento"
        elif var < -0.05:
            tendencia = "queda"
        else:
            tendencia = "estável"
    else:
        tendencia = "estável"

    confianca = "alta" if len(receita) >= 12 else "média" if len(receita) >= 6 else "baixa"

    return {
        "run_rate_3m": rr3,
        "run_rate_6m": rr6,
        "run_rate_12m": rr12,
        "tendencia": tendencia,
        "confianca": confianca,
    }


@st.cache_data(ttl=300, show_spinner=False)
def forma_pagamento_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Analisa distribuição e performance por forma de pagamento.

    Returns:
        DataFrame com Receita, Ticket Médio, Margem por Forma_Pagamento.
    """
    if df.empty or "Forma_Pagamento" not in df.columns:
        return pd.DataFrame()

    result = (
        df.groupby("Forma_Pagamento", as_index=False)
        .agg(
            Receita=("Receita", "sum"),
            Lucro=("Lucro", "sum"),
            Pedidos=("ID_Pedido", "nunique"),
            Ticket_Medio=("Receita", "mean"),
            Frete=("Frete", "sum"),
        )
        .sort_values("Receita", ascending=False)
    )

    result["Margem"] = np.where(
        result["Receita"] != 0,
        result["Lucro"] / result["Receita"] * 100,
        0,
    )
    result["Share"] = result["Receita"] / result["Receita"].sum() * 100

    return result


@st.cache_data(ttl=300, show_spinner=False)
def sazonalidade_analysis(monthly: pd.DataFrame) -> pd.DataFrame:
    """Analisa padrão sazonal mensal ao longo dos anos.

    Calcula média por mês do ano (1-12) e desvio padrão.

    Returns:
        DataFrame com colunas: Mes, MesNome, Receita_Media, Desvio_Padrao, CV.
    """
    if monthly.empty or "MesNumero" not in monthly.columns:
        return pd.DataFrame()

    meses_nome = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
        5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
        9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
    }

    result = (
        monthly.groupby("MesNumero")
        .agg(
            Receita_Media=("Receita", "mean"),
            Desvio_Padrao=("Receita", "std"),
        )
        .reset_index()
    )

    result["MesNome"] = result["MesNumero"].map(meses_nome)
    result["CV"] = np.where(
        result["Receita_Media"] != 0,
        result["Desvio_Padrao"] / result["Receita_Media"] * 100,
        0,
    )

    return result.sort_values("MesNumero")
