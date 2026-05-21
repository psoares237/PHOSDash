# PHOSDash

Dashboard Executivo de Performance — PHOSFit Brasil.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Estrutura

```
PHOSDash/
├── app.py                     # Shell principal: sidebar, hero, navegação, roteamento
├── assets/theme.css           # CSS premium (dark theme)
├── core/
│   ├── config.py              # Configuração central (paths, constantes, watermark)
│   ├── data_loader.py         # Carregamento e cache dos dados Excel
│   └── sidebar.py             # Renderização da sidebar (filtros, ano, página)
├── state/
│   └── filters.py             # FilterState — estado dos cross-filters por página
├── components/
│   ├── crossfilter.py         # Motor de cross-filtering (Power BI style)
│   ├── ui.py                  # KPIs, chart_block, section_header
│   └── charts.py              # Limpeza de figuras Plotly
├── services/
│   ├── analytics_service.py   # Agregações (grouped_sales, monthly_sales, top_share)
│   ├── alert_engine.py        # Motor de alertas automáticos (HHI, margens, etc.)
│   ├── insights_engine.py     # Insights automáticos
│   ├── kpi_service.py         # Cálculo de KPIs e índices (HHI, etc.)
│   ├── page_engine.py         # Orquestração dos dados por página (PageContext)
│   └── pdf_export.py          # Exportação de relatório PDF executivo (1 página)
├── views/
│   ├── Overview.py            # Visão Geral Operacional
│   ├── Receita.py             # Visão Estratégica (Receita)
│   └── Financeiro.py          # Visão Financeira
├── utils/
│   └── formatters.py          # fmt_currency, fmt_pct, fmt_int, pct_change
├── tests/
│   ├── test_analytics.py
│   ├── test_alert_engine.py
│   ├── test_filters.py
│   ├── test_kpi_service.py
│   └── test_page_engine.py
├── Dados_PHOSDash.xlsx        # Base de dados Excel
└── requirements.txt           # Dependências Python
```