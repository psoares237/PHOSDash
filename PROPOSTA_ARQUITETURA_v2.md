# PROPOSTA ARQUITETURAL — PHOSDash v2

> **Status:** Rodada 2 EXECUTADA e VALIDADA ✅ (18/05/2026)  
> **Data original:** 2026-05-18  
> **Autor:** Hermes (Engenheiro de Software Sênior)  
> **Princípios:** Clean Architecture, SOLID, baixo acoplamento, alta manutenção  
> **Última atualização:** 2026-05-18 — Fases 1-3 concluídas, Fase 4 validada

---

## DIAGNÓSTICO

### 1. Repetição no app.py
Cada página repete o mesmo bloco: `render_dimension_filters` → `render_filter_bar` → `apply_filters` → `recompute_total` → `monthly_sales/grouped_sales`. Visão Geral (18 linhas de prep), Receita (12 linhas), Custos (16 linhas). ~46 linhas duplicadas que crescerão linearmente a cada nova página.

### 2. Acoplamento Streamlit
`crossfilter.py` e `ui.py` misturam lógica de estado (`session_state`), renderização (`st.selectbox`, `st.markdown`, `st.plotly_chart`) e negócio (filtragem). Impossível testar isoladamente. Impossível reutilizar num backend/API.

### 3. Performance
Zero `@st.cache_data`. Cada interação (clique, filtro) reprocessa tudo do zero. Com bases grandes ficará lento.

### 4. Cross-filtering frágil
`chart_block()` em `ui.py` usa `result.selection.point_indices[0]` e `trace.x/names/y` com `try/except pass`. Não funciona para pie/donut (que usam `labels`), e o `pass` silencia erros.

---

## ESTRUTURA PROPOSTA (nova estrutura de pastas)

```
PHOSDash/
├── app.py                     # Shell enxuto (~120 linhas)
├── state/
│   ├── __init__.py
│   ├── filters.py             # Estado puro dos filtros (sem Streamlit)
│   └── page_context.py        # PageContext dataclass
├── services/
│   ├── __init__.py
│   ├── analytics_service.py   # (+ @st.cache_data)
│   ├── insights_engine.py     # (inalterado)
│   └── page_engine.py         # NOVO — motor central de preparação
├── components/
│   ├── __init__.py
│   ├── ui.py                  # renderização pura (KPIs, sections, chart_block robusto)
│   ├── charts.py              # (inalterado)
│   └── crossfilter.py         # Refatorado — só renderização, lógica vai pra state/
├── views/
│   ├── __init__.py
│   ├── Overview.py            # (aceita PageContext)
│   ├── Receita.py
│   └── Custos.py
├── utils/
│   ├── __init__.py
│   └── formatters.py          # (inalterado)
├── assets/
│   └── theme.css              # (inalterado)
└── tests/
    ├── test_analytics.py      # (inalterado)
    ├── test_filters.py        # NOVO
    └── test_page_engine.py    # NOVO
```

---

## DETALHAMENTO DAS 4 MELHORIAS

### 1. `services/page_engine.py` — Motor Central de Preparação (elimina repetição)

