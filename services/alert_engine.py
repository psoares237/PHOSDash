"""Alert Engine — motor de alertas com thresholds configuráveis.

Gera alertas proativos baseados em thresholds de negócio para
margem, frete, crescimento, concentração e descontos.
"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st


# ── Dataclasses ──

@dataclass
class Alert:
    """Alerta individual gerado pelo motor.

    Attributes:
        name: Nome curto do alerta (ex: "Margem Baixa").
        severity: Nível de severidade: "critical", "warning", "info".
        message: Descrição legível para exibição.
        value: Valor atual da métrica que disparou o alerta.
        threshold: Valor do threshold que foi violado.
    """

    name: str
    severity: str  # "critical", "warning", "info"
    message: str
    value: float
    threshold: float

    @property
    def icon(self) -> str:
        """Ícone visual baseado na severidade."""
        return {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(
            self.severity, "⚪"
        )

    @property
    def css_class(self) -> str:
        """Classe CSS para o card do alerta."""
        return f"alert-{self.severity}"


# ── Default thresholds ──

DEFAULT_THRESHOLDS = {
    "margem_bruta_min": 25.0,       # % — margem bruta mínima aceitável
    "frete_pct_max": 12.0,          # % — frete máximo como % da receita
    "crescimento_mom_min": -5.0,    # % — queda MoM máxima tolerada
    "concentracao_hhi_max": 2500.0, # HHI — acima disso é concentrado
    "desconto_pct_max": 15.0,       # % — desconto médio máximo
}


# ── Alert Engine ──

class AlertEngine:
    """Motor de alertas com thresholds configuráveis.

    Uso:
        engine = AlertEngine()                        # thresholds padrão
        engine = AlertEngine(margem_bruta_min=30.0)   # customizado
        alerts = engine.check_all(df, monthly, ctx)
    """

    def __init__(self, **thresholds):
        """Inicializa o motor com thresholds customizáveis.

        Args:
            **thresholds: Quaisquer thresholds para sobrepor os defaults.
                          Ex: margem_bruta_min=30.0, frete_pct_max=10.0
        """
        self.thresholds = {**DEFAULT_THRESHOLDS, **thresholds}

    # ── Helpers ──

    @staticmethod
    def _safe_div(a: float, b: float) -> float:
        """Divisão segura, retorna 0 se denominador for 0."""
        return a / b if b else 0.0

    @staticmethod
    def _compute_hhi_for_dimension(df: pd.DataFrame, column: str) -> float:
        """Calcula HHI para uma dimensão, com cache Streamlit."""
        from services.kpi_service import hhi_index
        return hhi_index(df, column)

    # ── Checks Individuais ──

    def _check_margem_bruta(
        self, current_total: dict
    ) -> Optional[Alert]:
        """Verifica se a margem bruta está abaixo do mínimo."""
        receita = current_total.get("receita", 0)
        lucro = current_total.get("lucro", 0)
        if receita <= 0:
            return None
        margem = self._safe_div(lucro, receita) * 100
        threshold = self.thresholds["margem_bruta_min"]
        if margem < threshold:
            return Alert(
                name="Margem Bruta Baixa",
                severity="critical",
                message=(
                    f"Margem bruta de {margem:.1f}% está abaixo "
                    f"do mínimo aceitável de {threshold:.0f}%."
                ),
                value=round(margem, 2),
                threshold=threshold,
            )
        elif margem < threshold * 1.4:  # warning zone: < 35% do threshold
            return Alert(
                name="Margem Bruta Atenção",
                severity="warning",
                message=(
                    f"Margem bruta de {margem:.1f}% está próxima "
                    f"do limite de {threshold:.0f}%."
                ),
                value=round(margem, 2),
                threshold=threshold,
            )
        return None

    def _check_frete(
        self, current_total: dict
    ) -> Optional[Alert]:
        """Verifica se o frete (% da receita) está acima do máximo."""
        receita = current_total.get("receita", 0)
        frete = current_total.get("frete", 0)
        if receita <= 0:
            return None
        frete_pct = self._safe_div(frete, receita) * 100
        threshold = self.thresholds["frete_pct_max"]
        if frete_pct > threshold:
            return Alert(
                name="Frete Elevado",
                severity="warning",
                message=(
                    f"Frete representa {frete_pct:.1f}% da receita, "
                    f"acima do máximo de {threshold:.0f}%."
                ),
                value=round(frete_pct, 2),
                threshold=threshold,
            )
        return None

    def _check_crescimento_mom(
        self, monthly: pd.DataFrame
    ) -> list[Alert]:
        """Verifica meses com crescimento MoM abaixo do mínimo tolerado."""
        threshold = self.thresholds["crescimento_mom_min"]
        alerts: list[Alert] = []
        if monthly is None or monthly.empty or "MoM_Receita" not in monthly.columns:
            return alerts
        mom_data = monthly.dropna(subset=["MoM_Receita"])
        if mom_data.empty:
            return alerts
        bad_months = mom_data[mom_data["MoM_Receita"] < threshold]
        if bad_months.empty:
            return alerts

        # Se muitos meses ruins, gera um alerta agregado
        if len(bad_months) >= 3:
            worst = bad_months.loc[bad_months["MoM_Receita"].idxmin()]
            mes_label = worst.get("MesLabel", "?")
            alerts.append(Alert(
                name="Queda MoM Frequente",
                severity="warning",
                message=(
                    f"{len(bad_months)} meses com variação MoM abaixo de "
                    f"{threshold:+.0f}%. Pior mês: {mes_label} "
                    f"({worst['MoM_Receita']:+.1f}%)."
                ),
                value=round(worst["MoM_Receita"], 2),
                threshold=threshold,
            ))
        else:
            for _, row in bad_months.iterrows():
                mes_label = row.get("MesLabel", "?")
                alerts.append(Alert(
                    name="Queda MoM",
                    severity="warning",
                    message=(
                        f"{mes_label}: variação MoM de "
                        f"{row['MoM_Receita']:+.1f}% "
                        f"(limite: {threshold:+.0f}%)."
                    ),
                    value=round(row["MoM_Receita"], 2),
                    threshold=threshold,
                ))
        return alerts

    def _check_concentracao(
        self, df: pd.DataFrame
    ) -> list[Alert]:
        """Verifica concentração (HHI) por dimensões relevantes."""
        threshold = self.thresholds["concentracao_hhi_max"]
        alerts: list[Alert] = []
        if df is None or df.empty:
            return alerts
        dimensions = ["Categoria", "Canal_Venda", "Regiao", "Vendedor"]
        for dim in dimensions:
            if dim not in df.columns:
                continue
            hhi = self._compute_hhi_for_dimension(df, dim)
            if hhi > threshold:
                alerts.append(Alert(
                    name=f"Concentração Alta: {dim}",
                    severity="warning" if hhi < 4000 else "critical",
                    message=(
                        f"HHI de {dim} = {hhi:.0f} (>{threshold:.0f}). "
                        f"Risco de dependência."
                    ),
                    value=round(hhi, 2),
                    threshold=threshold,
                ))
        return alerts

    def _check_desconto(
        self, current_total: dict
    ) -> Optional[Alert]:
        """Verifica se o desconto médio está acima do máximo tolerado."""
        desconto = current_total.get("desconto_medio", 0)
        threshold = self.thresholds["desconto_pct_max"]
        if desconto > threshold:
            return Alert(
                name="Desconto Médio Elevado",
                severity="warning",
                message=(
                    f"Desconto médio de {desconto:.1f}% está acima "
                    f"do máximo de {threshold:.0f}%."
                ),
                value=round(desconto, 2),
                threshold=threshold,
            )
        return None

    # ── Método Principal ──

    def check_all(
        self,
        df: pd.DataFrame,
        monthly: pd.DataFrame,
        ctx=None,
    ) -> list[Alert]:
        """Executa todas as verificações e retorna lista de alertas.

        Args:
            df: DataFrame com dados do período atual.
            monthly: DataFrame de vendas mensais (com colunas MoM_Receita, MesLabel).
            ctx: PageContext opcional. Se fornecido, extrai current_total dele.

        Returns:
            Lista de Alert ordenada por severidade (critical → warning → info).
        """
        # Resolve current_total do ctx se disponível
        if ctx is not None:
            current_total = ctx.current_total
        else:
            from services.analytics_service import recompute_total
            current_total = recompute_total(df)

        alerts: list[Alert] = []

        # Margem bruta
        alert = self._check_margem_bruta(current_total)
        if alert:
            alerts.append(alert)

        # Frete % receita
        alert = self._check_frete(current_total)
        if alert:
            alerts.append(alert)

        # Crescimento MoM
        alerts.extend(self._check_crescimento_mom(monthly))

        # Concentração HHI
        alerts.extend(self._check_concentracao(df))

        # Desconto médio
        alert = self._check_desconto(current_total)
        if alert:
            alerts.append(alert)

        # Ordena: critical primeiro, depois warning, depois info
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        alerts.sort(key=lambda a: severity_order.get(a.severity, 99))

        return alerts


# ── Função Conveniente ──

def render_alert_badge(count: int) -> None:
    """Renderiza um badge com a contagem de alertas."""
    if count <= 0:
        return
    badge_class = "alert-badge-critical" if count >= 3 else "alert-badge-warning"
    st.markdown(
        f'<span class="{badge_class}">🔔 {count} alerta{"s" if count > 1 else ""}</span>',
        unsafe_allow_html=True,
    )


def render_active_alerts(alerts: list[Alert]) -> None:
    """Renderiza a seção de Alertas Ativos com cards coloridos.

    Args:
        alerts: Lista de Alert para renderizar.
    """
    if not alerts:
        return

    st.markdown("---")
    st.markdown(
        '<div class="alert-section-title">🚨 Alertas Ativos</div>',
        unsafe_allow_html=True,
    )

    # Agrupa por severidade para ordenação visual
    for alert in alerts:
        severity_color = {
            "critical": "rgba(248, 113, 113, 0.15)",
            "warning": "rgba(251, 191, 36, 0.12)",
            "info": "rgba(96, 165, 250, 0.10)",
        }.get(alert.severity, "rgba(170,183,196,0.10)")

        border_color = {
            "critical": "#F87171",
            "warning": "#d3b73e",
            "info": "#60A5FA",
        }.get(alert.severity, "#AAB7C4")

        severity_label = {
            "critical": "CRÍTICO",
            "warning": "ATENÇÃO",
            "info": "INFO",
        }.get(alert.severity, alert.severity.upper())

        st.markdown(
            f"""
            <div class="alert-card" style="
                background: {severity_color};
                border-left: 4px solid {border_color};
                border-radius: 8px;
                padding: 12px 16px;
                margin-bottom: 8px;
            ">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 20px;">{alert.icon}</span>
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <strong style="font-size: 14px; color: #F7FAFC;">
                                {alert.name}
                            </strong>
                            <span style="
                                font-size: 11px;
                                font-weight: 600;
                                padding: 2px 8px;
                                border-radius: 4px;
                                background: {border_color}22;
                                color: {border_color};
                            ">{severity_label}</span>
                        </div>
                        <div style="font-size: 12px; color: #AAB7C4; margin-top: 4px;">
                            {alert.message}
                        </div>
                        <div style="font-size: 11px; color: #6B7280; margin-top: 2px;">
                            Atual: <strong>{alert.value}{'%' if 'MoM' in alert.name or 'Margem' in alert.name or 'Frete' in alert.name or 'Desconto' in alert.name else ''}</strong>
                            &nbsp;|&nbsp;
                            Limite: <strong>{alert.threshold}</strong>
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
