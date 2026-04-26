"""
UI Panels for Quantum Investment Terminal.

Panels represent the main application screens:
- DashboardPanel: Portfolio overview with KPIs
- WatchlistPanel: Live stock data and watchlist
- AnalyzerPanel: Comprehensive Graham-Dodd analysis (7 tabs)

Phase 3 - UI Layer Implementation
Reference: PLAN_MAESTRO.md - Phase 3: UI Skeleton
"""

from .dashboard_panel import DashboardPanel
from .watchlist_panel import WatchlistPanel
from .analyzer_panel import AnalyzerPanel

__all__ = [
    "DashboardPanel",
    "WatchlistPanel",
    "AnalyzerPanel",
]
