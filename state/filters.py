"""Gerenciador de filtros — lógica pura, Streamlit como backend de persistência.

Toda leitura/escrita de session_state passa por esta classe. Testável
isoladamente (basta injetar um dict como store). Preparado para migração
futura para FastAPI ou outro backend (trocar o store).

Responsabilidades:
- get/set/toggle/clear de filtros por página
- apply: filtrar DataFrame pelos filtros ativos
- has_filters: verificar se há filtros ativos
- clear_all: limpar todos os filtros de uma página

NÃO renderiza nada — renderização continua em crossfilter.py.
"""

import pandas as pd
import streamlit as st

PREFIX = "cf_"


class FilterState:
    """Gerenciador de filtros por página — bridge entre lógica pura e session_state.

    Uso:
        fs = FilterState("overview")
        fs.set("Categoria", "Esportes")
        fs.has_filters  # True
        filtered_df = fs.apply(df)
        fs.toggle("Categoria", "Esportes")  # remove
        fs.clear_all()
    """

    def __init__(self, page_key: str, store=None):
        """Inicializa o FilterState.

        Args:
            page_key: Identificador da página (ex: "overview", "receita").
            store: Backend de persistência. Default: st.session_state.
                   Para testes, passe um dict simples.
        """
        self.page_key = page_key
        self._key = f"{PREFIX}{page_key}"
        self._store = store  # None = usa st.session_state

    # ── Leitura ──

    @property
    def filters(self) -> dict:
        """Retorna todos os filtros ativos da página."""
        if self._store is not None:
            return self._store.get(self._key, {})
        return st.session_state.get(self._key, {})

    def get(self, column: str):
        """Retorna o valor do filtro para uma coluna, ou None."""
        return self.filters.get(column)

    @property
    def has_filters(self) -> bool:
        """True se há pelo menos um filtro ativo."""
        return bool(self.filters)

    # ── Escrita ──

    def set(self, column: str, value):
        """Define um filtro para uma coluna."""
        if self._store is not None:
            if self._key not in self._store:
                self._store[self._key] = {}
            self._store[self._key][column] = value
        else:
            if self._key not in st.session_state:
                st.session_state[self._key] = {}
            st.session_state[self._key][column] = value

    def toggle(self, column: str, value):
        """Seleciona ou desseleciona um filtro (toggle)."""
        if self.filters.get(column) == value:
            self.clear(column)
        else:
            self.set(column, value)

    def clear(self, column: str):
        """Remove o filtro de uma coluna específica."""
        if self._store is not None:
            if self._key in self._store and column in self._store[self._key]:
                del self._store[self._key][column]
        else:
            if self._key in st.session_state and column in st.session_state[self._key]:
                del st.session_state[self._key][column]
            # Remove o widget específico para forçar reset visual
            _widget_keys_to_clear = [
                k for k in st.session_state
                if k.startswith(f"cf_sel_{self.page_key}_{column}")
            ]
            for _k in _widget_keys_to_clear:
                del st.session_state[_k]

    def clear_all(self):
        """Remove todos os filtros da página."""
        if self._store is not None:
            self._store[self._key] = {}
        else:
            st.session_state[self._key] = {}
            # Incrementa reset counter para forçar recriação dos widgets
            _reset_key = f"cf_reset_{self.page_key}"
            st.session_state[_reset_key] = st.session_state.get(_reset_key, 0) + 1
            # Limpa widgets de selectbox
            _widget_prefix = f"cf_sel_{self.page_key}_"
            _to_delete = [k for k in st.session_state if k.startswith(_widget_prefix)]
            for _k in _to_delete:
                del st.session_state[_k]

    # ── Filtragem ──

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filtra o DataFrame pelos filtros ativos.

        Args:
            df: DataFrame original (não filtrado).

        Returns:
            DataFrame filtrado por todos os filtros ativos.
        """
        result = df.copy()
        for col, val in self.filters.items():
            if col in result.columns:
                result = result[result[col] == val]
        return result