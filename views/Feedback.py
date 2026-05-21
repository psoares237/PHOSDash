"""PHOSDash — Pesquisa de Experiência e Evolução do Produto.

Formulário de feedback com 12 perguntas em 4 blocos temáticos + campo aberto.
Respostas salvas em /opt/PHOSDash/data/feedback.csv (append).
"""

import csv
import os
from datetime import datetime, timezone

import streamlit as st

from core.config import Config

# ── Constantes ──
FEEDBACK_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "feedback.csv")

# ── Opções por pergunta ──
OPCOES_Q1 = ["", "Excelente", "Boa", "Regular", "Ruim", "Péssima"]
OPCOES_SIM_PARCIAL = ["", "Sim", "Em partes", "Não", "Outro"]
OPCOES_Q6 = ["", "Visão Geral", "Visão Estratégica", "Financeira", "Todas igualmente", "Outro"]
OPCOES_Q7 = ["", "Sim", "Talvez", "Não", "Outro"]
OPCOES_Q8 = ["", "Indicadores", "Análises", "Comparativos", "Visualização", "Outro"]
OPCOES_Q10 = ["", "Mais indicadores", "Mais filtros", "Mais automações", "Análises preditivas", "Outro"]
OPCOES_Q11 = ["", "Visualização", "Velocidade", "Análises financeiras", "Inteligência estratégica", "Outro"]


def _safe_index(opcoes: list, valor: str) -> int:
    """Retorna o índice do valor na lista de opções, ou 0 se não encontrado."""
    try:
        return opcoes.index(valor)
    except ValueError:
        return 0


