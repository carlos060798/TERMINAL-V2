# QUANTUM INVESTMENT TERMINAL — PLAN MAESTRO DE DESARROLLO
## Arquitectura Final · Librerías · Módulos · Orden de Construcción

---

# I. STACK TECNOLÓGICO COMPLETO

## Lenguaje y entorno
```
Python 3.12         → última versión estable, typing mejorado
uv                  → gestor de paquetes ultrarrápido (reemplaza pip)
pyproject.toml      → configuración moderna del proyecto
.env                → secretos (nunca en código)
```

---

## UI — Interfaz de Escritorio
```
PyQt6               → framework principal de ventanas nativas
  PyQt6-Qt6         → runtime Qt6
  PyQt6-sip         → bindings C++

pyqtgraph           → gráficas tiempo real (usado en terminales reales:
                       QuantConnect, AlgoTrader, Sierra Chart Python)
                       candlestick, volume, indicadores técnicos live

PyQtWebEngine       → widget browser embebido en Qt
                       → embebe TradingView charts (HTML/JS)
                       → embebe reportes Plotly interactivos

plotly              → gráficas interactivas ricas (heatmaps, 3D, sankey)
                       exporta a HTML → carga en QWebEngine

mplfinance          → candlestick con matplotlib para análisis estático

qt-material         → tema Material Design para PyQt6 (bloomberg dark)
```

---

## Datos de Mercado y Financieros
```
yfinance            → Yahoo Finance: precios, info, opciones, historial
                       (usado en QuantConnect, Zipline, Backtrader)

pandas-datareader   → FRED, Banco Mundial, otras fuentes macro

httpx               → cliente HTTP async moderno (reemplaza requests)
                       soporte HTTP/2, timeouts, retry automático

websockets          → WebSocket para precios Finnhub en tiempo real

aiohttp             → cliente async alternativo para batch requests
```

---

## Análisis Técnico
```
pandas-ta           → 130+ indicadores técnicos en pandas puro
                       RSI, MACD, Bollinger, EMA, ATR, Stochastic
                       (más completo que ta-lib, sin compilar C)

vectorbt            → backtesting vectorizado ultrarrápido
                       usado en hedge funds quant para estrategias
                       1000x más rápido que backtrader en señales

quantstats          → métricas de performance de portafolio
                       Sharpe, Sortino, Calmar, drawdown, estadísticas
                       genera reportes HTML estilo Quantopian

pyfolio             → análisis de portafolio (creado por Quantopian)
                       tear sheets profesionales

ta                  → librería TA alternativa ligera (fallback pandas-ta)
```

---

## Optimización de Portafolio
```
riskfolio-lib       → optimización de portafolio institucional
                       Markowitz, CVaR, Black-Litterman, HRP
                       usado en gestoras reales

PyPortfolioOpt      → Markowitz mean-variance, efficient frontier
                       más simple que riskfolio, buen complemento

scipy               → optimización numérica, estadística avanzada
numpy               → álgebra lineal, cálculos vectorizados
```

---

## Machine Learning y Redes Neuronales
```
scikit-learn        → ML clásico: clasificación, regresión, clustering
                       → Scoring del screener (RandomForest sobre ratios)
                       → Detección de anomalías contables (IsolationForest)
                       → PCA para reducción dimensional de factores

lightgbm            → gradient boosting ultrarrápido (Microsoft)
                       → Score de calidad 0-100 (modelo supervisado)
                       → Predicción de sorpresas de earnings
                       → Clasificación de manipulación contable
                       usado en: Two Sigma, Citadel, Jane Street

xgboost             → gradient boosting alternativo (Kaggle estándar)
                       → Ensemble con lightgbm para más robustez

torch (PyTorch)     → redes neuronales profundas
                       → LSTM para predicción de series de tiempo
                       → Transformer para análisis de texto financiero
                       → Modelo de scoring de tesis de inversión

prophet             → forecasting de series de tiempo (Meta/Facebook)
                       → Proyección de ingresos/EPS para DCF dinámico
                       → Detección de estacionalidad en earnings
                       usado en: equipos de FP&A en Fortune 500

statsmodels         → modelos estadísticos clásicos
                       → ARIMA para series financieras
                       → Tests de estacionariedad (ADF, KPSS)
                       → Regresión Fama-French 3 factores
```

