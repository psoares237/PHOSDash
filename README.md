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
├── app.py                  # Shell: sidebar, hero, navegação, importação
├── assets/theme.css         # CSS premium (dark theme)
├── components/
│   ├── crossfilter.py      # Motor de cross-filtering (Power BI style)
│   ├── ui.py               # KPIs, chart_block, section_header
│   └── charts.py           # Limpeza de figuras Plotly
├── services/
│   ├── analytics_service.py # Agragações (grouped_sales, monthly_sales, top_share)
│   └── insights_engine.py  # Insights automáticos
├── utils/
│   └── formatters.py       # fmt_currency, fmt_pct, etc.
├── pages/
│   ├── 01_Overview.py      # Visão Geral
│   └── 02_Receita.py       # Receita e Crescimento
└── tests/
    └── test_analytics.py
```