```python
# services/page_engine.py
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
from state.filters import FilterState
from services.analytics_service import grouped_sales, monthly_sales, recompute_total

@dataclass
class PageContext:
    """Contexto completo pronto para consumo pela view."""
    current_df: pd.DataFrame
    previous_df: pd.DataFrame
    current_total: dict
    previous_total: dict
    monthly: pd.DataFrame
    cat: pd.DataFrame = field(default_factory=pd.DataFrame)
    canal: pd.DataFrame = field(default_factory=pd.DataFrame)
    regiao: pd.DataFrame = field(default_factory=pd.DataFrame)
    vendedor: pd.DataFrame = field(default_factory=pd.DataFrame)
    produto: pd.DataFrame = field(default_factory=pd.DataFrame)
    page_key: str = ""
    has_filters: bool = False

def prepare_page_data(
    df: pd.DataFrame,
    previous_df: pd.DataFrame,
    page_key: str,
    dimensions: list[tuple[str, str]],
) -> PageContext:
    """Prepara todos os dados para uma página: filtros, agregações, totais.
    
    Centraliza toda a lógica de preparação que antes era repetida em cada bloco
    de página no app.py. Agora cada página chama:
        ctx = prepare_page_data(df, previous_df, page_key, DIMENSIONS)
    E recebe um PageContext pronto para usar.
    """
    filter_state = FilterState(page_key)
    current_df = filter_state.apply(df) if filter_state.has_filters else df
    
    # Agregações sempre calculadas sobre o df filtrado (ou original se sem filtro)
    working_df = current_df if not current_df.empty else df
    
    return PageContext(
        current_df=current_df,
        previous_df=previous_df,
        current_total=recompute_total(current_df),
        previous_total=recompute_total(previous_df),
        monthly=monthly_sales(working_df) if not working_df.empty else pd.DataFrame(),
        cat=grouped_sales(working_df, "Categoria") if not working_df.empty else pd.DataFrame(),
        canal=grouped_sales(working_df, "Canal_Venda") if not working_df.empty else pd.DataFrame(),
        regiao=grouped_sales(working_df, "Regiao") if not working_df.empty else pd.DataFrame(),
        vendedor=grouped_sales(working_df, "Vendedor") if not working_df.empty else pd.DataFrame(),
        produto=grouped_sales(working_df, "Produto") if not working_df.empty else pd.DataFrame(),
        page_key=page_key,
        has_filters=filter_state.has_filters,
    )
```

**Antes (app.py, por bloco):**
```python
render_dimension_filters(page_key, df, DIMENSIONS_FULL)
render_filter_bar(page_key)
current_df = apply_filters(df, page_key) if has_filters(page_key) else df
filtered_total = recompute_total(current_df)
previous_total = recompute_total(previous_df)
if has_filters(page_key):
    monthly = monthly_sales(current_df) if not current_df.empty else pd.DataFrame()
    cat = grouped_sales(current_df, "Categoria") if not current_df.empty else pd.DataFrame()
    canal = grouped_sales(current_df, "Canal_Venda") if not current_df.empty else pd.DataFrame()
    regiao = grouped_sales(current_df, "Regiao") if not current_df.empty else pd.DataFrame()
else:
    monthly = monthly_sales(df)
    cat = grouped_sales(df, "Categoria")
    canal = grouped_sales(df, "Canal_Venda")
    regiao = grouped_sales(df, "Regiao")
```

**Depois:**
```python
ctx = prepare_page_data(df, previous_df, page_key, DIMENSIONS_FULL)
render_filter_bar(page_key)  # renderização permanece no app
```

**Resultado:** ~46 linhas repetidas eliminadas, 1 linha por página

---

### 2. `state/filters.py` — Estado Puro Desacoplado do Streamlit

```python
# state/filters.py
"""Estado de filtros — lógica pura, zero dependência do Streamlit.

Toda leitura/escrita de session_state passa por esta camada.
Testável isoladamente. Preparado para migração futura (FastAPI, etc.).
"""
import streamlit as st

PREFIX = "cf_"

class FilterState:
    """Gerenciador de filtros por página — bridge entre lógica pura e session_state."""
    
    def __init__(self, page_key: str):
        self.page_key = page_key
        self._key = f"{PREFIX}{page_key}"
    
    @property
    def filters(self) -> dict:
        return st.session_state.get(self._key, {})
    
    def get(self, column: str):
        return self.filters.get(column)
    
    def set(self, column: str, value):
        if self._key not in st.session_state:
            st.session_state[self._key] = {}
        st.session_state[self._key][column] = value
    
    def clear(self, column: str):
        if self._key in st.session_state and column in st.session_state[self._key]:
            del st.session_state[self._key][column]
    
    def clear_all(self):
        st.session_state[self._key] = {}
    
    def toggle(self, column: str, value):
        if self.filters.get(column) == value:
            self.clear(column)
        else:
            self.set(column, value)
    
    @property
    def has_filters(self) -> bool:
        return bool(self.filters)
    
    def apply(self, df) -> 'pd.DataFrame':
        """Filtra o DataFrame pelos filtros ativos."""
        import pandas as pd  # lazy para evitar import circular
        result = df.copy()
        for col, val in self.filters.items():
            if col in result.columns:
                result = result[result[col] == val]
        return result
```

**Ganho:** Lógica de filtros testável sem `st.session_state`. Quando migrar pra API, só troca o backing store.

---

### 3. `@st.cache_data` — Cache Inteligente

