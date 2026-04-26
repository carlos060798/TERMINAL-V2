"""
Forecast Panel - EPS/Revenue Forecasting + Momentum Signals (4 Tabs).

Complements Analyzer panel with forward-looking projections:

Tab 1: EPS Forecast
  - Historical quarterly EPS (10 years)
  - Prophet 4-8 quarter forecast
  - Confidence bands (80%, 95%)
  - MAPE accuracy metric

Tab 2: Revenue Forecast
  - Historical quarterly revenue
  - Prophet forecast with seasonality
  - Trend analysis (growth, stagnation, decline)
  - Bands show uncertainty range

Tab 3: Price Signal (Momentum)
  - 60-day price action + indicators (RSI, MACD, SMA)
  - LSTM-based momentum probability (0-1)
  - BUY/HOLD/SELL signal
  - Complements Graham valuation (does NOT predict price)

Tab 4: Confidence & Analysis
  - Forecast accuracy (MAPE, historical residuals)
  - Sensitivity: what if growth ±20%?
  - DCF impact: new IV based on forecast
  - "Upside case: IV could be $X if revenue grows 15%"

Integration with Analyzer:
  - Tab 7 (Valuation) uses forecast EPS to update Graham IV
  - "Based on current trend, IV could be $X in 2 years"

Phase 3 - UI Layer Implementation
Reference: PLAN_MAESTRO.md - Phase 3: UI Skeleton
"""

from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime
import logging
import asyncio

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QPushButton,
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QColor
import pyqtgraph as pg
import pandas as pd
import numpy as np

from quantum_terminal.ui.widgets import ChartWidget
from quantum_terminal.utils.logger import get_logger
from quantum_terminal.infrastructure.ml.forecast_engine import (
    EPSForecaster, MomentumSignalGenerator, ForecastResult, MomentumSignal
)

logger = get_logger(__name__)


