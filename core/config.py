"""Configuração centralizada do PHOSDash.

Agrupa paths, dimensões, cores e mapeamentos de colunas num
único dataclass Config. Basta instanciar com o diretório base
do projeto e todos os caminhos são resolvidos automaticamente.
"""

import os
from dataclasses import dataclass, field


# Cores oficiais do PHOSDash (dark theme)
CHART_COLORS: list[str] = [
    "#2c6b96",  # Azul principal
    "#d3b73e",  # Dourado
    "#357560",  # Verde
    "#cabdaf",  # Areia
    "#384727",  # Verde escuro
    "#8B5CF6",  # Roxo
    "#F87171",  # Vermelho suave
    "#60A5FA",  # Azul claro
]

# Mapeamento de colunas oficiais → nome interno
COL_MAP: dict[str, str] = {
    "Valor_Total": "Receita",
    "Custo_total": "Custo",
}

# Dimensões disponíveis para cross-filtering
DIMENSIONS_FULL: list[tuple[str, str]] = [
    ("Categoria", "Categoria"),
    ("Canal_Venda", "Canal"),
    ("Regiao", "Região"),
    ("Vendedor", "Vendedor"),
    ("Forma_Pagamento", "Pagamento"),
]


@dataclass
class Config:
    """Configuração centralizada do PHOSDash.

    Attributes:
        base_dir: Diretório raiz do projeto (onde está app.py).
        dados_oficiais: Caminho para a planilha oficial Dados_PHOSDash.xlsx.
        modelo_download: Caminho para o modelo de preenchimento .xlsx.
        logo_sidebar: Caminho para o logo PHOS (sidebar).
        bg_watermark: Caminho para a marca d'água de fundo.
        assets_css: Caminho para a folha de estilos CSS.
        col_map: Mapeamento de colunas originais → internas.
        dimensions_full: Dimensões para cross-filtering.
        chart_colors: Paleta de cores para gráficos.
    """

    base_dir: str

    # ── Paths ──
    dados_oficiais: str = field(init=False)
    modelo_download: str = field(init=False)
    logo_sidebar: str = field(init=False)
    bg_watermark: str = field(init=False)
    assets_css: str = field(init=False)

    # ── Dimensões ──
    col_map: dict[str, str] = field(default_factory=lambda: COL_MAP.copy())
    dimensions_full: list[tuple[str, str]] = field(
        default_factory=lambda: DIMENSIONS_FULL.copy()
    )

    # ── Cores ──
    chart_colors: list[str] = field(default_factory=lambda: CHART_COLORS.copy())

    def __post_init__(self) -> None:
        """Resolve todos os caminhos a partir de base_dir."""
        self.dados_oficiais = os.path.join(self.base_dir, "Dados_PHOSDash.xlsx")
        self.modelo_download = os.path.join(self.base_dir, "Modelo_dados_PHOSDash.xlsx")
        self.logo_sidebar = os.path.join(self.base_dir, "assets", "logo_phos_transparent.png")
        self.bg_watermark = os.path.join(self.base_dir, "assets", "bg_watermark.png")
        self.assets_css = os.path.join(self.base_dir, "assets", "theme.css")