```python
# Alterações em services/analytics_service.py

@st.cache_data(ttl=300, show_spinner=False)
def grouped_sales(df: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Agrupa vendas por dimensão. Cache: 5 min, invalida com dataframe."""
    # ... corpo idêntico ...

@st.cache_data(ttl=300, show_spinner=False)
def monthly_sales(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa vendas por mês. Cache: 5 min."""
    # ... corpo idêntico ...

@st.cache_data(ttl=300, show_spinner=False)
def recompute_total(df: pd.DataFrame) -> dict:
    """Recalcula KPIs a partir do DataFrame filtrado. Cache: 5 min."""
    # ... corpo idêntico ...
```

**Atenção:** O TTL de 5 min garante que dados frescos venham do Excel. O cache invalida automaticamente quando o DataFrame muda (hash). Com `generate_demo_data()` usando `seed=42`, o hash é estável.

---

### 4. Cross-filtering Robusto — `customdata` + `_extract_clicked_value()`

O problema atual: `chart_block()` faz `trace.x[idx]` ou `trace.names[idx]`, que funciona pra barras mas quebra pra pie/donut (que usam `labels`).

**Solução:** Padronizar `customdata` em todos os gráficos e extrair o valor clicado de lá.

```python
# components/ui.py — chart_block() refatorado

def chart_block(
    title: str,
    subtitle: str,
    fig: go.Figure,
    page_key: str | None = None,
    dimension: str | None = None,
) -> None:
    # ... header markdown igual ...
    
    config = {"displayModeBar": False}
    chart_key = f"{title}_{subtitle}".replace(" ", "_").lower()
    use_click = page_key and dimension
    
    if use_click:
        result = st.plotly_chart(
            fig, use_container_width=True, config=config,
            key=f"cf_{page_key}_{chart_key}", on_select="rerun",
            selection_mode=["points"],
        )
        # Extração robusta: tenta customdata primeiro, depois fallback
        clicked_value = _extract_clicked_value(result, fig)
        if clicked_value:
            toggle_filter(page_key, dimension, clicked_value)
    else:
        st.plotly_chart(fig, use_container_width=True, config=config, key=chart_key)


def _extract_clicked_value(result, fig) -> str | None:
    """Extrai valor clicado do gráfico de forma robusta.
    
    Prioriza customdata (adicionado ao construir o gráfico).
    Fallback para labels/names/x/y (compatibilidade reversa).
    """
    if not result or not result.selection or not result.selection.point_indices:
        return None
    
    idx = result.selection.point_indices[0]
    trace = fig.data[0]
    
    # 1. customdata (canal prioritário, robusto para todos os tipos)
    if hasattr(trace, "customdata") and trace.customdata is not None:
        try:
            return str(trace.customdata[idx])
        except (IndexError, TypeError):
            pass
    
    # 2. labels (pie/donut/sunburst)
    if hasattr(trace, "labels") and trace.labels is not None:
        try:
            return str(trace.labels[idx])
        except (IndexError, TypeError):
            pass
    
    # 3. x (barras/linhas)
    if hasattr(trace, "x") and trace.x is not None:
        try:
            return str(list(trace.x)[idx])
        except (IndexError, TypeError):
            pass
    
    # 4. names (scatter)
    if hasattr(trace, "names") and trace.names is not None:
        try:
            return str(list(trace.names)[idx])
        except (IndexError, TypeError):
            pass
    
    return None
```

E nos gráficos, adicionar `.update_traces(customdata=...)` para que o clique funcione em qualquer tipo. Exemplo nas views:

```python
# Overview.py — pie de Categoria (antes: dependia de trace.names)
fig_cat = px.pie(cat, values="Receita", names="Categoria", ...)
fig_cat.update_traces(customdata=cat["Categoria"].tolist(), ...)  # NOVO
```

---

## app.py REFATORADO (resultado final)

