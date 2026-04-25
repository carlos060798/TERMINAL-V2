#!/usr/bin/env python3
"""
AGENT: Dependency Checker

Validates all project dependencies and API configurations.
Generates status report and recommendations.

Usage:
  python scripts/dep_checker.py
  python scripts/dep_checker.py --verbose
  python scripts/dep_checker.py --fix
"""

import importlib
import sys
from pathlib import Path
from typing import Dict, List, Optional


DEPENDENCIES = {
    "critical": [
        ("PyQt6", "UI framework"),
        ("pandas", "Data manipulation"),
        ("numpy", "Numerics"),
        ("sqlalchemy", "Database ORM"),
        ("pydantic", "Data validation"),
    ],
    "finance": [
        ("yfinance", "Yahoo Finance data"),
        ("pandas_ta", "Technical analysis"),
        ("quantstats", "Portfolio metrics"),
        ("riskfolio", "Portfolio optimization"),
        ("vectorbt", "Backtesting"),
    ],
    "ml": [
        ("sklearn", "scikit-learn - Machine learning"),
        ("lightgbm", "Gradient boosting"),
        ("torch", "PyTorch - Neural networks"),
        ("prophet", "Time series forecasting"),
        ("transformers", "HuggingFace - NLP models"),
    ],
    "visualization": [
        ("plotly", "Interactive charts"),
        ("matplotlib", "Static plots"),
        ("pyqtgraph", "Real-time charting"),
    ],
    "nlp": [
        ("sentence_transformers", "Embeddings"),
        ("chromadb", "Vector database"),
        ("spacy", "NLP pipeline"),
    ],
    "utils": [
        ("loguru", "Logging"),
        ("rich", "Rich terminal output"),
        ("dotenv", "Environment variables"),
        ("diskcache", "Disk caching"),
    ],
}

API_KEYS = {
    "IA": ["GROQ_API_KEY", "DEEPSEEK_API_KEY", "OPENROUTER_API_KEY", "KAMI_IA", "HF_TOKEN"],
    "Market": ["FINNHUB_API_KEY", "FMP_API_KEY", "TIINGO_API_KEY"],
    "Macro": ["FRED_API_KEY", "EIA_API_KEY", "SEC_USER_AGENT"],
    "Sentiment": ["NEWSAPI_KEY", "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"],
    "Crypto": ["MESSARI_API_KEY", "COINBASE_API_KEY"],
}


class DepChecker:
    """Check and validate project dependencies."""

    def __init__(self, verbose: bool = False) -> None:
        """Initialize checker."""
        self.verbose = verbose
        self.env_file = Path(".env")
        self.results: Dict[str, Dict[str, bool]] = {}

    def check_package(self, import_name: str, display_name: str) -> bool:
        """Check if a package is installed."""
        try:
            importlib.import_module(import_name)
            if self.verbose:
                print(f"  ✓ {display_name}")
            return True
        except ImportError as e:
            print(f"  ❌ {display_name}")
            if self.verbose:
                print(f"     Error: {e}")
            return False

    def check_category(self, category: str, packages: List[tuple]) -> None:
        """Check all packages in a category."""
        print(f"\n{category}:")
        results = {}

        for import_name, display_name in packages:
            results[display_name] = self.check_package(import_name, display_name)

        self.results[category] = results

    def check_all_dependencies(self) -> None:
        """Check all dependencies by category."""
        for category, packages in DEPENDENCIES.items():
            self.check_category(category.title(), packages)

    def check_api_keys(self) -> None:
        """Check which API keys are configured."""
        print("\n" + "=" * 60)
        print("API KEYS STATUS")
        print("=" * 60)

        if not self.env_file.exists():
            print("⚠ .env file not found. Copy from .env.template and configure.")
            return

        with open(self.env_file) as f:
            env_content = f.read()

        for category, keys in API_KEYS.items():
            print(f"\n{category}:")
            for key in keys:
                if key in env_content and key not in "REMPLAZAME":
                    # Check if value is set
                    for line in env_content.split("\n"):
                        if line.startswith(key):
                            value = line.split("=", 1)[1].strip()
                            if value and value != "your_" + key.lower() + "_here":
                                print(f"  ✓ {key}")
                            else:
                                print(f"  ⊘ {key} (not configured)")
                            break
                else:
                    print(f"  ⊘ {key} (not configured)")

    def summary(self) -> None:
        """Print summary and recommendations."""
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        total = 0
        installed = 0

        for category, packages in self.results.items():
            for pkg, status in packages.items():
                total += 1
                if status:
                    installed += 1

        print(f"\nDependencies: {installed}/{total} installed ({100 * installed // total}%)")

        if installed < total:
            print("\n🔧 Missing dependencies. Run:")
            print("  uv sync")
            return

        print("\n✓ All critical dependencies installed")
        print("\n📝 Next steps:")
        print("  1. Configure .env file with API keys")
        print("  2. Run: python scripts/project_orchestrator.py --generate 1")
        print("  3. Run: pytest domain/ -v")


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Check project dependencies")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix missing deps")

    args = parser.parse_args()

    checker = DepChecker(verbose=args.verbose)

    print("\n" + "=" * 60)
    print("QUANTUM INVESTMENT TERMINAL — DEPENDENCY CHECK")
    print("=" * 60)

    checker.check_all_dependencies()
    checker.check_api_keys()
    checker.summary()


if __name__ == "__main__":
    main()