---

## NLP y Sentimiento (Redes Neuronales Pre-entrenadas)
```
transformers        → HuggingFace: modelos pre-entrenados
  FinBERT           → BERT entrenado en texto financiero
                       → Score sentimiento de noticias/earnings calls
                       → Clasificación: positivo/negativo/neutral
                       (paper original: ProsusAI/finbert en HuggingFace)

  FinancialBERT     → variante más reciente de FinBERT
  
  sec-bert-base     → BERT entrenado en filings SEC
                       → Extracción de información de 10-K/10-Q

sentence-transformers → embeddings semánticos de texto
                        → RAG: búsqueda en tesis de inversión guardadas
                        → Similaridad entre tesis actuales e históricas
                        → Clustering de noticias por tema

chromadb            → base de datos vectorial local
                       → Almacena embeddings de tesis, noticias, análisis
                       → Búsqueda semántica: "show me similar theses"

vaderSentiment      → sentimiento rápido basado en léxico
                       → Fallback si HuggingFace está lento
                       → Ideal para volumen masivo de tweets/Reddit

spacy               → NLP pipeline: NER, POS, dependencias
                       → Extrae nombres de empresas/personas de noticias
                       → Identifica métricas en texto de earnings
```

---

## Base de Datos
```
SQLite              → base de datos principal (archivo local)
                       WAL mode, índices, foreign keys habilitadas

SQLAlchemy 2.0      → ORM moderno con typed models
alembic             → migraciones de schema versionadas

diskcache           → cache en disco con TTL por tipo de dato
cachetools          → LRU cache en memoria (lru_cache mejorado)
```

---

## PDF y Documentos
```
pdfplumber          → extracción de texto y tablas de PDFs digitales
                       más preciso que pypdf para tablas financieras

pypdf               → operaciones básicas: merge, split, metadata

python-docx         → lectura de archivos .docx (manuales, reportes)

Pillow              → procesamiento de imágenes para Vision API
                       → Convierte páginas PDF escaneadas a imágenes
```

---

## Utilidades
```
pydantic v2         → validación de datos con tipos (modelos de dominio)
                       usado en FastAPI, muy robusto

python-dotenv       → carga variables de entorno desde .env

loguru              → logging moderno (reemplaza logging estándar)
                       colores, rotación automática, stack traces

rich                → output rico en consola (tablas, progress bars)
                       → útil para scripts de diagnóstico

schedule            → scheduler simple para background jobs
                       → actualiza precios cada 60 segundos

apscheduler         → scheduler avanzado con cron y jobs persistentes

tenacity            → retry con backoff exponencial para APIs
                       → reintenta llamadas fallidas automáticamente

tqdm                → progress bars para operaciones largas
                       → descarga masiva de datos históricos

pytest              → framework de tests
pytest-qt           → tests de UI Qt
pytest-asyncio      → tests de código async
```

---

# II. ADAPTADORES POR FUENTE DE DATOS