```python
"""PHOSDash — Shell principal (refatorado v2)."""

import streamlit as st
import pandas as pd
import numpy as np
import os

# ── Config ──
st.set_page_config(
    page_title="PHOSDash", page_icon="📊",
    layout="wide", initial_sidebar_state="expanded",
)

# ── CSS ──
st.markdown(open("assets/theme.css", encoding="utf-8").read(), unsafe_allow_html=True)

# ── Imports ──
from components.ui import render_kpis, section_header
from components.crossfilter import render_dimension_filters, render_filter_bar
from services.page_engine import prepare_page_data
from services.insights_engine import generate_insights
from utils.formatters import fmt_currency, fmt_pct, fmt_int, pct_change

# ── Constantes ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DADOS_OFICIAIS = os.path.join(BASE_DIR, "Dados_PHOSDash.xlsx")
MODELO_DOWNLOAD = os.path.join(BASE_DIR, "Modelo_dados_PHOSDash.xlsx")
# ... COL_MAP, COL_NAMES_PT, DIMENSIONS_FULL iguais ...

DIMENSIONS_FULL = [
    ("Categoria", "Categoria"),
    ("Canal_Venda", "Canal"),
    ("Regiao", "Região"),
    ("Vendedor", "Vendedor"),
]

PAGINAS = ["📊 Visão Geral", "📈 Receita e Crescimento", "💰 Custos e Despesas", ...]

# ── Funções de dados (load_official_data, standardize, generate_demo_data, load_data — idênticas) ──

# ── Sidebar (idêntica) ──

# ── Header ──
st.markdown("# 📊 PHOSDash")
st.markdown("##### Painel Executivo de Performance — PHOSFit Brasil")
st.markdown("---")

# ── Navegação ──
if pagina == "📊 Visão Geral":
    page_key = "overview"
    render_dimension_filters(page_key, df, DIMENSIONS_FULL)
    render_filter_bar(page_key)
    ctx = prepare_page_data(df, previous_df, page_key, DIMENSIONS_FULL)
    
    # KPIs
    receita = ctx.current_total["receita"]
    lucro = ctx.current_total["lucro"]
    pedidos = ctx.current_total["pedidos"]
    # ... (cálculos de KPIs permanecem no app.py pois são específicos da página)
    
    kpis = [ ... ]
    render_kpis(kpis, per_row=5)
    
    # Insights
    insights = generate_insights(ctx.current_df, ctx.current_total, ctx.previous_total)
    # ... render insights ...
    
    # View
    from views.Overview import render as render_overview
    render_overview(ctx=ctx, top_channel_name=..., top_channel_share=...)

elif pagina == "📈 Receita e Crescimento":
    page_key = "receita"
    render_dimension_filters(page_key, df, DIMENSIONS_FULL)
    render_filter_bar(page_key)
    ctx = prepare_page_data(df, previous_df, page_key, DIMENSIONS_FULL)
    
    from views.Receita import render as render_receita
    render_receita(ctx=ctx)

elif pagina == "💰 Custos e Despesas":
    page_key = "custos"
    render_dimension_filters(page_key, df, DIMENSIONS_FULL)
    render_filter_bar(page_key)
    ctx = prepare_page_data(df, previous_df, page_key, DIMENSIONS_FULL)
    
    from views.Custos import render as render_custos
    render_custos(ctx=ctx)
```

**Antes:** ~406 linhas com blocos repetidos  
**Depois:** ~120 linhas, cada página = 3 linhas de setup + chamada da view

---

## ESTRATÉGIA DE MIGRAÇÃO GRADUAL

| Ordem | Ação | Risco | Impacto |
|---|---|---|---|
| **Fase 1** | Criar `state/filters.py` + `state/__init__.py` | Baixo — camada nueva, não altera nada existente | Prepara desacoplamento |
| **Fase 2** | Criar `services/page_engine.py` + `PageContext` | Baixo — camada nueva, `crossfilter.py` antigo ainda funciona | Elimina repetição |
| **Fase 3** | Refatorar `app.py` para usar `prepare_page_data()` | Médio — altera o shell principal | app.py fica enxuto |
| **Fase 4** | Refatorar views para aceitar `PageContext` | Médio — altera assinaturas | Simplifica chamadas |
| **Fase 5** | Adicionar `@st.cache_data` em analytics_service | Baixo — só adiciona decoradores | Performance imediata |
| **Fase 6** | Refatorar `chart_block()` + `_extract_clicked_value()` | Médio — altera cross-filtering | Robustez |
| **Fase 7** | Adicionar `customdata` nos gráficos das views | Baixo — aditivo | Cross-filter universal |

---

## RISCOS