def _salvar_resposta(dados: dict) -> None:
    """Salva uma linha no CSV de feedback (append). Cria arquivo + header se necessário."""
    os.makedirs(os.path.dirname(FEEDBACK_CSV), exist_ok=True)
    existe = os.path.isfile(FEEDBACK_CSV)

    fieldnames = [
        "timestamp", "email",
        "q1_experiencia_geral",
        "q2_visual_profissionalismo", "q2_outro",
        "q3_navegacao_intuitiva", "q3_outro",
        "q4_indicadores_faceis", "q4_outro",
        "q5_graficos_interpretacao", "q5_outro",
        "q6_tela_mais_util", "q6_outro",
        "q7_usaria_empresa_real", "q7_outro",
        "q8_area_mais_valor", "q8_outro",
        "q9_ajuda_tomada_decisao", "q9_outro",
        "q10_sentiu_falta", "q10_outro",
        "q11_melhoria_maior_impacto", "q11_outro",
        "q12_opiniao_sugestao",
    ]

    with open(FEEDBACK_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        if not existe:
            writer.writeheader()
        writer.writerow(dados)


# ── Helpers para selectbox com "Outro" ──
def _select_com_outro(label: str, opcoes: list, session_key: str, widget_key: str) -> None:
    """Renderiza um selectbox e, se 'Outro', mostra text_input para especificação."""
    valor = st.selectbox(
        label, opcoes,
        key=widget_key,
        index=_safe_index(opcoes, st.session_state.get(session_key, "")),
    )
    st.session_state[session_key] = valor

    outro_key = f"{session_key}_outro"
    if outro_key not in st.session_state:
        st.session_state[outro_key] = ""

    if valor == "Outro":
        st.session_state[outro_key] = st.text_input(
            "Especifique:",
            value=st.session_state[outro_key],
            key=f"{widget_key}_outro_widget",
            placeholder="Descreva...",
        )
    else:
        st.session_state[outro_key] = ""


def _select_simples(label: str, opcoes: list, session_key: str, widget_key: str) -> None:
    """Renderiza um selectbox simples, sem campo 'Outro'."""
    valor = st.selectbox(
        label, opcoes,
        key=widget_key,
        index=_safe_index(opcoes, st.session_state.get(session_key, "")),
    )
    st.session_state[session_key] = valor


def render(cfg: Config) -> None:
    """Renderiza o formulário completo de feedback."""

    # ── Cabeçalho ──
    st.markdown("""
    <div style="text-align:center; padding: 10px 0 0 0;">
        <h2 style="color:#d3b73e; margin-bottom:6px;">Pesquisa de Experiência e Evolução do Produto</h2>
        <p style="color:#7B8FA8; font-style:italic; font-size:0.95rem;">
            Sua percepção é importante para evoluirmos o PHOSDash. A pesquisa leva menos de 2 minutos.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="feedback-divider"></div>', unsafe_allow_html=True)

    # ── Inicializa session state ──
    if "fb_email" not in st.session_state:
        st.session_state.fb_email = ""
    for i in range(1, 13):
        key = f"fb_q{i}"
        if key not in st.session_state:
            st.session_state[key] = ""
    # Inicializa campos "outro" (q2..q11)
    for i in range(2, 12):
        key = f"fb_q{i}_outro"
        if key not in st.session_state:
            st.session_state[key] = ""

    # ═══════════════════════════════════════════
    # BLOCO 1 — Experiência Geral
    # ═══════════════════════════════════════════
    with st.container():
        st.markdown('<div class="feedback-block">', unsafe_allow_html=True)
        st.markdown('<h2 class="feedback-block-title">📌 Experiência Geral</h2>', unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            _select_simples(
                "1. Como você avalia a experiência geral do dashboard?",
                OPCOES_Q1, "fb_q1", "fb_q1_widget",
            )
        with col_b:
            _select_com_outro(
                "2. O visual transmite profissionalismo?",
                OPCOES_SIM_PARCIAL, "fb_q2", "fb_q2_widget",
            )

        _select_com_outro(
            "3. A navegação entre telas está intuitiva?",
            OPCOES_SIM_PARCIAL, "fb_q3", "fb_q3_widget",
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════
    # BLOCO 2 — Clareza
    # ═══════════════════════════════════════════
    with st.container():
        st.markdown('<div class="feedback-block">', unsafe_allow_html=True)
        st.markdown('<h2 class="feedback-block-title">🔍 Clareza</h2>', unsafe_allow_html=True)

        col_c, col_d = st.columns(2)
        with col_c:
            _select_com_outro(
                "4. Os indicadores principais estão fáceis de entender?",
                OPCOES_SIM_PARCIAL, "fb_q4", "fb_q4_widget",
            )
        with col_d:
            _select_com_outro(
                "5. Os gráficos ajudam na interpretação?",
                OPCOES_SIM_PARCIAL, "fb_q5", "fb_q5_widget",
            )

        _select_com_outro(
            "6. Qual tela você considerou mais útil?",
            OPCOES_Q6, "fb_q6", "fb_q6_widget",
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════
    # BLOCO 3 — Utilidade
    # ═══════════════════════════════════════════
    with st.container():
        st.markdown('<div class="feedback-block">', unsafe_allow_html=True)
        st.markdown('<h2 class="feedback-block-title">💡 Utilidade</h2>', unsafe_allow_html=True)

        col_e, col_f = st.columns(2)
        with col_e:
            _select_com_outro(
                "7. Você utilizaria esse dashboard em uma empresa real?",
                OPCOES_Q7, "fb_q7", "fb_q7_widget",
            )
        with col_f:
            _select_com_outro(
                "8. Qual área possui mais valor?",
                OPCOES_Q8, "fb_q8", "fb_q8_widget",
            )

        _select_com_outro(
            "9. O dashboard ajuda na tomada de decisão?",
            OPCOES_SIM_PARCIAL, "fb_q9", "fb_q9_widget",
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════
    # BLOCO 4 — Evolução
    # ═══════════════════════════════════════════
    with st.container():
        st.markdown('<div class="feedback-block">', unsafe_allow_html=True)
        st.markdown('<h2 class="feedback-block-title">🚀 Evolução</h2>', unsafe_allow_html=True)

        col_g, col_h = st.columns(2)
        with col_g:
            _select_com_outro(
                "10. O que mais sentiu falta?",
                OPCOES_Q10, "fb_q10", "fb_q10_widget",
            )
        with col_h:
            _select_com_outro(
                "11. Qual melhoria teria maior impacto?",
                OPCOES_Q11, "fb_q11", "fb_q11_widget",
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════
    # BLOCO FINAL — Pergunta aberta unificada
    # ═══════════════════════════════════════════
    with st.container():
        st.markdown('<div class="feedback-block feedback-block-final">', unsafe_allow_html=True)
        st.markdown('<h2 class="feedback-block-title">💬 Para finalizar</h2>', unsafe_allow_html=True)

        st.session_state.fb_q12 = st.text_area(
            "💬 Deixe sua opinião ou sugestão de funcionalidade",
            value=st.session_state.fb_q12,
            key="fb_q12_widget",
            max_chars=300,
            placeholder="Compartilhe sua ideia...",
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # ── E-mail (movido para depois das perguntas, antes do botão) ──
    st.markdown("<br>", unsafe_allow_html=True)
    st.session_state.fb_email = st.text_input(
        "📧 E-mail (opcional — para receber novidades do PHOSDash)",
        value=st.session_state.fb_email,
        key="fb_email_widget",
        placeholder="seu@email.com",
    )

    st.markdown('<div class="feedback-divider"></div>', unsafe_allow_html=True)

    # ── Botão de envio ──
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    with col_btn2:
        enviado = st.button(
            "✅ Enviar Feedback",
            type="primary",
            width="stretch",
            key="fb_submit_btn",
        )

    if enviado:
        respostas_preenchidas = sum(
            1 for i in range(1, 12)
            if st.session_state.get(f"fb_q{i}", "")
        )

        if respostas_preenchidas < 6:
            st.warning("Responda pelo menos 6 das 11 perguntas principais antes de enviar. Obrigado!")
        else:
            dados = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "email": st.session_state.fb_email,
                "q1_experiencia_geral": st.session_state.fb_q1,
                "q2_visual_profissionalismo": st.session_state.fb_q2,
                "q2_outro": st.session_state.fb_q2_outro,
                "q3_navegacao_intuitiva": st.session_state.fb_q3,
                "q3_outro": st.session_state.fb_q3_outro,
                "q4_indicadores_faceis": st.session_state.fb_q4,
                "q4_outro": st.session_state.fb_q4_outro,
                "q5_graficos_interpretacao": st.session_state.fb_q5,
                "q5_outro": st.session_state.fb_q5_outro,
                "q6_tela_mais_util": st.session_state.fb_q6,
                "q6_outro": st.session_state.fb_q6_outro,
                "q7_usaria_empresa_real": st.session_state.fb_q7,
                "q7_outro": st.session_state.fb_q7_outro,
                "q8_area_mais_valor": st.session_state.fb_q8,
                "q8_outro": st.session_state.fb_q8_outro,
                "q9_ajuda_tomada_decisao": st.session_state.fb_q9,
                "q9_outro": st.session_state.fb_q9_outro,
                "q10_sentiu_falta": st.session_state.fb_q10,
                "q10_outro": st.session_state.fb_q10_outro,
                "q11_melhoria_maior_impacto": st.session_state.fb_q11,
                "q11_outro": st.session_state.fb_q11_outro,
                "q12_opiniao_sugestao": st.session_state.fb_q12,
            }

            _salvar_resposta(dados)

            # Mensagem de agradecimento elaborada
            st.markdown("""
            <div style="text-align:center; padding:20px;">
                <h3>✅ Feedback registrado!</h3>
                <p>Obrigado por contribuir com a evolução do PHOSDash. Sua opinião faz diferença.</p>
            </div>
            """, unsafe_allow_html=True)
            st.balloons()

            # Limpa o formulário
            st.session_state.fb_email = ""
            for i in range(1, 13):
                st.session_state[f"fb_q{i}"] = ""
            for i in range(2, 12):
                st.session_state[f"fb_q{i}_outro"] = ""
            st.rerun()
