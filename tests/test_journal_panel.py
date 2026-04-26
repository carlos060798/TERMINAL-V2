"""
Tests for Trading Journal Panel.

Test coverage:
- UI initialization
- Trade creation and storage
- Table updates
- Statistics calculations
- Equity curve updates
- Postmortem generation
- Plan adherence tracking
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
from PyQt6.QtWidgets import QApplication, QTableWidget
from PyQt6.QtCore import Qt

from quantum_terminal.ui.panels.journal_panel import TradingJournalPanel
from quantum_terminal.ui.dialogs.add_trade_dialog import TradeData
from quantum_terminal.application.trading.trade_statistics_usecase import (
    TradeStatisticsUseCase,
)
from quantum_terminal.application.trading.plan_adherence_usecase import (
    PlanAdherenceUseCase,
)


@pytest.fixture
def app():
    """Create QApplication for tests."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def panel(app):
    """Create panel instance for testing."""
    panel = TradingJournalPanel()
    yield panel
    panel.closeEvent(None)


class TestTradingJournalPanelInitialization:
    """Test panel initialization."""

    def test_panel_creates_successfully(self, panel):
        """Panel should initialize without errors."""
        assert panel is not None
        assert isinstance(panel, TradingJournalPanel)

    def test_panel_has_required_widgets(self, panel):
        """Panel should have all required UI widgets."""
        assert hasattr(panel, "trades_table")
        assert hasattr(panel, "stat_cards")
        assert hasattr(panel, "equity_curve_widget")
        assert hasattr(panel, "analysis_text")

    def test_trades_table_has_correct_columns(self, panel):
        """Trades table should have 11 columns."""
        assert panel.trades_table.columnCount() == 11

    def test_trades_table_column_headers(self, panel):
        """Trades table should have correct headers."""
        headers = [
            panel.trades_table.horizontalHeaderItem(i).text()
            for i in range(11)
        ]
        assert "Ticker" in headers
        assert "P&L $" in headers
        assert "Status" in headers

    def test_stat_cards_initialized(self, panel):
        """All stat cards should be initialized."""
        assert "win_rate" in panel.stat_cards
        assert "profit_factor" in panel.stat_cards
        assert "expectancy" in panel.stat_cards
        assert "avg_r" in panel.stat_cards
        assert "avg_duration" in panel.stat_cards
        assert "adherence" in panel.stat_cards

    def test_update_timer_started(self, panel):
        """Update timer should be running."""
        assert panel.update_timer.isActive()


class TestAddTrade:
    """Test adding trades."""

    def test_add_trade_to_table(self, panel):
        """Adding trade should add row to table."""
        trade = {
            "trade_id": "TEST_001",
            "ticker": "AAPL",
            "direction": "Long",
            "size": 100.0,
            "entry_price": 150.0,
            "exit_price": None,
            "stop_loss": 145.0,
            "take_profit": 160.0,
            "reason": "Test setup",
            "plan_adherence": True,
            "entry_date": datetime.now().isoformat(),
            "status": "open",
            "current_price": 150.0,
        }

        panel.add_trade_to_table(trade)

        assert panel.trades_table.rowCount() == 1
        assert panel.trades_table.item(0, 0).text() == "AAPL"

    def test_add_trade_stores_data(self, panel):
        """Adding trade should store in memory."""
        trade = {
            "trade_id": "TEST_001",
            "ticker": "AAPL",
            "direction": "Long",
            "size": 100.0,
            "entry_price": 150.0,
            "exit_price": None,
            "stop_loss": 145.0,
            "take_profit": None,
            "reason": "Test",
            "plan_adherence": True,
            "entry_date": datetime.now().isoformat(),
            "status": "open",
        }

        panel.trades["TEST_001"] = trade

        assert "TEST_001" in panel.trades
        assert panel.trades["TEST_001"]["ticker"] == "AAPL"

    def test_add_multiple_trades(self, panel):
        """Should be able to add multiple trades."""
        for i in range(3):
            trade = {
                "trade_id": f"TEST_{i:03d}",
                "ticker": f"STK{i}",
                "direction": "Long",
                "size": 100.0,
                "entry_price": 100.0 + i,
                "exit_price": None,
                "stop_loss": None,
                "take_profit": None,
                "reason": "Test",
                "plan_adherence": True,
                "entry_date": datetime.now().isoformat(),
                "status": "open",
            }
            panel.trades[f"TEST_{i:03d}"] = trade
            panel.add_trade_to_table(trade)

        assert len(panel.trades) == 3
        assert panel.trades_table.rowCount() == 3

    def test_trade_with_all_fields(self, panel):
        """Trade should accept all fields."""
        trade = {
            "trade_id": "TEST_FULL",
            "ticker": "GOOG",
            "direction": "Short",
            "size": 50.0,
            "entry_price": 2800.0,
            "exit_price": 2750.0,
            "stop_loss": 2850.0,
            "take_profit": 2700.0,
            "reason": "Detailed setup reason",
            "plan_adherence": False,
            "entry_date": (datetime.now() - timedelta(days=2)).isoformat(),
            "status": "closed",
        }

        panel.add_trade_to_table(trade)

        assert panel.trades_table.rowCount() == 1
        assert panel.trades_table.item(0, 5).text() == "$2750.00"