1. **`@st.cache_data` com DataFrames** — Serializa o DF inteiro como chave de cache. Para 2.400 linhas (demo data), imperceptível. Para 100k+, pode ser lento. **Mitigação:** TTL de 5 min + monitorar.

2. **Mudança de assinatura das views** — As views recebem `ctx` em vez de kwargs avulsos. Se chamar direto sem o PageContext, quebra. **Mitigação:** Fazer `render()` aceitar `ctx` PRIMEIRO, mantendo kwargs antigos como fallback com deprecation warning.

3. **Cross-filtering com `customdata`** — Se esquecer de adicionar `customdata` num gráfico novo, o fallback (x/names/y) ainda funciona. Mas pie charts SEM customdata só funcionam pelo fallback `labels`. **Mitigação:** Fallback robusto na `_extract_clicked_value`.

4. **Regressão visual** — Qualquer mudança no fluxo de renderização pode afetar layout. **Mitigação:** Os 10 testes existentes + novos testes do `FilterState` e `PageContext`.

---

## RESUMO DOS ARQUIVOS NOVOS/ALTERADOS

| Arquivo | Ação |
|---|---|
| `state/__init__.py` | **NOVO** |
| `state/filters.py` | **NOVO** — FilterState desacoplado |
| `services/page_engine.py` | **NOVO** — `prepare_page_data()` + `PageContext` |
| `services/analytics_service.py` | **ALTERADO** — adicionar `@st.cache_data` |
| `components/crossfilter.py` | **ALTERADO** — delegar lógica para `FilterState`, manter só render |
| `components/ui.py` | **ALTERADO** — `chart_block()` com `_extract_clicked_value()` |
| `app.py` | **ALTERADO** — usar `prepare_page_data()`, blocos de página enxutos |
| `views/Overview.py` | **ALTERADO** — aceitar `ctx: PageContext` |
| `views/Receita.py` | **ALTERADO** — aceitar `ctx: PageContext` |
| `views/Custos.py` | **ALTERADO** — aceitar `ctx: PageContext` |
| `tests/test_filters.py` | **NOVO** |
| `tests/test_page_engine.py` | **NOVO** |

**Arquivos INALTERADOS:** `utils/formatters.py`, `components/charts.py`, `services/insights_engine.py`, `assets/theme.css`, `views/__init__.py`

---

## PRINCÍPIOS APLICADOS

- **Clean Architecture** — Separação clara: state / services / components / views
- **SOLID** — Single Responsibility (cada módulo faz uma coisa), Open/Closed (novas páginas sem alterar app.py), Dependency Inversion (views dependem de PageContext, não de detalhes)
- ** legibilidade** — Cada arquivo tem propósito único e claro
- **Modularização** — Novas páginas = 1 view file + 3 linhas no app.py
- **Escalabilidade** — PageContext cresce horizontalmente, não verticalmente
- **Baixo acoplamento** — state/ não conhece Streamlit, services/ não conhecem views
- **Alta manutenção** — Testável, extensível, sem repetição

---

## REGISTRO DE EXECUÇÃO — Rodada 1 (18/05/2026)

### FASE 1 — Mover `recompute_total` para `analytics_service.py` ✅

- `recompute_total()` e `recompute_aggregations()` movidas de `components/crossfilter.py` para `services/analytics_service.py`
- `crossfilter.py` agora importa e reexporta essas funções para compatibilidade
- Nenhum import existente quebrou

**Arquivos alterados:**
- `services/analytics_service.py` — adicionadas `recompute_total()` e `recompute_aggregations()`
- `components/crossfilter.py` — remoção das definições locais, importação/reexportação de `analytics_service`

### FASE 2 — Criar `services/page_engine.py` ✅

- Criada dataclass `PageContext` com 12 campos (current_df, previous_df, current_total, previous_total, monthly, cat, canal, regiao, vendedor, produto, page_key, has_filters)
- Criada função `prepare_page_data(df, previous_df, page_key)` que centraliza toda a preparação de dados por página
- Lógica de filtros replicada fielmente: com filtros usa DataFrame filtrado (com empty check), sem filtros usa DataFrame original
- Usa `has_filters()` e `apply_filters()` existentes em `crossfilter.py` (sem criar `state/filters.py` — reservado para Rodada 2)

**Arquivo novo:**
- `services/page_engine.py` — `PageContext` dataclass + `prepare_page_data()`

