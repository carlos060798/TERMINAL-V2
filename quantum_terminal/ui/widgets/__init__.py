"""
Reusable widgets for Quantum Investment Terminal UI.

Exports:
- MetricCard: KPI display with animated value and change percentage
- ChartWidget: Candlestick chart with technical indicators
- DataTable: Enhanced table with sorting and filtering
- TickerSearch: Autocomplete ticker search widget
- AlertBanner: Notification banner (info/warning/error/success)
- AIChatWidget: Chat panel with message history
- HeatmapWidget: Sector heatmap with Plotly
- EquityCurveWidget: Equity curve and drawdown visualization
"""

from .metric_card import MetricCard
from .chart_widget import ChartWidget
from .data_table import DataTable
from .ticker_search import TickerSearch
from .alert_banner import AlertBanner
from .ai_chat_widget import AIChatWidget
from .heatmap_widget import HeatmapWidget
from .equity_curve_widget import EquityCurveWidget

__all__ = [
    "MetricCard",
    "ChartWidget",
    "DataTable",
    "TickerSearch",
    "AlertBanner",
    "AIChatWidget",
    "HeatmapWidget",
    "EquityCurveWidget",
]
