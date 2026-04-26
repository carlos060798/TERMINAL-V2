"""
Tests for Backtesting Panel module.

Tests cover:
- Configuration validation
- Signal generation (SMA, RSI, MACD, Graham Net-Net, Multi-factor)
- Backtest execution with vectorbt
- Metrics calculation (CAGR, Sharpe, Sortino, Max DD, Win Rate, Profit Factor)
- Visualization updates
- Error handling

pytest tests/test_backtest_panel.py -v
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import pandas as pd
import numpy as np
import warnings

from PyQt6.QtCore import QDate

from quantum_terminal.ui.panels.backtest_panel import (
    StrategyType, BacktestConfig, BacktestResults, BacktestWorker, BacktestPanel
)

# Suppress warnings
warnings.filterwarnings("ignore")


class TestStrategyType:
    """Test strategy enum."""

    def test_strategy_types_exist(self):
        """Test that all strategies are defined."""
        strategies = list(StrategyType)
        assert len(strategies) == 5
        assert StrategyType.SMA_CROSSOVER in strategies
        assert StrategyType.RSI_MEAN_REVERSION in strategies
        assert StrategyType.MACD_MOMENTUM in strategies
        assert StrategyType.GRAHAM_NET_NET in strategies
        assert StrategyType.MULTI_FACTOR in strategies

    def test_strategy_values(self):
        """Test strategy display names."""
        assert StrategyType.SMA_CROSSOVER.value == "SMA Crossover"
        assert StrategyType.RSI_MEAN_REVERSION.value == "RSI Mean Reversion"


class TestBacktestConfig:
    """Test configuration dataclass."""

    def test_config_creation(self):
        """Test creating a valid config."""
        config = BacktestConfig(
            strategy=StrategyType.SMA_CROSSOVER,
            tickers=["AAPL", "MSFT"],
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2024, 1, 1),
            initial_capital=100000,
            position_size_pct=10
        )
        assert config.strategy == StrategyType.SMA_CROSSOVER
        assert config.tickers == ["AAPL", "MSFT"]
        assert config.initial_capital == 100000
        assert config.position_size_pct == 10

    def test_config_defaults(self):
        """Test config default values."""
        config = BacktestConfig(
            strategy=StrategyType.SMA_CROSSOVER,
            tickers=["AAPL"],
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2024, 1, 1),
            initial_capital=100000,
            position_size_pct=10
        )
        assert config.slippage_pct == 0.01
        assert config.commission == 0.0
        assert config.sma_fast == 20
        assert config.sma_slow == 50
        assert config.rsi_period == 14


class TestBacktestResults:
    """Test results dataclass."""

    def test_results_creation(self):
        """Test creating backtest results."""
        mock_portfolio = Mock()
        mock_trades = pd.DataFrame()
        equity = pd.Series([100000, 101000, 102000])
        daily_returns = pd.Series([0.01, 0.0099])
        benchmark = pd.Series([0.005, 0.006])

        results = BacktestResults(
            strategy=StrategyType.SMA_CROSSOVER,
            portfolio=mock_portfolio,
            trades=mock_trades,
            equity_curve=equity,
            daily_returns=daily_returns,
            benchmark_returns=benchmark,
            total_return=0.02,
            cagr=0.15,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            max_drawdown=-0.05,
            win_rate=0.65,
            profit_factor=2.5,
            num_trades=50,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2024, 1, 1),
            duration_days=365
        )
        assert results.cagr == 0.15
        assert results.sharpe_ratio == 1.5
        assert results.win_rate == 0.65


class TestBacktestWorker:
    """Test worker thread functionality."""

    def test_worker_creation(self):
        """Test creating a backtest worker."""
        config = BacktestConfig(
            strategy=StrategyType.SMA_CROSSOVER,
            tickers=["AAPL"],
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2024, 1, 1),
            initial_capital=100000,
            position_size_pct=10
        )
        worker = BacktestWorker(config)
        assert worker.config == config

    def test_calculate_rsi(self):
        """Test RSI calculation."""
        # Create sample price data
        prices = pd.DataFrame(np.sin(np.arange(100)) * 10 + 100)
        rsi = BacktestWorker._calculate_rsi(prices, 14)
        assert len(rsi) == len(prices)
        assert rsi.max() <= 100
        assert rsi.min() >= 0

    def test_calculate_macd(self):
        """Test MACD calculation."""
        prices = pd.DataFrame(np.linspace(100, 150, 100))
        macd, signal, histogram = BacktestWorker._calculate_macd(prices, 12, 26, 9)
        assert len(macd) == len(prices)
        assert len(signal) == len(prices)
        assert len(histogram) == len(prices)

    def test_calculate_cagr(self):
        """Test CAGR calculation."""
        cagr = BacktestWorker._calculate_cagr(100000, 150000, 1)
        assert 0.4 < cagr < 0.6  # Should be around 50%

        cagr = BacktestWorker._calculate_cagr(100000, 100000, 1)
        assert cagr == 0  # No growth

    def test_calculate_sharpe(self):
        """Test Sharpe ratio calculation."""
        returns = pd.Series(np.random.randn(252) * 0.01 + 0.0005)
        sharpe = BacktestWorker._calculate_sharpe(returns)
        assert isinstance(sharpe, float)
        assert -10 < sharpe < 10

    def test_calculate_sortino(self):
        """Test Sortino ratio calculation."""
        returns = pd.Series(np.random.randn(252) * 0.01 + 0.0005)
        sortino = BacktestWorker._calculate_sortino(returns)
        assert isinstance(sortino, float)
        assert -10 < sortino < 10

    def test_calculate_max_drawdown(self):
        """Test maximum drawdown calculation."""
        equity = pd.Series([100, 110, 105, 95, 100, 120])
        max_dd = BacktestWorker._calculate_max_drawdown(equity)
        assert max_dd < 0  # Drawdown is negative
        assert -0.15 < max_dd < 0  # Around -13.6%

    def test_calculate_profit_factor(self):
        """Test profit factor calculation."""
        trades = pd.DataFrame({
            'profit': [100, 50, -30, -20, 150]
        })
        pf = BacktestWorker._calculate_profit_factor(trades)
        # Profits: 100 + 50 + 150 = 300
        # Losses: 30 + 20 = 50
        # PF = 300 / 50 = 6.0
        assert abs(pf - 6.0) < 0.01

    def test_calculate_profit_factor_no_losses(self):
        """Test profit factor with no losses."""
        trades = pd.DataFrame({
            'profit': [100, 50, 150]
        })
        pf = BacktestWorker._calculate_profit_factor(trades)
        assert pf == float('inf')

    def test_calculate_profit_factor_no_profits(self):
        """Test profit factor with no profits."""
        trades = pd.DataFrame({
            'profit': [-100, -50]
        })
        pf = BacktestWorker._calculate_profit_factor(trades)
        assert pf == 0.0

    def test_extract_trades_empty(self):
        """Test extracting trades from empty portfolio."""
        trades = BacktestWorker._extract_trades(Mock())
        assert isinstance(trades, pd.DataFrame)

    def test_sma_crossover_signals(self):
        """Test SMA crossover signal generation."""
        close = pd.DataFrame(np.linspace(100, 120, 100))
        config = BacktestConfig(
            strategy=StrategyType.SMA_CROSSOVER,
            tickers=["TEST"],
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=100000,
            position_size_pct=10,
            sma_fast=10,
            sma_slow=20
        )
        worker = BacktestWorker(config)
        entries, exits = worker._sma_crossover_signals(close)
        assert len(entries) == len(close)
        assert len(exits) == len(close)
        assert entries.isnull().sum() > 0  # Some NaN values from rolling

    def test_rsi_signals(self):
        """Test RSI mean reversion signals."""
        close = pd.DataFrame(np.sin(np.arange(100)) * 10 + 100)
        config = BacktestConfig(
            strategy=StrategyType.RSI_MEAN_REVERSION,
            tickers=["TEST"],
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=100000,
            position_size_pct=10,
            rsi_period=14,
            rsi_oversold=30,
            rsi_overbought=70
        )
        worker = BacktestWorker(config)
        entries, exits = worker._rsi_signals(close)
        assert len(entries) == len(close)
        assert len(exits) == len(close)

    def test_macd_signals(self):
        """Test MACD momentum signals."""
        close = pd.DataFrame(np.linspace(100, 130, 100))
        config = BacktestConfig(
            strategy=StrategyType.MACD_MOMENTUM,
            tickers=["TEST"],
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=100000,
            position_size_pct=10,
            macd_fast=12,
            macd_slow=26,
            macd_signal=9
        )
        worker = BacktestWorker(config)
        entries, exits = worker._macd_signals(close)
        assert len(entries) == len(close)
        assert len(exits) == len(close)

    def test_graham_net_net_signals(self):
        """Test Graham Net-Net signals."""
        close = pd.DataFrame(np.linspace(100, 110, 100))
        config = BacktestConfig(
            strategy=StrategyType.GRAHAM_NET_NET,
            tickers=["TEST"],
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=100000,
            position_size_pct=10
        )
        worker = BacktestWorker(config)
        entries, exits = worker._graham_net_net_signals(close)
        assert len(entries) == len(close)
        assert len(exits) == len(close)

    def test_multi_factor_signals(self):
        """Test multi-factor signals."""
        close = pd.DataFrame(np.linspace(100, 120, 100))
        config = BacktestConfig(
            strategy=StrategyType.MULTI_FACTOR,
            tickers=["TEST"],
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=100000,
            position_size_pct=10,
            sma_fast=10,
            sma_slow=20,
            rsi_period=14
        )
        worker = BacktestWorker(config)
        entries, exits = worker._multi_factor_signals(close)
        assert len(entries) == len(close)
        assert len(exits) == len(close)


class TestBacktestPanel:
    """Test the PyQt6 panel itself."""

    @pytest.fixture
    def panel(self, qapp):
        """Fixture to create a backtest panel."""
        return BacktestPanel()

    def test_panel_creation(self, panel):
        """Test panel initialization."""
        assert panel.current_results is None
        assert panel.backtest_worker is None

    def test_panel_strategy_combo(self, panel):
        """Test strategy dropdown has all strategies."""
        combo_count = panel.strategy_combo.count()
        assert combo_count == 5

    def test_panel_tickers_input(self, panel):
        """Test tickers input field."""
        assert panel.tickers_input.text() == "AAPL,MSFT"

    def test_panel_initial_capital(self, panel):
        """Test initial capital default."""
        assert panel.initial_capital.value() == 100000

    def test_panel_position_size(self, panel):
        """Test position size default."""
        assert panel.position_size_pct.value() == 10

    def test_panel_slippage(self, panel):
        """Test slippage default."""
        assert panel.slippage_pct.value() == 0.01

    def test_panel_commission(self, panel):
        """Test commission default."""
        assert panel.commission.value() == 5

    def test_panel_sma_fast(self, panel):
        """Test SMA fast parameter."""
        assert panel.sma_fast.value() == 20

    def test_panel_sma_slow(self, panel):
        """Test SMA slow parameter."""
        assert panel.sma_slow.value() == 50

    def test_panel_result_tabs(self, panel):
        """Test result tabs initialization."""
        assert panel.result_tabs.count() == 5
        assert panel.result_tabs.tabText(0) == "Equity Curve"
        assert panel.result_tabs.tabText(1) == "Metrics"
        assert panel.result_tabs.tabText(2) == "Trades"
        assert panel.result_tabs.tabText(3) == "Monte Carlo"
        assert panel.result_tabs.tabText(4) == "Returns Distribution"

    def test_panel_invalid_tickers_validation(self, panel, qapp):
        """Test validation of empty tickers."""
        panel.tickers_input.setText("")
        panel.on_run_backtest()
        # Should show warning, not crash

    def test_panel_strategy_changed_signal(self, panel):
        """Test strategy change signal."""
        signal_received = False

        def on_strategy_changed():
            nonlocal signal_received
            signal_received = True

        panel.strategy_combo.currentIndexChanged.connect(on_strategy_changed)
        panel.strategy_combo.setCurrentIndex(1)
        # Signal should be connected

    def test_panel_metrics_display(self, panel):
        """Test metrics display update."""
        mock_results = BacktestResults(
            strategy=StrategyType.SMA_CROSSOVER,
            portfolio=Mock(),
            trades=pd.DataFrame(),
            equity_curve=pd.Series([100000, 101000]),
            daily_returns=pd.Series([0.01, 0.0099]),
            benchmark_returns=pd.Series([0.005, 0.006]),
            total_return=0.02,
            cagr=0.15,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            max_drawdown=-0.05,
            win_rate=0.65,
            profit_factor=2.5,
            num_trades=50,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2024, 1, 1),
            duration_days=365
        )

        panel._update_metrics_display(mock_results)
        metrics_text = panel.metrics_text.toPlainText()
        assert "SMA Crossover" in metrics_text
        assert "15.00%" in metrics_text or "0.15" in metrics_text
        assert "1.50" in metrics_text

    def test_panel_equity_chart_update(self, panel):
        """Test equity chart visualization."""
        mock_results = BacktestResults(
            strategy=StrategyType.SMA_CROSSOVER,
            portfolio=Mock(),
            trades=pd.DataFrame(),
            equity_curve=pd.Series([100000, 101000, 102000],
                                 index=pd.date_range('2023-01-01', periods=3)),
            daily_returns=pd.Series([0.01, 0.0099]),
            benchmark_returns=pd.Series([0.005, 0.006]),
            total_return=0.02,
            cagr=0.15,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            max_drawdown=-0.05,
            win_rate=0.65,
            profit_factor=2.5,
            num_trades=50,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2024, 1, 1),
            duration_days=365
        )

        panel._update_equity_chart(mock_results)
        # Chart should not raise exception

    def test_panel_returns_distribution(self, panel):
        """Test returns distribution histogram."""
        mock_results = BacktestResults(
            strategy=StrategyType.SMA_CROSSOVER,
            portfolio=Mock(),
            trades=pd.DataFrame(),
            equity_curve=pd.Series([100000, 101000, 102000]),
            daily_returns=pd.Series(np.random.randn(252) * 0.01),
            benchmark_returns=pd.Series([0.005] * 251),
            total_return=0.02,
            cagr=0.15,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            max_drawdown=-0.05,
            win_rate=0.65,
            profit_factor=2.5,
            num_trades=50,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2024, 1, 1),
            duration_days=365
        )

        panel._update_returns_distribution(mock_results)
        # Should not raise exception

    def test_panel_monte_carlo(self, panel):
        """Test Monte Carlo simulation."""
        mock_results = BacktestResults(
            strategy=StrategyType.SMA_CROSSOVER,
            portfolio=Mock(),
            trades=pd.DataFrame(),
            equity_curve=pd.Series([100000, 101000, 102000] * 50),
            daily_returns=pd.Series(np.random.randn(150) * 0.01),
            benchmark_returns=pd.Series([0.005] * 150),
            total_return=0.02,
            cagr=0.15,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            max_drawdown=-0.05,
            win_rate=0.65,
            profit_factor=2.5,
            num_trades=50,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2024, 1, 1),
            duration_days=365
        )

        panel._update_monte_carlo(mock_results)
        # Should not raise exception
