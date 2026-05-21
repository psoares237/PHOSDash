"""Wrapper da página nativa de Feedback.

Mantém compatibilidade com /dash/Feedback sem duplicar a lógica do formulário.
"""

import os
import sys

import streamlit as st

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.config import Config  # noqa: E402
from views.Feedback import render  # noqa: E402

st.set_page_config(
    page_title="PHOSDash - Feedback",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

cfg = Config(base_dir=BASE_DIR)
with open(cfg.assets_css, encoding="utf-8") as css:
    st.markdown(css.read(), unsafe_allow_html=True)

render(cfg)
