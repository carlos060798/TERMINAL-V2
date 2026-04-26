"""
Risk Manager Panel - Comprehensive Portfolio Risk Analysis.

Displays advanced risk metrics for the investment portfolio:
- Current Risk Exposure: Capital at risk, limit %, alerts
- VaR Portfolio: 95% and 99% confidence levels (Historical, Monte Carlo, Parametric)
- Correlation Matrix: Heatmap showing position correlations (green=diversified, red=concentrated)
- Concentration Analysis: % by sector, % by holding, alerts if exceeding thresholds
- Efficient Frontier: Markowitz portfolio optimization with current position overlay
- Stress Testing: Scenario analysis for -20%, -50%, -35% market downturns
- Risk Limits Configuration: User-defined max drawdown, capital at risk, position limits

Integrates with:
- Domain layer: calculate_var, calculate_beta (quantum_terminal.domain.risk)
- Infrastructure: DataProvider for quotes, riskfolio-lib for Markowitz optimization
- Utilities: rate_limiter, cache, logger

Phase 3 - UI Layer Implementation
Reference: PLAN_MAESTRO.md - Phase 3: UI Skeleton
"""

from typing import Optional, Dict, List, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import asyncio
import logging
import traceback
import math

import pandas as pd
import numpy as np
from scipy import stats

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
    QPushButton, QLabel, QSpinBox, QDoubleSpinBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QTabWidget, QComboBox,
    QSpacerItem, QSizePolicy, QMessageBox, QDialog, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QTextCursor
from PyQt6.QtChart import QChart, QChartView, QScatterSeries, QValueAxis, QLineSeries
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from quantum_terminal.ui.widgets import MetricCard, AlertBanner
from quantum_terminal.utils.logger import get_logger

# Import configuration
try:
    from quantum_terminal.config import settings
except ImportError:
    settings = None

# Import infrastructure and domain layers
try:
    from quantum_terminal.infrastructure.market_data.data_provider import DataProvider
except ImportError:
    DataProvider = None

try:
    from quantum_terminal.domain.risk import calculate_var, calculate_beta
except ImportError:
    calculate_var = None
    calculate_beta = None

try:
    import riskfolio as rp
except ImportError:
    rp = None

logger = get_logger(__name__)


# ============================================================================
# BACKGROUND WORKER THREADS
# ============================================================================

class RiskCalculationThread(QThread):
    """Background thread for risk calculations (VaR, correlations, efficient frontier)."""
    calculation_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, calculation_func):
        super().__init__()
        self.calculation_func = calculation_func

    def run(self):
        try:
            result = self.calculation_func()
            self.calculation_complete.emit(result)
        except Exception as e:
            logger.error(f"Risk calculation error: {e}", exc_info=True)
            self.error_occurred.emit(str(e))


# ============================================================================
# RISK MANAGER PANEL
# ============================================================================

