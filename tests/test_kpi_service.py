"""Testes dos serviços de KPIs financeiros — kpi_service.py."""

import numpy as np
import pandas as pd
import pytest

from services.kpi_service import (
    margem_contribuicao,
    hhi_index,
    hhi_by_dimensions,
    desconto_margem_correlation,
    run_rate_projection,
    forma_pagamento_analysis,
    sazonalidade_analysis,
    produto_margem_analysis,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_sales_df():
    """DataFrame de vendas sintético com colunas necessárias para todos os KPIs."""
    rng = np.random.default_rng(42)
    n = 30
    return pd.DataFrame({
        "ID_Pedido": [f"PED-{i:04d}" for i in range(n)],
        "Receita": rng.uniform(100, 1000, n).round(2),
        "Custo": rng.uniform(50, 500, n).round(2),
        "Frete": rng.uniform(10, 100, n).round(2),
        "Lucro": rng.uniform(10, 300, n).round(2),
        "Desconto_Pct": rng.uniform(0, 20, n).round(2),
        "Categoria": rng.choice(["Eletrônicos", "Esportes", "Livros"], n),
        "Canal_Venda": rng.choice(["Site Próprio", "Marketplace"], n),
        "Forma_Pagamento": rng.choice(["Cartão", "Boleto", "Pix"], n),
    })


@pytest.fixture
def sample_monthly_df():
    """DataFrame mensal com 24 meses (2 anos), colunas MesNumero (1-12) e Receita."""
    meses = list(range(1, 13)) + list(range(1, 13))
    return pd.DataFrame({
        "MesNumero": meses,
        "Receita": [1000 + i * 100 + m * 50 for i, m in enumerate(meses)],
    })


@pytest.fixture
def empty_df():
    """DataFrame vazio com as colunas esperadas."""
    return pd.DataFrame(columns=[
        "ID_Pedido", "Receita", "Custo", "Frete", "Lucro",
        "Desconto_Pct", "Categoria", "Canal_Venda", "Forma_Pagamento",
    ])


# ===================================================================
# margem_contribuicao
# ===================================================================

class TestMargemContribuicao:
    """Testes para margem_contribuicao(df)."""

    def test_happy_path(self, sample_sales_df):
        """Caso feliz: calcula Margem_Contrib e Margem_Contrib_Pct corretamente."""
        result = margem_contribuicao(sample_sales_df)
        assert "Margem_Contrib" in result.columns
        assert "Margem_Contrib_Pct" in result.columns
        # Margem_Contrib = Receita - Custo - Frete
        expected = sample_sales_df["Receita"] - sample_sales_df["Custo"] - sample_sales_df["Frete"]
        assert np.allclose(result["Margem_Contrib"], expected)

    def test_zero_receita(self):
        """Edge case: Receita = 0 deve produzir Margem_Contrib_Pct = 0, sem divisão por zero."""
        df = pd.DataFrame({
            "Receita": [0, 100, 0],
            "Custo": [10, 50, 0],
            "Frete": [5, 20, 0],
        })
        result = margem_contribuicao(df)
        assert result.loc[0, "Margem_Contrib_Pct"] == 0
        assert result.loc[2, "Margem_Contrib_Pct"] == 0
        # Linha com receita > 0 deve ter percentual calculado
        assert result.loc[1, "Margem_Contrib_Pct"] == pytest.approx(30.0, 0.01)

    def test_empty_dataframe(self):
        """Edge case: DataFrame vazio retorna DataFrame vazio com as colunas extras."""
        df = pd.DataFrame(columns=["Receita", "Custo", "Frete"])
        result = margem_contribuicao(df)
        assert result.empty
        assert "Margem_Contrib" in result.columns
        assert "Margem_Contrib_Pct" in result.columns

    def test_pct_calculation_precision(self, sample_sales_df):
        """Verifica precisão do percentual de margem."""
        result = margem_contribuicao(sample_sales_df)
        for _, row in result.iterrows():
            if row["Receita"] != 0:
                expected_pct = (row["Receita"] - row["Custo"] - row["Frete"]) / row["Receita"] * 100
                assert abs(row["Margem_Contrib_Pct"] - expected_pct) < 0.01


# ===================================================================
# hhi_index
# ===================================================================

class TestHhiIndex:
    """Testes para hhi_index(df, column)."""

    def test_normal_concentration(self):
        """Caso feliz: duas categorias com pesos diferentes geram HHI entre 0 e 10000."""
        df = pd.DataFrame({
            "Receita": [700, 300],
            "Categoria": ["A", "B"],
        })
        result = hhi_index(df, "Categoria")
        # shares: 0.7 e 0.3 → HHI = (0.7² + 0.3²) × 10000 = 5800
        assert result == pytest.approx(5800.0, 0.01)

    def test_monopoly(self):
        """Monopólio (uma única categoria) → HHI = 10000."""
        df = pd.DataFrame({
            "Receita": [500],
            "Categoria": ["A"],
        })
        result = hhi_index(df, "Categoria")
        assert result == pytest.approx(10000.0, 0.01)

    def test_perfect_competition(self):
        """Concorrência perfeita (4 segmentos iguais) → HHI = 2500."""
        df = pd.DataFrame({
            "Receita": [250, 250, 250, 250],
            "Categoria": ["A", "B", "C", "D"],
        })
        result = hhi_index(df, "Categoria")
        # shares: 0.25 each → HHI = 4 × 0.0625 × 10000 = 2500
        assert result == pytest.approx(2500.0, 0.01)

    def test_empty_dataframe(self):
        """Edge case: DataFrame vazio → retorna 0."""
        df = pd.DataFrame(columns=["Receita", "Categoria"])
        result = hhi_index(df, "Categoria")
        assert result == 0

    def test_missing_column(self):
        """Edge case: coluna não existe no DataFrame → retorna 0."""
        df = pd.DataFrame({"Receita": [100, 200]})
        result = hhi_index(df, "Categoria_Inexistente")
        assert result == 0

    def test_zero_revenue(self):
        """Edge case: Receita total = 0 → retorna 0."""
        df = pd.DataFrame({
            "Receita": [0, 0],
            "Categoria": ["A", "B"],
        })
        result = hhi_index(df, "Categoria")
        assert result == 0


# ===================================================================
# hhi_by_dimensions
# ===================================================================

class TestHhiByDimensions:
    """Testes para hhi_by_dimensions(df, dimensions)."""

    def test_all_dimensions_exist(self, sample_sales_df):
        """Caso feliz: retorna dict com HHI para cada dimensão existente."""
        result = hhi_by_dimensions(sample_sales_df, ["Categoria", "Canal_Venda"])
        assert isinstance(result, dict)
        assert "Categoria" in result
        assert "Canal_Venda" in result
        assert 0 <= result["Categoria"] <= 10000
        assert 0 <= result["Canal_Venda"] <= 10000

    def test_some_dimensions_missing(self, sample_sales_df):
        """Edge case: apenas dimensões existentes entram no resultado."""
        result = hhi_by_dimensions(sample_sales_df, ["Categoria", "Coluna_Fantasma"])
        assert "Categoria" in result
        assert "Coluna_Fantasma" not in result
        assert len(result) == 1

    def test_empty_dataframe(self):
        """Edge case: DataFrame vazio → dict vazio (nenhuma coluna existe)."""
        df = pd.DataFrame(columns=["Receita", "Categoria"])
        result = hhi_by_dimensions(df, ["Categoria"])
        # hhi_index returns 0 for empty df → key still present
        assert "Categoria" in result
        assert result["Categoria"] == 0


# ===================================================================
# desconto_margem_correlation
# ===================================================================

class TestDescontoMargemCorrelation:
    """Testes para desconto_margem_correlation(df)."""

    def test_happy_path(self, sample_sales_df):
        """Caso feliz: retorna dict com as 4 chaves esperadas."""
        result = desconto_margem_correlation(sample_sales_df)
        assert isinstance(result, dict)
        for key in ["categorias", "canais", "global_r", "insight"]:
            assert key in result
        assert -1.0 <= result["global_r"] <= 1.0
        assert isinstance(result["insight"], str)

    def test_empty_dataframe(self):
        """Edge case: DataFrame vazio → retorna dict padrão."""
        df = pd.DataFrame(columns=["Desconto_Pct", "Lucro", "Receita",
                                    "Categoria", "Canal_Venda"])
        result = desconto_margem_correlation(df)
        assert result["categorias"].empty
        assert result["canais"].empty
        assert result["global_r"] == 0.0
        assert result["insight"] == "Sem dados"

    def test_negative_correlation_insight(self):
        """Correlação negativa forte gera insight de revisão de política de desconto."""
        df = pd.DataFrame({
            "Receita": [1000] * 6,
            "Lucro": [400, 200, 50, 500, 350, 100],
            "Desconto_Pct": [0, 5, 15, 0, 2, 12],
            "Categoria": ["A", "A", "A", "B", "B", "B"],
            "Canal_Venda": ["Site", "Site", "Site", "MP", "MP", "MP"],
        })
        result = desconto_margem_correlation(df)
        assert result["global_r"] < -0.3
        assert "revisar política de desconto" in result["insight"].lower()

    def test_output_structure(self, sample_sales_df):
        """Verifica estrutura dos DataFrames de categorias e canais."""
        result = desconto_margem_correlation(sample_sales_df)
        cat_df = result["categorias"]
        can_df = result["canais"]
        assert isinstance(cat_df, pd.DataFrame)
        assert isinstance(can_df, pd.DataFrame)
        if not cat_df.empty:
            for col in ["Desconto_Medio", "Margem_Media", "Receita"]:
                assert col in cat_df.columns
        if not can_df.empty:
            for col in ["Desconto_Medio", "Margem_Media", "Receita"]:
                assert col in can_df.columns


# ===================================================================
# run_rate_projection
# ===================================================================

class TestRunRateProjection:
    """Testes para run_rate_projection(monthly, sazonalidade=None)."""

    def test_12_months_normal(self):
        """Caso feliz: 12 meses de dados, confiança alta."""
        monthly = pd.DataFrame({
            "Receita": [1000 + i * 50 for i in range(12)],
        })
        result = run_rate_projection(monthly)
        assert result["run_rate_3m"] > 0
        assert result["run_rate_6m"] > 0
        assert result["run_rate_12m"] > 0
        assert result["confianca"] == "alta"
        assert result["tendencia"] in ("crescimento", "queda", "estável")
        # Novas chaves devem estar presentes
        assert "run_rate_3m_ajustado" in result
        assert "run_rate_6m_ajustado" in result
        assert "run_rate_12m_ajustado" in result
        assert "tem_sazonalidade" in result
        assert "insight" in result
        assert result["tem_sazonalidade"] is False
        assert result["insight"] == ""

    def test_empty_dataframe(self):
        """Edge case: DataFrame vazio → run rates zerados."""
        df = pd.DataFrame(columns=["Receita"])
        result = run_rate_projection(df)
        assert result["run_rate_3m"] == 0
        assert result["run_rate_6m"] == 0
        assert result["run_rate_12m"] == 0
        assert result["confianca"] == "baixa"
        assert result["tem_sazonalidade"] is False

    def test_fewer_than_3_records(self):
        """Edge case: menos de 3 registros → run rates zerados."""
        monthly = pd.DataFrame({"Receita": [1000, 1100]})
        result = run_rate_projection(monthly)
        assert result["run_rate_3m"] == 0
        assert result["run_rate_6m"] == 0
        assert result["run_rate_12m"] == 0
        assert result["confianca"] == "baixa"

    def test_tendencia_crescimento(self):
        """Receita crescente forte → tendencia='crescimento'."""
        monthly = pd.DataFrame({
            "Receita": list(range(1000, 1130, 10)),  # 13 valores crescentes
        })
        result = run_rate_projection(monthly)
        assert result["tendencia"] == "crescimento"
        assert result["confianca"] == "alta"

    def test_tendencia_queda(self):
        """Receita em queda → tendencia='queda'."""
        monthly = pd.DataFrame({
            "Receita": list(range(1200, 950, -20)),  # 13 valores decrescentes
        })
        result = run_rate_projection(monthly)
        assert result["tendencia"] == "queda"

    def test_missing_receita_column(self):
        """Edge case: coluna Receita ausente → retorna defaults."""
        monthly = pd.DataFrame({"Mes": [1, 2, 3], "Valor": [100, 200, 300]})
        result = run_rate_projection(monthly)
        assert result["run_rate_3m"] == 0
        assert result["confianca"] == "baixa"

    # ── Seasonal adjustment tests ──

    def test_with_sazonalidade(self):
        """Projeção com ajuste sazonal: flags e insight preenchidos."""
        # Receita mensal com padrão sazonal: meses altos (6-7-8) e baixos (1-2-12)
        monthly = pd.DataFrame({
            "MesNumero": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            "Receita":   [50, 60, 90, 100, 110, 140, 150, 140, 120, 100, 80, 60],
        })

        # Sazonalidade com fatores fortes
        saz = pd.DataFrame({
            "MesNumero": list(range(1, 13)),
            "Receita_Media": [55, 65, 90, 100, 110, 145, 155, 145, 120, 100, 80, 60],
            "Fator_Sazonal": [0.55, 0.65, 0.9, 1.0, 1.1, 1.45, 1.55, 1.45, 1.2, 1.0, 0.8, 0.6],
        })

        result = run_rate_projection(monthly, saz)
        assert result["tem_sazonalidade"] is True
        assert result["insight"] != ""
        assert result["run_rate_12m_ajustado"] > 0
        # Projeção ajustada deve ser diferente da simples quando há sazonalidade
        assert result["run_rate_12m_ajustado"] != result["run_rate_12m"]

    def test_sazonalidade_missing_columns(self):
        """DataFrame de sazonalidade sem colunas esperadas → ignora ajuste."""
        monthly = pd.DataFrame({
            "MesNumero": [1, 2, 3],
            "Receita": [100, 200, 300],
        })
        saz_bad = pd.DataFrame({"coluna_errada": [1, 2, 3]})
        result = run_rate_projection(monthly, saz_bad)
        assert result["tem_sazonalidade"] is False
        assert result["insight"] == ""

    def test_sazonalidade_empty(self):
        """DataFrame de sazonalidade vazio → ignora ajuste."""
        monthly = pd.DataFrame({
            "MesNumero": [1, 2, 3],
            "Receita": [100, 200, 300],
        })
        result = run_rate_projection(monthly, pd.DataFrame())
        assert result["tem_sazonalidade"] is False

    def test_sazonalidade_no_mesnumero_in_monthly(self):
        """Monthly sem MesNumero → não consegue alinhar fatores, ajuste ignorado."""
        monthly = pd.DataFrame({
            "Receita": [100, 200, 300, 400, 500, 600],
        })
        saz = pd.DataFrame({
            "MesNumero": [1, 2],
            "Fator_Sazonal": [0.8, 1.2],
        })
        result = run_rate_projection(monthly, saz)
        assert result["tem_sazonalidade"] is False

    def test_sazonalidade_adjusted_values_match_expected(self):
        """Verifica matemática da projeção ajustada."""
        # Dados: mês 1 fator 0.5 (mês fraco), mês 2 fator 2.0 (mês forte)
        # Receita: mês 1 = 100, mês 2 = 400
        # Ajustado: mês 1 = 100/0.5 = 200, mês 2 = 400/2.0 = 200
        # Média ajustada = 200, run rate 12m ajustado = 200 * 12 = 2400
        monthly = pd.DataFrame({
            "MesNumero": [1, 2],
            "Receita": [100, 400],
        })
        saz = pd.DataFrame({
            "MesNumero": [1, 2],
            "Fator_Sazonal": [0.5, 2.0],
        })
        result = run_rate_projection(monthly, saz)
        # Com apenas 2 registros, < 3 → zera tudo
        assert result["run_rate_3m"] == 0
        assert result["run_rate_12m"] == 0
        assert result["tem_sazonalidade"] is False

        # Com 6 meses (≥6, <12): run rate 12m = run rate 6m
        monthly6 = pd.DataFrame({
            "MesNumero": [1, 2, 1, 2, 1, 2],
            "Receita": [100, 400, 100, 400, 100, 400],
        })
        result6 = run_rate_projection(monthly6, saz)
        assert result6["tem_sazonalidade"] is True
        # Média ajustada = 200 → anualizado = 2400
        assert result6["run_rate_6m_ajustado"] == pytest.approx(2400.0, 0.01)
        assert result6["run_rate_12m_ajustado"] == pytest.approx(2400.0, 0.01)


# ===================================================================
# forma_pagamento_analysis
# ===================================================================

class TestFormaPagamentoAnalysis:
    """Testes para forma_pagamento_analysis(df)."""

    def test_happy_path(self, sample_sales_df):
        """Caso feliz: DataFrame com Margem, Share, Receita por Forma_Pagamento."""
        result = forma_pagamento_analysis(sample_sales_df)
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        for col in ["Receita", "Lucro", "Pedidos", "Ticket_Medio",
                     "Frete", "Margem", "Share"]:
            assert col in result.columns
        # Share deve somar aproximadamente 100%
        assert abs(result["Share"].sum() - 100.0) < 0.1
        # Margem deve estar entre -inf e +inf (ou 0 se Receita 0)
        assert (result["Margem"].notna()).all()

    def test_empty_dataframe(self):
        """Edge case: DataFrame vazio → retorna DataFrame vazio."""
        df = pd.DataFrame(columns=["Forma_Pagamento", "Receita", "Lucro",
                                    "ID_Pedido", "Frete"])
        result = forma_pagamento_analysis(df)
        assert result.empty
        assert isinstance(result, pd.DataFrame)

    def test_missing_forma_pagamento(self, sample_sales_df):
        """Edge case: coluna Forma_Pagamento ausente → retorna DataFrame vazio."""
        df = sample_sales_df.drop(columns=["Forma_Pagamento"])
        result = forma_pagamento_analysis(df)
        assert result.empty

    def test_single_payment_method(self):
        """Apenas uma forma de pagamento → Share = 100%."""
        df = pd.DataFrame({
            "ID_Pedido": ["P1", "P2"],
            "Receita": [500, 300],
            "Lucro": [100, 60],
            "Frete": [20, 15],
            "Forma_Pagamento": ["Cartão", "Cartão"],
        })
        result = forma_pagamento_analysis(df)
        assert len(result) == 1
        assert result.iloc[0]["Share"] == pytest.approx(100.0, 0.01)


# ===================================================================
# sazonalidade_analysis
# ===================================================================

class TestSazonalidadeAnalysis:
    """Testes para sazonalidade_analysis(monthly)."""

    def test_happy_path(self, sample_monthly_df):
        """Caso feliz: 24 meses retornam 12 linhas com MesNome, CV e Fator_Sazonal."""
        result = sazonalidade_analysis(sample_monthly_df)
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert len(result) == 12  # um por mês
        for col in ["MesNumero", "MesNome", "Receita_Media",
                     "Desvio_Padrao", "CV", "Fator_Sazonal"]:
            assert col in result.columns
        # MesNome deve ter as siglas corretas
        assert result.iloc[0]["MesNome"] == "Jan"
        assert result.iloc[11]["MesNome"] == "Dez"
        # Fator_Sazonal: média = 1.0
        assert abs(result["Fator_Sazonal"].mean() - 1.0) < 0.01

    def test_empty_dataframe(self):
        """Edge case: DataFrame vazio → retorna DataFrame vazio."""
        df = pd.DataFrame(columns=["MesNumero", "Receita"])
        result = sazonalidade_analysis(df)
        assert result.empty

    def test_missing_mesnumero(self):
        """Edge case: coluna MesNumero ausente → retorna DataFrame vazio."""
        monthly = pd.DataFrame({"Mes": [1, 2, 3], "Receita": [100, 200, 300]})
        result = sazonalidade_analysis(monthly)
        assert result.empty

    def test_cv_calculation(self):
        """Coeficiente de variação (CV) calculado como Desvio_Padrao / Receita_Media * 100."""
        monthly = pd.DataFrame({
            "MesNumero": [1, 1, 1, 2, 2, 2],
            "Receita": [100, 200, 300, 500, 600, 700],
        })
        result = sazonalidade_analysis(monthly)
        # Mês 1: média=200, std=100 → CV = 50%
        row_jan = result[result["MesNumero"] == 1].iloc[0]
        expected_cv = row_jan["Desvio_Padrao"] / row_jan["Receita_Media"] * 100
        assert abs(row_jan["CV"] - expected_cv) < 0.01
        assert row_jan["CV"] > 0

    def test_single_month_data(self):
        """Dados de um único mês: CV = 0 (std de um único valor é 0 ou NaN)."""
        monthly = pd.DataFrame({
            "MesNumero": [3],
            "Receita": [500],
        })
        result = sazonalidade_analysis(monthly)
        assert len(result) == 1
        assert result.iloc[0]["MesNome"] == "Mar"
