"""
UI Panels for Quantum Investment Terminal.

Panels represent the main application screens:
- DashboardPanel: Portfolio overview with KPIs
- WatchlistPanel: Live stock data and watchlist
- AnalyzerPanel: Comprehensive Graham-Dodd analysis (7 tabs)
- TradingJournalPanel: Complete trade logging and analysis
- ThesisPanel: Investment thesis creation, tracking, and analysis

Phase 3 - UI Layer Implementation
Reference: PLAN_MAESTRO.md - Phase 3: UI Skeleton
"""

from .dashboard_panel import DashboardPanel
from .watchlist_panel import WatchlistPanel
from .analyzer_panel import AnalyzerPanel
from .journal_panel import TradingJournalPanel
from .thesis_panel import ThesisPanel

__all__ = [
    "DashboardPanel",
    "WatchlistPanel",
    "AnalyzerPanel",
    "TradingJournalPanel",
    "ThesisPanel",
]