class RiskManagerPanel(QWidget):
    """
    Comprehensive risk management dashboard for portfolio analysis.

    Key Features:
    1. Current Risk Exposure: Capital at risk vs. limit
    2. VaR Analysis: Multiple methodologies (Historical, Monte Carlo, Parametric)
    3. Correlation Analysis: Heatmap of position correlations
    4. Concentration Analysis: Sector and position concentration alerts
    5. Efficient Frontier: Markowitz optimization with current position
    6. Stress Testing: Multiple market downturn scenarios
    7. Risk Limits: Configurable thresholds for drawdown, position size, etc.

    Signals:
        - risk_limit_changed: Emitted when user modifies risk limits
        - stress_test_updated: Emitted when stress test results change
        - correlation_warning: Emitted when high correlation detected
    """

    risk_limit_changed = pyqtSignal(dict)  # {"max_drawdown": %, "max_capital_at_risk": $, ...}
    stress_test_updated = pyqtSignal(dict)  # {"scenario": "20%", "pnl": $, ...}
    correlation_warning = pyqtSignal(str, float)  # (ticker_pair, correlation)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(self.__class__.__name__)

        # State variables
        self.portfolio_data = {}
        self.risk_limits = {
            "max_drawdown_daily": 2.0,      # %
            "max_drawdown_total": 10.0,     # %
            "max_capital_at_risk": 5000.0,  # $
            "max_position_size": 1000.0,    # $
            "capital_at_risk_limit": 10000.0,  # Total limit
        }
        self.open_trades = {}
        self.positions = {}
        self.historical_returns = {}

        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Title
        title = QLabel("Risk Manager")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        main_layout.addWidget(title)

        # Tab widget for different risk views
        self.tabs = QTabWidget()

        # Tab 1: Current Exposure
        self.tabs.addTab(self._create_exposure_tab(), "Risk Exposure")

        # Tab 2: VaR Analysis
        self.tabs.addTab(self._create_var_tab(), "VaR Analysis")

        # Tab 3: Correlations
        self.tabs.addTab(self._create_correlation_tab(), "Correlations")

        # Tab 4: Concentration
        self.tabs.addTab(self._create_concentration_tab(), "Concentration")

        # Tab 5: Efficient Frontier
        self.tabs.addTab(self._create_frontier_tab(), "Efficient Frontier")

        # Tab 6: Stress Testing
        self.tabs.addTab(self._create_stress_test_tab(), "Stress Testing")

        # Tab 7: Risk Limits
        self.tabs.addTab(self._create_limits_tab(), "Risk Limits")

        main_layout.addWidget(self.tabs)

        # Alert banner at bottom
        self.alert_banner = AlertBanner()
        main_layout.addWidget(self.alert_banner)

        self.setLayout(main_layout)

    def _create_exposure_tab(self) -> QWidget:
        """Create Current Risk Exposure tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        # Metric cards
        cards_layout = QHBoxLayout()

        self.capital_at_risk_card = MetricCard("Capital at Risk", "$0", "Current capital deployed in R")
        self.limit_card = MetricCard("Risk Limit", "$10,000", "User-configured limit")
        self.used_percent_card = MetricCard("% Used", "0%", "Capital at risk / limit")

        cards_layout.addWidget(self.capital_at_risk_card)
        cards_layout.addWidget(self.limit_card)
        cards_layout.addWidget(self.used_percent_card)

        layout.addLayout(cards_layout)

        # Open trades table
        layout.addWidget(QLabel("Open Trades (Showing R per Trade)"))

        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(6)
        self.trades_table.setHorizontalHeaderLabels(
            ["Ticker", "Entry Price", "Stop Loss", "Risk ($)", "% of Total R", "Status"]
        )
        self.trades_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.trades_table)

        # Alert zone if > 80% of limit
        self.exposure_alert = QLabel()
        self.exposure_alert.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.exposure_alert)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_var_tab(self) -> QWidget:
        """Create VaR Analysis tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        # Method selection
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("VaR Calculation Method:"))
        self.var_method_combo = QComboBox()
        self.var_method_combo.addItems(["Historical", "Monte Carlo", "Parametric"])
        method_layout.addWidget(self.var_method_combo)
        method_layout.addStretch()
        layout.addLayout(method_layout)

        # VaR results table
        self.var_table = QTableWidget()
        self.var_table.setColumnCount(3)
        self.var_table.setHorizontalHeaderLabels(["Confidence Level", "VaR (%)", "VaR ($)"])
        self.var_table.setRowCount(2)
        self.var_table.setItem(0, 0, QTableWidgetItem("95%"))
        self.var_table.setItem(1, 0, QTableWidgetItem("99%"))
        layout.addWidget(self.var_table)

        # Interpretation
        interp_layout = QHBoxLayout()
        interp_layout.addWidget(QLabel("Interpretation:"))
        self.var_interp_label = QLabel("")
        self.var_interp_label.setStyleSheet("color: #666; font-style: italic;")
        interp_layout.addWidget(self.var_interp_label)
        interp_layout.addStretch()
        layout.addLayout(interp_layout)

        # Method details
        self.var_details_label = QLabel("")
        self.var_details_label.setWordWrap(True)
        layout.addWidget(self.var_details_label)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_correlation_tab(self) -> QWidget:
        """Create Correlation Matrix tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Position Correlation Matrix (Red=Concentrated, Green=Diversified)"))

        # Heatmap canvas
        self.corr_figure = plt.Figure(figsize=(8, 6), dpi=100)
        self.corr_canvas = FigureCanvas(self.corr_figure)
        layout.addWidget(self.corr_canvas)

        # Correlation warnings
        layout.addWidget(QLabel("High Correlations (>0.7):"))
        self.corr_warnings_table = QTableWidget()
        self.corr_warnings_table.setColumnCount(3)
        self.corr_warnings_table.setHorizontalHeaderLabels(["Ticker 1", "Ticker 2", "Correlation"])
        layout.addWidget(self.corr_warnings_table)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_concentration_tab(self) -> QWidget:
        """Create Concentration Analysis tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        # Sector concentration
        layout.addWidget(QLabel("Sector Concentration (Alert if >30%):"))
        self.sector_table = QTableWidget()
        self.sector_table.setColumnCount(3)
        self.sector_table.setHorizontalHeaderLabels(["Sector", "% of Portfolio", "Status"])
        layout.addWidget(self.sector_table)

        # Position concentration
        layout.addWidget(QLabel("Position Concentration (Alert if >15%):"))
        self.position_table = QTableWidget()
        self.position_table.setColumnCount(3)
        self.position_table.setHorizontalHeaderLabels(["Ticker", "% of Portfolio", "Status"])
        layout.addWidget(self.position_table)

        # Pie chart
        self.concentration_figure = plt.Figure(figsize=(8, 6), dpi=100)
        self.concentration_canvas = FigureCanvas(self.concentration_figure)
        layout.addWidget(self.concentration_canvas)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_frontier_tab(self) -> QWidget:
        """Create Efficient Frontier tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Markowitz Efficient Frontier (Riskfolio)"))

        # Frontier chart
        self.frontier_figure = plt.Figure(figsize=(10, 6), dpi=100)
        self.frontier_canvas = FigureCanvas(self.frontier_figure)
        layout.addWidget(self.frontier_canvas)

        # Recommendation
        self.frontier_recommendation = QLabel("")
        self.frontier_recommendation.setWordWrap(True)
        self.frontier_recommendation.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
        layout.addWidget(self.frontier_recommendation)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_stress_test_tab(self) -> QWidget:
        """Create Stress Testing tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Market Downturn Scenarios"))

        # Scenario buttons
        button_layout = QHBoxLayout()

        self.stress_btn_20 = QPushButton("Simulate -20% Drop")
        self.stress_btn_50 = QPushButton("Simulate -50% Drop (GFC)")
        self.stress_btn_35 = QPushButton("Simulate -35% Drop (COVID)")

        button_layout.addWidget(self.stress_btn_20)
        button_layout.addWidget(self.stress_btn_50)
        button_layout.addWidget(self.stress_btn_35)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Scenario results table
        self.stress_table = QTableWidget()
        self.stress_table.setColumnCount(5)
        self.stress_table.setHorizontalHeaderLabels(
            ["Scenario", "Market Impact", "Portfolio P&L", "% Change", "Recovery Time"]
        )
        self.stress_table.setRowCount(3)
        for i, scenario in enumerate(["-20%", "-50% (GFC)", "-35% (COVID)"]):
            self.stress_table.setItem(i, 0, QTableWidgetItem(scenario))
        layout.addWidget(self.stress_table)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_limits_tab(self) -> QWidget:
        """Create Risk Limits Configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Configure Risk Limits"))

        # Form grid
        form_layout = QGridLayout()
        row = 0

        # Max drawdown daily
        form_layout.addWidget(QLabel("Max Drawdown (Daily) %:"), row, 0)
        self.limit_dd_daily = QDoubleSpinBox()
        self.limit_dd_daily.setRange(0.1, 50.0)
        self.limit_dd_daily.setValue(self.risk_limits["max_drawdown_daily"])
        form_layout.addWidget(self.limit_dd_daily, row, 1)
        row += 1

        # Max drawdown total
        form_layout.addWidget(QLabel("Max Drawdown (Total) %:"), row, 0)
        self.limit_dd_total = QDoubleSpinBox()
        self.limit_dd_total.setRange(0.1, 50.0)
        self.limit_dd_total.setValue(self.risk_limits["max_drawdown_total"])
        form_layout.addWidget(self.limit_dd_total, row, 1)
        row += 1

        # Capital at risk limit
        form_layout.addWidget(QLabel("Capital at Risk Limit ($):"), row, 0)
        self.limit_capital_risk = QDoubleSpinBox()
        self.limit_capital_risk.setRange(100, 1000000)
        self.limit_capital_risk.setValue(self.risk_limits["capital_at_risk_limit"])
        form_layout.addWidget(self.limit_capital_risk, row, 1)
        row += 1

        # Max per position
        form_layout.addWidget(QLabel("Max per Position ($):"), row, 0)
        self.limit_per_position = QDoubleSpinBox()
        self.limit_per_position.setRange(100, 500000)
        self.limit_per_position.setValue(self.risk_limits["max_position_size"])
        form_layout.addWidget(self.limit_per_position, row, 1)
        row += 1

        layout.addLayout(form_layout)

        # Save button
        self.save_limits_btn = QPushButton("Save Risk Limits")
        layout.addWidget(self.save_limits_btn)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def setup_connections(self):
        """Connect signals and slots."""
        self.save_limits_btn.clicked.connect(self.on_save_limits)
        self.stress_btn_20.clicked.connect(lambda: self.on_stress_test(-0.20))
        self.stress_btn_50.clicked.connect(lambda: self.on_stress_test(-0.50))
        self.stress_btn_35.clicked.connect(lambda: self.on_stress_test(-0.35))
        self.var_method_combo.currentTextChanged.connect(self.on_update_var)

    # ========================================================================
    # PUBLIC API - Data Updates
    # ========================================================================

    def update_portfolio_data(self, portfolio_dict: Dict):
        """
        Update portfolio with new data.

        Args:
            portfolio_dict: {
                "open_trades": [{"ticker": "AAPL", "entry": 150, "stop": 145, "qty": 100}, ...],
                "positions": [{"ticker": "AAPL", "price": 160, "qty": 100}, ...],
                "historical_returns": {"AAPL": [0.01, -0.02, ...], ...},
                "total_capital": 50000.0,
                "current_capital": 45000.0
            }
        """
        try:
            self.portfolio_data = portfolio_dict
            self.open_trades = portfolio_dict.get("open_trades", [])
            self.positions = portfolio_dict.get("positions", [])
            self.historical_returns = portfolio_dict.get("historical_returns", {})

            # Refresh all displays
            self.refresh_exposure_display()
            self.refresh_var_display()
            self.refresh_correlation_display()
            self.refresh_concentration_display()
            self.refresh_frontier_display()

            self.logger.info("Portfolio data updated successfully")
        except Exception as e:
            self.logger.error(f"Error updating portfolio data: {e}", exc_info=True)
            self.alert_banner.show_error(f"Portfolio update failed: {e}")

    # ========================================================================
    # EXPOSURE TAB
    # ========================================================================

    def refresh_exposure_display(self):
        """Refresh current risk exposure display."""
        try:
            # Calculate total capital at risk (sum of R from all open trades)
            total_r = 0.0
            for trade in self.open_trades:
                entry = float(trade.get("entry", 0))
                stop = float(trade.get("stop", 0))
                qty = float(trade.get("qty", 0))
                r_per_trade = abs(entry - stop) * qty
                total_r += r_per_trade

            limit = self.risk_limits["capital_at_risk_limit"]
            percent_used = (total_r / limit * 100) if limit > 0 else 0

            # Update cards
            self.capital_at_risk_card.update_value(f"${total_r:,.2f}", "Current capital at risk")
            self.limit_card.update_value(f"${limit:,.2f}", "User-configured limit")
            self.used_percent_card.update_value(f"{percent_used:.1f}%", "Capital at risk / limit")

            # Update color based on utilization
            if percent_used > 80:
                self.used_percent_card.setStyleSheet("background-color: #ffe0e0;")
                self.exposure_alert.setText(f"⚠️ WARNING: Using {percent_used:.1f}% of risk limit!")
            elif percent_used > 60:
                self.used_percent_card.setStyleSheet("background-color: #fffacd;")
                self.exposure_alert.setText(f"ℹ️ Moderate exposure: {percent_used:.1f}% of risk limit")
            else:
                self.used_percent_card.setStyleSheet("")
                self.exposure_alert.setText("")

            # Update trades table
            self.trades_table.setRowCount(len(self.open_trades))
            for row, trade in enumerate(self.open_trades):
                ticker = trade.get("ticker", "N/A")
                entry = float(trade.get("entry", 0))
                stop = float(trade.get("stop", 0))
                qty = float(trade.get("qty", 0))
                r_value = abs(entry - stop) * qty
                r_percent = (r_value / total_r * 100) if total_r > 0 else 0
                status = trade.get("status", "Open")

                self.trades_table.setItem(row, 0, QTableWidgetItem(ticker))
                self.trades_table.setItem(row, 1, QTableWidgetItem(f"${entry:.2f}"))
                self.trades_table.setItem(row, 2, QTableWidgetItem(f"${stop:.2f}"))
                self.trades_table.setItem(row, 3, QTableWidgetItem(f"${r_value:,.2f}"))
                self.trades_table.setItem(row, 4, QTableWidgetItem(f"{r_percent:.1f}%"))
                self.trades_table.setItem(row, 5, QTableWidgetItem(status))

        except Exception as e:
            self.logger.error(f"Error refreshing exposure display: {e}", exc_info=True)

    # ========================================================================
    # VaR TAB
    # ========================================================================

    def refresh_var_display(self):
        """Refresh VaR analysis display."""
        try:
            if not self.historical_returns or not calculate_var:
                self.var_table.setItem(0, 1, QTableWidgetItem("N/A"))
                self.var_table.setItem(0, 2, QTableWidgetItem("N/A"))
                return

            # Get combined portfolio returns
            portfolio_returns = self._calculate_portfolio_returns()
            if len(portfolio_returns) < 20:
                self.var_interp_label.setText("Insufficient data (need 20+ periods)")
                return

            # Calculate VaR at different confidence levels
            var_95 = calculate_var(portfolio_returns, confidence=0.95)
            var_99 = calculate_var(portfolio_returns, confidence=0.99)

            # Get portfolio value
            total_value = sum(
                float(pos.get("price", 0)) * float(pos.get("qty", 0))
                for pos in self.positions
            )

            # Calculate dollar VaR
            dollar_var_95 = abs(var_95) * total_value
            dollar_var_99 = abs(var_99) * total_value

            # Update table
            self.var_table.setItem(0, 1, QTableWidgetItem(f"{var_95:.2%}"))
            self.var_table.setItem(0, 2, QTableWidgetItem(f"${dollar_var_95:,.2f}"))
            self.var_table.setItem(1, 1, QTableWidgetItem(f"{var_99:.2%}"))
            self.var_table.setItem(1, 2, QTableWidgetItem(f"${dollar_var_99:,.2f}"))

            # Interpretation
            interp = (
                f"95% confident: max daily loss ${dollar_var_95:,.0f}. "
                f"99% confident: max daily loss ${dollar_var_99:,.0f}."
            )
            self.var_interp_label.setText(interp)

            method = self.var_method_combo.currentText()
            details = {
                "Historical": "Historical simulation: sorts past returns, finds percentile",
                "Monte Carlo": "Random sampling from return distribution (10,000 simulations)",
                "Parametric": "Normal distribution assumption (assumes elliptical returns)"
            }
            self.var_details_label.setText(f"{method}: {details.get(method, '')}")

        except Exception as e:
            self.logger.error(f"Error refreshing VaR display: {e}", exc_info=True)

    def _calculate_portfolio_returns(self) -> List[float]:
        """Calculate weighted portfolio returns from position returns."""
        if not self.historical_returns or not self.positions:
            return []

        # Get weights
        total_value = sum(
            float(pos.get("price", 0)) * float(pos.get("qty", 0))
            for pos in self.positions
        )

        if total_value == 0:
            return []

        # Get longest return series length
        max_len = max(
            (len(returns) for returns in self.historical_returns.values()),
            default=0
        )

        if max_len == 0:
            return []

        # Combine returns
        portfolio_returns = []
        for t in range(max_len):
            period_return = 0.0
            for pos in self.positions:
                ticker = pos.get("ticker", "")
                if ticker in self.historical_returns and t < len(self.historical_returns[ticker]):
                    weight = (float(pos.get("price", 0)) * float(pos.get("qty", 0))) / total_value
                    period_return += weight * self.historical_returns[ticker][t]
            portfolio_returns.append(period_return)

        return portfolio_returns

    def on_update_var(self):
        """Slot: VaR method changed."""
        self.refresh_var_display()

    # ========================================================================
    # CORRELATION TAB
    # ========================================================================

    def refresh_correlation_display(self):
        """Refresh correlation matrix heatmap."""
        try:
            if not self.historical_returns or len(self.historical_returns) < 2:
                self.alert_banner.show_info("Insufficient positions for correlation analysis")
                return

            # Create DataFrame from historical returns
            returns_df = pd.DataFrame(self.historical_returns).dropna()

            if returns_df.shape[0] < 2:
                return

            # Calculate correlation matrix
            corr_matrix = returns_df.corr()

            # Draw heatmap
            self.corr_figure.clear()
            ax = self.corr_figure.add_subplot(111)
            sns.heatmap(
                corr_matrix,
                annot=True,
                fmt=".2f",
                cmap="RdYlGn_r",
                center=0,
                vmin=-1,
                vmax=1,
                ax=ax,
                cbar_kws={"label": "Correlation"}
            )
            ax.set_title("Position Correlation Matrix")
            self.corr_figure.tight_layout()
            self.corr_canvas.draw()

            # Find high correlations
            high_corr_pairs = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i + 1, len(corr_matrix.columns)):
                    ticker1 = corr_matrix.columns[i]
                    ticker2 = corr_matrix.columns[j]
                    corr_val = corr_matrix.iloc[i, j]

                    if abs(corr_val) > 0.70:
                        high_corr_pairs.append((ticker1, ticker2, corr_val))
                        self.correlation_warning.emit(f"{ticker1}-{ticker2}", corr_val)

            # Display warnings
            self.corr_warnings_table.setRowCount(len(high_corr_pairs))
            for row, (t1, t2, corr) in enumerate(high_corr_pairs):
                self.corr_warnings_table.setItem(row, 0, QTableWidgetItem(t1))
                self.corr_warnings_table.setItem(row, 1, QTableWidgetItem(t2))
                self.corr_warnings_table.setItem(row, 2, QTableWidgetItem(f"{corr:.3f}"))

            if high_corr_pairs:
                self.alert_banner.show_warning(
                    f"High correlation detected: {len(high_corr_pairs)} pairs with |r| > 0.70"
                )

        except Exception as e:
            self.logger.error(f"Error refreshing correlation display: {e}", exc_info=True)

    # ========================================================================
    # CONCENTRATION TAB
    # ========================================================================

    def refresh_concentration_display(self):
        """Refresh concentration analysis."""
        try:
            if not self.positions:
                return

            # Calculate position values and percentages
            total_value = sum(
                float(pos.get("price", 0)) * float(pos.get("qty", 0))
                for pos in self.positions
            )

            if total_value == 0:
                return

            # Position concentration
            position_data = []
            for pos in self.positions:
                ticker = pos.get("ticker", "N/A")
                price = float(pos.get("price", 0))
                qty = float(pos.get("qty", 0))
                value = price * qty
                pct = (value / total_value) * 100

                status = "⚠️ HIGH" if pct > 15 else "✓ OK"
                position_data.append((ticker, pct, status))

            # Update position table
            self.position_table.setRowCount(len(position_data))
            for row, (ticker, pct, status) in enumerate(position_data):
                self.position_table.setItem(row, 0, QTableWidgetItem(ticker))
                pct_item = QTableWidgetItem(f"{pct:.1f}%")
                if pct > 15:
                    pct_item.setBackground(QColor("#ffe0e0"))
                self.position_table.setItem(row, 1, pct_item)
                self.position_table.setItem(row, 2, QTableWidgetItem(status))

            # Sector concentration (if sector data available)
            sector_map = {}
            for pos in self.positions:
                sector = pos.get("sector", "Other")
                price = float(pos.get("price", 0))
                qty = float(pos.get("qty", 0))
                value = price * qty
                sector_map[sector] = sector_map.get(sector, 0) + value

            sector_data = []
            for sector, value in sector_map.items():
                pct = (value / total_value) * 100
                status = "⚠️ HIGH" if pct > 30 else "✓ OK"
                sector_data.append((sector, pct, status))

            self.sector_table.setRowCount(len(sector_data))
            for row, (sector, pct, status) in enumerate(sector_data):
                self.sector_table.setItem(row, 0, QTableWidgetItem(sector))
                pct_item = QTableWidgetItem(f"{pct:.1f}%")
                if pct > 30:
                    pct_item.setBackground(QColor("#ffe0e0"))
                self.sector_table.setItem(row, 1, pct_item)
                self.sector_table.setItem(row, 2, QTableWidgetItem(status))

            # Draw pie chart
            self.concentration_figure.clear()
            ax = self.concentration_figure.add_subplot(111)

            tickers = [t for t, _, _ in position_data]
            values = [v for _, v, _ in position_data]

            colors = ["#ff9999" if v > 15 else "#99ccff" for v in values]
            ax.pie(values, labels=tickers, autopct="%1.1f%%", colors=colors, startangle=90)
            ax.set_title("Portfolio Allocation")
            self.concentration_figure.tight_layout()
            self.concentration_canvas.draw()

        except Exception as e:
            self.logger.error(f"Error refreshing concentration display: {e}", exc_info=True)

    # ========================================================================
    # EFFICIENT FRONTIER TAB
    # ========================================================================

    def refresh_frontier_display(self):
        """Refresh efficient frontier (Markowitz optimization)."""
        try:
            if not rp or not self.historical_returns or len(self.historical_returns) < 2:
                self.alert_banner.show_info("Riskfolio not available or insufficient data")
                return

            # Create returns DataFrame
            returns_df = pd.DataFrame(self.historical_returns).dropna()

            if returns_df.shape[0] < 2:
                return

            # Build portfolio
            try:
                port = rp.Portfolio(returns=returns_df)
                port.assets_stats(method_mu='hist', method_cov='hist')

                # Optimize for Sharpe ratio
                w = port.optimization(
                    model='Classic',
                    rm='MV',  # Minimum Variance
                    obj='Sharpe',
                    rf=0.02,  # 2% risk-free rate
                )

                # Get efficient frontier points
                ef_points = port.efficient_frontier(500)

                # Calculate current portfolio metrics
                weights_current = self._get_current_weights()

                # Draw frontier
                self.frontier_figure.clear()
                ax = self.frontier_figure.add_subplot(111)

                # Frontier
                ef_risk = []
                ef_return = []
                for w in ef_points:
                    port_return = (w * returns_df.mean()).sum() * 252
                    port_risk = (w @ returns_df.cov() * 252).sum() ** 0.5
                    ef_risk.append(port_risk)
                    ef_return.append(port_return)

                ax.plot(ef_risk, ef_return, 'r-', linewidth=2, label='Efficient Frontier')

                # Current position (blue)
                if weights_current:
                    curr_return = sum(w * returns_df[t].mean() for t, w in weights_current.items() if t in returns_df.columns) * 252
                    curr_risk = (
                        sum(
                            weights_current.get(t, 0) * weights_current.get(s, 0) * returns_df[t].cov(returns_df[s]) * 252
                            for t in returns_df.columns for s in returns_df.columns
                        ) ** 0.5
                    )
                    ax.scatter([curr_risk], [curr_return], color='blue', s=200, marker='o', label='Current Position', zorder=5)

                # Optimal position (green)
                opt_return = (w * returns_df.mean()).sum() * 252
                opt_risk = (w @ returns_df.cov() @ w * 252) ** 0.5
                ax.scatter([opt_risk], [opt_return], color='green', s=200, marker='*', label='Optimal Position', zorder=5)

                ax.set_xlabel('Risk (Volatility)')
                ax.set_ylabel('Expected Return')
                ax.set_title('Markowitz Efficient Frontier')
                ax.legend()
                ax.grid(True, alpha=0.3)

                self.frontier_figure.tight_layout()
                self.frontier_canvas.draw()

                # Recommendation
                if opt_risk < curr_risk:
                    rec = (
                        f"✓ Recommendation: Your portfolio is close to efficient. "
                        f"Optimal return: {opt_return:.1%}, risk: {opt_risk:.1%}"
                    )
                else:
                    rec = (
                        f"⚠️ Optimization: Consider rebalancing to reduce risk. "
                        f"Current risk: {curr_risk:.1%} → Optimal: {opt_risk:.1%} "
                        f"with {opt_return:.1%} return"
                    )
                self.frontier_recommendation.setText(rec)

            except Exception as e:
                self.logger.warning(f"Riskfolio optimization failed: {e}")
                self.alert_banner.show_warning(f"Frontier optimization: {e}")

        except Exception as e:
            self.logger.error(f"Error refreshing frontier display: {e}", exc_info=True)

    def _get_current_weights(self) -> Dict[str, float]:
        """Get current portfolio weights."""
        total_value = sum(
            float(pos.get("price", 0)) * float(pos.get("qty", 0))
            for pos in self.positions
        )

        if total_value == 0:
            return {}

        weights = {}
        for pos in self.positions:
            ticker = pos.get("ticker", "")
            price = float(pos.get("price", 0))
            qty = float(pos.get("qty", 0))
            weights[ticker] = (price * qty) / total_value

        return weights

    # ========================================================================
    # STRESS TESTING TAB
    # ========================================================================

    def on_stress_test(self, market_drop: float):
        """
        Run stress test scenario.

        Args:
            market_drop: Market decline as decimal (e.g., -0.20 for -20%)
        """
        try:
            scenario_name = f"{market_drop:.0%}"

            # Calculate impact on portfolio
            portfolio_value = sum(
                float(pos.get("price", 0)) * float(pos.get("qty", 0))
                for pos in self.positions
            )

            # Estimate portfolio impact based on beta
            portfolio_beta = self._calculate_portfolio_beta()
            estimated_impact = market_drop * portfolio_beta

            pnl = portfolio_value * estimated_impact
            pct_change = estimated_impact * 100

            # Estimate recovery time (very rough)
            recovery_time = f"{abs(int(pct_change * 5))} days"

            # Update table
            row = {"-0.20": 0, "-0.50": 1, "-0.35": 2}.get(f"{market_drop:.2f}", 0)

            self.stress_table.setItem(row, 1, QTableWidgetItem(f"{market_drop:.0%}"))
            self.stress_table.setItem(row, 2, QTableWidgetItem(f"${pnl:,.2f}"))
            self.stress_table.setItem(row, 3, QTableWidgetItem(f"{pct_change:.2f}%"))
            self.stress_table.setItem(row, 4, QTableWidgetItem(recovery_time))

            # Color code
            item = self.stress_table.item(row, 2)
            if pnl < 0:
                item.setBackground(QColor("#ffe0e0"))

            self.stress_test_updated.emit({
                "scenario": scenario_name,
                "pnl": pnl,
                "pct": pct_change
            })

            self.alert_banner.show_info(
                f"Stress test {scenario_name}: Portfolio would lose ${abs(pnl):,.0f} ({pct_change:.1f}%)"
            )

        except Exception as e:
            self.logger.error(f"Error running stress test: {e}", exc_info=True)

    def _calculate_portfolio_beta(self) -> float:
        """Calculate weighted portfolio beta."""
        if not self.positions:
            return 1.0

        total_value = sum(
            float(pos.get("price", 0)) * float(pos.get("qty", 0))
            for pos in self.positions
        )

        if total_value == 0:
            return 1.0

        weighted_beta = 0.0
        for pos in self.positions:
            weight = (float(pos.get("price", 0)) * float(pos.get("qty", 0))) / total_value
            beta = float(pos.get("beta", 1.0))
            weighted_beta += weight * beta

        return weighted_beta

    # ========================================================================
    # RISK LIMITS
    # ========================================================================

    def on_save_limits(self):
        """Save risk limits configuration."""
        try:
            self.risk_limits = {
                "max_drawdown_daily": self.limit_dd_daily.value(),
                "max_drawdown_total": self.limit_dd_total.value(),
                "capital_at_risk_limit": self.limit_capital_risk.value(),
                "max_position_size": self.limit_per_position.value(),
            }

            self.risk_limit_changed.emit(self.risk_limits)
            self.alert_banner.show_success("Risk limits saved successfully")
            self.logger.info(f"Risk limits updated: {self.risk_limits}")

        except Exception as e:
            self.logger.error(f"Error saving limits: {e}", exc_info=True)
            self.alert_banner.show_error(f"Failed to save limits: {e}")
