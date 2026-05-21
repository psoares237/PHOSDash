"""Motor central de preparação de dados por página.

Centraliza toda a lógica de filtros, agregações e totais que antes era
repetida em cada bloco de página do app.py. Cada página agora chama
prepare_page_data() e recebe um PageContext pronto para consumo.

Responsabilidades:
- Verificar filtros ativos (via crossfilter)
- Aplicar filtros ao DataFrame
- Calcular totais (current + previous)
- Calcular agregações (monthly, cat, canal, regiao, vendedor, produto)
- Retornar tudo empacotado num PageContext
"""

from dataclasses import dataclass, field
import pandas as pd
import streamlit as st


@dataclass
class PageContext:
    """Contexto completo de dados pronto para consumo pela view.

    Atributos:
        current_df:        DataFrame filtrado (ou original se sem filtros).
        previous_df:       DataFrame do período anterior (não filtrado por cross-filter).
        current_total:      Dict com KPIs do período atual.
        previous_total:     Dict com KPIs do período anterior.
        monthly:           DataFrame de vendas mensais.
        cat:               DataFrame de vendas por Categoria.
        canal:             DataFrame de vendas por Canal de Venda.
        regiao:            DataFrame de vendas por Região.
        vendedor:          DataFrame de vendas por Vendedor.
        produto:           DataFrame de vendas por Produto.
        top_channel_name:  Nome do canal líder.
        top_channel_share: Share (%) do canal líder.
        page_key:          Identificador da página (ex: "overview", "receita").
        has_filters:       Se há cross-filters ativos nesta página.
    """

    current_df: pd.DataFrame
    previous_df: pd.DataFrame
    current_total: dict
    previous_total: dict
    monthly: pd.DataFrame
    cat: pd.DataFrame = field(default_factory=pd.DataFrame)
    canal: pd.DataFrame = field(default_factory=pd.DataFrame)
    regiao: pd.DataFrame = field(default_factory=pd.DataFrame)
    vendedor: pd.DataFrame = field(default_factory=pd.DataFrame)
    produto: pd.DataFrame = field(default_factory=pd.DataFrame)
    top_channel_name: str = "Sem dados"
    top_channel_share: float = 0.0
    page_key: str = ""
    has_filters: bool = False


@st.cache_data(ttl=300, show_spinner=False)
def prepare_page_data(
    current_df: pd.DataFrame,
    previous_df: pd.DataFrame,
    page_key: str,
    has_filters: bool = False,
) -> PageContext:
    """Prepara todos os dados para uma página: agregações, totais.

    O caller (app.py) já aplicou os cross-filtros no current_df.
    Esta função é pura: recebe DataFrames e retorna PageContext,
    sem dependência de session_state. Cacheada por 5 minutos.

    Args:
        current_df:   DataFrame já filtrado (ou original, se sem filtros).
        previous_df:  DataFrame do período anterior.
        page_key:     Identificador da página (ex: "overview").
        has_filters:  Se há cross-filtros ativos nesta página.

    Returns:
        PageContext com todos os dados prontos para a view.
    """
    # Lazy imports — evita conflito com @st.cache_data no runtime do Streamlit
    from services.analytics_service import (
        grouped_sales, monthly_sales, recompute_total, top_share,
    )

    # Guarda: DataFrame vazio ou sem colunas essenciais
    required_cols = {"Receita", "Mes"}
    empty_result = PageContext(
        current_df=current_df,
        previous_df=previous_df,
        current_total=recompute_total(current_df),
        previous_total=recompute_total(previous_df),
        monthly=pd.DataFrame(),
        cat=pd.DataFrame(),
        canal=pd.DataFrame(),
        regiao=pd.DataFrame(),
        vendedor=pd.DataFrame(),
        produto=pd.DataFrame(),
        page_key=page_key,
        has_filters=has_filters,
    )

    if current_df.empty or not required_cols.issubset(current_df.columns):
        return empty_result

    # Total do período atual e anterior
    current_total = recompute_total(current_df)
    previous_total = recompute_total(previous_df)

    # Agregações (current_df já está filtrado ou é o original)
    working_df = current_df
    if working_df.empty:
        monthly = pd.DataFrame()
        cat = pd.DataFrame()
        canal = pd.DataFrame()
        regiao = pd.DataFrame()
        vendedor = pd.DataFrame()
        produto = pd.DataFrame()
    else:
        monthly = monthly_sales(working_df)
        cat = grouped_sales(working_df, "Categoria")
        canal = grouped_sales(working_df, "Canal_Venda")
        regiao = grouped_sales(working_df, "Regiao")
        vendedor = grouped_sales(working_df, "Vendedor")
        produto = grouped_sales(working_df, "Produto")

    # Top canal (share)
    top_channel_name, top_channel_share = top_share(
        canal if not canal.empty else current_df, "Canal_Venda"
    )

    return PageContext(
        current_df=current_df,
        previous_df=previous_df,
        current_total=current_total,
        previous_total=previous_total,
        monthly=monthly,
        cat=cat,
        canal=canal,
        regiao=regiao,
        vendedor=vendedor,
        produto=produto,
        top_channel_name=top_channel_name,
        top_channel_share=top_channel_share,
        page_key=page_key,
        has_filters=has_filters,
    )