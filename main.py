"""
Quantum Investment Terminal - Main entry point.

Run this file to launch the PyQt6 application.
"""

import sys
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from quantum_terminal.ui.main_window import QuantumTerminal
from quantum_terminal.utils.logger import get_logger

logger = get_logger(__name__)


def main() -> int:
    """Main entry point for the application."""
    try:
        # Create application
        app = QApplication(sys.argv)

        # Set application name and version
        app.setApplicationName("Quantum Investment Terminal")
        app.setApplicationVersion("1.0.0")

        # Set application style
        app.setStyle("Fusion")

        logger.info("Starting Quantum Investment Terminal")

        # Create and show main window
        window = QuantumTerminal()
        window.show()

        logger.info("Window displayed, entering event loop")

        # Run event loop
        return app.exec()

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())