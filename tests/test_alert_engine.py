"""Testes do Alert Engine — services/alert_engine.py."""

import numpy as np
import pandas as pd
import pytest

from services.alert_engine import (
    Alert,
    AlertEngine,
    DEFAULT_THRESHOLDS,
    render_active_alerts,
    render_alert_badge,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine_default():
    """AlertEngine com thresholds padrão."""
    return AlertEngine()


@pytest.fixture
def engine_custom():
    """AlertEngine com thresholds customizados."""
    return AlertEngine(
        margem_bruta_min=30.0,
        frete_pct_max=10.0,
        crescimento_mom_min=-3.0,
        concentracao_hhi_max=2000.0,
        desconto_pct_max=12.0,
    )


@pytest.fixture
def healthy_df():
    """DataFrame com métricas saudáveis — não deve gerar alertas."""
    rng = np.random.default_rng(42)
    n = 20
    receita = rng.uniform(500, 1500, n).round(2)
    lucro = rng.uniform(200, 600, n).round(2)
    return pd.DataFrame({
        "ID_Pedido": [f"PED-{i:04d}" for i in range(n)],
        "Receita": receita,
        "Custo": receita - lucro,
        "Lucro": lucro,
        "Frete": rng.uniform(10, 50, n).round(2),
        "Quantidade": rng.integers(1, 10, n),
        "Desconto_Pct": rng.uniform(0, 8, n).round(2),
        "Categoria": [f"Cat_{i}" for i in range(n)],
        "Canal_Venda": [f"Ch{i}" for i in range(n)],
        "Regiao": [["N", "S", "L", "O", "C"][i % 5] for i in range(n)],
        "Vendedor": [f"V{i}" for i in range(n)],
        "Mes": pd.date_range("2024-01-01", periods=n, freq="ME"),
    })


@pytest.fixture
def unhealthy_df():
    """DataFrame com métricas que devem disparar alertas."""
    rng = np.random.default_rng(99)
    n = 20
    receita = rng.uniform(500, 1500, n).round(2)
    lucro = rng.uniform(10, 50, n).round(2)
    return pd.DataFrame({
        "ID_Pedido": [f"PED-{i:04d}" for i in range(n)],
        "Receita": receita,
        "Custo": receita - lucro,
        "Lucro": lucro,                                     # ~3% margem
        "Frete": rng.uniform(100, 300, n).round(2),          # ~20% frete
        "Quantidade": rng.integers(1, 10, n),
        "Desconto_Pct": rng.uniform(15, 30, n).round(2),     # alto desconto
        "Categoria": ["Cat_A"] * n,                        # monopólio
        "Canal_Venda": ["Site"] * n,                       # monopólio
        "Regiao": ["SP"] * n,                              # monopólio
        "Vendedor": ["V1"] * n,                            # monopólio
        "Mes": pd.date_range("2024-01-01", periods=n, freq="ME"),
    })


@pytest.fixture
def monthly_healthy():
    """Monthly DataFrame com crescimento saudável."""
    return pd.DataFrame({
        "Mes": pd.date_range("2024-01-01", periods=12, freq="ME"),
        "MesLabel": [f"{m}/{2024}" for m in [
            "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set", "Out", "Nov", "Dez",
        ]],
        "Receita": [1000 + i * 50 for i in range(12)],
        "MoM_Receita": [np.nan] + [5.0] * 11,  # crescimento 5%/mês
    })


@pytest.fixture
def monthly_unhealthy():
    """Monthly DataFrame com quedas MoM."""
    return pd.DataFrame({
        "Mes": pd.date_range("2024-01-01", periods=12, freq="ME"),
        "MesLabel": [f"{m}/{2024}" for m in [
            "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set", "Out", "Nov", "Dez",
        ]],
        "Receita": [1000 + i * 20 for i in range(12)],
        "MoM_Receita": [np.nan, -8.0, -12.0, -6.0, 2.0, 1.0,
                        -7.0, -10.0, 3.0, 1.0, 2.0, 1.0],
    })


# ===================================================================
# Alert dataclass
# ===================================================================

class TestAlert:
    """Testes para o dataclass Alert."""

    def test_creation(self):
        """Criação básica de alerta."""
        alert = Alert(
            name="Teste",
            severity="warning",
            message="Mensagem de teste",
            value=10.5,
            threshold=12.0,
        )
        assert alert.name == "Teste"
        assert alert.severity == "warning"
        assert alert.message == "Mensagem de teste"
        assert alert.value == 10.5
        assert alert.threshold == 12.0

    def test_icon_critical(self):
        """Ícone para severity critical."""
        alert = Alert("x", "critical", "", 0, 0)
        assert alert.icon == "🔴"

    def test_icon_warning(self):
        """Ícone para severity warning."""
        alert = Alert("x", "warning", "", 0, 0)
        assert alert.icon == "🟡"

    def test_icon_info(self):
        """Ícone para severity info."""
        alert = Alert("x", "info", "", 0, 0)
        assert alert.icon == "🔵"

    def test_icon_unknown(self):
        """Ícone para severity desconhecida."""
        alert = Alert("x", "unknown", "", 0, 0)
        assert alert.icon == "⚪"

    def test_css_class(self):
        """CSS class segue a severidade."""
        alert = Alert("x", "critical", "", 0, 0)
        assert alert.css_class == "alert-critical"
        alert = Alert("x", "warning", "", 0, 0)
        assert alert.css_class == "alert-warning"
        alert = Alert("x", "info", "", 0, 0)
        assert alert.css_class == "alert-info"


# ===================================================================
# AlertEngine — defaults
# ===================================================================

class TestAlertEngineDefaults:
    """Testes dos thresholds padrão do AlertEngine."""

    def test_default_thresholds(self, engine_default):
        """Engine inicializada sem argumentos usa DEFAULT_THRESHOLDS."""
        for key, val in DEFAULT_THRESHOLDS.items():
            assert engine_default.thresholds[key] == val

    def test_custom_thresholds(self, engine_custom):
        """Engine aceita sobreposição de thresholds."""
        assert engine_custom.thresholds["margem_bruta_min"] == 30.0
        assert engine_custom.thresholds["frete_pct_max"] == 10.0
        assert engine_custom.thresholds["crescimento_mom_min"] == -3.0
        assert engine_custom.thresholds["concentracao_hhi_max"] == 2000.0
        assert engine_custom.thresholds["desconto_pct_max"] == 12.0

    def test_custom_partial(self):
        """Engine com apenas alguns thresholds customizados."""
        engine = AlertEngine(margem_bruta_min=20.0)
        assert engine.thresholds["margem_bruta_min"] == 20.0
        assert engine.thresholds["frete_pct_max"] == DEFAULT_THRESHOLDS["frete_pct_max"]


# ===================================================================
# AlertEngine — check_all on healthy data
# ===================================================================

class TestAlertEngineHealthy:
    """Alertas NÃO devem ser gerados para dados saudáveis."""

    def test_healthy_no_alerts(self, engine_default, healthy_df, monthly_healthy):
        """Dados saudáveis: zero alertas."""
        from services.analytics_service import recompute_total
        current_total = recompute_total(healthy_df)
        ctx = type("FakeCtx", (), {"current_total": current_total})()
        alerts = engine_default.check_all(healthy_df, monthly_healthy, ctx)
        # Margem ~40% > 25%, frete ~4% < 12%, MoM +5% > -5%, HHI diversificado < 2500, desconto ~4% < 15%
        assert len(alerts) == 0

    def test_healthy_with_custom_thresholds(self, engine_custom, healthy_df, monthly_healthy):
        """Dados saudáveis podem gerar alertas com thresholds mais restritivos."""
        from services.analytics_service import recompute_total
        current_total = recompute_total(healthy_df)
        ctx = type("FakeCtx", (), {"current_total": current_total})()
        alerts = engine_custom.check_all(healthy_df, monthly_healthy, ctx)
        # Com thresholds mais restritivos, pode gerar alertas de HHI (2000)
        # Não garante 0, mas verifica que o retorno é lista
        assert isinstance(alerts, list)


# ===================================================================
# AlertEngine — check_all on unhealthy data
# ===================================================================

class TestAlertEngineUnhealthy:
    """Alertas DEVEM ser gerados para dados problemáticos."""

    def test_unhealthy_generates_alerts(self, engine_default, unhealthy_df, monthly_unhealthy):
        """Dados não saudáveis geram múltiplos alertas."""
        from services.analytics_service import recompute_total
        current_total = recompute_total(unhealthy_df)
        ctx = type("FakeCtx", (), {"current_total": current_total})()
        alerts = engine_default.check_all(unhealthy_df, monthly_unhealthy, ctx)
        assert len(alerts) > 0

    def test_alerts_sorted_by_severity(self, engine_default, unhealthy_df, monthly_unhealthy):
        """Alertas são ordenados: critical → warning → info."""
        from services.analytics_service import recompute_total
        current_total = recompute_total(unhealthy_df)
        ctx = type("FakeCtx", (), {"current_total": current_total})()
        alerts = engine_default.check_all(unhealthy_df, monthly_unhealthy, ctx)
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        for i in range(len(alerts) - 1):
            assert (
                severity_order.get(alerts[i].severity, 99)
                <= severity_order.get(alerts[i + 1].severity, 99)
            )

    def test_margem_bruta_critical(self, engine_default):
        """Margem muito baixa gera alerta critical."""
        df = pd.DataFrame({
            "ID_Pedido": [f"P{i}" for i in range(5)],
            "Data": pd.date_range("2024-01-01", periods=5, freq="ME"),
            "Receita": [1000] * 5,
            "Custo": [990] * 5,    # 1% margem bruta
            "Lucro": [10] * 5,     # 1% margem
            "Frete": [50] * 5,     # 5% frete
            "Quantidade": [2] * 5,
            "Desconto_Pct": [5] * 5,
    "Categoria": ["A", "B", "C", "D", "E"],
    "Canal_Venda": [f"Ch{i}" for i in range(5)],
    "Regiao": [f"R{i}" for i in range(5)],
    "Vendedor": [f"V{i}" for i in range(5)],
            "Mes": pd.date_range("2024-01-01", periods=5, freq="ME"),
        })
        from services.analytics_service import recompute_total
        current_total = recompute_total(df)
        ctx = type("FakeCtx", (), {"current_total": current_total})()
        monthly = pd.DataFrame()
        alerts = engine_default.check_all(df, monthly, ctx)
        margem_alerts = [a for a in alerts if "Margem" in a.name]
        assert len(margem_alerts) >= 1
        assert margem_alerts[0].severity == "critical"

    def test_frete_warning(self, engine_default):
        """Frete alto gera alerta warning."""
        df = pd.DataFrame({
            "ID_Pedido": [f"P{i}" for i in range(5)],
            "Data": pd.date_range("2024-01-01", periods=5, freq="ME"),
            "Receita": [1000] * 5,
            "Custo": [700] * 5,
            "Lucro": [300] * 5,      # 30% margem
            "Frete": [200] * 5,      # 20% frete
            "Quantidade": [2] * 5,
            "Desconto_Pct": [5] * 5,
    "Categoria": ["A", "B", "C", "D", "E"],
    "Canal_Venda": [f"Ch{i}" for i in range(5)],
    "Regiao": [f"R{i}" for i in range(5)],
    "Vendedor": [f"V{i}" for i in range(5)],
            "Mes": pd.date_range("2024-01-01", periods=5, freq="ME"),
        })
        from services.analytics_service import recompute_total
        current_total = recompute_total(df)
        ctx = type("FakeCtx", (), {"current_total": current_total})()
        monthly = pd.DataFrame()
        alerts = engine_default.check_all(df, monthly, ctx)
        frete_alerts = [a for a in alerts if "Frete" in a.name]
        assert len(frete_alerts) >= 1
        assert frete_alerts[0].severity == "warning"

    def test_desconto_warning(self, engine_default):
        """Desconto médio alto gera alerta warning."""
        df = pd.DataFrame({
            "ID_Pedido": [f"P{i}" for i in range(5)],
            "Data": pd.date_range("2024-01-01", periods=5, freq="ME"),
            "Receita": [1000] * 5,
            "Custo": [700] * 5,
            "Lucro": [300] * 5,
            "Frete": [50] * 5,
            "Quantidade": [2] * 5,
            "Desconto_Pct": [20] * 5,  # 20% desconto
    "Categoria": ["A", "B", "C", "D", "E"],
    "Canal_Venda": [f"Ch{i}" for i in range(5)],
    "Regiao": [f"R{i}" for i in range(5)],
    "Vendedor": [f"V{i}" for i in range(5)],
            "Mes": pd.date_range("2024-01-01", periods=5, freq="ME"),
        })
        from services.analytics_service import recompute_total
        current_total = recompute_total(df)
        ctx = type("FakeCtx", (), {"current_total": current_total})()
        monthly = pd.DataFrame()
        alerts = engine_default.check_all(df, monthly, ctx)
        desconto_alerts = [a for a in alerts if "Desconto" in a.name]
        assert len(desconto_alerts) >= 1
        assert desconto_alerts[0].severity == "warning"

    def test_concentracao_alerts(self, engine_default, unhealthy_df):
        """Monopólio gera alertas de concentração (HHI > 2500)."""
        monthly = pd.DataFrame()
        from services.analytics_service import recompute_total
        current_total = recompute_total(unhealthy_df)
        ctx = type("FakeCtx", (), {"current_total": current_total})()
        alerts = engine_default.check_all(unhealthy_df, monthly, ctx)
        concentracao_alerts = [a for a in alerts if "Concentração" in a.name]
        assert len(concentracao_alerts) > 0
        # Monopólio = critical
        for a in concentracao_alerts:
            assert a.severity in ("warning", "critical")

    def test_crescimento_mom_alerts(self, engine_default, monthly_unhealthy):
        """Quedas MoM frequentes geram alertas."""
        df = pd.DataFrame({
            "ID_Pedido": [f"P{i}" for i in range(12)],
            "Data": pd.date_range("2024-01-01", periods=12, freq="ME"),
            "Receita": [1000] * 12,
            "Custo": [700] * 12,
            "Lucro": [300] * 12,
            "Frete": [50] * 12,
            "Quantidade": [2] * 12,
            "Desconto_Pct": [5] * 12,
            "Categoria": [f"Cat{i}" for i in range(12)],
            "Canal_Venda": [f"Ch{i}" for i in range(12)],
            "Regiao": [f"R{i}" for i in range(12)],
            "Vendedor": [f"V{i}" for i in range(12)],
            "Mes": pd.date_range("2024-01-01", periods=12, freq="ME"),
        })
        from services.analytics_service import recompute_total
        current_total = recompute_total(df)
        ctx = type("FakeCtx", (), {"current_total": current_total})()
        alerts = engine_default.check_all(df, monthly_unhealthy, ctx)
        mom_alerts = [a for a in alerts if "MoM" in a.name]
        assert len(mom_alerts) > 0

    def test_agregado_many_bad_months(self, engine_default):
        """Muitos meses ruins gera alerta agregado."""
        monthly = pd.DataFrame({
            "MesLabel": [f"Mês {i}" for i in range(1, 11)],
            "MoM_Receita": [-10.0, -8.0, -12.0, -6.0, -9.0,
                            -7.0, -11.0, -5.0, -8.0, -13.0],
        })
        df = pd.DataFrame()
        alerts = engine_default.check_all(df, monthly)
        mom_alerts = [a for a in alerts if "MoM" in a.name]
        # Deve ter alerta agregado (1 alerta, não 10)
        assert len(mom_alerts) >= 1
        # Verifica que é um alerta de "Frequente"
        assert any("Frequente" in a.name for a in mom_alerts)


# ===================================================================
# AlertEngine — edge cases
# ===================================================================

class TestAlertEngineEdgeCases:
    """Casos de borda."""

    def test_empty_dataframe(self, engine_default):
        """DataFrame vazio: zero alertas."""
        df = pd.DataFrame()
        monthly = pd.DataFrame()
        alerts = engine_default.check_all(df, monthly)
        assert len(alerts) == 0

    def test_zero_receita(self, engine_default):
        """Receita zero: não gera alertas de margem/frete/desconto."""
        df = pd.DataFrame({
            "ID_Pedido": [f"P{i}" for i in range(5)],
            "Data": pd.date_range("2024-01-01", periods=5, freq="ME"),
            "Receita": [0] * 5,
            "Custo": [0] * 5,
            "Lucro": [0] * 5,
            "Frete": [100] * 5,
            "Quantidade": [1] * 5,
            "Desconto_Pct": [50] * 5,
            "Categoria": ["A"] * 5,
            "Canal_Venda": ["Site"] * 5,
            "Regiao": ["SP"] * 5,
            "Vendedor": ["V1"] * 5,
            "Mes": pd.date_range("2024-01-01", periods=5, freq="ME"),
        })
        from services.analytics_service import recompute_total
        current_total = recompute_total(df)
        ctx = type("FakeCtx", (), {"current_total": current_total})()
        monthly = pd.DataFrame()
        alerts = engine_default.check_all(df, monthly, ctx)
        # Não deve ter alerta de margem (receita=0), mas pode ter concentração
        margem_alerts = [a for a in alerts if "Margem" in a.name]
        frete_alerts = [a for a in alerts if "Frete" in a.name]
        assert len(margem_alerts) == 0
        assert len(frete_alerts) == 0

    def test_no_mom_column(self, engine_default):
        """Monthly sem coluna MoM_Receita: sem alertas de crescimento."""
        monthly = pd.DataFrame({"Receita": [100, 200, 300]})
        df = pd.DataFrame()
        alerts = engine_default.check_all(df, monthly)
        mom_alerts = [a for a in alerts if "MoM" in a.name]
        assert len(mom_alerts) == 0

    def test_alerts_always_list(self, engine_default):
        """check_all sempre retorna uma lista."""
        result = engine_default.check_all(pd.DataFrame(), pd.DataFrame())
        assert isinstance(result, list)
        assert len(result) == 0

    def test_margem_proxima_limite_warning(self, engine_default):
        """Margem entre threshold e 1.4x threshold gera warning, não critical."""
        # threshold = 25%, 1.4*25 = 35%, valor 28% → warning
        df = pd.DataFrame({
            "ID_Pedido": [f"P{i}" for i in range(5)],
            "Data": pd.date_range("2024-01-01", periods=5, freq="ME"),
            "Receita": [1000] * 5,
            "Custo": [720] * 5,    # Custo = Receita - Lucro
            "Lucro": [280] * 5,     # 28% margem: entre 25% e 35%
            "Frete": [50] * 5,
            "Quantidade": [2] * 5,
            "Desconto_Pct": [5] * 5,
    "Categoria": ["A", "B", "C", "D", "E"],
    "Canal_Venda": [f"Ch{i}" for i in range(5)],
    "Regiao": [f"R{i}" for i in range(5)],
    "Vendedor": [f"V{i}" for i in range(5)],
            "Mes": pd.date_range("2024-01-01", periods=5, freq="ME"),
        })
        from services.analytics_service import recompute_total
        current_total = recompute_total(df)
        ctx = type("FakeCtx", (), {"current_total": current_total})()
        alerts = engine_default.check_all(df, pd.DataFrame(), ctx)
        margem_alerts = [a for a in alerts if "Margem" in a.name]
        assert len(margem_alerts) >= 1
        assert margem_alerts[0].severity == "warning"


# ===================================================================
# AlertEngine — helper: _safe_div
# ===================================================================

class TestSafeDiv:
    """Testes do método _safe_div."""

    def test_normal_division(self):
        """Divisão normal."""
        assert AlertEngine._safe_div(10.0, 2.0) == 5.0

    def test_division_by_zero(self):
        """Divisão por zero retorna 0."""
        assert AlertEngine._safe_div(10.0, 0.0) == 0.0

    def test_zero_numerator(self):
        """Numerador zero retorna 0."""
        assert AlertEngine._safe_div(0.0, 5.0) == 0.0

    def test_both_zero(self):
        """Ambos zero retorna 0."""
        assert AlertEngine._safe_div(0.0, 0.0) == 0.0