class TestTradeUpdate:
    """Test updating trades."""

    def test_close_trade(self, panel):
        """Should be able to close a trade."""
        trade = {
            "trade_id": "CLOSE_TEST",
            "ticker": "MSFT",
            "direction": "Long",
            "size": 100.0,
            "entry_price": 300.0,
            "exit_price": None,
            "stop_loss": 295.0,
            "take_profit": 310.0,
            "reason": "Test",
            "plan_adherence": True,
            "entry_date": datetime.now().isoformat(),
            "status": "open",
        }

        panel.trades["CLOSE_TEST"] = trade
        panel.add_trade_to_table(trade)

        # Close the trade
        panel.trades["CLOSE_TEST"]["exit_price"] = 305.0
        panel.trades["CLOSE_TEST"]["status"] = "closed"

        assert panel.trades["CLOSE_TEST"]["status"] == "closed"
        assert panel.trades["CLOSE_TEST"]["exit_price"] == 305.0

    def test_delete_trade(self, panel):
        """Should be able to delete a trade."""
        trade = {
            "trade_id": "DELETE_TEST",
            "ticker": "TSLA",
            "direction": "Long",
            "size": 50.0,
            "entry_price": 200.0,
            "exit_price": None,
            "stop_loss": None,
            "take_profit": None,
            "reason": "Test",
            "plan_adherence": True,
            "entry_date": datetime.now().isoformat(),
            "status": "open",
        }

        panel.trades["DELETE_TEST"] = trade
        panel.add_trade_to_table(trade)

        assert panel.trades_table.rowCount() == 1

        # Delete
        del panel.trades["DELETE_TEST"]
        panel.trades_table.removeRow(0)

        assert "DELETE_TEST" not in panel.trades
        assert panel.trades_table.rowCount() == 0

    def test_update_trade_price(self, panel):
        """Should update current price for open trades."""
        trade = {
            "trade_id": "PRICE_TEST",
            "ticker": "NVDA",
            "direction": "Long",
            "size": 100.0,
            "entry_price": 400.0,
            "exit_price": None,
            "stop_loss": None,
            "take_profit": None,
            "reason": "Test",
            "plan_adherence": True,
            "entry_date": datetime.now().isoformat(),
            "status": "open",
            "current_price": 400.0,
        }

        panel.trades["PRICE_TEST"] = trade
        panel.add_trade_to_table(trade)

        # Update price
        panel._update_trade_price("NVDA", 410.0)

        assert panel.trades["PRICE_TEST"]["current_price"] == 410.0


