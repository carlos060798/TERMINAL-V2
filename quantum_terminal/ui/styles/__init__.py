"""UI Styles package for Quantum Investment Terminal."""

from pathlib import Path

from quantum_terminal.ui.styles.colors import Colors, Fonts

__all__ = ["Colors", "Fonts", "load_stylesheet"]


def load_stylesheet() -> str:
    """
    Load Bloomberg dark theme stylesheet.

    Returns:
        str: QSS stylesheet content.
    """
    qss_path = Path(__file__).parent / "bloomberg_dark.qss"
    if qss_path.exists():
        return qss_path.read_text(encoding="utf-8")
    return ""
