"""PHOSDash — Pesquisa de Experiência e Evolução do Produto.

Formulário de feedback com 12 perguntas em 4 blocos temáticos + campo aberto.
Respostas salvas em /opt/PHOSDash/data/feedback.csv (append).
"""

import csv
import json
import os
import shutil
from datetime import datetime, timezone

import streamlit as st

from core.config import Config

# ── Constantes ──
FEEDBACK_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "feedback.csv")
FEEDBACK_FIELDS = [
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


def _get_google_sheets_config() -> dict:
    """Lê configuração do Google Sheets via secrets ou variáveis de ambiente."""
    secrets = {}
    try:
        secrets = dict(st.secrets.get("google_sheets", {}))
    except Exception:
        secrets = {}

    return {
        "sheet_id": secrets.get("sheet_id") or os.getenv("GOOGLE_SHEETS_ID", ""),
        "worksheet": secrets.get("worksheet") or os.getenv("GOOGLE_SHEETS_WORKSHEET", "Feedback"),
        "service_account_file": (
            secrets.get("service_account_file")
            or os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")
        ),
        "service_account_json": (
            secrets.get("service_account_json")
            or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        ),
    }


def _append_google_sheets(dados: dict) -> tuple[bool, bool, str]:
    """Envia a resposta para Google Sheets quando a integração estiver configurada."""
    config = _get_google_sheets_config()
    sheet_id = config["sheet_id"]
    worksheet_name = config["worksheet"]
    service_account_file = config["service_account_file"]
    service_account_json = config["service_account_json"]

    if not sheet_id or not (service_account_file or service_account_json):
        return False, False, "Google Sheets não configurado."

    try:
        import gspread

        if service_account_json:
            credentials_info = json.loads(service_account_json)
            client = gspread.service_account_from_dict(credentials_info)
        else:
            client = gspread.service_account(filename=service_account_file)

        spreadsheet = client.open_by_key(sheet_id)
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=worksheet_name,
                rows=1000,
                cols=len(FEEDBACK_FIELDS),
            )

        header = worksheet.row_values(1)
        if header != FEEDBACK_FIELDS:
            worksheet.update("A1", [FEEDBACK_FIELDS])

        row = [dados.get(field, "") for field in FEEDBACK_FIELDS]
        worksheet.append_row(row, value_input_option="USER_ENTERED")
        return True, True, "Feedback enviado ao Google Sheets."
    except Exception as exc:
        return True, False, f"Feedback salvo localmente, mas falhou no Google Sheets: {exc}"


def _salvar_resposta(dados: dict) -> tuple[bool, bool, str]:
    """Salva uma linha no CSV e, se configurado, replica no Google Sheets."""
    os.makedirs(os.path.dirname(FEEDBACK_CSV), exist_ok=True)
    existe = os.path.isfile(FEEDBACK_CSV)
    mode = "a"

    if existe:
        with open(FEEDBACK_CSV, newline="", encoding="utf-8") as f:
            header = next(csv.reader(f), [])
        if header != FEEDBACK_FIELDS:
            backup_path = f"{FEEDBACK_CSV}.bak"
            if not os.path.exists(backup_path):
                shutil.copy2(FEEDBACK_CSV, backup_path)
            existe = False
            mode = "w"

    with open(FEEDBACK_CSV, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=FEEDBACK_FIELDS,
            quoting=csv.QUOTE_ALL,
            extrasaction="ignore",
        )
        if not existe:
            writer.writeheader()
        writer.writerow(dados)

    return _append_google_sheets(dados)


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

    if st.session_state.pop("fb_submitted", False):
        st.success("Feedback registrado com sucesso. Obrigado por contribuir com a evolução do PHOSDash.")
        google_sync_message = st.session_state.pop("fb_google_sync_message", "")
        google_sync_ok = st.session_state.pop("fb_google_sync_ok", None)
        if google_sync_message:
            if google_sync_ok:
                st.info(google_sync_message)
            else:
                st.warning(google_sync_message)
        st.markdown(
            '<div class="feedback-back-wrap">'
            '<a href="/dash" class="feedback-back-btn">Voltar ao dashboard</a>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.balloons()

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

            google_configured, google_ok, google_message = _salvar_resposta(dados)

            # Limpa o formulário
            st.session_state.fb_submitted = True
            if google_configured:
                st.session_state.fb_google_sync_ok = google_ok
                st.session_state.fb_google_sync_message = google_message
            st.session_state.fb_email = ""
            for i in range(1, 13):
                st.session_state[f"fb_q{i}"] = ""
            for i in range(2, 12):
                st.session_state[f"fb_q{i}_outro"] = ""
            st.rerun()