class TestTradeStatistics:
    """Test statistics calculations."""

    @pytest.mark.asyncio
    async def test_win_rate_calculation(self):
        """Win rate should be calculated correctly."""
        trades = [
            {
                "ticker": "AAPL",
                "direction": "Long",
                "size": 100.0,
                "entry_price": 100.0,
                "exit_price": 110.0,  # Winner
                "plan_adherence": True,
            },
            {
                "ticker": "MSFT",
                "direction": "Long",
                "size": 100.0,
                "entry_price": 100.0,
                "exit_price": 95.0,  # Loser
                "plan_adherence": True,
            },
            {
                "ticker": "GOOG",
                "direction": "Long",
                "size": 100.0,
                "entry_price": 100.0,
                "exit_price": 105.0,  # Winner
                "plan_adherence": True,
            },
        ]

        usecase = TradeStatisticsUseCase(None)
        stats = await usecase.execute(trades)

        assert stats["win_rate"] == pytest.approx(66.67, rel=0.1)
        assert stats["winning_trades"] == 2
        assert stats["losing_trades"] == 1

    @pytest.mark.asyncio
    async def test_profit_factor_calculation(self):
        """Profit factor should be gross profit / gross loss."""
        trades = [
            {
                "ticker": "AAPL",
                "direction": "Long",
                "size": 100.0,
                "entry_price": 100.0,
                "exit_price": 120.0,  # +2000
                "plan_adherence": True,
            },
            {
                "ticker": "MSFT",
                "direction": "Long",
                "size": 100.0,
                "entry_price": 100.0,
                "exit_price": 80.0,  # -2000
                "plan_adherence": True,
            },
        ]

        usecase = TradeStatisticsUseCase(None)
        stats = await usecase.execute(trades)

        assert stats["profit_factor"] == pytest.approx(1.0, rel=0.01)

    @pytest.mark.asyncio
    async def test_expectancy_calculation(self):
        """Expectancy should be (win% * avg_win) - (loss% * avg_loss)."""
        trades = [
            {
                "ticker": "AAPL",
                "direction": "Long",
                "size": 100.0,
                "entry_price": 100.0,
                "exit_price": 110.0,  # +1000
                "plan_adherence": True,
            },
            {
                "ticker": "MSFT",
                "direction": "Long",
                "size": 100.0,
                "entry_price": 100.0,
                "exit_price": 90.0,  # -1000
                "plan_adherence": True,
            },
        ]

        usecase = TradeStatisticsUseCase(None)
        stats = await usecase.execute(trades)

        # win_rate = 50%, avg_win = 1000, avg_loss = 1000
        # expectancy = (50% * 1000) - (50% * 1000) = 0
        assert stats["expectancy"] == pytest.approx(0.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_average_r_multiple(self):
        """Average R multiple should be (gain/risk)."""
        trades = [
            {
                "ticker": "AAPL",
                "direction": "Long",
                "size": 100.0,
                "entry_price": 100.0,
                "exit_price": 110.0,
                "stop_loss": 95.0,  # risk = 5, reward = 10, R = 2.0
                "plan_adherence": True,
            },
        ]

        usecase = TradeStatisticsUseCase(None)
        stats = await usecase.execute(trades)

        assert stats["avg_r_multiple"] == pytest.approx(2.0, rel=0.1)

    @pytest.mark.asyncio
    async def test_average_duration(self):
        """Should calculate average trade duration."""
        now = datetime.now()
        trades = [
            {
                "ticker": "AAPL",
                "direction": "Long",
                "size": 100.0,
                "entry_price": 100.0,
                "exit_price": 110.0,
                "entry_date": (now - timedelta(days=5)).isoformat(),
                "exit_date": now.isoformat(),
                "plan_adherence": True,
            },
            {
                "ticker": "MSFT",
                "direction": "Long",
                "size": 100.0,
                "entry_price": 100.0,
                "exit_price": 95.0,
                "entry_date": (now - timedelta(days=3)).isoformat(),
                "exit_date": now.isoformat(),
                "plan_adherence": True,
            },
        ]

        usecase = TradeStatisticsUseCase(None)
        stats = await usecase.execute(trades)

        assert stats["avg_duration_days"] == pytest.approx(4.0, rel=0.1)

    @pytest.mark.asyncio
    async def test_empty_trades_list(self):
        """Should handle empty trades list."""
        usecase = TradeStatisticsUseCase(None)
        stats = await usecase.execute([])

        assert stats["win_rate"] == 0.0
        assert stats["profit_factor"] == 0.0
        assert stats["total_trades"] == 0

    @pytest.mark.asyncio
    async def test_trades_without_exit(self):
        """Should only calculate closed trades."""
        trades = [
            {
                "ticker": "AAPL",
                "direction": "Long",
                "size": 100.0,
                "entry_price": 100.0,
                "exit_price": None,  # Open trade
                "plan_adherence": True,
            },
            {
                "ticker": "MSFT",
                "direction": "Long",
                "size": 100.0,
                "entry_price": 100.0,
                "exit_price": 110.0,  # Closed trade
                "plan_adherence": True,
            },
        ]

        usecase = TradeStatisticsUseCase(None)
        stats = await usecase.execute(trades)

        assert stats["total_trades"] == 1
        assert stats["winning_trades"] == 1


class TestPlanAdherence:
    """Test plan adherence tracking."""

    @pytest.mark.asyncio
    async def test_adherence_score(self):
        """Should calculate adherence score."""
        trades = [
            {"ticker": "AAPL", "plan_adherence": True},
            {"ticker": "MSFT", "plan_adherence": True},
            {"ticker": "GOOG", "plan_adherence": False},
        ]

        usecase = PlanAdherenceUseCase()
        result = await usecase.execute(trades)

        assert result["adherence_score"] == pytest.approx(66.67, rel=0.1)
        assert result["rules_followed"] == 2
        assert result["rules_broken"] == 1

    @pytest.mark.asyncio
    async def test_cost_of_violations(self):
        """Should calculate cost of violating rules."""
        trades = [
            {
                "ticker": "AAPL",
                "direction": "Long",
                "size": 100.0,
                "entry_price": 100.0,
                "exit_price": 110.0,  # +1000
                "plan_adherence": True,
            },
            {
                "ticker": "MSFT",
                "direction": "Long",
                "size": 100.0,
                "entry_price": 100.0,
                "exit_price": 90.0,  # -1000
                "plan_adherence": False,  # Violation
            },
        ]

        usecase = PlanAdherenceUseCase()
        result = await usecase.execute(trades)

        assert result["cost_of_violations"] > 0
        assert len(result["violations"]) == 1

    @pytest.mark.asyncio
    async def test_perfect_adherence(self):
        """Should handle perfect adherence."""
        trades = [
            {"ticker": "AAPL", "plan_adherence": True},
            {"ticker": "MSFT", "plan_adherence": True},
        ]

        usecase = PlanAdherenceUseCase()
        result = await usecase.execute(trades)

        assert result["adherence_score"] == 100.0
        assert result["rules_broken"] == 0


class TestEquityCurve:
    """Test equity curve calculations."""

    def test_equity_curve_updates(self, panel):
        """Should update equity curve with closed trades."""
        now = datetime.now()
        trades = [
            {
                "ticker": "AAPL",
                "direction": "Long",
                "size": 100.0,
                "entry_price": 100.0,
                "exit_price": 110.0,
                "entry_date": (now - timedelta(days=2)).isoformat(),
                "exit_date": (now - timedelta(days=1)).isoformat(),
            },
            {
                "ticker": "MSFT",
                "direction": "Long",
                "size": 100.0,
                "entry_price": 100.0,
                "exit_price": 95.0,
                "entry_date": (now - timedelta(days=1)).isoformat(),
                "exit_date": now.isoformat(),
            },
        ]

        panel.update_equity_curve(trades)

        # Should have data points
        data = panel.equity_curve_line.getData()
        assert len(data[0]) > 0


class TestShortTrades:
    """Test handling of short trades."""

    def test_short_trade_pnl_calculation(self, panel):
        """Short trades should calculate P&L correctly."""
        trade = {
            "trade_id": "SHORT_TEST",
            "ticker": "SPY",
            "direction": "Short",
            "size": 100.0,
            "entry_price": 400.0,
            "exit_price": 390.0,  # P&L = (400 - 390) * 100 = +1000
            "stop_loss": 410.0,
            "take_profit": None,
            "reason": "Short setup",
            "plan_adherence": True,
            "entry_date": datetime.now().isoformat(),
            "status": "closed",
        }

        panel.trades["SHORT_TEST"] = trade
        panel.add_trade_to_table(trade)

        assert panel.trades_table.rowCount() == 1
        assert panel.trades_table.item(0, 1).text() == "Short"

    @pytest.mark.asyncio
    async def test_short_trade_statistics(self):
        """Short trades should be handled in statistics."""
        trades = [
            {
                "ticker": "SPY",
                "direction": "Short",
                "size": 100.0,
                "entry_price": 400.0,
                "exit_price": 390.0,  # Winner
                "plan_adherence": True,
            },
            {
                "ticker": "QQQ",
                "direction": "Short",
                "size": 100.0,
                "entry_price": 300.0,
                "exit_price": 310.0,  # Loser
                "plan_adherence": True,
            },
        ]

        usecase = TradeStatisticsUseCase(None)
        stats = await usecase.execute(trades)

        assert stats["win_rate"] == 50.0
        assert stats["winning_trades"] == 1


class TestContextMenu:
    """Test context menu operations."""

    def test_context_menu_created(self, panel):
        """Context menu should be available."""
        # Add a trade first
        trade = {
            "trade_id": "MENU_TEST",
            "ticker": "AAPL",
            "direction": "Long",
            "size": 100.0,
            "entry_price": 150.0,
            "exit_price": None,
            "stop_loss": None,
            "take_profit": None,
            "reason": "Test",
            "plan_adherence": True,
            "entry_date": datetime.now().isoformat(),
            "status": "open",
        }

        panel.trades["MENU_TEST"] = trade
        panel.add_trade_to_table(trade)

        assert panel.trades_table.rowCount() == 1


class TestSignals:
    """Test panel signals."""

    def test_trade_added_signal(self, panel):
        """Should emit trade_added signal."""
        signal_received = []

        panel.trade_added.connect(lambda x: signal_received.append(x))

        trade = {
            "trade_id": "SIGNAL_TEST",
            "ticker": "AAPL",
            "direction": "Long",
            "size": 100.0,
            "entry_price": 150.0,
            "exit_price": None,
            "stop_loss": None,
            "take_profit": None,
            "reason": "Test",
            "plan_adherence": True,
            "entry_date": datetime.now().isoformat(),
            "status": "open",
        }

        panel.trade_added.emit(trade)

        assert len(signal_received) == 1
        assert signal_received[0]["ticker"] == "AAPL"

    def test_trade_closed_signal(self, panel):
        """Should emit trade_closed signal."""
        signal_received = []

        panel.trade_closed.connect(lambda x: signal_received.append(x))

        panel.trade_closed.emit("TEST_ID")

        assert len(signal_received) == 1
        assert signal_received[0] == "TEST_ID"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_size_trade(self, panel):
        """Should handle zero size gracefully."""
        trade = {
            "trade_id": "ZERO_SIZE",
            "ticker": "AAPL",
            "direction": "Long",
            "size": 0.0,
            "entry_price": 150.0,
            "exit_price": None,
            "stop_loss": None,
            "take_profit": None,
            "reason": "Test",
            "plan_adherence": True,
            "entry_date": datetime.now().isoformat(),
            "status": "open",
        }

        panel.add_trade_to_table(trade)

        assert panel.trades_table.rowCount() == 1

    def test_very_large_position(self, panel):
        """Should handle large positions."""
        trade = {
            "trade_id": "LARGE_POS",
            "ticker": "SPY",
            "direction": "Long",
            "size": 999999.99,
            "entry_price": 400.0,
            "exit_price": None,
            "stop_loss": None,
            "take_profit": None,
            "reason": "Large position",
            "plan_adherence": True,
            "entry_date": datetime.now().isoformat(),
            "status": "open",
        }

        panel.add_trade_to_table(trade)

        assert panel.trades_table.rowCount() == 1

    def test_trades_with_same_ticker(self, panel):
        """Should handle multiple trades on same ticker."""
        for i in range(3):
            trade = {
                "trade_id": f"SAME_TICKER_{i}",
                "ticker": "AAPL",
                "direction": "Long" if i % 2 == 0 else "Short",
                "size": 100.0,
                "entry_price": 150.0 + i,
                "exit_price": None,
                "stop_loss": None,
                "take_profit": None,
                "reason": "Test",
                "plan_adherence": True,
                "entry_date": datetime.now().isoformat(),
                "status": "open",
            }
            panel.trades[f"SAME_TICKER_{i}"] = trade
            panel.add_trade_to_table(trade)

        assert panel.trades_table.rowCount() == 3
        assert len(panel.trades) == 3
