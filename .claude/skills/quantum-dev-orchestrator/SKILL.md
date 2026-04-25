---
name: quantum-dev-orchestrator
description: |
  Master orchestrator for Quantum Investment Terminal development.
  Coordinates Phase scaffolding, domain layer implementation, API adapters, and testing across all 7 phases.
  Spawns parallel agents for independent modules, aggregates results, runs verification tests.
  Use at phase kickoffs or when multiple modules need parallel development.
  Input: phase number or task list. Output: complete working phase with tests passing.
---

# Quantum Dev Orchestrator (Master Commander)

Master orchestrator that coordinates all development tasks across Quantum Terminal.

## What it does

**Phase Orchestration**:
- Phase 1 (Weeks 1-2): domain layer + utils + database
- Phase 2 (Weeks 3-4): 5+ API adapters + AI gateway + sentiment
- Phase 3+ (ongoing): UI modules + features

**Parallel Agent Spawning**:
- Spawns independent agents for each module (no dependencies)
- Each agent uses phase-skeleton-generator, domain-layer-scaffolder, api-adapter-factory
- Aggregates results, runs tests, reports status

**Testing & Verification**:
- Runs `pytest domain/ -v` after Phase 1
- Runs `pytest infrastructure/ -v` after Phase 2
- Validates all imports, no circular dependencies
- Reports coverage, linting, type checking

**Model Assignment**:
- Assigns Claude Haiku for quick tasks (scaffolding, simple adapters)
- Assigns Claude Sonnet for complex logic (domain formulas, ML models)
- Assigns Claude Opus for architecture decisions (fallback chains, caching strategy)

## When to use

- **Phase kickoff**: `I'm starting Phase 1, orchestrate everything`
- **Parallel development**: `Implement these 5 adapters in parallel`
- **Full CI/CD**: `Run Phase 1 → Phase 2 → full test suite`
- **Status check**: `Show me what needs to be done`

## Command examples

```
Orchestrate Phase 1: domain layer + utils + database setup
```

```
Generate Phase 2 in parallel: 
- finnhub_adapter
- yfinance_adapter  
- fmp_adapter
- fred_adapter
- groq_backend
All at the same time with tests
```

```
Run full verification:
- pytest domain/ -v
- pytest infrastructure/ -v
- mypy quantum_terminal/
- black . --check
- ruff check .
```

## Agent assignment strategy

| Task | Model | Reason |
|------|-------|--------|
| Scaffolding (phase_skeleton_generator) | Haiku | Fast, deterministic |
| Domain formulas (valuation, risk) | Sonnet | Complex math, many edge cases |
| API adapters | Haiku | Template-based, repetitive |
| Macro adapters (FRED, EIA) | Haiku | Straightforward API calls |
| AI gateways | Sonnet | Routing logic, fallback chains |
| ML models (LightGBM, Prophet) | Opus | Complex algorithms, hyperparameter tuning |
| PyQt6 UI | Sonnet | Layout logic, event handling |
| Tests | Haiku | Clear test templates |

## Phase 1 Master Plan (Weeks 1-2)

```
Task Group 1 (Day 1-2, parallel):
├── Agent 1: Phase 1 Skeleton (phase-skeleton-generator)
├── Agent 2: Domain Models (domain-layer-scaffolder → models.py)
├── Agent 3: Valuation Module (domain-layer-scaffolder → valuation.py)
└── Agent 4: Risk Module (domain-layer-scaffolder → risk.py)

Task Group 2 (Day 3, after 1 passes):
├── Agent 5: Utils - Logger (phase-skeleton-generator)
├── Agent 6: Utils - Cache (phase-skeleton-generator)
├── Agent 7: Utils - RateLimiter (phase-skeleton-generator)
└── Agent 8: Database Setup (phase-skeleton-generator)

Verification (Day 4-5):
├── Run: pytest domain/ -v (must pass 100%)
├── Run: mypy quantum_terminal/ (no errors)
├── Run: black . --check (formatting)
└── Commit & Push

Result: Phase 1 complete, ready for Phase 2
```

## Phase 2 Master Plan (Weeks 3-4)

```
Task Group 1 (Week 3, parallel adapters):
├── Agent 1: Finnhub Adapter (api-adapter-factory)
├── Agent 2: yfinance Adapter (api-adapter-factory)
├── Agent 3: FMP Adapter (api-adapter-factory)
├── Agent 4: Tiingo Adapter (api-adapter-factory)
├── Agent 5: SEC Adapter (api-adapter-factory)
└── Agent 6: data_provider.py (fallback coordinator)

Task Group 2 (Week 3, macro + macro):
├── Agent 7: FRED Adapter (api-adapter-factory)
├── Agent 8: EIA Adapter (api-adapter-factory)
└── Agent 9: AI Gateway (api-adapter-factory)

Task Group 3 (Week 4, AI backends):
├── Agent 10: Groq Backend (api-adapter-factory)
├── Agent 11: DeepSeek Backend (api-adapter-factory)
├── Agent 12: Qwen Backend (api-adapter-factory)
├── Agent 13: OpenRouter Backend (api-adapter-factory)
└── Agent 14: HF Backend (api-adapter-factory)

Task Group 4 (Week 4, sentiment):
├── Agent 15: NewsAPI Adapter (api-adapter-factory)
├── Agent 16: FinBERT Analyzer (api-adapter-factory)
├── Agent 17: Reddit Adapter (api-adapter-factory)
└── Agent 18: FINRA Adapter (api-adapter-factory)

Verification (Week 4, Day 4-5):
├── Run: pytest infrastructure/ -v (must pass 100%)
├── Run: Integration tests (all adapters + fallback chain)
├── Benchmark: Data fetching performance (100 tickers < 5 sec)
└── Commit & Push

Result: Phase 2 complete, 15+ adapters + AI gateway working
```

## Status reporting

After each task group:
```
✅ Phase 1 Task Group 1: 4/4 agents completed
   └─ Skeleton: OK | Models: OK | Valuation: OK | Risk: OK
   
✅ Phase 1 Task Group 2: 4/4 agents completed
   └─ Logger: OK | Cache: OK | RateLimiter: OK | Database: OK

✅ Verification:
   └─ pytest: 45 passed, 0 failed ✓
   └─ mypy: 0 errors ✓
   └─ black: all formatted ✓

🎯 Phase 1 COMPLETE — Ready for Phase 2
```

## Critical success criteria

**Phase 1**:
- ✅ `pytest domain/ -v` → all tests pass
- ✅ `mypy quantum_terminal/` → zero errors
- ✅ No bare excepts in code
- ✅ SQLAlchemy ORM (no raw SQL)
- ✅ Git commits with clear messages

**Phase 2**:
- ✅ `pytest infrastructure/ -v` → all tests pass
- ✅ Fallback chain tested (all 5 market data adapters working)
- ✅ Rate limiting verified (no 429 errors)
- ✅ Caching working (90% cache hit on repeated calls)
- ✅ AI gateway routing all 6 backends

## Notes

- Orchestrator spawns agents with clear task boundaries (no overlaps)
- Each agent reports back: OK ✓ or FAILED ✗
- If any agent fails, orchestrator stops and reports what needs fixing
- Verification tests run after all agents complete
- Ready for CI/CD automation later

## See also

- `phase-skeleton-generator` — Generate scaffolding
- `domain-layer-scaffolder` — Create domain logic
- `api-adapter-factory` — Create API adapters
- `CLAUDE.md` — Development rules
- `PLAN_MAESTRO.md` — Full architecture