class ForecastPanel(QWidget):
    """
    Forecast panel with 4 tabs: EPS, Revenue, Momentum, Analysis.

    Signals:
        - forecast_complete: Emitted when forecast generation is complete
        - signal_generated: Emitted when momentum signal is generated
    """

    forecast_complete = pyqtSignal(str, str)  # ticker, metric
    signal_generated = pyqtSignal(str, str)  # ticker, signal

    def __init__(self, parent=None):
        """Initialize forecast panel."""
        super().__init__(parent)
        self.current_ticker = None
        self.forecast_data: Dict[str, ForecastResult] = {}
        self.momentum_data: Optional[MomentumSignal] = None

        # Initialize forecasters
        self.eps_forecaster = EPSForecaster()
        self.momentum_generator = MomentumSignalGenerator()

        self.initUI()
        self.setup_connections()

    def initUI(self):
        """Build the UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Title and ticker selector
        title_layout = self._build_title_section()
        title_widget = QWidget()
        title_widget.setLayout(title_layout)
        main_layout.addWidget(title_widget, 0)

        # Tabs
        self.tabs = self._build_tabs()
        main_layout.addWidget(self.tabs, 1)

        self.setLayout(main_layout)

    def _build_title_section(self) -> QVBoxLayout:
        """Build title and ticker selector."""
        layout = QVBoxLayout()

        # Header
        header = QLabel("📊 Forecast Engine")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(header)

        # Ticker selector
        ticker_layout = QHBoxLayout()
        ticker_label = QLabel("Ticker:")
        self.ticker_input = QLineEdit()
        self.ticker_input.setPlaceholderText("Enter ticker (e.g., AAPL)")
        self.ticker_input.setMaximumWidth(150)

        self.load_btn = QPushButton("Load Data")
        self.load_btn.setMaximumWidth(120)

        ticker_layout.addWidget(ticker_label)
        ticker_layout.addWidget(self.ticker_input)
        ticker_layout.addWidget(self.load_btn)
        ticker_layout.addStretch()

        layout.addLayout(ticker_layout)

        return layout

    def _build_tabs(self) -> QTabWidget:
        """Build 4 tabs."""
        tabs = QTabWidget()

        # Tab 1: EPS Forecast
        eps_tab = self._build_eps_tab()
        tabs.addTab(eps_tab, "📈 EPS Forecast")

        # Tab 2: Revenue Forecast
        revenue_tab = self._build_revenue_tab()
        tabs.addTab(revenue_tab, "💰 Revenue Forecast")

        # Tab 3: Momentum Signal
        momentum_tab = self._build_momentum_tab()
        tabs.addTab(momentum_tab, "⚡ Momentum Signal")

        # Tab 4: Confidence & Analysis
        analysis_tab = self._build_analysis_tab()
        tabs.addTab(analysis_tab, "📊 Analysis")

        return tabs

    def _build_eps_tab(self) -> QWidget:
        """Build EPS forecast tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Controls
        controls_layout = QHBoxLayout()

        periods_label = QLabel("Forecast Periods:")
        self.eps_periods = QSpinBox()
        self.eps_periods.setValue(8)
        self.eps_periods.setRange(4, 12)
        self.eps_periods.setMaximumWidth(100)

        interval_label = QLabel("Confidence:")
        self.eps_interval = QComboBox()
        self.eps_interval.addItems(["80%", "95%"])
        self.eps_interval.setMaximumWidth(100)

        forecast_btn = QPushButton("Forecast EPS")
        forecast_btn.clicked.connect(self._on_forecast_eps)

        controls_layout.addWidget(periods_label)
        controls_layout.addWidget(self.eps_periods)
        controls_layout.addWidget(interval_label)
        controls_layout.addWidget(self.eps_interval)
        controls_layout.addWidget(forecast_btn)
        controls_layout.addStretch()

        layout.addLayout(controls_layout, 0)

        # Chart
        self.eps_chart = ChartWidget(title="EPS Forecast")
        layout.addWidget(self.eps_chart, 1)

        # Stats table
        self.eps_stats_table = QTableWidget()
        self.eps_stats_table.setColumnCount(4)
        self.eps_stats_table.setHorizontalHeaderLabels([
            "Quarter", "Forecast", "Lower 80%", "Upper 80%"
        ])
        self.eps_stats_table.setMaximumHeight(200)
        layout.addWidget(self.eps_stats_table, 0)

        return widget

    def _build_revenue_tab(self) -> QWidget:
        """Build Revenue forecast tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Controls
        controls_layout = QHBoxLayout()

        periods_label = QLabel("Forecast Periods:")
        self.rev_periods = QSpinBox()
        self.rev_periods.setValue(8)
        self.rev_periods.setRange(4, 12)
        self.rev_periods.setMaximumWidth(100)

        interval_label = QLabel("Confidence:")
        self.rev_interval = QComboBox()
        self.rev_interval.addItems(["80%", "95%"])
        self.rev_interval.setMaximumWidth(100)

        forecast_btn = QPushButton("Forecast Revenue")
        forecast_btn.clicked.connect(self._on_forecast_revenue)

        controls_layout.addWidget(periods_label)
        controls_layout.addWidget(self.rev_periods)
        controls_layout.addWidget(interval_label)
        controls_layout.addWidget(self.rev_interval)
        controls_layout.addWidget(forecast_btn)
        controls_layout.addStretch()

        layout.addLayout(controls_layout, 0)

        # Chart
        self.revenue_chart = ChartWidget(title="Revenue Forecast")
        layout.addWidget(self.revenue_chart, 1)

        # Stats table
        self.revenue_stats_table = QTableWidget()
        self.revenue_stats_table.setColumnCount(4)
        self.revenue_stats_table.setHorizontalHeaderLabels([
            "Quarter", "Forecast ($M)", "Lower 80%", "Upper 80%"
        ])
        self.revenue_stats_table.setMaximumHeight(200)
        layout.addWidget(self.revenue_stats_table, 0)

        return widget

    def _build_momentum_tab(self) -> QWidget:
        """Build momentum signal tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Controls
        controls_layout = QHBoxLayout()

        lookback_label = QLabel("Lookback:")
        self.momentum_lookback = QSpinBox()
        self.momentum_lookback.setValue(60)
        self.momentum_lookback.setRange(20, 120)
        self.momentum_lookback.setMaximumWidth(100)
        self.momentum_lookback.setSuffix(" days")

        signal_btn = QPushButton("Generate Signal")
        signal_btn.clicked.connect(self._on_generate_signal)

        controls_layout.addWidget(lookback_label)
        controls_layout.addWidget(self.momentum_lookback)
        controls_layout.addWidget(signal_btn)
        controls_layout.addStretch()

        layout.addLayout(controls_layout, 0)

        # Signal display
        signal_layout = QHBoxLayout()

        # Signal box
        signal_box = QWidget()
        signal_box_layout = QVBoxLayout(signal_box)
        signal_label = QLabel("Signal:")
        signal_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.momentum_signal_label = QLabel("--")
        self.momentum_signal_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.momentum_signal_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        signal_box_layout.addWidget(signal_label)
        signal_box_layout.addWidget(self.momentum_signal_label)

        signal_layout.addWidget(signal_box, 1)

        # Metrics
        metrics_box = QWidget()
        metrics_layout = QVBoxLayout(metrics_box)
        self.momentum_metrics = QTableWidget()
        self.momentum_metrics.setColumnCount(2)
        self.momentum_metrics.setHorizontalHeaderLabels(["Metric", "Value"])
        self.momentum_metrics.setMaximumHeight(250)
        metrics_layout.addWidget(self.momentum_metrics)

        signal_layout.addWidget(metrics_box, 2)

        layout.addLayout(signal_layout, 1)

        return widget

    def _build_analysis_tab(self) -> QWidget:
        """Build confidence and sensitivity analysis tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Accuracy section
        accuracy_label = QLabel("📊 Forecast Accuracy")
        accuracy_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(accuracy_label)

        self.accuracy_table = QTableWidget()
        self.accuracy_table.setColumnCount(3)
        self.accuracy_table.setHorizontalHeaderLabels(["Metric", "EPS", "Revenue"])
        self.accuracy_table.setMaximumHeight(150)
        layout.addWidget(self.accuracy_table)

        # Sensitivity section
        sensitivity_label = QLabel("📈 Sensitivity Analysis")
        sensitivity_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(sensitivity_label)

        sensitivity_layout = QHBoxLayout()

        growth_label = QLabel("Growth Adjustment:")
        self.growth_adjust = QDoubleSpinBox()
        self.growth_adjust.setValue(0)
        self.growth_adjust.setRange(-50, 50)
        self.growth_adjust.setSuffix("%")
        self.growth_adjust.setMaximumWidth(120)

        sensitivity_btn = QPushButton("Update Forecast")
        sensitivity_btn.clicked.connect(self._on_sensitivity_change)

        sensitivity_layout.addWidget(growth_label)
        sensitivity_layout.addWidget(self.growth_adjust)
        sensitivity_layout.addWidget(sensitivity_btn)
        sensitivity_layout.addStretch()

        layout.addLayout(sensitivity_layout)

        # Impact section
        impact_label = QLabel("💡 DCF Impact")
        impact_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(impact_label)

        self.impact_text = QTableWidget()
        self.impact_text.setColumnCount(2)
        self.impact_text.setHorizontalHeaderLabels(["Scenario", "Impact"])
        self.impact_text.setMaximumHeight(200)
        layout.addWidget(self.impact_text)

        layout.addStretch()

        return widget

    def setup_connections(self):
        """Setup signal/slot connections."""
        self.load_btn.clicked.connect(self._on_load_ticker)

    def _on_load_ticker(self):
        """Load ticker data."""
        ticker = self.ticker_input.text().upper()
        if not ticker:
            QMessageBox.warning(self, "Error", "Please enter a ticker")
            return

        self.current_ticker = ticker
        logger.info(f"Loading data for {ticker}")

    async def _on_forecast_eps(self):
        """Generate EPS forecast."""
        if not self.current_ticker:
            QMessageBox.warning(self, "Error", "Please load a ticker first")
            return

        try:
            # Mock data generation for demo
            # In real implementation, fetch from SEC adapter
            dates = pd.date_range(end=datetime.now(), periods=40, freq='Q')
            eps_values = np.random.normal(2.5, 0.5, 40)
            eps_values = np.abs(eps_values)  # Ensure positive

            historical_df = pd.DataFrame({
                'date': dates,
                'eps': eps_values
            })

            periods = self.eps_periods.value()
            forecast = await self.eps_forecaster.forecast_eps(
                self.current_ticker,
                historical_df,
                periods=periods
            )

            self.forecast_data['eps'] = forecast
            self._display_eps_forecast(forecast)
            self.forecast_complete.emit(self.current_ticker, 'eps')

        except Exception as e:
            logger.error(f"EPS forecast error: {e}")
            QMessageBox.critical(self, "Error", f"Forecast failed: {str(e)}")

    async def _on_forecast_revenue(self):
        """Generate revenue forecast."""
        if not self.current_ticker:
            QMessageBox.warning(self, "Error", "Please load a ticker first")
            return

        try:
            # Mock data for demo
            dates = pd.date_range(end=datetime.now(), periods=40, freq='Q')
            revenue_values = np.random.normal(50000, 10000, 40)
            revenue_values = np.abs(revenue_values)

            historical_df = pd.DataFrame({
                'date': dates,
                'revenue': revenue_values
            })

            periods = self.rev_periods.value()
            forecast = await self.eps_forecaster.forecast_revenue(
                self.current_ticker,
                historical_df,
                periods=periods
            )

            self.forecast_data['revenue'] = forecast
            self._display_revenue_forecast(forecast)
            self.forecast_complete.emit(self.current_ticker, 'revenue')

        except Exception as e:
            logger.error(f"Revenue forecast error: {e}")
            QMessageBox.critical(self, "Error", f"Forecast failed: {str(e)}")

    async def _on_generate_signal(self):
        """Generate momentum signal."""
        if not self.current_ticker:
            QMessageBox.warning(self, "Error", "Please load a ticker first")
            return

        try:
            # Mock data for demo
            days = self.momentum_lookback.value()
            dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
            close_prices = np.random.normal(150, 20, days)
            close_prices = np.cumsum(np.random.normal(0.5, 5, days)) + 150

            price_df = pd.DataFrame({
                'date': dates,
                'open': close_prices + np.random.normal(0, 2, days),
                'high': close_prices + np.abs(np.random.normal(0, 3, days)),
                'low': close_prices - np.abs(np.random.normal(0, 3, days)),
                'close': close_prices,
                'volume': np.random.normal(10000000, 2000000, days)
            })

            signal = await self.momentum_generator.generate_signal(
                self.current_ticker,
                price_df
            )

            self.momentum_data = signal
            self._display_momentum_signal(signal)
            self.signal_generated.emit(self.current_ticker, signal.signal)

        except Exception as e:
            logger.error(f"Signal generation error: {e}")
            QMessageBox.critical(self, "Error", f"Signal failed: {str(e)}")

    def _on_sensitivity_change(self):
        """Update forecast based on growth adjustment."""
        adjustment = self.growth_adjust.value()

        if 'eps' not in self.forecast_data:
            QMessageBox.warning(self, "Error", "Please generate EPS forecast first")
            return

        # Adjust values and redisplay
        forecast = self.forecast_data['eps']
        adjusted_values = [v * (1 + adjustment / 100) for v in forecast.forecast_values]

        logger.info(f"Sensitivity analysis: EPS adjusted by {adjustment}%")

        # Update display
        self._update_eps_display_with_adjustment(adjusted_values)

    def _display_eps_forecast(self, forecast: ForecastResult):
        """Display EPS forecast on chart and table."""
        # Update table
        self.eps_stats_table.setRowCount(len(forecast.forecast_dates))

        for i, (date, value, lower, upper) in enumerate(zip(
            forecast.forecast_dates,
            forecast.forecast_values,
            forecast.lower_bounds_80,
            forecast.upper_bounds_80
        )):
            self.eps_stats_table.setItem(i, 0, QTableWidgetItem(date.strftime('%Y-Q%q')))
            self.eps_stats_table.setItem(i, 1, QTableWidgetItem(f"${value:.2f}"))
            self.eps_stats_table.setItem(i, 2, QTableWidgetItem(f"${lower:.2f}"))
            self.eps_stats_table.setItem(i, 3, QTableWidgetItem(f"${upper:.2f}"))

        # Update chart
        self.eps_chart.plot_forecast(
            forecast.forecast_dates,
            forecast.forecast_values,
            forecast.lower_bounds_80,
            forecast.upper_bounds_80,
            title=f"EPS Forecast for {forecast.ticker}"
        )

        logger.info(
            f"Displayed EPS forecast for {forecast.ticker}: "
            f"MAPE={forecast.mape:.2f}%"
        )

    def _display_revenue_forecast(self, forecast: ForecastResult):
        """Display revenue forecast."""
        # Update table
        self.revenue_stats_table.setRowCount(len(forecast.forecast_dates))

        for i, (date, value, lower, upper) in enumerate(zip(
            forecast.forecast_dates,
            forecast.forecast_values,
            forecast.lower_bounds_80,
            forecast.upper_bounds_80
        )):
            self.revenue_stats_table.setItem(i, 0, QTableWidgetItem(date.strftime('%Y-Q%q')))
            self.revenue_stats_table.setItem(i, 1, QTableWidgetItem(f"${value/1e6:.1f}M"))
            self.revenue_stats_table.setItem(i, 2, QTableWidgetItem(f"${lower/1e6:.1f}M"))
            self.revenue_stats_table.setItem(i, 3, QTableWidgetItem(f"${upper/1e6:.1f}M"))

        # Update chart
        self.revenue_chart.plot_forecast(
            forecast.forecast_dates,
            forecast.forecast_values,
            forecast.lower_bounds_80,
            forecast.upper_bounds_80,
            title=f"Revenue Forecast for {forecast.ticker}"
        )

        logger.info(
            f"Displayed revenue forecast for {forecast.ticker}: "
            f"MAPE={forecast.mape:.2f}%"
        )

    def _display_momentum_signal(self, signal: MomentumSignal):
        """Display momentum signal."""
        # Update signal label with color
        self.momentum_signal_label.setText(signal.signal)
        if signal.signal == "BUY":
            self.momentum_signal_label.setStyleSheet("color: green; font-weight: bold;")
        elif signal.signal == "SELL":
            self.momentum_signal_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.momentum_signal_label.setStyleSheet("color: orange; font-weight: bold;")

        # Update metrics table
        metrics = [
            ("Signal", signal.signal),
            ("Confidence", f"{signal.probability:.1%}"),
            ("RSI", f"{signal.rsi:.1f}"),
            ("MACD", f"{signal.macd:.4f}"),
            ("Price", f"${signal.current_price:.2f}"),
            ("SMA 20", f"${signal.sma_20:.2f}"),
            ("SMA 50", f"${signal.sma_50:.2f}"),
            ("Trend Strength", f"{signal.trend_strength:.1%}"),
        ]

        self.momentum_metrics.setRowCount(len(metrics))
        for i, (name, value) in enumerate(metrics):
            self.momentum_metrics.setItem(i, 0, QTableWidgetItem(name))
            self.momentum_metrics.setItem(i, 1, QTableWidgetItem(value))

        logger.info(
            f"Displayed momentum signal for {signal.ticker}: "
            f"{signal.signal} ({signal.probability:.1%})"
        )

    def _update_eps_display_with_adjustment(self, adjusted_values: List[float]):
        """Update EPS display with sensitivity adjustment."""
        if 'eps' not in self.forecast_data:
            return

        forecast = self.forecast_data['eps']

        # Update table with adjusted values
        for i, (value, lower, upper) in enumerate(zip(
            adjusted_values,
            forecast.lower_bounds_80,
            forecast.upper_bounds_80
        )):
            self.eps_stats_table.setItem(i, 1, QTableWidgetItem(f"${value:.2f}"))

        logger.info("Updated EPS forecast display with sensitivity adjustment")

    def set_data(self, ticker: str, eps_data: Optional[pd.DataFrame] = None,
                 revenue_data: Optional[pd.DataFrame] = None,
                 price_data: Optional[pd.DataFrame] = None):
        """
        Set data for forecasting.

        Args:
            ticker: Stock ticker
            eps_data: Historical EPS DataFrame
            revenue_data: Historical revenue DataFrame
            price_data: Historical price DataFrame
        """
        self.current_ticker = ticker
        self.ticker_input.setText(ticker)

        # Store data for forecasting
        self.eps_historical = eps_data
        self.revenue_historical = revenue_data
        self.price_historical = price_data

        logger.info(f"Forecast panel data set for {ticker}")


__all__ = ['ForecastPanel']
