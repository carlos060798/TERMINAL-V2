#!/usr/bin/env python3
"""
AGENT: Phase Scaffolder

Generates all skeleton files for a specific development phase.
Reads the plan document and creates empty modules with docstrings.

Usage:
  python scripts/phase_generator.py --phase 1
  python scripts/phase_generator.py --phase 2 --verbose
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

PHASES = {
    1: {
        "name": "Cimientos",
        "files": {
            "quantum_terminal/config.py": "Configuration management",
            "quantum_terminal/utils/logger.py": "Logging setup",
            "quantum_terminal/utils/cache.py": "Disk cache wrapper",
            "quantum_terminal/utils/rate_limiter.py": "API rate limiting",
            "quantum_terminal/infrastructure/db/database.py": "SQLite interface",
            "quantum_terminal/domain/models.py": "Dataclasses and models",
            "quantum_terminal/domain/valuation.py": "Graham valuation formulas",
            "quantum_terminal/domain/risk.py": "Risk metrics and quality scoring",
            "tests/test_valuation.py": "Valuation tests",
            "tests/test_risk.py": "Risk calculation tests",
        },
    },
    2: {
        "name": "Adaptadores de Datos",
        "files": {
            "quantum_terminal/infrastructure/market_data/finnhub_adapter.py": "Finnhub API",
            "quantum_terminal/infrastructure/market_data/yfinance_adapter.py": "Yahoo Finance",
            "quantum_terminal/infrastructure/market_data/fmp_adapter.py": "FMP API",
            "quantum_terminal/infrastructure/market_data/tiingo_adapter.py": "Tiingo API",
            "quantum_terminal/infrastructure/market_data/data_provider.py": "Fallback chain",
            "quantum_terminal/infrastructure/macro/fred_adapter.py": "FRED API",
            "quantum_terminal/infrastructure/macro/sec_adapter.py": "SEC XBRL API",
            "quantum_terminal/infrastructure/sentiment/finbert_analyzer.py": "FinBERT sentiment",
            "quantum_terminal/infrastructure/ai/ai_gateway.py": "AI router",
        },
    },
    3: {
        "name": "Esqueleto UI",
        "files": {
            "quantum_terminal/ui/main_window.py": "Main window",
            "quantum_terminal/ui/styles/bloomberg_dark.qss": "Dark theme",
            "quantum_terminal/ui/widgets/metric_card.py": "KPI card widget",
            "quantum_terminal/ui/widgets/data_table.py": "Data table widget",
            "quantum_terminal/ui/widgets/chart_widget.py": "Chart widget",
            "quantum_terminal/ui/widgets/ai_chat_widget.py": "Chat widget",
            "main.py": "Application entry point",
        },
    },
    4: {
        "name": "Módulos Core",
        "files": {
            "quantum_terminal/ui/panels/analyzer_panel.py": "Stock analyzer (Module 3)",
            "quantum_terminal/ui/panels/watchlist_panel.py": "Watchlist (Module 2)",
            "quantum_terminal/ui/panels/dashboard_panel.py": "Dashboard (Module 1)",
            "quantum_terminal/ui/panels/macro_panel.py": "Macro context (Module 5)",
            "quantum_terminal/application/market/get_fundamentals.py": "Fundamentals",
            "quantum_terminal/application/ai/generate_investment_thesis.py": "Thesis generation",
        },
    },
    5: {
        "name": "Trading y Tesis",
        "files": {
            "quantum_terminal/ui/panels/journal_panel.py": "Trading journal (Module 6)",
            "quantum_terminal/ui/panels/thesis_panel.py": "Investment thesis (Module 7)",
            "quantum_terminal/ui/panels/risk_panel.py": "Risk manager (Module 12)",
            "quantum_terminal/domain/thesis_scorer.py": "Thesis scoring model",
            "quantum_terminal/infrastructure/ml/embeddings.py": "Embeddings for RAG",
        },
    },
    6: {
        "name": "Screener e Inteligencia",
        "files": {
            "quantum_terminal/ui/panels/screener_panel.py": "Screener (Module 4)",
            "quantum_terminal/ui/panels/pdf_intel_panel.py": "PDF intel (Module 8)",
            "quantum_terminal/ui/panels/market_monitor_panel.py": "Market monitor (Module 10)",
            "quantum_terminal/ui/panels/earnings_panel.py": "Earnings tracker (Module 9)",
            "quantum_terminal/domain/screener_rules.py": "Filter predicates",
            "quantum_terminal/infrastructure/ml/screener_model.py": "Screener ML model",
        },
    },
    7: {
        "name": "ML Avanzado y Backtesting",
        "files": {
            "quantum_terminal/ui/panels/backtest_panel.py": "Backtesting (Module 11)",
            "quantum_terminal/infrastructure/ml/forecast_engine.py": "Prophet forecasting",
            "quantum_terminal/infrastructure/ml/lstm_model.py": "LSTM neural network",
            "quantum_terminal/infrastructure/crypto/messari_adapter.py": "Messari API",
            "quantum_terminal/infrastructure/sentiment/reddit_adapter.py": "Reddit sentiment",
        },
    },
}


def create_skeleton_file(filepath: Path, description: str, verbose: bool = False) -> None:
    """Create a skeleton Python file with docstring."""
    filepath.parent.mkdir(parents=True, exist_ok=True)

    if filepath.exists():
        if verbose:
            print(f"⊘ {filepath} already exists")
        return

    # Determine if it's a test file, config, or regular module
    if "test_" in filepath.name:
        content = f'''"""Tests for {description}."""

import pytest


class Test{filepath.stem.replace("test_", "").title()}:
    """Test suite for {description}."""

    def test_placeholder(self) -> None:
        """Placeholder test."""
        assert True
'''
    elif filepath.suffix == ".qss":
        content = f"""/* {description} */

QWidget {{
    background-color: #0A0A0A;
    color: #E8E8E8;
}}
"""
    elif filepath.suffix == ".py":
        module_name = filepath.stem.replace("_", " ").title()
        content = f'''"""{description}."""

from typing import Any, Optional


# TODO: Implement {module_name}
'''
    else:
        content = f"# {description}\n"

    with open(filepath, "w") as f:
        f.write(content)

    print(f"✓ {filepath}")


def generate_phase(phase_num: int, verbose: bool = False) -> None:
    """Generate all files for a specific phase."""
    if phase_num not in PHASES:
        print(f"❌ Phase {phase_num} not found. Valid phases: {sorted(PHASES.keys())}")
        sys.exit(1)

    phase_info = PHASES[phase_num]
    print(f"\n📋 Phase {phase_num}: {phase_info['name']}")
    print(f"{'=' * 60}")

    root = Path(".").resolve()
    for filepath_str, description in phase_info["files"].items():
        filepath = root / filepath_str
        create_skeleton_file(filepath, description, verbose)

    print(f"\n✓ Phase {phase_num} scaffold created")
    print(f"\nNext steps:")
    print(f"  1. Run: pytest --collect-only")
    print(f"  2. Implement modules in order")
    print(f"  3. Run: pytest -xvs")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate skeleton files for a development phase"
    )
    parser.add_argument(
        "--phase",
        type=int,
        required=True,
        help=f"Phase number (1-{max(PHASES.keys())})",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--list", action="store_true", help="List all phases")

    args = parser.parse_args()

    if args.list:
        print("\nAvailable phases:\n")
        for num, info in PHASES.items():
            file_count = len(info["files"])
            print(f"  Phase {num}: {info['name']} ({file_count} files)")
        return

    generate_phase(args.phase, args.verbose)


if __name__ == "__main__":
    main()
