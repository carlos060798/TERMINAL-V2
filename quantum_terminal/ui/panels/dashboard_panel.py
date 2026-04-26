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
from datetime import datetime, timedelta
import asyncio
import logging
import traceback

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
    QPushButton, QLabel, QSpacerItem, QSizePolicy, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt6.QtGui import QFont

from quantum_terminal.ui.widgets import (
    MetricCard, HeatmapWidget, EquityCurveWidget, AlertBanner
)
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
    from quantum_terminal.infrastructure.macro.fred_adapter import FREDAdapter
except ImportError:
    FREDAdapter = None

try:
    from quantum_terminal.infrastructure.ai.ai_gateway import AIGateway
except ImportError:
    AIGateway = None

try:
    from quantum_terminal.domain.risk import (
        calculate_sharpe_ratio, calculate_sortino_ratio,
        calculate_var, calculate_max_drawdown, calculate_beta
    )
except ImportError:
    calculate_sharpe_ratio = None

logger = get_logger(__name__)


class DataLoaderThread(QThread):
    """Background thread for async data loading."""
    data_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, data_fetcher):
        super().__init__()
        self.data_fetcher = data_fetcher

    def run(self):
        try:
            data = asyncio.run(self.data_fetcher())
            self.data_loaded.emit(data)
        except Exception as e:
            logger.error(f"Data loader thread error: {e}", exc_info=True)
            self.error_occurred.emit(str(e))


