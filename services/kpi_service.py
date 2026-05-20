"""Serviço de KPIs Financeiros — indicadores de 2ª linha para FinOps.

Fornece métricas de concentração, correlação, projeção e rentabilidade
que complementam o analytics_service com visão de CFO.
"""

import numpy as np
import pandas as pd
import streamlit as st

from utils.formatters import fmt_currency


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
def run_rate_projection(
    monthly: pd.DataFrame,
    sazonalidade: pd.DataFrame | None = None,
) -> dict:
    """Projeta receita anualizada com base nos últimos meses.

    Usa média móvel dos últimos 3, 6 e 12 meses. Se dados de sazonalidade
    forem fornecidos (coluna 'Fator_Sazonal' + 'MesNumero'), calcula também
    a projeção com ajuste sazonal, removendo o efeito de cada mês antes
    de projetar.

    A projeção ajustada dessazonaliza cada mês histórico dividindo a receita
    pelo fator sazonal do mês correspondente, projeta a partir da média
    dessazonalizada e produz um insight automático comparando as projeções.

    Args:
        monthly: DataFrame com colunas 'MesNumero' (1-12) e 'Receita'.
        sazonalidade: (Opcional) DataFrame com colunas 'MesNumero' e
                      'Fator_Sazonal', retornado por sazonalidade_analysis().

    Returns:
        Dict com projeções simples, projeções ajustadas, tendência,
        confiança e insight automático.
    """
    if monthly.empty or "Receita" not in monthly.columns:
        return {
            "run_rate_3m": 0, "run_rate_6m": 0, "run_rate_12m": 0,
            "run_rate_3m_ajustado": 0, "run_rate_6m_ajustado": 0,
            "run_rate_12m_ajustado": 0,
            "tendencia": "estável", "confianca": "baixa",
            "tem_sazonalidade": False, "insight": "",
        }

    receita = monthly["Receita"].tail(12)

    if len(receita) < 3:
        return {
            "run_rate_3m": 0, "run_rate_6m": 0, "run_rate_12m": 0,
            "run_rate_3m_ajustado": 0, "run_rate_6m_ajustado": 0,
            "run_rate_12m_ajustado": 0,
            "tendencia": "estável", "confianca": "baixa",
            "tem_sazonalidade": False, "insight": "",
        }

    rr3 = float(receita.tail(3).mean() * 12)
    rr6 = float(receita.tail(6).mean() * 12)
    rr12 = float(receita.tail(12).mean() * 12) if len(receita) >= 12 else rr6

    # ── Projeção com ajuste sazonal ──
    tem_saz = False
    rr3_ajustado = rr3
    rr6_ajustado = rr6
    rr12_ajustado = rr12
    insight = ""

    if (
        sazonalidade is not None
        and not sazonalidade.empty
        and "MesNumero" in sazonalidade.columns
        and "Fator_Sazonal" in sazonalidade.columns
    ):
        # Mapeia MesNumero → Fator_Sazonal
        fatores = dict(zip(sazonalidade["MesNumero"], sazonalidade["Fator_Sazonal"]))

        # Dessazonaliza cada mês: Receita / Fator_Sazonal
        # Precisa de MesNumero em monthly para fazer o lookup
        if "MesNumero" in monthly.columns:
            # Trabalha com os mesmos últimos 12 meses, mas usando índice
            # alinhado com MesNumero
            tail_df = monthly.tail(12).copy()
            if len(tail_df) >= 3:
                # Mapeia fator sazonal para cada linha
                fatores_alinhados = tail_df["MesNumero"].map(fatores).fillna(1.0)
                # Evita divisão por zero
                fatores_alinhados = fatores_alinhados.replace(0, 1.0)
                receita_ajustada = tail_df["Receita"] / fatores_alinhados

                if len(receita_ajustada) >= 3:
                    rr3_ajustado = float(receita_ajustada.tail(3).mean() * 12)
                if len(receita_ajustada) >= 6:
                    rr6_ajustado = float(receita_ajustada.tail(6).mean() * 12)
                if len(receita_ajustada) >= 12:
                    rr12_ajustado = float(receita_ajustada.tail(12).mean() * 12)
                else:
                    rr12_ajustado = rr6_ajustado

                tem_saz = True

    # ── Insight automático ──
    if tem_saz and rr12 > 0:
        diff_pct = (rr12_ajustado - rr12) / rr12 * 100
        if abs(diff_pct) < 2:
            insight = (
                f"Projeção ajustada ({fmt_currency(rr12_ajustado)}) "
                f"praticamente igual à simples ({fmt_currency(rr12)}). "
                f"A sazonalidade tem baixo impacto na projeção anual — "
                f"os picos e vales se compensam ao longo do ano."
            )
        elif diff_pct > 0:
            insight = (
                f"Projeção ajustada ({fmt_currency(rr12_ajustado)}) é "
                f"{diff_pct:+.1f}% maior que a simples ({fmt_currency(rr12)}). "
                f"Os meses recentes estão abaixo da média sazonal esperada, "
                f"então a projeção ajustada indica potencial de recuperação. "
                f"Considere metas mais ambiciosas se a sazonalidade se confirmar."
            )
        else:
            insight = (
                f"Projeção ajustada ({fmt_currency(rr12_ajustado)}) é "
                f"{diff_pct:+.1f}% menor que a simples ({fmt_currency(rr12)}). "
                f"Os meses recentes estão acima da média sazonal — "
                f"a projeção simples pode estar superestimando. "
                f"Recomenda-se cautela e metas mais conservadoras."
            )

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
        "run_rate_3m_ajustado": rr3_ajustado,
        "run_rate_6m_ajustado": rr6_ajustado,
        "run_rate_12m_ajustado": rr12_ajustado,
        "tendencia": tendencia,
        "confianca": confianca,
        "tem_sazonalidade": tem_saz,
        "insight": insight,
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

    # Fator Sazonal: razão entre a média do mês e a média global
    media_global = result["Receita_Media"].mean()
    if media_global > 0:
        result["Fator_Sazonal"] = result["Receita_Media"] / media_global
    else:
        result["Fator_Sazonal"] = 1.0

    return result.sort_values("MesNumero")


