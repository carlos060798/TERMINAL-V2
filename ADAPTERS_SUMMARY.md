# 7 Adaptadores Completos para Quantum Investment Terminal

## Resumen de Entrega

Se han generado **7 adaptadores funcionales** con arquitectura async, rate limiting, caching, excepciones específicas y 15+ tests cada uno.

### Macro Adapters (2)

#### 1. `infrastructure/macro/fred_adapter.py` (420 líneas)
**Adaptador FRED para datos macroeconómicos**

Métodos principales:
- `get_series(series_id, start_date, end_date)` - Obtener serie completa
- `get_latest(series_id)` - Último valor de una serie
- `batch_latest(series_ids)` - Múltiples series en lote
- `get_observations(series_id, limit, sort_order)` - Observaciones con paginación

Características:
- Rate limiting: 42 req/hora (1000 req/día)
- Cache: 24 horas
- Series críticas: DGS10, CPI, UNRATE, M2SL, FEDFUNDS
- Excepciones: FREDRateLimitException, FREDAuthException, FREDSeriesException, FREDDataException

---

#### 2. `infrastructure/macro/eia_adapter.py` (410 líneas)
**Adaptador EIA para datos de energía**

Métodos principales:
- `get_crude_oil_wti()` - Precio WTI
- `get_crude_oil_brent()` - Precio Brent
- `get_natural_gas()` - Precio gas natural
- `get_inventories()` - Niveles de inventario
- `get_refinery_utilization()` - Utilización de refinerías
- `batch_latest(series_names)` - Múltiples series

Características:
- Rate limiting: 120 req/hora
- Cache: 24 horas
- Excepciones específicas por tipo de error

---

### AI Backends (5)

#### 3. `infrastructure/ai/backends/groq_backend.py` (390 líneas)
**Backend Groq - Llama 3.3 70B**

- `generate(prompt, max_tokens, temperature)` - Generación de texto
- `stream(prompt)` - Streaming
- `batch_generate(prompts)` - Procesamiento en lote

Rate limiting: 30 req/minuto
Modelo: llama-3.3-70b-versatile

---

#### 4. `infrastructure/ai/backends/deepseek_backend.py` (385 líneas)
**Backend DeepSeek - R1 Reasoner**

- `generate(prompt, thinking_budget, max_tokens)` - Con razonamiento extendido
- `batch_generate(prompts)` - Lote con reasoning

Rate limiting: 60 req/minuto
Retorna: dict con "thinking" y "content"

---

#### 5. `infrastructure/ai/backends/qwen_backend.py` (355 líneas)
**Backend Qwen - Qwen2.5-72B**

- `generate(prompt, max_tokens, temperature)`
- `batch_generate(prompts)`

Rate limiting: 100 req/minuto
Optimizado para análisis en lote

---

#### 6. `infrastructure/ai/backends/openrouter_backend.py` (375 líneas)
**Backend OpenRouter - Fallback Universal**

- `generate(prompt, model, max_tokens, temperature)`
- `batch_generate(prompts, model)`
- `list_models()` - Modelos disponibles

Rate limiting: 100 req/minuto
Modelos: Llama 2, Claude, GPT-4, Mistral

---

#### 7. `infrastructure/ai/backends/hf_backend.py` (430 líneas)
**Backend HuggingFace - Local Sentiment & Embeddings**

- `analyze_sentiment(text, model)` - FinBERT o SEC-BERT
- `batch_analyze(texts, model)` - Lote de análisis
- `get_embedding(text)` - Embeddings (cached LRU)
- `batch_get_embeddings(texts)` - Lote de embeddings
- `get_cache_stats()` - Estadísticas
- `clear_embedding_cache()` - Limpiar caché

Características:
- Totalmente local, sin API calls
- LRU cache (10,000 items)
- Soporte GPU opcional
- Tres modelos: FinBERT, SEC-BERT, Sentence-Transformers

---

## Tests

7 archivos de tests con 15+ casos cada uno:

- `tests/test_fred_adapter.py` - FRED API
- `tests/test_eia_adapter.py` - EIA API
- `tests/test_groq_backend.py` - Groq backend
- `tests/test_deepseek_backend.py` - DeepSeek backend
- `tests/test_qwen_backend.py` - Qwen backend
- `tests/test_openrouter_backend.py` - OpenRouter backend
- `tests/test_hf_backend.py` - HuggingFace backend

**Total: 105+ tests**

Cobertura:
- Inicialización y configuración
- Rate limiting
- Caching
- Manejo de errores (401, 404, 429, timeout)
- Excepciones específicas
- Métodos principales
- Context managers
- Instancias globales

---

## Características Transversales

### Async/Await
Todos implementan async/await completo para operaciones I/O.

### Rate Limiting
- FRED: 1000 req/day (42 req/h)
- EIA: 120 req/h
- Groq: 30 req/min
- DeepSeek: 60 req/min
- Qwen: 100 req/min
- OpenRouter: 100 req/min
- HF: Ilimitado (local)

### Caching
- Macro (FRED, EIA): 24 horas
- IA: No (generación única)
- HF: LRU en memoria para embeddings

### Excepciones Específicas
Cada adaptador define su propia jerarquía:
- RateLimitException
- AuthException
- DataException
- SeriesException (macro)
- GenerationException (IA)
- LoadException (HF)

---

## Instalación

```bash
pip install aiohttp groq transformers sentence-transformers
pip install torch  # Para GPU en HF
```

---

## Archivo __init__.py

Los backends están organizados en:
`infrastructure/ai/backends/__init__.py`

Exporta:
- GroqBackend, GroqException
- DeepSeekBackend, DeepSeekException
- QwenBackend, QwenException
- OpenRouterBackend, OpenRouterException
- HFBackend, HFException
