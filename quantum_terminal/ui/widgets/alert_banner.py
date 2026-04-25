"""
AlertBanner: Notification banner with auto-dismiss and multiple severity levels.

Types: info, warning, error, success (color-coded).
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QIcon
from typing import Optional


class AlertBanner(QWidget):
    """Notification banner with auto-dismiss."""

    dismissed = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize AlertBanner."""
        super().__init__(parent)
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.dismiss)

        self.initUI()
        self.hide()

    def initUI(self) -> None:
        """Build banner UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(20, 20)
        layout.addWidget(self.icon_label)

        # Message
        self.message_label = QLabel()
        self.message_label.setFont(QFont("Inter", 11))
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        layout.addStretch()

        # Close button
        self.close_button = QPushButton("✕")
        self.close_button.setFont(QFont("Inter", 12))
        self.close_button.setFixedSize(24, 24)
        self.close_button.setFlat(True)
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.clicked.connect(self.dismiss)
        layout.addWidget(self.close_button)

        self.setLayout(layout)

    def show_alert(
        self,
        message: str,
        level: str = "info",
        duration_ms: int = 5000,
    ) -> None:
        """
        Show alert banner.

        Args:
            message: Alert message
            level: "info", "warning", "error", or "success"
            duration_ms: Auto-dismiss duration (0 = no auto-dismiss)
        """
        self.message_label.setText(message)
        self.timer.stop()

        # Apply style and icon based on level
        styles = {
            "info": {
                "bg": "#0066CC",
                "text": "#FFFFFF",
                "icon": "ℹ",
            },
            "warning": {
                "bg": "#FFA500",
                "text": "#000000",
                "icon": "⚠",
            },
            "error": {
                "bg": "#FF3B30",
                "text": "#FFFFFF",
                "icon": "✕",
            },
            "success": {
                "bg": "#00D26A",
                "text": "#000000",
                "icon": "✓",
            },
        }

        style = styles.get(level, styles["info"])
        self.icon_label.setText(style["icon"])
        self.icon_label.setStyleSheet(f"color: {style['text']}; font-size: 16px;")
        self.message_label.setStyleSheet(f"color: {style['text']};")
        self.close_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {style['text']};
                border: none;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 0, 0, 0.2);
                border-radius: 4px;
            }}
        """
        )

        self.setStyleSheet(
            f"""
            AlertBanner {{
                background-color: {style['bg']};
                border-radius: 4px;
                border: 1px solid {self._darken_color(style['bg'])};
            }}
        """
        )

        self.show()

        # Auto-dismiss if duration > 0
        if duration_ms > 0:
            self.timer.start(duration_ms)

    def dismiss(self) -> None:
        """Dismiss banner."""
        self.timer.stop()
        self.hide()
        self.dismissed.emit()

    @staticmethod
    def _darken_color(hex_color: str) -> str:
        """Darken a hex color."""
        try:
            # Remove '#' if present
            hex_color = hex_color.lstrip("#")

            # Parse RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)

            # Darken by 20%
            r = max(0, int(r * 0.8))
            g = max(0, int(g * 0.8))
            b = max(0, int(b * 0.8))

            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color