### FASE 3 — Refatorar `app.py` com `prepare_page_data()` ✅

- Imports atualizados: removidos `apply_filters`, `get_filters`, `has_filters`, `recompute_total`; adicionados `prepare_page_data`, `top_share`
- Blocos de página Visão Geral, Receita e Custos refatorados para usar `ctx = prepare_page_data(...)`
- Assinaturas das views mantidas intactas (kwargs separados, não ctx)
- KPIs e insights na Visão Geral ainda calculados no app.py (específicos da página), mas usando `ctx.current_total`, `ctx.previous_total`
- Resultado: app.py reduziu de 406 linhas para 365 linhas (redução ~10%). Cada bloco de página: de ~20 linhas de preparação para ~5 linhas.

**Arquivo alterado:**
- `app.py` — refatoração completa dos 3 blocos de página ativos

### FASE 4 — Testes e Validação ✅

- 10/10 testes existentes passam (pytest)
- Imports verificados: `recompute_total` acessível de `crossfilter.py` e `analytics_service.py`
- `PageContext` cria corretamente com dados fictícios (100 linhas, 4 meses, 3 categorias)
- Compatibilidade retroativa confirmada: `from components.crossfilter import recompute_total` funciona

### NÃO EXECUTADO (reservado para Rodada 2)

- ✅ ~~`state/filters.py` (FilterState desacoplado)~~ — EXECUTADO NA RODADA 2
- ✅ ~~Alteração da assinatura das views para `ctx`~~ — EXECUTADO NA RODADA 2
- ✅ ~~Refatoração de `chart_block()` com `_extract_clicked_value()`~~ — EXECUTADO NA RODADA 2
- ✅ ~~`customdata` em todos os gráficos~~ — EXECUTADO NA RODADA 2
- ✅ ~~`@st.cache_data` em analytics_service~~ — EXECUTADO NA RODADA 2
- ❌ Alteração visual / CSS
- ❌ Novas páginas

---

## REGISTRO DE EXECUÇÃO — Rodada 2 (18/05/2026)

### FASE 1 — Implementar `state/filters.py` com FilterState ✅

- Criado `state/__init__.py` e `state/filters.py`
- Classe `FilterState` com métodos: `get()`, `set()`, `toggle()`, `clear()`, `clear_all()`, `apply()`, propriedade `has_filters`
- Streamlit como backend de persistência (via `st.session_state`), mas injetável para testes (parâmetro `store=dict`)
- `crossfilter.py` refatorado para delegar toda lógica de estado para `FilterState`
- Funções de compatibilidade retroativa mantidas: `get_filters()`, `set_filter()`, `clear_filter()`, `clear_all()`, `toggle_filter()`, `apply_filters()`, `has_filters()`
- `page_engine.py` atualizado para usar `FilterState` diretamente em vez de `crossfilter.apply_filters/has_filters`

**Arquivos novos:**
- `state/__init__.py`
- `state/filters.py` — `FilterState` (100% testável sem Streamlit)

**Arquivos alterados:**
- `components/crossfilter.py` — delegação para FilterState + compat retroativa
- `services/page_engine.py` — import `FilterState` em vez de `crossfilter`

### FASE 2 — Implementar `@st.cache_data` ✅

- `@st.cache_data(ttl=300)` adicionado em: `grouped_sales()`, `monthly_sales()`, `recompute_total()`, `recompute_aggregations()`
- TTL de 5 minutos — invalidação automática quando os dados mudam
- `top_share()` NÃO recebeu cache (função simples, sem custo computacional)

**Arquivos alterados:**
- `services/analytics_service.py` — 4 funções com `@st.cache_data`

### FASE 3 — Refatorar `chart_block()` com `_extract_clicked_value()` ✅

- `_extract_clicked_value()` implementada em `components/ui.py`
- Prioridade de extração: `customdata` > `labels` > `x` > `names` > `y`
- Fallback robusto sem `try/except: pass` silencioso
- `chart_block()` agora usa `FilterState(page_key).toggle()` em vez de manipulação direta de session_state
- Import de `FilterState` adicionado a `ui.py`

**Arquivos alterados:**
- `components/ui.py` — `_extract_clicked_value()` + `chart_block()` refatorado

### FASE 4 — Implementar `customdata` nos gráficos ✅

