"""Serviços de análise — agragações e KPIs."""

import streamlit as st
import numpy as np
import pandas as pd

from utils.formatters import month_label


@st.cache_data(ttl=300, show_spinner=False)
def grouped_sales(df: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Agrupa vendas por dimensão (Categoria, Canal_Venda, Regiao, Vendedor, Produto).

    Cache: 5 minutos, invalida automaticamente quando o DataFrame muda (hash).
    """
    out = (
        df.groupby(dimension, as_index=False)
        .agg(
            Receita=("Receita", "sum"),
            Lucro=("Lucro", "sum"),
            Custo=("Custo", "sum"),
            Pedidos=("ID_Pedido", "nunique"),
            Quantidade=("Quantidade", "sum"),
            Desconto_Medio=("Desconto_Pct", "mean"),
            Frete_Medio=("Frete", "mean"),
            Frete=("Frete", "sum"),
        )
        .sort_values("Receita", ascending=False)
    )
    out["Margem"] = np.where(out["Receita"] != 0, out["Lucro"] / out["Receita"] * 100, 0)
    out["Lucro_Liquido"] = out["Lucro"] - out["Frete"]
    return out


@st.cache_data(ttl=300, show_spinner=False)
def monthly_sales(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa vendas por mês com indicadores acumulados e MoM.

    Cache: 5 minutos.
    """
    monthly = (
        df.groupby("Mes", as_index=False)
        .agg(
            Receita=("Receita", "sum"),
            Lucro=("Lucro", "sum"),
            Custo=("Custo", "sum"),
            Pedidos=("ID_Pedido", "nunique"),
            Quantidade=("Quantidade", "sum"),
            Frete=("Frete", "sum"),
            Desconto_Medio=("Desconto_Pct", "mean"),
        )
        .sort_values("Mes")
    )
    monthly["Data"] = monthly["Mes"].dt.to_timestamp()
    monthly["Margem"] = np.where(
        monthly["Receita"] != 0,
        monthly["Lucro"] / monthly["Receita"] * 100,
        0,
    )
    monthly["Lucro_Liquido"] = monthly["Lucro"] - monthly["Frete"]
    monthly["Acumulado_Receita"] = monthly["Receita"].cumsum()
    monthly["Acumulado_Lucro"] = monthly["Lucro"].cumsum()
    monthly["MoM_Receita"] = monthly["Receita"].pct_change() * 100
    monthly["MoM_Lucro"] = monthly["Lucro"].pct_change() * 100
    # YoY (Year-over-Year) — comparação com mesmo mês do ano anterior
    monthly["Receita_Mes_Anterior_Ano"] = monthly["Receita"].shift(12)
    monthly["Receita_YoY_Var"] = monthly["Receita"] - monthly["Receita_Mes_Anterior_Ano"]
    monthly["Receita_YoY_Pct"] = np.where(
        monthly["Receita_Mes_Anterior_Ano"].notna() & (monthly["Receita_Mes_Anterior_Ano"] != 0),
        (monthly["Receita"] - monthly["Receita_Mes_Anterior_Ano"]) / monthly["Receita_Mes_Anterior_Ano"] * 100,
        np.nan,
    )
    monthly["Ano"] = monthly["Data"].dt.year
    monthly["MesNumero"] = monthly["Data"].dt.month
    monthly["MesLabel"] = monthly["Data"].apply(month_label)
    return monthly


def top_share(df: pd.DataFrame, column: str) -> tuple[str, float]:
    """Retorna (nome_do_top, share%) da maior receita na coluna."""
    if df.empty or column not in df.columns:
        return "Sem dados", 0
    grouped = (
        df.groupby(column, as_index=False)["Receita"]
        .sum()
        .sort_values("Receita", ascending=False)
    )
    if grouped.empty:
        return "Sem dados", 0
    top_name = grouped.iloc[0][column]
    total = grouped["Receita"].sum()
    share = grouped.iloc[0]["Receita"] / total * 100 if total else 0
    return str(top_name), share


@st.cache_data(ttl=300, show_spinner=False)
def recompute_total(df: pd.DataFrame) -> dict:
    """Recalcula KPIs a partir do DataFrame filtrado.

    Cache: 5 minutos.
    """
    if df.empty:
        return {
            "receita": 0, "lucro": 0, "custo": 0,
            "pedidos": 0, "qtd": 0, "frete": 0, "desconto_medio": 0,
            "vendedores": 0, "qtd_total": 0,
        }
    return {
        "receita": df["Receita"].sum(),
        "lucro": df["Lucro"].sum(),
        "custo": df["Custo"].sum(),
        "pedidos": df["ID_Pedido"].nunique(),
        "qtd": df["Quantidade"].sum(),
        "frete": df["Frete"].sum(),
        "desconto_medio": df["Desconto_Pct"].mean(),
        "vendedores": df["Vendedor"].nunique() if "Vendedor" in df.columns else 0,
        "qtd_total": df["Quantidade"].sum() if "Quantidade" in df.columns else 0,
    }


@st.cache_data(ttl=300, show_spinner=False)
def recompute_aggregations(df: pd.DataFrame) -> dict:
    """Recomputa todas as agregações a partir do DataFrame filtrado.

    Cache: 5 minutos.
    """
    return {
        "current_df": df,
        "current_total": recompute_total(df),
        "monthly": monthly_sales(df) if not df.empty else pd.DataFrame(),
        "cat": grouped_sales(df, "Categoria").sort_values("Receita", ascending=False) if not df.empty else pd.DataFrame(),
        "canal": grouped_sales(df, "Canal_Venda").sort_values("Receita", ascending=False) if not df.empty else pd.DataFrame(),
        "regiao": grouped_sales(df, "Regiao").sort_values("Receita", ascending=False) if not df.empty else pd.DataFrame(),
        "vendedor": grouped_sales(df, "Vendedor").sort_values("Receita", ascending=False) if not df.empty else pd.DataFrame(),
        "produto": grouped_sales(df, "Produto").sort_values("Receita", ascending=False) if not df.empty else pd.DataFrame(),
    }