class DashboardPanel(QWidget):
    """
    Main dashboard panel showing portfolio overview and key metrics.

    Integrates with:
    - Domain layer: Risk metrics (Sharpe, Sortino, VaR, Beta, Max Drawdown)
    - Infrastructure: DataProvider (quotes), FREDAdapter (macro), AIGateway (insights)
    - UI Widgets: MetricCard, HeatmapWidget, EquityCurveWidget

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
        self.market_data = {}
        self.data_loader_thread = None

        # Initialize infrastructure adapters
        self.data_provider = DataProvider() if DataProvider else None
        self.fred_adapter = FREDAdapter(settings.fred_api_key) if FREDAdapter and hasattr(settings, 'fred_api_key') else None
        self.ai_gateway = AIGateway() if AIGateway else None

        # Timers
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._on_auto_refresh)
        self.market_update_timer = QTimer()
        self.market_update_timer.timeout.connect(self._on_market_update)

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

        # Market bar (top indicators: S&P, NASDAQ, BTC, VIX, etc.)
        market_layout = self._build_market_bar()
        main_layout.addLayout(market_layout)

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

        # Row 5: AI Insights
        ai_label = QLabel("AI Market Insights")
        ai_label_font = QFont()
        ai_label_font.setBold(True)
        ai_label.setFont(ai_label_font)
        content_layout.addWidget(ai_label)

        ai_layout = QHBoxLayout()
        self.ai_insights_text = QTextEdit()
        self.ai_insights_text.setReadOnly(True)
        self.ai_insights_text.setMaximumHeight(150)
        self.ai_insights_text.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 8px;
                font-family: monospace;
                font-size: 10pt;
            }
        """)
        ai_layout.addWidget(self.ai_insights_text)

        generate_insight_btn = QPushButton("Generate Insight")
        generate_insight_btn.setMaximumWidth(120)
        generate_insight_btn.clicked.connect(self._on_generate_insight)
        ai_layout.addWidget(generate_insight_btn, 0, Qt.AlignmentFlag.AlignTop)

        content_layout.addLayout(ai_layout)

        content_layout.addSpacing(20)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        self.setLayout(main_layout)

    def _build_market_bar(self) -> QHBoxLayout:
        """Build market indicators bar (S&P, NASDAQ, BTC, VIX, etc.)."""
        layout = QHBoxLayout()
        layout.setSpacing(16)

        # S&P 500
        self.label_sp500 = QLabel("S&P 500: --")
        self.label_sp500.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        layout.addWidget(self.label_sp500)

        # NASDAQ
        self.label_nasdaq = QLabel("NASDAQ: --")
        self.label_nasdaq.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        layout.addWidget(self.label_nasdaq)

        # Bitcoin
        self.label_btc = QLabel("BTC: --")
        self.label_btc.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        layout.addWidget(self.label_btc)

        # VIX
        self.label_vix = QLabel("VIX: --")
        self.label_vix.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        layout.addWidget(self.label_vix)

        # 10Y Treasury
        self.label_dgs10 = QLabel("10Y Yield: --")
        self.label_dgs10.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        layout.addWidget(self.label_dgs10)

        # Dollar Index
        self.label_dxy = QLabel("DXY: --")
        self.label_dxy.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        layout.addWidget(self.label_dxy)

        layout.addStretch()
        return layout

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
        self.period_buttons = {}
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
            self.period_buttons[period] = btn

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

    def _on_market_update(self):
        """Update market indicators every 5 seconds."""
        asyncio.create_task(self._update_market_indicators())

    async def _update_market_indicators(self) -> None:
        """Fetch and update market bar indicators."""
        if not self.data_provider:
            return

        indicators = {
            "^GSPC": self.label_sp500,
            "^IXIC": self.label_nasdaq,
            "BTC-USD": self.label_btc,
            "^VIX": self.label_vix,
            "DX-Y.NYB": self.label_dxy,
        }

        for ticker, label in indicators.items():
            try:
                quote = await self._get_quote_async(ticker)
                if quote and "price" in quote:
                    price = quote["price"]
                    change = quote.get("change_pct", 0)
                    color = "#00ff00" if change >= 0 else "#ff4444"
                    label.setText(f"{ticker}: ${price:.2f} ({change:+.2f}%)")
                    label.setStyleSheet(f"color: {color}; font-weight: bold;")
            except Exception as e:
                logger.debug(f"Failed to update {ticker}: {e}")

        # Update 10Y Treasury yield from FRED
        try:
            if self.fred_adapter:
                dgs10 = await self._get_fred_series("DGS10")
                if dgs10 is not None:
                    self.label_dgs10.setText(f"10Y Yield: {dgs10:.3f}%")
        except Exception as e:
            logger.debug(f"Failed to fetch FRED data: {e}")

    async def _get_fred_series(self, series_id: str) -> Optional[float]:
        """Fetch FRED series value asynchronously."""
        try:
            if self.fred_adapter and hasattr(self.fred_adapter, 'get_series'):
                return await self.fred_adapter.get_series(series_id)
        except Exception as e:
            logger.debug(f"Failed to fetch {series_id} from FRED: {e}")
        return None

    def _on_generate_insight(self) -> None:
        """Generate AI market insight."""
        if not self.ai_gateway:
            self.ai_insights_text.setText("AI Gateway not initialized. Check API keys in .env")
            return

        self.ai_insights_text.setText("Generating insight...")

        async def generate():
            try:
                portfolio_value = self.portfolio_data.get("total_value", "N/A")
                sharpe = self.portfolio_data.get("sharpe_ratio", "N/A")
                vix = self.market_data.get("vix", "N/A")
                top_holdings = "AAPL, MSFT, GOOGL"  # Mock

                prompt = f"""Portfolio Summary (2 paragraphs max):
- Total Value: {portfolio_value}
- Sharpe Ratio: {sharpe}
- VIX Level: {vix}
- Top Holdings: {top_holdings}

Provide brief market insights and portfolio assessment."""

                result = await self.ai_gateway.generate(prompt, task_type="fast")
                self.ai_insights_text.setText(result)
                logger.info("AI insight generated successfully")
            except Exception as e:
                logger.error(f"Failed to generate insight: {e}", exc_info=True)
                self.ai_insights_text.setText(f"Error: {str(e)}")

        # Run async in background
        try:
            asyncio.create_task(generate())
        except RuntimeError:
            # No running event loop, try to create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.create_task(generate())

    def load_portfolio_data(self, period: str = "1D") -> None:
        """
        Load portfolio data from infrastructure layer asynchronously.

        Args:
            period: Time period for metrics ("1D", "1W", "1M", etc.)

        Fetches data without blocking UI using background thread.
        """
        try:
            # Create async data fetcher
            async def fetch_portfolio_data():
                return await self._fetch_portfolio_data_async(period)

            # Start background thread
            self.data_loader_thread = DataLoaderThread(fetch_portfolio_data)
            self.data_loader_thread.data_loaded.connect(self._on_data_loaded)
            self.data_loader_thread.error_occurred.connect(self._on_data_error)
            self.data_loader_thread.start()
        except Exception as e:
            logger.error(f"Failed to start data load: {e}", exc_info=True)
            self._show_error(f"Failed to load portfolio data: {str(e)}")

    async def _fetch_portfolio_data_async(self, period: str = "1D") -> Dict:
        """
        Async portfolio data fetch from infrastructure.

        Integrates with:
        - domain/risk.py: Sharpe, Sortino, VaR, Beta, Max Drawdown
        - infrastructure/market_data: Quote data
        - database: Historical portfolio values
        """
        try:
            # For now, use mock data with some real infrastructure calls
            # In Phase 4+, replace with real DB queries and risk calculations

            data = self._get_mock_portfolio_data(period)

            # Try to fetch market data (non-blocking)
            try:
                if self.data_provider:
                    quote = await self._get_quote_async("SPY")
                    if quote:
                        data["market_snapshot"] = quote
            except Exception as e:
                logger.warning(f"Failed to fetch market data: {e}")

            return data
        except Exception as e:
            logger.error(f"Async data fetch error: {e}", exc_info=True)
            raise

    async def _get_quote_async(self, ticker: str) -> Optional[Dict]:
        """Fetch quote asynchronously from data provider."""
        try:
            if self.data_provider and hasattr(self.data_provider, 'get_quote'):
                return await self.data_provider.get_quote(ticker)
        except Exception as e:
            logger.debug(f"Failed to fetch {ticker}: {e}")
        return None

    @pyqtSlot(dict)
    def _on_data_loaded(self, data: Dict) -> None:
        """Handle successful data load from background thread."""
        self.portfolio_data = data
        self.update_metrics()
        logger.info("Portfolio data loaded successfully")

    @pyqtSlot(str)
    def _on_data_error(self, error: str) -> None:
        """Handle data load error from background thread."""
        logger.error(f"Data load error: {error}")
        self._show_error(f"Failed to load portfolio data: {error}")

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

        # Also start market update timer (every 5 seconds)
        self.market_update_timer.setInterval(5000)
        self.market_update_timer.start()

        logger.info(f"Auto-refresh started (interval: {interval_seconds}s)")
        logger.info("Market update timer started (5s interval)")

    def stop_auto_refresh(self) -> None:
        """Stop automatic refresh timer."""
        self.refresh_timer.stop()
        self.market_update_timer.stop()
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
