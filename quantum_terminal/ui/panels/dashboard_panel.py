"""
Dashboard Panel - Portfolio Overview with KPIs and Charts.

Displays key performance indicators (KPIs) for the investment portfolio:
- Row 1: Total Value, P&L ($), P&L (%), Sharpe, Sortino, VaR
- Row 2: Max Drawdown, Beta, Quality Score, Correlation
- Row 3: Sector Heatmap
- Row 4: Animated Equity Curve

Phase 3 - UI Layer Implementation
Reference: PLAN_MAESTRO.md - Phase 3: UI Skeleton
"""

from typing import Optional, Dict, List
from decimal import Decimal
from datetime import datetime
import asyncio
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
    QPushButton, QLabel, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from quantum_terminal.ui.widgets import (
    MetricCard, HeatmapWidget, EquityCurveWidget, AlertBanner
)
from quantum_terminal.utils.logger import get_logger

logger = get_logger(__name__)


class DashboardPanel(QWidget):
    """
    Main dashboard panel showing portfolio overview and key metrics.

    Signals:
        - sector_clicked: Emitted when user clicks on a sector in heatmap
        - refresh_requested: Emitted when manual refresh is requested
    """

    sector_clicked = pyqtSignal(str)  # sector_name
    refresh_requested = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize the dashboard panel."""
        super().__init__(parent)
        self.portfolio_data = {}
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._on_auto_refresh)
        self.initUI()
        self.setup_connections()

    def initUI(self):
        """Build the UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Title bar
        title_layout = self._build_title_bar()
        main_layout.addLayout(title_layout)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                width: 8px;
                background-color: #1e1e1e;
            }
            QScrollBar::handle:vertical {
                background-color: #444;
                border-radius: 4px;
            }
        """)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        # Row 1: KPI Cards (6 metrics)
        row1_layout = self._build_kpi_row1()
        content_layout.addLayout(row1_layout)

        # Row 2: Advanced metrics
        row2_layout = self._build_kpi_row2()
        content_layout.addLayout(row2_layout)

        # Row 3: Sector Heatmap
        self.heatmap = HeatmapWidget()
        self.heatmap.sector_clicked.connect(self._on_sector_clicked)
        content_layout.addWidget(QLabel("Sector Allocation"), 0)
        content_layout.addWidget(self.heatmap)

        # Row 4: Equity Curve
        self.equity_chart = EquityCurveWidget()
        content_layout.addWidget(QLabel("Equity Curve & Drawdown"), 0)
        content_layout.addWidget(self.equity_chart)

        content_layout.addSpacing(20)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        self.setLayout(main_layout)

    def _build_title_bar(self) -> QHBoxLayout:
        """Build title and control buttons."""
        layout = QHBoxLayout()

        title = QLabel("Portfolio Dashboard")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        layout.addSpacing(20)

        # Time period selector
        period_label = QLabel("Period:")
        layout.addWidget(period_label)

        periods = ["1D", "1W", "1M", "3M", "YTD", "1Y", "All"]
        for period in periods:
            btn = QPushButton(period)
            btn.setMaximumWidth(60)
            btn.setStyleSheet("""
                QPushButton {
                    padding: 4px 8px;
                    background-color: #2d2d2d;
                    color: #fff;
                    border: 1px solid #444;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #3d3d3d;
                }
                QPushButton:pressed {
                    background-color: #1e90ff;
                }
            """)
            btn.clicked.connect(lambda checked, p=period: self._on_period_changed(p))
            layout.addWidget(btn)

        layout.addSpacing(20)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setMaximumWidth(80)
        refresh_btn.clicked.connect(self._on_refresh_clicked)
        layout.addWidget(refresh_btn)

        layout.addStretch()
        return layout

    def _build_kpi_row1(self) -> QHBoxLayout:
        """Build Row 1: Total Value, P&L $, P&L %, Sharpe, Sortino, VaR."""
        layout = QHBoxLayout()
        layout.setSpacing(12)

        # Store references for later updates
        self.card_total_value = MetricCard("Total Value", "$", value="$0.00")
        self.card_pnl_usd = MetricCard("P&L Today", "$", value="$0.00", change_pct="+0.00%")
        self.card_pnl_pct = MetricCard("P&L %", "%", value="0.00%", change_pct="+0.00%")
        self.card_sharpe = MetricCard("Sharpe Ratio", "σ", value="0.00")
        self.card_sortino = MetricCard("Sortino Ratio", "σ", value="0.00")
        self.card_var = MetricCard("VaR (95%)", "$", value="$0.00")

        for card in [
            self.card_total_value, self.card_pnl_usd, self.card_pnl_pct,
            self.card_sharpe, self.card_sortino, self.card_var
        ]:
            layout.addWidget(card)

        return layout

    def _build_kpi_row2(self) -> QHBoxLayout:
        """Build Row 2: Max Drawdown, Beta, Quality Score, Correlation."""
        layout = QHBoxLayout()
        layout.setSpacing(12)

        self.card_max_dd = MetricCard("Max Drawdown", "%", value="-0.00%")
        self.card_beta = MetricCard("Beta (vs SPY)", "β", value="0.00")
        self.card_quality = MetricCard("Avg Quality Score", "pts", value="0.00/100")
        self.card_correlation = MetricCard("Correlation", "r", value="0.00")

        for card in [self.card_max_dd, self.card_beta, self.card_quality, self.card_correlation]:
            layout.addWidget(card)

        return layout

    def _on_period_changed(self, period: str):
        """Handle period selection change."""
        logger.info(f"Period changed to {period}")
        self.load_portfolio_data(period=period)

    def _on_refresh_clicked(self):
        """Handle manual refresh button click."""
        logger.info("Manual refresh triggered")
        self.refresh_requested.emit()
        self.load_portfolio_data()

    def _on_sector_clicked(self, sector: str):
        """Handle sector heatmap click."""
        logger.info(f"Sector clicked: {sector}")
        self.sector_clicked.emit(sector)

    def _on_auto_refresh(self):
        """Auto-refresh timer callback (every 60 seconds)."""
        self.load_portfolio_data()

    def load_portfolio_data(self, period: str = "1D") -> None:
        """
        Load portfolio data from infrastructure layer.

        Args:
            period: Time period for metrics ("1D", "1W", "1M", etc.)

        Note:
            In Phase 3, this calls async infrastructure methods.
            For MVP, uses mock data.
        """
        try:
            # TODO: Replace with actual async infrastructure call
            # portfolio_metrics = await get_portfolio_metrics(period)
            self.portfolio_data = self._get_mock_portfolio_data(period)
            self.update_metrics()
        except Exception as e:
            logger.error(f"Failed to load portfolio data: {e}", exc_info=True)
            self._show_error(f"Failed to load portfolio data: {str(e)}")

    def update_metrics(self) -> None:
        """Update all KPI cards and charts with current portfolio data."""
        try:
            data = self.portfolio_data

            # Update Row 1 KPIs
            self.card_total_value.update_value(
                data.get("total_value", "$0.00"),
                data.get("total_value_change_pct", "+0.00%")
            )
            self.card_pnl_usd.update_value(
                data.get("pnl_usd", "$0.00"),
                data.get("pnl_pct", "+0.00%")
            )
            self.card_pnl_pct.update_value(
                data.get("pnl_pct", "0.00%"),
                data.get("pnl_trend", "+0.00%")
            )
            self.card_sharpe.update_value(data.get("sharpe_ratio", "0.00"))
            self.card_sortino.update_value(data.get("sortino_ratio", "0.00"))
            self.card_var.update_value(data.get("var_95", "$0.00"))

            # Update Row 2 KPIs
            self.card_max_dd.update_value(data.get("max_drawdown", "-0.00%"))
            self.card_beta.update_value(data.get("beta", "0.00"))
            self.card_quality.update_value(data.get("avg_quality_score", "0.00/100"))
            self.card_correlation.update_value(data.get("correlation_spy", "0.00"))

            # Update heatmap
            if "sector_allocation" in data:
                self.heatmap.set_data(data["sector_allocation"])

            # Update equity curve
            if "equity_curve" in data:
                self.equity_chart.set_data(
                    dates=data["equity_curve"]["dates"],
                    values=data["equity_curve"]["values"],
                    drawdown=data["equity_curve"]["drawdown"]
                )

        except Exception as e:
            logger.error(f"Failed to update metrics: {e}", exc_info=True)
            self._show_error(f"Failed to update metrics: {str(e)}")

    def refresh_equity_curve(self, dates: List[str], values: List[float]) -> None:
        """
        Update equity curve chart with new data.

        Args:
            dates: List of date strings
            values: List of portfolio values
        """
        try:
            self.equity_chart.set_data(dates=dates, values=values)
        except Exception as e:
            logger.error(f"Failed to refresh equity curve: {e}", exc_info=True)

    def start_auto_refresh(self, interval_seconds: int = 60) -> None:
        """
        Start automatic refresh timer.

        Args:
            interval_seconds: Refresh interval in seconds (default: 60)
        """
        self.refresh_timer.setInterval(interval_seconds * 1000)
        self.refresh_timer.start()
        logger.info(f"Auto-refresh started (interval: {interval_seconds}s)")

    def stop_auto_refresh(self) -> None:
        """Stop automatic refresh timer."""
        self.refresh_timer.stop()
        logger.info("Auto-refresh stopped")

    def setup_connections(self):
        """Set up signal/slot connections."""
        pass  # Signals defined in __init__

    def _show_error(self, message: str):
        """Show error message (placeholder for alert banner)."""
        logger.error(f"UI Error: {message}")

    @staticmethod
    def _get_mock_portfolio_data(period: str = "1D") -> Dict:
        """
        Return mock portfolio data for MVP.

        Args:
            period: Time period

        Returns:
            Dictionary with portfolio metrics
        """
        return {
            "total_value": "$1,234,567.89",
            "total_value_change_pct": "+2.34%",
            "pnl_usd": "$12,345.67",
            "pnl_pct": "+1.23%",
            "pnl_trend": "+0.50%",
            "sharpe_ratio": "1.45",
            "sortino_ratio": "2.10",
            "var_95": "$34,567.89",
            "max_drawdown": "-8.50%",
            "beta": "0.95",
            "avg_quality_score": "75.5/100",
            "correlation_spy": "0.82",
            "sector_allocation": {
                "Technology": {"value": 350000, "pct": 28.4, "change": "+2.1%"},
                "Financials": {"value": 280000, "pct": 22.7, "change": "+1.5%"},
                "Healthcare": {"value": 250000, "pct": 20.3, "change": "+0.8%"},
                "Industrials": {"value": 180000, "pct": 14.6, "change": "-0.3%"},
                "Consumer": {"value": 95000, "pct": 7.7, "change": "+3.2%"},
                "Energy": {"value": 60000, "pct": 4.9, "change": "-1.2%"},
                "Materials": {"value": 40000, "pct": 3.2, "change": "+1.8%"},
            },
            "equity_curve": {
                "dates": ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-25"],
                "values": [1000000, 1050000, 1150000, 1234567.89],
                "drawdown": [0, -2.1, -1.5, 0],
            },
        }


# Module-level exports
__all__ = ["DashboardPanel"]