## Cadena de Fallback — Datos de Mercado
```
infrastructure/market_data/
│
├── finnhub_adapter.py      FINNHUB_API_KEY
│   Provee: precio live, earnings calendar, recomendaciones analistas
│   Rate limit: 60 req/min  |  Latencia: ~200ms  |  WebSocket: sí
│   Prioridad: 1 (primera opción para precios)
│
├── yfinance_adapter.py     (sin key)
│   Provee: historial OHLCV, info empresa, opciones, dividendos
│   Rate limit: ~2000 req/día implícito  |  Delay: 15 min
│   Prioridad: 2 (historial y datos cualitativos)
│
├── tiingo_adapter.py       TIINGO_API_KEY
│   Provee: precios ajustados limpios, fondos, ETFs
│   Rate limit: 500 req/día  |  Historial: limpio, ajustado splits
│   Prioridad: 3 (historial largo y limpio)
│
├── fmp_adapter.py          FMP_API_KEY
│   Provee: fundamentales procesados, peers, ratios ya calculados
│   Rate limit: 250 req/día  |  Fuerza: fundamentales completos
│   Prioridad: 1 para fundamentales (complementa SEC)
│
├── alphavantage_adapter.py ALPHA_VANTAGE_API_KEY
│   Provee: OHLCV, indicadores técnicos pre-calculados, forex
│   Rate limit: 25 req/día (free)  |  Fuerza: técnicos
│   Prioridad: 4 (fallback técnicos)
│
└── data_provider.py        (coordinador)
    Lógica: intenta en orden → captura error → siguiente proveedor
    Cache: resultado exitoso se guarda en diskcache
    Batch: agrupa 50 tickers → 1 llamada yfinance.download([list])
```

## Cadena de Fallback — IA
```
infrastructure/ai/
│
├── groq_backend.py         GROQ_API_KEY
│   Modelo: Llama 3.3 70B  |  Velocidad: ~500 tok/seg
│   Uso: análisis rápidos, sentimiento, chat, thesis summaries
│   Prioridad: 1
│
├── deepseek_backend.py     DEEPSEEK_API_KEY
│   Modelo: DeepSeek R1  |  Especialidad: razonamiento complejo
│   Uso: DCF multi-escenario, análisis Graham 7 pasos, post-mortem
│   Prioridad: 2 (para análisis que requieren pensar)
│
├── qwen_backend.py         QWEN_API_KEY
│   Modelo: Qwen2.5-72B  |  Especialidad: volumen y Asia
│   Uso: screener masivo (500+ tickers), mercados asiáticos
│   Prioridad: 3
│
├── kami_backend.py         KAMI_IA
│   Capacidad: Vision API (análisis de imágenes)
│   Uso: PDFs escaneados, análisis de charts subidos por usuario
│   Prioridad: 1 para Vision
│
├── openrouter_backend.py   OPENROUTER_API_KEY
│   Uso: fallback universal cuando los anteriores fallan
│   Prioridad: 4 (último recurso texto)
│
├── hf_backend.py           HF_TOKEN
│   Modelos: FinBERT, sec-bert-base, sentence-transformers
│   Uso: sentimiento masivo, embeddings, RAG
│   Prioridad: 1 para NLP/sentimiento batch
│
└── ai_gateway.py           (coordinador + balanceador)
    Selección automática según tipo de tarea:
      tipo="fast"     → Groq
      tipo="reason"   → DeepSeek
      tipo="vision"   → Kami
      tipo="sentiment"→ HuggingFace FinBERT
      tipo="bulk"     → Qwen
      tipo="fallback" → OpenRouter
    Contador de tokens por proveedor por día
    Retry automático con tenacity
```

## Adaptadores Macro y Especializados
```
infrastructure/macro/
├── fred_adapter.py         FRED_API_KEY
│   Series clave: DGS10, DGS2, CPIAUCSL, UNRATE, M2SL, FEDFUNDS
│   Input directo: bono 10Y → Graham Formula en tiempo real
│
├── eia_adapter.py          EIA_API_KEY
│   Series: WTI, Brent, Henry Hub gas, inventarios petróleo
│
└── sec_adapter.py          SEC_USER_AGENT (sin key)
    Endpoints: submissions, companyfacts, companyconcept
    65+ campos XBRL por empresa, histórico 10+ años
    Forms: 10-K, 10-Q, 8-K, Form 4, 13F, 13D/13G

infrastructure/sentiment/
├── newsapi_adapter.py      NEWSAPI_KEY
├── finbert_analyzer.py     HF_TOKEN (FinBERT local)
├── reddit_adapter.py       REDDIT_CLIENT_ID/SECRET
└── finra_adapter.py        (sin key) — short volume diario

infrastructure/crypto/
├── messari_adapter.py      MESSARI_API_KEY
└── coinbase_adapter.py     COINBASE_API_KEY
```

