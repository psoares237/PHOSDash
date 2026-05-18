"""Testes dos serviços de analytics."""

import pandas as pd
import numpy as np
import pytest

from services.analytics_service import grouped_sales, monthly_sales, top_share


def _sample_df():
    """Cria DataFrame de vendas fictício para testes."""
    dates = pd.date_range("2023-01-01", periods=6, freq="MS")
    rows = []
    for i, d in enumerate(dates):
        for cat in ["Esportes", "Informática"]:
            for canal in ["Site Próprio", "Marketplace"]:
                rows.append({
                    "Mes": d.to_period("M"),
                    "Data": d,
                    "Receita": 1000 + i * 100,
                    "Lucro": 300 + i * 30,
                    "Custo": 700 + i * 70,
                    "ID_Pedido": f"P{i}_{cat[:3]}_{canal[:3]}",
                    "Quantidade": 5 + i,
                    "Desconto_Pct": 5.0,
                    "Frete": 20.0,
                    "Categoria": cat,
                    "Canal_Venda": canal,
                    "Regiao": "Sudeste",
                    "Vendedor": "Ana",
                    "Produto": f"Produto_{i}",
                })
    return pd.DataFrame(rows)


class TestGroupedSales:
    def test_grouped_by_category(self):
        df = _sample_df()
        result = grouped_sales(df, "Categoria")
        assert not result.empty
        assert "Receita" in result.columns
        assert "Margem" in result.columns
        assert len(result) == 2  # Esportes, Informática

    def test_grouped_by_channel(self):
        df = _sample_df()
        result = grouped_sales(df, "Canal_Venda")
        assert len(result) == 2  # Site Próprio, Marketplace

    def test_margem_calculation(self):
        df = _sample_df()
        result = grouped_sales(df, "Categoria")
        for _, row in result.iterrows():
            expected = row["Lucro"] / row["Receita"] * 100
            assert abs(row["Margem"] - expected) < 0.01


class TestMonthlySales:
    def test_monthly_has_meslabel(self):
        df = _sample_df()
        result = monthly_sales(df)
        assert "MesLabel" in result.columns

    def test_monthly_cumulative(self):
        df = _sample_df()
        result = monthly_sales(df)
        assert "Acumulado_Receita" in result.columns
        assert "Acumulado_Lucro" in result.columns

    def test_mom_columns(self):
        df = _sample_df()
        result = monthly_sales(df)
        assert "MoM_Receita" in result.columns
        assert "MoM_Lucro" in result.columns


class TestTopShare:
    def test_top_share_category(self):
        df = _sample_df()
        # Não há dominância → top share < 100%
        name, share = top_share(df, "Categoria")
        assert name in ["Esportes", "Informática"]
        assert share > 0

    def test_top_share_empty(self):
        df = pd.DataFrame()
        name, share = top_share(df, "Categoria")
        assert name == "Sem dados"
        assert share == 0


class TestInsightsEngine:
    def test_generate_insights_basic(self):
        from services.insights_engine import generate_insights
        df = _sample_df()
        total = {
            "receita": 100_000, "lucro": 43_000, "custo": 57_000,
            "pedidos": 500, "frete": 5000, "desconto_medio": 8.0,
        }
        insights = generate_insights(df, total)
        assert len(insights) >= 2
        assert any(i["title"] == "Receita em destaque" for i in insights)

    def test_generate_insights_with_previous(self):
        from services.insights_engine import generate_insights
        df = _sample_df()
        total = {
            "receita": 120_000, "lucro": 50_000, "custo": 70_000,
            "pedidos": 600, "frete": 5000, "desconto_medio": 8.0,
        }
        previous = {
            "receita": 100_000, "lucro": 40_000, "custo": 60_000,
            "pedidos": 500, "frete": 4000, "desconto_medio": 7.0,
        }
        insights = generate_insights(df, total, previous)
        assert any("Crescimento" in i["title"] for i in insights)