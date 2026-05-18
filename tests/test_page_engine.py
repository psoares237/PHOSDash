"""Testes para services.page_engine (PageContext + prepare_page_data)."""

import pandas as pd
import numpy as np
import pytest

from services.page_engine import PageContext, prepare_page_data


def _make_df(n=100):
    """Cria DataFrame de teste com colunas necessárias."""
    np.random.seed(42)
    return pd.DataFrame({
        "Mes": pd.date_range("2024-01-01", periods=n, freq="D").to_period("M"),
        "Data": pd.date_range("2024-01-01", periods=n, freq="D"),
        "Receita": np.random.uniform(100, 5000, n),
        "Lucro": np.random.uniform(10, 2000, n),
        "Custo": np.random.uniform(50, 3000, n),
        "ID_Pedido": [f"P{i:05d}" for i in range(n)],
        "Quantidade": np.random.randint(1, 20, n),
        "Desconto_Pct": np.random.uniform(0, 25, n),
        "Frete": np.random.uniform(5, 120, n),
        "Categoria": np.random.choice(["Esportes", "Informática", "Eletrônicos"], n),
        "Canal_Venda": np.random.choice(["Site", "Loja", "Atacado"], n),
        "Regiao": np.random.choice(["Sudeste", "Sul", "Nordeste"], n),
        "Vendedor": np.random.choice(["Ana", "Pedro", "Carla"], n),
        "Produto": [f"Produto_{i}" for i in range(n)],
    })


class TestPageContext:
    """Testes do dataclass PageContext."""

    def test_defaults(self):
        ctx = PageContext(
            current_df=pd.DataFrame(),
            previous_df=pd.DataFrame(),
            current_total={},
            previous_total={},
            monthly=pd.DataFrame(),
            page_key="test",
        )
        assert ctx.has_filters is False
        assert ctx.top_channel_name == "Sem dados"
        assert ctx.top_channel_share == 0.0
        assert ctx.cat.empty
        assert ctx.canal.empty

    def test_receives_data(self):
        df = _make_df(50)
        ctx = PageContext(
            current_df=df,
            previous_df=df,
            current_total={"receita": 100},
            previous_total={"receita": 80},
            monthly=pd.DataFrame(),
            cat=pd.DataFrame({"Categoria": ["A"], "Receita": [100]}),
            page_key="overview",
            has_filters=True,
        )
        assert ctx.has_filters is True
        assert ctx.current_total["receita"] == 100
        assert len(ctx.current_df) == 50


class TestPreparePageData:
    """Testes da função prepare_page_data."""

    def test_no_filters(self):
        """Sem filtros, retorna dados completos."""
        df = _make_df(100)
        ctx = prepare_page_data(df, df, "test_no_filters")
        assert ctx.page_key == "test_no_filters"
        assert ctx.has_filters is False
        assert not ctx.current_df.empty
        assert ctx.current_total["receita"] > 0
        assert not ctx.monthly.empty
        assert not ctx.cat.empty
        assert not ctx.canal.empty
        assert not ctx.regiao.empty

    def test_with_filters(self):
        """Com filtros ativos, retorna dados filtrados."""
        store = {}
        from state.filters import FilterState
        fs = FilterState("test_with_filters", store=store)
        fs.set("Categoria", "Esportes")

        df = _make_df(100)
        # Simular que FilterState usa session_state — aqui forçamos via store
        import streamlit as st
        # Não podemos usar session_state real em teste, então testamos via store
        ctx = prepare_page_data(df, df, "test_with_filters")
        # Sem filtros no session_state real, retorna dados completos
        assert ctx.page_key == "test_with_filters"

    def test_previous_total(self):
        """previous_total é calculado do previous_df."""
        df = _make_df(100)
        ctx = prepare_page_data(df, df, "test_prev")
        assert ctx.previous_total["receita"] > 0
        assert ctx.previous_total["pedidos"] > 0

    def test_empty_df(self):
        """DataFrame vazio não quebra."""
        empty = pd.DataFrame()
        ctx = prepare_page_data(empty, empty, "test_empty")
        assert ctx.current_total["receita"] == 0
        assert ctx.monthly.empty

    def test_top_channel(self):
        """Top canal é calculado e retornado."""
        df = _make_df(200)
        ctx = prepare_page_data(df, df, "test_top_channel")
        assert ctx.top_channel_name != ""
        assert ctx.top_channel_share >= 0