---

# III. ESTRUCTURA COMPLETA DEL PROYECTO

```
quantum_terminal/
│
├── main.py                     → QApplication, splash screen, init
├── config.py                   → todas las API keys desde .env, settings
├── pyproject.toml              → dependencias con uv
├── .env                        → secrets (nunca en git)
├── .gitignore
│
├── domain/                     ← LÓGICA PURA (sin I/O, sin UI)
│   ├── models.py               → dataclasses/pydantic: Portfolio, Trade,
│   │                              Quote, Company, Thesis, Alert, Screener
│   ├── valuation.py            → Graham Formula, NNWC, Liquidación,
│   │                              EPV, P/E ajustado sector
│   ├── risk.py                 → VaR, Sharpe, Sortino, Beta,
│   │                              Score calidad 0-100, detección manipulación
│   ├── screener_rules.py       → predicados de filtro (pure functions)
│   ├── portfolio_metrics.py    → Markowitz, efficient frontier, correlation
│   ├── thesis_scorer.py        → scoring de tesis (ML con lightgbm)
│   └── trading_metrics.py      → Profit Factor, Expectancy, R multiples,
│                                  adherencia al plan
│
├── infrastructure/             ← TODO EL I/O
│   ├── market_data/
│   │   ├── data_provider.py    → coordinador con fallback chain
│   │   ├── finnhub_adapter.py
│   │   ├── yfinance_adapter.py
│   │   ├── tiingo_adapter.py
│   │   ├── fmp_adapter.py
│   │   └── alphavantage_adapter.py
│   ├── macro/
│   │   ├── fred_adapter.py
│   │   ├── eia_adapter.py
│   │   └── sec_adapter.py      → XBRL + filings (portar sec_api.py)
│   ├── sentiment/
│   │   ├── newsapi_adapter.py
│   │   ├── finbert_analyzer.py
│   │   ├── reddit_adapter.py
│   │   └── finra_adapter.py
│   ├── crypto/
│   │   ├── messari_adapter.py
│   │   └── coinbase_adapter.py
│   ├── ai/
│   │   ├── ai_gateway.py
│   │   └── backends/           → 6 archivos (portar existentes)
│   ├── pdf/
│   │   ├── pdf_extractor.py    → pdfplumber (portar pdf_parser.py)
│   │   └── vision_analyzer.py  → Kami Vision API
│   ├── ml/
│   │   ├── screener_model.py   → LightGBM score calidad
│   │   ├── anomaly_detector.py → IsolationForest manipulación
│   │   ├── forecast_engine.py  → Prophet (EPS/revenue forecasting)
│   │   ├── lstm_model.py       → PyTorch LSTM series de tiempo
│   │   └── embeddings.py       → sentence-transformers + chromadb
│   └── db/
│       ├── database.py         → SQLite limpio, WAL, sin injection
│       ├── migrations/         → Alembic scripts
│       └── repositories/
│           ├── portfolio_repo.py
│           ├── trade_repo.py
│           ├── watchlist_repo.py
│           ├── thesis_repo.py
│           └── intel_repo.py
│
├── application/                ← CASOS DE USO (orquestan dominio + infra)
│   ├── portfolio/
│   │   ├── get_portfolio_summary.py
│   │   ├── add_trade.py
│   │   ├── close_position.py
│   │   └── calculate_risk_metrics.py
│   ├── market/
│   │   ├── get_quote.py
│   │   ├── get_history.py
│   │   ├── get_fundamentals.py
│   │   ├── run_screener.py
│   │   └── run_backtest.py
│   ├── ai/
│   │   ├── generate_investment_thesis.py
│   │   ├── analyze_news_sentiment.py
│   │   ├── score_thesis.py
│   │   └── chat_with_terminal.py
│   ├── trading/
│   │   ├── log_trade.py
│   │   ├── evaluate_plan_adherence.py
│   │   ├── generate_weekly_postmortem.py
│   │   └── calculate_journal_stats.py
│   ├── thesis/
│   │   ├── create_thesis.py
│   │   ├── update_thesis_status.py
│   │   ├── track_thesis_vs_market.py
│   │   └── find_similar_thesis.py   → RAG con embeddings
│   ├── pdf/
│   │   └── ingest_pdf_report.py
│   └── alerts/
│       ├── set_price_alert.py
│       └── check_alerts.py
│
├── ui/                         ← PRESENTACIÓN PyQt6
│   ├── main_window.py          → QMainWindow, layout Bloomberg
│   ├── panels/
│   │   ├── dashboard_panel.py      MÓDULO 1
│   │   ├── watchlist_panel.py      MÓDULO 2
│   │   ├── analyzer_panel.py       MÓDULO 3
│   │   ├── screener_panel.py       MÓDULO 4
│   │   ├── macro_panel.py          MÓDULO 5
│   │   ├── journal_panel.py        MÓDULO 6
│   │   ├── thesis_panel.py         MÓDULO 7
│   │   ├── pdf_intel_panel.py      MÓDULO 8
│   │   ├── earnings_panel.py       MÓDULO 9
│   │   ├── market_monitor_panel.py MÓDULO 10
│   │   ├── backtest_panel.py       MÓDULO 11
│   │   └── risk_panel.py           MÓDULO 12
│   ├── widgets/
│   │   ├── chart_widget.py         → pyqtgraph candlestick + indicadores
│   │   ├── tradingview_widget.py   → QWebEngine con TradingView embed
│   │   ├── metric_card.py          → tarjeta KPI animada
│   │   ├── heatmap_widget.py       → plotly → QWebEngine
│   │   ├── ai_chat_widget.py       → chat lateral con contexto
│   │   ├── alert_banner.py         → notificaciones precio
│   │   ├── news_feed_widget.py     → feed noticias con sentimiento
│   │   ├── data_table.py           → QTableView sorteable y filtrable
│   │   ├── ticker_search.py        → autocompletado con fuzzy search
│   │   └── equity_curve_widget.py  → curva equity animada
│   ├── dialogs/
│   │   ├── add_trade_dialog.py     → formulario nuevo trade
│   │   ├── new_thesis_dialog.py    → formulario nueva tesis
│   │   └── settings_dialog.py     → configurar API keys, plan trading
│   └── styles/
│       ├── bloomberg_dark.qss      → tema oscuro Bloomberg
│       └── colors.py              → paleta de colores centralizada
│
└── utils/
    ├── cache.py                → diskcache wrapper con TTL por tipo
    ├── rate_limiter.py         → token bucket por proveedor
    ├── security.py             → validación tickers, anti-injection
    ├── batch_fetcher.py        → agrupa requests (50 tickers → 1 call)
    ├── logger.py               → loguru config
    └── background_worker.py    → QThreadPool + QRunnable (no daemon)
```

---

# IV. LOS 12 MÓDULOS — DESCRIPCIÓN COMPLETA

Ver README.md y PROJECT_SCAFFOLD_SUMMARY.md para detalles de módulos 1-12, APIs, y próximos pasos.

---

# V. VERIFICACIÓN Y DESARROLLO

**Estado**: Fase 1 lista para comenzar
**Próximos pasos**: `uv sync` → configurar .env → `python scripts/phase_generator.py --phase 1`

Para información completa ver: README.md, PROJECT_SCAFFOLD_SUMMARY.md, CLAUDE.md
