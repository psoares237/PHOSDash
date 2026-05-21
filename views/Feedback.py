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
ESCALA_PADRAO = ["", "Excelente", "Bom", "Regular", "Ruim", "Outro"]


def _salvar_resposta(dados: dict) -> None:
    """Salva uma linha no CSV de feedback (append). Cria arquivo + header se necessário."""
    os.makedirs(os.path.dirname(FEEDBACK_CSV), exist_ok=True)
    existe = os.path.isfile(FEEDBACK_CSV)

    fieldnames = [
        "timestamp", "email",
        "q1_experiencia_geral", "q2_visual_profissionalismo",
        "q3_navegacao_intuitiva", "q4_indicadores_faceis",
        "q5_graficos_interpretacao", "q6_tela_mais_util",
        "q7_usaria_empresa_real", "q8_area_mais_valor",
        "q9_ajuda_tomada_decisao", "q10_sentiu_falta",
        "q11_melhoria_maior_impacto", "q12_funcionalidade_extra",
    ]

    with open(FEEDBACK_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        if not existe:
            writer.writeheader()
        writer.writerow(dados)


# ── Opções por pergunta ──
OPCOES_Q6 = ["", "Visão Geral", "Visão Estratégica", "Financeira", "Todas igualmente", "Outro"]
OPCOES_Q8 = ["", "Indicadores", "Análises", "Comparativos", "Visualização", "Outro"]
OPCOES_Q10 = ["", "Mais indicadores", "Mais filtros", "Mais automações", "Análises preditivas", "Outro"]
OPCOES_Q11 = ["", "Visualização", "Velocidade", "Análises financeiras", "Inteligência estratégica", "Outro"]


def render(cfg: Config) -> None:
    """Renderiza o formulário completo de feedback."""

    # ── Cabeçalho ──
    st.markdown("""
    <div class="feedback-header">
        <h1 class="feedback-title">Pesquisa de Experiência e Evolução do Produto</h1>
        <p class="feedback-subtitle">Sua percepção é importante para evoluirmos o PHOSDash. A pesquisa leva menos de 2 minutos.</p>
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

    # ═══════════════════════════════════════════
    # E-mail opcional
    # ═══════════════════════════════════════════
    st.session_state.fb_email = st.text_input(
        "📧 E-mail (opcional — para receber atualizações do PHOSDash)",
        value=st.session_state.fb_email,
        key="fb_email_widget",
        placeholder="seu@email.com",
    )
    st.markdown("<br>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════
    # BLOCO 1 — Experiência Geral
    # ═══════════════════════════════════════════
    with st.container():
        st.markdown('<div class="feedback-block">', unsafe_allow_html=True)
        st.markdown('<h2 class="feedback-block-title">📌 Experiência Geral</h2>', unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.session_state.fb_q1 = st.selectbox(
                "1. Como você avalia a experiência geral do dashboard?",
                ESCALA_PADRAO, key="fb_q1_widget",
                index=ESCALA_PADRAO.index(st.session_state.fb_q1) if st.session_state.fb_q1 in ESCALA_PADRAO else 0,
            )
        with col_b:
            st.session_state.fb_q2 = st.selectbox(
                "2. O visual transmite profissionalismo?",
                ESCALA_PADRAO, key="fb_q2_widget",
                index=ESCALA_PADRAO.index(st.session_state.fb_q2) if st.session_state.fb_q2 in ESCALA_PADRAO else 0,
            )

        st.session_state.fb_q3 = st.selectbox(
            "3. A navegação entre telas está intuitiva?",
            ESCALA_PADRAO, key="fb_q3_widget",
            index=ESCALA_PADRAO.index(st.session_state.fb_q3) if st.session_state.fb_q3 in ESCALA_PADRAO else 0,
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
            st.session_state.fb_q4 = st.selectbox(
                "4. Os indicadores principais estão fáceis de entender?",
                ESCALA_PADRAO, key="fb_q4_widget",
                index=ESCALA_PADRAO.index(st.session_state.fb_q4) if st.session_state.fb_q4 in ESCALA_PADRAO else 0,
            )
        with col_d:
            st.session_state.fb_q5 = st.selectbox(
                "5. Os gráficos ajudam na interpretação?",
                ESCALA_PADRAO, key="fb_q5_widget",
                index=ESCALA_PADRAO.index(st.session_state.fb_q5) if st.session_state.fb_q5 in ESCALA_PADRAO else 0,
            )

        st.session_state.fb_q6 = st.selectbox(
            "6. Qual tela você considerou mais útil?",
            OPCOES_Q6, key="fb_q6_widget",
            index=OPCOES_Q6.index(st.session_state.fb_q6) if st.session_state.fb_q6 in OPCOES_Q6 else 0,
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
            st.session_state.fb_q7 = st.selectbox(
                "7. Você utilizaria esse dashboard em uma empresa real?",
                ESCALA_PADRAO, key="fb_q7_widget",
                index=ESCALA_PADRAO.index(st.session_state.fb_q7) if st.session_state.fb_q7 in ESCALA_PADRAO else 0,
            )
        with col_f:
            st.session_state.fb_q8 = st.selectbox(
                "8. Qual área possui mais valor?",
                OPCOES_Q8, key="fb_q8_widget",
                index=OPCOES_Q8.index(st.session_state.fb_q8) if st.session_state.fb_q8 in OPCOES_Q8 else 0,
            )

        st.session_state.fb_q9 = st.selectbox(
            "9. O dashboard ajuda na tomada de decisão?",
            ESCALA_PADRAO, key="fb_q9_widget",
            index=ESCALA_PADRAO.index(st.session_state.fb_q9) if st.session_state.fb_q9 in ESCALA_PADRAO else 0,
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
            st.session_state.fb_q10 = st.selectbox(
                "10. O que mais sentiu falta?",
                OPCOES_Q10, key="fb_q10_widget",
                index=OPCOES_Q10.index(st.session_state.fb_q10) if st.session_state.fb_q10 in OPCOES_Q10 else 0,
            )
        with col_h:
            st.session_state.fb_q11 = st.selectbox(
                "11. Qual melhoria teria maior impacto?",
                OPCOES_Q11, key="fb_q11_widget",
                index=OPCOES_Q11.index(st.session_state.fb_q11) if st.session_state.fb_q11 in OPCOES_Q11 else 0,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════
    # BLOCO FINAL — Pergunta aberta
    # ═══════════════════════════════════════════
    with st.container():
        st.markdown('<div class="feedback-block feedback-block-final">', unsafe_allow_html=True)
        st.markdown('<h2 class="feedback-block-title">💬 Para finalizar</h2>', unsafe_allow_html=True)

        st.session_state.fb_q12 = st.text_input(
            "12. Se pudesse adicionar uma funcionalidade, qual seria?",
            value=st.session_state.fb_q12,
            key="fb_q12_widget",
            max_chars=200,
            placeholder="Descreva em poucas palavras...",
        )
        st.markdown('</div>', unsafe_allow_html=True)

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
        # Validação: pelo menos as obrigatórias (q1 a q11 são selects, sempre tem algo selecionado ou vazio)
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
                "q3_navegacao_intuitiva": st.session_state.fb_q3,
                "q4_indicadores_faceis": st.session_state.fb_q4,
                "q5_graficos_interpretacao": st.session_state.fb_q5,
                "q6_tela_mais_util": st.session_state.fb_q6,
                "q7_usaria_empresa_real": st.session_state.fb_q7,
                "q8_area_mais_valor": st.session_state.fb_q8,
                "q9_ajuda_tomada_decisao": st.session_state.fb_q9,
                "q10_sentiu_falta": st.session_state.fb_q10,
                "q11_melhoria_maior_impacto": st.session_state.fb_q11,
                "q12_funcionalidade_extra": st.session_state.fb_q12,
            }

            _salvar_resposta(dados)

            st.success("Feedback registrado com sucesso! Obrigado por contribuir com a evolução do PHOSDash.")
            st.balloons()

            # Limpa o formulário
            st.session_state.fb_email = ""
            for i in range(1, 13):
                st.session_state[f"fb_q{i}"] = ""
            st.rerun()