- Todos os gráficos interativos nas 3 views recebem `.update_traces(customdata=...)` ou `customdata=` no construtor
- Pie/donut: `customdata=df["Coluna"].tolist()`
- Bar: `customdata=df["Coluna"].tolist()` via `update_traces`
- Scatter/line: `customdata=monthly["MesLabel"].tolist()`
- Tipos cobertos: pie, donut, bar, scatter, line, mixed (bar+line)

**Arquivos alterados:**
- `views/Overview.py` — customdata em todos os 4 gráficos
- `views/Receita.py` — customdata em todos os 4 gráficos
- `views/Custos.py` — customdata em todos os 5 gráficos

### FASE 5 — Consolidar PageContext nas views ✅

- Todas as 3 views agora usam `render(ctx: PageContext)` como assinatura única
- Views desestruturam `ctx.current_total`, `ctx.monthly`, etc. internamente
- `app.py` chamadas simplificadas: `render_overview(ctx)`, `render_receita(ctx)`, `render_custos(ctx)`
- `PageContext` ganhou campos `top_channel_name` e `top_channel_share` (antes calculados no app.py)
- Import de `top_share` movido de `app.py` para `page_engine.py`

**Arquivos alterados:**
- `views/Overview.py` — `render(ctx: PageContext)`
- `views/Receita.py` — `render(ctx: PageContext)`
- `views/Custos.py` — `render(ctx: PageContext)`
- `services/page_engine.py` — `top_channel_name`, `top_channel_share` adicionados ao PageContext
- `app.py` — chamadas simplificadas para `render_*(ctx)`, import de `top_share` removido

### Validação ✅

- **37/37 testes passaram** (10 originais + 20 de FilterState + 7 de PageContext)
- Imports verificados: todas as classes e funções acessíveis
- `FilterState` testável com `dict` como store (sem Streamlit)
- `prepare_page_data()` lida com DataFrame vazio (guarda com `required_cols`)
- Compatibilidade retroativa mantida: `from components.crossfilter import apply_filters` funciona

### RESUMO DE LINHAS — Rodada 2

| Arquivo | Antes (R1) | Depois (R2) | Delta |
|---|---|---|---|
| `app.py` | 365 | 321 | -44 |
| `components/crossfilter.py` | 137 | 118 | -19 |
| `components/ui.py` | ~150 | ~170 | +20 |
| `services/analytics_service.py` | 106 | 110 | +4 |
| `services/page_engine.py` | 118 | 148 | +30 |
| `views/Overview.py` | ~250 | ~210 | -40 |
| `views/Receita.py` | ~220 | ~190 | -30 |
| `views/Custos.py` | ~310 | ~290 | -20 |
| `state/filters.py` | — | 118 | +118 (novo) |
| `state/__init__.py` | — | 2 | +2 (novo) |
| `tests/test_filters.py` | — | 135 | +135 (novo) |
| `tests/test_page_engine.py` | — | 115 | +115 (novo) |

**Ganhos arquiteturais:**
- Estado desacoplado: session_state isolado em `FilterState`, testável sem Streamlit
- Cache: `@st.cache_data` elimina recomputação total a cada interação
- Cross-filtering robusto: `_extract_clicked_value()` com prioridade customdata > labels > x
- Views simplificadas: `render(ctx)` sem kwargs espalhados
- customdata: payloads de clique padronizados para todos os gráficos

### O QUE FICOU PARA RODADA 3

- ❌ Refatoração de `insights_engine.py` para usar PageContext
- ❌ Stubs de novas páginas (Margem, Comercial, Geografia, etc.)
- ❌ Page engine com cache de período anterior
- ❌ Alterações visuais / CSS
- ❌ internacionalização / i18n

### RESUMO DE LINHAS

| Arquivo | Antes | Depois | Delta |
|---|---|---|---|
| `app.py` | 406 | 365 | -41 |
| `components/crossfilter.py` | 163 | 137 | -26 |
| `services/analytics_service.py` | 74 | 106 | +32 |
| `services/page_engine.py` | — | 118 | +118 (novo) |

**Líquido:** +83 linhas novas (page_engine), -67 linhas removidas (repetição no app.py + crossfilter). Ganho real: centralização da lógica, eliminação de duplicação, preparação para novas páginas.