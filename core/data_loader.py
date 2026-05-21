"""Carregamento de dados do PHOSDash com tratamento de erro robusto.

Hierarquia de carregamento:
    1. Upload do usuário (session_state.uploaded_file)
    2. Planilha oficial (Dados_PHOSDash.xlsx)
    3. Dados demo (gerados deterministicamente)
"""

import os

import numpy as np
import pandas as pd
import streamlit as st

from core.config import COL_MAP


@st.cache_data(ttl=600, show_spinner=False)
def load_official_data(path: str) -> pd.DataFrame | None:
    """Carrega a planilha oficial Dados_PHOSDash.xlsx.

    Args:
        path: Caminho completo para o arquivo .xlsx oficial.

    Returns:
        DataFrame padronizado ou None se o arquivo não existir,
        estiver vazio ou não puder ser lido.
    """
    if not os.path.exists(path):
        st.warning(f"📁 Planilha oficial não encontrada: {os.path.basename(path)}")
        return None

    try:
        df = pd.read_excel(path)
    except FileNotFoundError:
        st.warning(f"📁 Arquivo removido durante a leitura: {os.path.basename(path)}")
        return None
    except ValueError as exc:
        st.warning(f"📄 Formato de arquivo inválido: {exc}")
        return None
    except OSError as exc:
        st.warning(f"💾 Erro de I/O ao ler planilha oficial: {exc}")
        return None

    if df.empty:
        st.warning("📭 Planilha oficial está vazia. Usando dados demo.")
        return None

    try:
        return standardize(df)
    except Exception as exc:
        st.warning(f"⚠️ Erro ao padronizar dados oficiais: {exc}")
        return None


def standardize(df: pd.DataFrame, col_map: dict | None = None) -> pd.DataFrame:
    """Padroniza colunas do DataFrame para o formato interno do PHOSDash.

    Realiza:
        - Renomeio de colunas (via col_map).
        - Criação da coluna 'Mes' a partir de 'Data'.
        - Criação de 'MesLabel' para cross-filtering.
        - Cálculo de colunas derivadas: Lucro, Desconto_Pct.

    Args:
        df: DataFrame bruto a ser padronizado.
        col_map: Mapeamento de nomes de colunas (default: COL_MAP).

    Returns:
        DataFrame padronizado com colunas normalizadas.
    """
    if col_map is None:
        col_map = COL_MAP

    # Garante que trabalhamos com uma cópia
    df = df.copy()

    # Renomeio de colunas
    df = df.rename(columns=col_map)

    # Conversão de data e criação de período mensal
    if "Mes" not in df.columns and "Data" in df.columns:
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
        df["Mes"] = df["Data"].dt.to_period("M")

    # MesLabel para cross-filtering — mesma formatação de utils.formatters.month_label
    if "MesLabel" not in df.columns and "Mes" in df.columns and "Data" in df.columns:
        from utils.formatters import month_label

        df["MesLabel"] = df["Data"].apply(month_label)

    # Colunas derivadas
    if "Receita" in df.columns and "Custo" in df.columns and "Lucro" not in df.columns:
        df["Lucro"] = df["Receita"] - df["Custo"]

    if (
        "Receita" in df.columns
        and "Desconto" in df.columns
        and "Desconto_Pct" not in df.columns
    ):
        mask = df["Receita"] != 0
        df["Desconto_Pct"] = 0.0
        df.loc[mask, "Desconto_Pct"] = (
            df.loc[mask, "Desconto"] / df.loc[mask, "Receita"]
        ) * 100

    return df


@st.cache_data(ttl=600, show_spinner=False)
def generate_demo_data() -> pd.DataFrame:
    """Gera dados fictícios para demonstração quando não há dados oficiais.

    Usa seed fixa (42) para reprodutibilidade. Gera 2400 registros
    com 6 categorias, 4 canais, 5 regiões e 5 vendedores.

    Returns:
        DataFrame com dados sintéticos padronizados.
    """
    np.random.seed(42)

    n = 2400
    meses = pd.date_range("2020-01-01", "2025-12-01", freq="MS")

    categorias = [
        "Esportes",
        "Informática",
        "Eletrônicos",
        "Móveis",
        "Eletrodomésticos",
        "Celulares",
    ]

    canais = ["Site Próprio", "Marketplace", "Loja Física", "Atacado"]
    regioes = ["Sudeste", "Sul", "Nordeste", "Norte", "Centro-Oeste"]
    vendedores = [
        "Ana Lima",
        "Pedro Santos",
        "Carla Mendes",
        "João Oliveira",
        "Mariana Costa",
    ]

    rows: list[dict] = []

    for _ in range(n):
        mes = meses[np.random.randint(0, len(meses))]
        receita = np.random.uniform(80, 8000)
        margem_pct = np.random.uniform(0.15, 0.55)
        lucro = receita * margem_pct
        custo = receita - lucro

        rows.append(
            {
                "Mes": mes.to_period("M"),
                "Data": mes,
                "Receita": round(receita, 2),
                "Lucro": round(lucro, 2),
                "Custo": round(custo, 2),
                "ID_Pedido": f"P{np.random.randint(10000, 99999)}",
                "Quantidade": np.random.randint(1, 20),
                "Desconto_Pct": round(np.random.uniform(0, 0.25) * 100, 2),
                "Frete": round(np.random.uniform(5, 120), 2),
                "Categoria": np.random.choice(categorias),
                "Canal_Venda": np.random.choice(canais),
                "Regiao": np.random.choice(regioes),
                "Vendedor": np.random.choice(vendedores),
                "Produto": f"Produto_{np.random.randint(1, 200)}",
            }
        )

    return pd.DataFrame(rows)


def load_data(official_path: str) -> pd.DataFrame:
    """Carrega dados obedecendo à hierarquia: upload > oficiais > demo.

    Prioridade:
        1. DataFrame em session_state.df (já carregado anteriormente).
        2. Upload do usuário (session_state.uploaded_file).
        3. Planilha oficial Dados_PHOSDash.xlsx.
        4. Dados demo gerados deterministicamente.

    O resultado é cacheado em st.session_state.df para reutilização
    entre páginas, evitando leitura de disco a cada troca.

    Args:
        official_path: Caminho para a planilha oficial.

    Returns:
        DataFrame pronto para uso no dashboard.
    """
    # 1. Cache de sessão
    if "df" in st.session_state and st.session_state.df is not None:
        return st.session_state.df

    # 2. Upload do usuário
    uploaded = st.session_state.get("uploaded_file")
    if uploaded:
        try:
            df = pd.read_excel(uploaded)
        except ValueError as exc:
            st.warning(f"📄 Formato de arquivo inválido no upload: {exc}")
            # Fall through to official/demo
        except OSError as exc:
            st.warning(f"💾 Erro ao ler arquivo enviado: {exc}")
        else:
            try:
                df = standardize(df)
            except Exception as exc:
                st.warning(f"⚠️ Erro ao padronizar dados enviados: {exc}")
            else:
                st.session_state.df = df
                return df

    # 3. Planilha oficial
    df = load_official_data(official_path)
    if df is not None:
        st.session_state.df = df
        return df

    # 4. Dados demo (fallback)
    df = generate_demo_data()
    st.session_state.df = df
    return df


def reset_uploaded_data() -> None:
    """Limpa o dataframe em sessão e o cache para permitir novo carregamento."""
    if "df" in st.session_state:
        del st.session_state.df
    st.cache_data.clear()