@st.cache_data(ttl=300, show_spinner=False)
def produto_margem_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Analisa margem unitária por produto usando Preco_Unitario e Custo_Unitario.

    Calcula para cada produto:
        - Receita_Total: receita bruta acumulada
        - Margem_Unitaria: margem bruta por unidade (Preco_Unitario - custo_unitario)
        - Margem_Pct: margem percentual sobre o preço
        - Ticket_Medio: valor médio por pedido
        - Rank: posição no ranking de margem (1 = maior margem)

    As colunas Preco_Unitario e custo_unitario são case-insensitive
    (aceita Preco_Unitario/Preço_Unitário e Custo_Unitario/custo_unitario).

    Returns:
        DataFrame ordenado por Margem_Pct decrescente, ou vazio se dados insuficientes.
    """
    if df.empty or "Produto" not in df.columns:
        return pd.DataFrame()

    # Detecta colunas de preço e custo unitário (case-insensitive)
    cols_lower = {c.lower(): c for c in df.columns}
    preco_col = cols_lower.get("preco_unitario")
    custo_col = cols_lower.get("custo_unitario")

    if preco_col is None or custo_col is None:
        return pd.DataFrame()

    result = (
        df.groupby("Produto", as_index=False)
        .agg(
            Receita_Total=("Receita", "sum"),
            Quantidade_Total=("Quantidade", "sum"),
            Pedidos=("ID_Pedido", "nunique"),
            Preco_Medio=(preco_col, "mean"),
            Custo_Medio=(custo_col, "mean"),
        )
    )

    result["Margem_Unitaria"] = result["Preco_Medio"] - result["Custo_Medio"]
    result["Margem_Pct"] = np.where(
        result["Preco_Medio"] != 0,
        result["Margem_Unitaria"] / result["Preco_Medio"] * 100,
        0,
    )
    result["Ticket_Medio"] = np.where(
        result["Pedidos"] != 0,
        result["Receita_Total"] / result["Pedidos"],
        0,
    )
    # Rank: 1 = maior margem percentual
    result["Rank"] = result["Margem_Pct"].rank(ascending=False, method="dense").astype(int)

    return result.sort_values("Margem_Pct", ascending=False)
