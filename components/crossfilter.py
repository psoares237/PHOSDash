"""Motor de cross-filtering estilo Power BI.

Renderização de filtros (selectboxes, barra de filtros ativos).
Lógica de estado delegada para state.filters.FilterState.
Compatibilidade retroativa mantida via funções wrapper.
"""

import streamlit as st
import pandas as pd

from state.filters import FilterState

# ── Funções de compatibilidade retroativa ──
# Mantidas para não quebrar imports existentes.
# Internamente delegam para FilterState.


def get_filters(page_key: str) -> dict:
    """Retorna filtros ativos da página (compatibilidade)."""
    return FilterState(page_key).filters


def set_filter(page_key: str, column: str, value):
    """Define um filtro (compatibilidade)."""
    FilterState(page_key).set(column, value)


def clear_filter(page_key: str, column: str):
    """Remove um filtro (compatibilidade)."""
    FilterState(page_key).clear(column)


def clear_all(page_key: str):
    """Remove todos os filtros da página (compatibilidade)."""
    FilterState(page_key).clear_all()


def toggle_filter(page_key: str, column: str, value):
    """Toggle de filtro (compatibilidade)."""
    FilterState(page_key).toggle(column, value)


def apply_filters(df: pd.DataFrame, page_key: str) -> pd.DataFrame:
    """Filtra DataFrame pelos cross-filters ativos (compatibilidade)."""
    return FilterState(page_key).apply(df)


def has_filters(page_key: str) -> bool:
    """Verifica se há filtros ativos na página (compatibilidade)."""
    return FilterState(page_key).has_filters


# ── Reexportações de analytics_service (compatibilidade) ──
# Lazy: evita conflito com @st.cache_data no runtime do Streamlit

def grouped_sales(*args, **kwargs):
    from services.analytics_service import grouped_sales as _fn
    return _fn(*args, **kwargs)

def monthly_sales(*args, **kwargs):
    from services.analytics_service import monthly_sales as _fn
    return _fn(*args, **kwargs)

def recompute_total(*args, **kwargs):
    from services.analytics_service import recompute_total as _fn
    return _fn(*args, **kwargs)

def recompute_aggregations(*args, **kwargs):
    from services.analytics_service import recompute_aggregations as _fn
    return _fn(*args, **kwargs)


# ── Renderização ──


def render_filter_bar(page_key: str):
    """Renderiza barra de filtros ativos com badges e botão limpar."""
    fs = FilterState(page_key)
    has_filtros = fs.has_filters

    # Funções de callback para limpar filtros
    def _clear_one(col_name: str = ""):
        fs.clear(col_name)

    def _clear_all_filters():
        fs.clear_all()

    st.markdown("---")
    if has_filtros:
        n_filtros = len(fs.filters)
        total_cols = 2 * n_filtros + 1
        cols = st.columns(total_cols)

        for i, (col_name, val) in enumerate(fs.filters.items()):
            with cols[2 * i]:
                st.markdown(
                    f'<span class="cf-badge">🏷️ <strong>{col_name}</strong>: {val}</span>',
                    unsafe_allow_html=True,
                )
            with cols[2 * i + 1]:
                st.button(
                    "✕",
                    key=f"cf_clear_one_{page_key}_{col_name}",
                    help=f"Remover filtro {col_name}",
                    on_click=_clear_one,
                    kwargs={"col_name": col_name},
                )

        with cols[-1]:
            st.button(
                "🗑️ Limpar Todos",
                key=f"cf_clear_{page_key}",
                on_click=_clear_all_filters,
            )
    else:
        st.button("🗑️ Limpar Todos", key=f"cf_clear_{page_key}", disabled=True)

    st.markdown("---")


def render_dimension_filters(
    page_key: str,
    df: pd.DataFrame,
    dimensions: list[tuple[str, str]],
):
    """Renderiza selectboxes para cada dimensão.

    Args:
        page_key: Identificador da página.
        df: DataFrame original (não filtrado).
        dimensions: Lista de (coluna, label)
                     ex: [("Categoria", "Categoria"), ("Canal_Venda", "Canal")]
    """
    fs = FilterState(page_key)
    n = len(dimensions)
    if n == 0:
        return

    cols = st.columns(n)

    for i, (col_name, label) in enumerate(dimensions):
        with cols[i]:
            if col_name not in df.columns:
                continue

            options = sorted(df[col_name].unique().tolist())
            current = fs.get(col_name)
            options_with_all = ["Todos"] + options

            idx = 0
            if current and current in options_with_all:
                idx = options_with_all.index(current)

            selected = st.selectbox(
                f"🔍 {label}",
                options=options_with_all,
                index=idx,
                key=f"cf_sel_{page_key}_{col_name}",
            )

            if selected == "Todos":
                if fs.get(col_name) is not None:
                    fs.clear(col_name)
                    st.rerun()
            else:
                if fs.get(col_name) != selected:
                    fs.set(col_name, selected)
                    st.rerun()