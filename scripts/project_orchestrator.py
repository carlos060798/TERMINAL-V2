#!/usr/bin/env python3
"""
AGENT: Project Orchestrator

Master script for managing Quantum Investment Terminal development.
Coordinates phases, tests, dependencies, and deployment.

Usage:
  python scripts/project_orchestrator.py --status          # Show project status
  python scripts/project_orchestrator.py --generate 1      # Generate phase 1
  python scripts/project_orchestrator.py --test domain     # Run domain tests
  python scripts/project_orchestrator.py --check-deps      # Check all dependencies
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional


class ProjectOrchestrator:
    """Orchestrates Quantum Investment Terminal development."""

    PHASES = {
        1: "Cimientos (Config, Domain, DB)",
        2: "Adaptadores de Datos (APIs, Macros)",
        3: "Esqueleto UI (PyQt6, Widgets)",
        4: "Módulos Core (Dashboard, Watchlist, Analyzer, Macro)",
        5: "Trading y Tesis (Journal, Thesis, Risk)",
        6: "Screener e Inteligencia (PDF, Earnings, Monitor)",
        7: "ML Avanzado y Backtesting",
    }

    PROJECT_ROOT = Path(__file__).parent.parent
    QUANTUM_TERMINAL = PROJECT_ROOT / "quantum_terminal"

    def __init__(self) -> None:
        """Initialize orchestrator."""
        self.project_root = self.PROJECT_ROOT
        self.quantum_terminal = self.QUANTUM_TERMINAL

    def check_python_version(self) -> bool:
        """Verify Python 3.12+."""
        import sys

        if sys.version_info < (3, 12):
            print(f"❌ Python 3.12+ required, got {sys.version_info.major}.{sys.version_info.minor}")
            return False
        print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}")
        return True

    def check_dependencies(self) -> bool:
        """Check critical dependencies."""
        critical = ["PyQt6", "pandas", "pydantic", "sqlalchemy", "transformers"]
        missing = []

        for pkg in critical:
            try:
                __import__(pkg.lower().replace("-", "_"))
                print(f"✓ {pkg}")
            except ImportError:
                missing.append(pkg)
                print(f"❌ {pkg} (run: uv sync)")

        if missing:
            print(f"\n⚠ Missing: {', '.join(missing)}")
            print("Run: uv sync")
            return False

        return True

    def show_status(self) -> None:
        """Display project status."""
        print("\n" + "=" * 70)
        print("QUANTUM INVESTMENT TERMINAL — PROJECT STATUS")
        print("=" * 70)

        print(f"\n📁 Project Root: {self.project_root}")
        print(f"🐍 Python: {sys.version.split()[0]}")

        # Directory structure
        print("\n📂 Directory Structure:")
        dirs_to_check = [
            ("Source Code", self.quantum_terminal),
            ("Tests", self.project_root / "tests"),
            ("Scripts", self.project_root / "scripts"),
            ("Docs", self.project_root / "docs"),
        ]

        for name, path in dirs_to_check:
            status = "✓" if path.exists() else "⊘"
            file_count = len(list(path.glob("**/*.py"))) if path.exists() else 0
            print(f"  {status} {name}: {path.name} ({file_count} .py files)")

        # Dependencies
        print("\n📦 Dependencies:")
        self.check_dependencies()

        # Phases
        print("\n📋 Development Phases:")
        for phase_num, phase_name in self.PHASES.items():
            print(f"  Phase {phase_num}: {phase_name}")

        print("\n💡 Next Steps:")
        print("  1. Run: uv sync  (install dependencies)")
        print("  2. Run: python scripts/project_orchestrator.py --generate 1")
        print("  3. Run: pytest domain/ -v")

    def generate_phase(self, phase_num: int) -> None:
        """Generate skeleton files for a phase."""
        print(f"\n🔧 Generating Phase {phase_num}: {self.PHASES.get(phase_num, 'Unknown')}")

        result = subprocess.run(
            [
                sys.executable,
                str(self.project_root / "scripts" / "phase_generator.py"),
                "--phase",
                str(phase_num),
            ],
            cwd=self.project_root,
        )

        if result.returncode == 0:
            print(f"\n✓ Phase {phase_num} generated successfully")
        else:
            print(f"\n❌ Failed to generate phase {phase_num}")
            sys.exit(1)

    def run_tests(self, target: str = "domain") -> None:
        """Run pytest for a specific module."""
        print(f"\n🧪 Running tests for: {target}")

        result = subprocess.run(
            [sys.executable, "-m", "pytest", f"{target}/", "-v", "--tb=short"],
            cwd=self.project_root,
        )

        sys.exit(result.returncode)

    def show_modules(self) -> None:
        """List all modules in quantum_terminal."""
        print("\n📦 Quantum Terminal Modules:")
        print("=" * 70)

        for item in sorted(self.quantum_terminal.iterdir()):
            if item.is_dir() and not item.name.startswith("_"):
                files = list(item.glob("*.py"))
                py_count = len([f for f in files if f.name != "__init__.py"])
                print(f"  {item.name:30} ({py_count} modules)")

    def show_plan(self) -> None:
        """Display development plan."""
        plan_file = Path(r"C:\Users\usuario\.claude\plans")
        if plan_file.exists():
            plan = list(plan_file.glob("*.md"))[0]
            print(f"\n📋 Development Plan: {plan.name}")
            print("=" * 70)
            with open(plan) as f:
                lines = f.readlines()[:30]
                print("".join(lines))
                print("\n... (see full plan file)")
        else:
            print("⚠ No plan file found")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Orchestrate Quantum Investment Terminal development"
    )
    parser.add_argument("--status", action="store_true", help="Show project status")
    parser.add_argument("--generate", type=int, help="Generate phase N skeleton")
    parser.add_argument("--test", default="domain", help="Run tests (default: domain)")
    parser.add_argument("--check-deps", action="store_true", help="Check dependencies")
    parser.add_argument("--modules", action="store_true", help="List all modules")
    parser.add_argument("--plan", action="store_true", help="Show development plan")

    args = parser.parse_args()

    orch = ProjectOrchestrator()

    if args.status:
        orch.show_status()
    elif args.generate:
        orch.generate_phase(args.generate)
    elif args.test:
        orch.run_tests(args.test)
    elif args.check_deps:
        orch.check_dependencies()
    elif args.modules:
        orch.show_modules()
    elif args.plan:
        orch.show_plan()
    else:
        orch.show_status()


if __name__ == "__main__":
    main()
