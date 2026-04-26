#!/usr/bin/env python3
"""
Quantum Investment Terminal — Main Entry Point

Bloomberg-like desktop terminal for Graham-Dodd value investing
with integrated trading journal, AI analysis, and risk management.
"""

import sys
import logging
from pathlib import Path

# Configure logging
from quantum_terminal.utils.logger import logger

# PyQt6
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QPixmap, QFont, QColor
from PyQt6.QtCore import Qt, QTimer

# Config
from quantum_terminal.config import settings


def create_splash_screen():
    """Create a splash screen for application startup."""
    splash_pixmap = QPixmap(800, 600)
    splash_pixmap.fill(QColor("#0A0A0A"))  # Bloomberg dark

    splash = QSplashScreen(splash_pixmap)

    # Add text
    splash.showMessage(
        "Quantum Investment Terminal\n\nLoading modules...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
        QColor("#FF6B00")  # Bloomberg orange
    )

    return splash


def main():
    """Main entry point for Quantum Terminal."""

    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Quantum Investment Terminal")
    app.setApplicationVersion("1.0.0")

    # Splash screen
    splash = create_splash_screen()
    splash.show()
    app.processEvents()

    logger.info("Starting Quantum Investment Terminal")

    try:
        # Import main window (lazy import to show splash)
        splash.showMessage(
            "Quantum Investment Terminal\n\nInitializing UI...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
            QColor("#FF6B00")
        )
        app.processEvents()

        from quantum_terminal.ui.main_window import MainWindow

        # Create main window
        main_window = MainWindow()

        # Hide splash and show main window
        splash.finish(main_window)
        main_window.show()

        logger.info("✓ Quantum Terminal started successfully")

        # Run application
        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"✗ Failed to start Quantum Terminal: {e}", exc_info=True)
        splash.hide()

        # Show error dialog
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "Quantum Terminal Error",
            f"Failed to start application:\n\n{str(e)}\n\nCheck logs for details."
        )

        sys.exit(1)


if __name__ == "__main__":
    main()
