"""
Quantum Investment Terminal — Main Entry Point

Bloomberg-like investment analysis platform with Graham-Dodd methodology.

Phase 3+: Replace this with PyQt6 QApplication initialization.
"""

import sys

from quantum_terminal.config import settings


def main() -> None:
    """Main application entry point."""
    print("=" * 70)
    print("QUANTUM INVESTMENT TERMINAL")
    print("=" * 70)
    print()
    print("📊 Investment Analysis Platform")
    print("📈 Graham-Dodd Methodology")
    print("🤖 Multi-LLM AI Analysis")
    print()
    print("Current Phase: Foundation (Phase 1)")
    print()
    print("Next Steps:")
    print("  1. Install dependencies: uv sync")
    print("  2. Configure .env with your API keys")
    print("  3. Run: python scripts/project_orchestrator.py --status")
    print("  4. Run: python scripts/phase_generator.py --phase 1")
    print("  5. Run: pytest domain/ -v")
    print()
    print("Project Root:", settings.project_root)
    print("Database Path:", settings.database_path)
    print()

    # API Key status
    api_status = settings.validate_api_keys()
    configured = sum(1 for v in api_status.values() if v)
    total = len(api_status)

    print(f"🔑 API Keys: {configured}/{total} configured")
    if configured < total:
        print("   Run: cp .env.template .env  (then add your keys)")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
