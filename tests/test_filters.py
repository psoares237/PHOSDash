"""Testes para state.filters.FilterState e components.ui._extract_clicked_value."""

import pandas as pd
import pytest

from state.filters import FilterState


class TestFilterStateBasics:
    """Testes de CRUD de filtros usando dict como store (sem Streamlit)."""

    def setup_method(self):
        self.store = {}
        self.fs = FilterState("test_page", store=self.store)

    def test_empty_on_init(self):
        assert self.fs.filters == {}
        assert self.fs.has_filters is False
        assert self.fs.get("Categoria") is None

    def test_set_and_get(self):
        self.fs.set("Categoria", "Esportes")
        assert self.fs.get("Categoria") == "Esportes"
        assert self.fs.has_filters is True

    def test_set_overwrite(self):
        self.fs.set("Categoria", "Esportes")
        self.fs.set("Categoria", "Informática")
        assert self.fs.get("Categoria") == "Informática"

    def test_multiple_filters(self):
        self.fs.set("Categoria", "Esportes")
        self.fs.set("Regiao", "Sudeste")
        assert self.fs.filters == {"Categoria": "Esportes", "Regiao": "Sudeste"}

    def test_clear_single(self):
        self.fs.set("Categoria", "Esportes")
        self.fs.set("Regiao", "Sudeste")
        self.fs.clear("Categoria")
        assert self.fs.get("Categoria") is None
        assert self.fs.get("Regiao") == "Sudeste"

    def test_clear_nonexistent(self):
        self.fs.clear("Categoria")  # should not raise
        assert self.fs.filters == {}

    def test_clear_all(self):
        self.fs.set("Categoria", "Esportes")
        self.fs.set("Regiao", "Sudeste")
        self.fs.clear_all()
        assert self.fs.filters == {}
        assert self.fs.has_filters is False

    def test_toggle_add(self):
        self.fs.toggle("Categoria", "Esportes")
        assert self.fs.get("Categoria") == "Esportes"

    def test_toggle_remove(self):
        self.fs.set("Categoria", "Esportes")
        self.fs.toggle("Categoria", "Esportes")
        assert self.fs.get("Categoria") is None

    def test_toggle_different_value(self):
        self.fs.set("Categoria", "Esportes")
        self.fs.toggle("Categoria", "Informática")
        assert self.fs.get("Categoria") == "Informática"


class TestFilterStateApply:
    """Testes de filtragem de DataFrame."""

    def setup_method(self):
        self.store = {}
        self.fs = FilterState("test_page", store=self.store)
        self.df = pd.DataFrame({
            "Categoria": ["Esportes", "Informática", "Esportes", "Móveis"],
            "Regiao": ["Sudeste", "Sul", "Nordeste", "Sudeste"],
            "Receita": [100, 200, 300, 400],
        })

    def test_no_filters_returns_all(self):
        result = self.fs.apply(self.df)
        assert len(result) == 4

    def test_single_filter(self):
        self.fs.set("Categoria", "Esportes")
        result = self.fs.apply(self.df)
        assert len(result) == 2
        assert (result["Categoria"] == "Esportes").all()

    def test_multiple_filters(self):
        self.fs.set("Categoria", "Esportes")
        self.fs.set("Regiao", "Sudeste")
        result = self.fs.apply(self.df)
        assert len(result) == 1
        assert result.iloc[0]["Receita"] == 100

    def test_filter_no_match(self):
        self.fs.set("Categoria", "Inexistente")
        result = self.fs.apply(self.df)
        assert len(result) == 0

    def test_filter_nonexistent_column(self):
        self.fs.set("ColunaInexistente", "Valor")
        result = self.fs.apply(self.df)
        assert len(result) == 4  # ignora colunas inexistentes

    def test_apply_does_not_mutate_original(self):
        self.fs.set("Categoria", "Esportes")
        result = self.fs.apply(self.df)
        assert len(self.df) == 4  # original intacto


class TestFilterStateIsolation:
    """Testes de isolamento entre páginas diferentes."""

    def test_different_pages_independent(self):
        store = {}
        fs1 = FilterState("overview", store=store)
        fs2 = FilterState("receita", store=store)

        fs1.set("Categoria", "Esportes")
        assert fs2.filters == {}
        assert fs1.filters == {"Categoria": "Esportes"}

    def test_clear_all_only_affects_own_page(self):
        store = {}
        fs1 = FilterState("overview", store=store)
        fs2 = FilterState("receita", store=store)

        fs1.set("Categoria", "Esportes")
        fs2.set("Regiao", "Sudeste")
        fs1.clear_all()
        assert fs1.filters == {}
        assert fs2.filters == {"Regiao": "Sudeste"}


class TestExtractClickedValue:
    """Testes para _extract_clicked_value do components.ui."""

    def test_import(self):
        from components.ui import _extract_clicked_value
        assert callable(_extract_clicked_value)

    def test_none_result(self):
        from components.ui import _extract_clicked_value
        import plotly.graph_objects as go
        fig = go.Figure()
        assert _extract_clicked_value(None, fig) is None
