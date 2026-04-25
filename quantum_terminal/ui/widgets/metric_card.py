"""
MetricCard: Animated KPI widget for dashboard displays.

Displays: title + large value + change percentage (color-coded).
Use cases: VaR, Sharpe ratio, equity, portfolio quality score.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QFont, QColor, QIcon
from typing import Optional


class MetricCard(QWidget):
    """KPI card with animated value updates and color-coded change indicator."""

    value_clicked = pyqtSignal(str)  # Emitted when value is clicked

    def __init__(self, title: str, unit: str = "", icon_path: Optional[str] = None):
        """
        Initialize MetricCard.

        Args:
            title: Display name (e.g., "Value at Risk")
            unit: Unit suffix (e.g., "$", "%", "pts")
            icon_path: Optional path to icon image
        """
        super().__init__()
        self.title = title
        self.unit = unit
        self.icon_path = icon_path
        self.current_value = 0.0
        self.previous_value = 0.0

        self.initUI()
        self.setStyleSheet(self._get_stylesheet())

    def initUI(self) -> None:
        """Build widget UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(4)

        # Header: icon + title
        header_layout = QHBoxLayout()
        if self.icon_path:
            self.icon_label = QLabel()
            self.icon_label.setPixmap(
                QIcon(self.icon_path).pixmap(QSize(16, 16))
            )
            header_layout.addWidget(self.icon_label)

        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("Inter", 11))
        self.title_label.setStyleSheet("color: #A0A0A0;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Main value (large, bold)
        self.value_label = QLabel("—")
        self.value_label.setFont(QFont("JetBrains Mono", 28, QFont.Weight.Bold))
        self.value_label.setStyleSheet("color: #FFFFFF;")
        self.value_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.value_label.mousePressEvent = self._on_value_clicked
        main_layout.addWidget(self.value_label)

        # Change percentage (smaller, color-coded)
        self.change_label = QLabel("")
        self.change_label.setFont(QFont("JetBrains Mono", 12))
        main_layout.addWidget(self.change_label)

        main_layout.addStretch()

    def set_value(self, value: float, animate: bool = True) -> None:
        """
        Update displayed value.

        Args:
            value: New value to display
            animate: Whether to animate the transition
        """
        self.previous_value = self.current_value
        self.current_value = value

        if animate:
            self._animate_value()
        else:
            self.value_label.setText(f"{value:,.2f} {self.unit}".strip())

    def set_change(self, change_pct: float, absolute: Optional[float] = None) -> None:
        """
        Update change percentage display.

        Args:
            change_pct: Percentage change (e.g., 2.5 for +2.5%)
            absolute: Optional absolute change amount
        """
        color = "#00D26A" if change_pct >= 0 else "#FF3B30"
        arrow = "▲" if change_pct >= 0 else "▼"

        text = f"{arrow} {abs(change_pct):.2f}%"
        if absolute is not None:
            text += f" ({absolute:+.2f})"

        self.change_label.setText(text)
        self.change_label.setStyleSheet(f"color: {color};")

    def set_color(self, color: str) -> None:
        """
        Set value label color.

        Args:
            color: Hex color code (e.g., "#00D26A" for green)
        """
        self.value_label.setStyleSheet(f"color: {color};")

    def set_warning_level(self, level: str = "normal") -> None:
        """
        Set card appearance based on risk level.

        Args:
            level: "normal", "warning", or "danger"
        """
        if level == "warning":
            self.setStyleSheet(self._get_stylesheet("#FFA500"))
        elif level == "danger":
            self.setStyleSheet(self._get_stylesheet("#FF3B30"))
        else:
            self.setStyleSheet(self._get_stylesheet())

    def clear(self) -> None:
        """Reset card to initial state."""
        self.value_label.setText("—")
        self.change_label.setText("")
        self.current_value = 0.0
        self.previous_value = 0.0

    def _animate_value(self) -> None:
        """Animate value transition."""
        # Simple update (full animation library would be overkill)
        self.value_label.setText(f"{self.current_value:,.2f} {self.unit}".strip())

    def _on_value_clicked(self, event) -> None:
        """Handle value click event."""
        self.value_clicked.emit(f"{self.current_value:.2f}")

    @staticmethod
    def _get_stylesheet(border_color: str = "#2A2A2A") -> str:
        """Get stylesheet for metric card."""
        return f"""
            MetricCard {{
                background-color: #1E1E1E;
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 0px;
            }}
        """
