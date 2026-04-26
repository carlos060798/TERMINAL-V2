"""
Tests for forecast engine - Prophet EPS/Revenue + LSTM momentum.

Test Coverage:
- EPS Forecaster: 8+ test cases
- Revenue Forecaster: 4+ test cases
- LSTM Momentum: 5+ test cases
- Model serialization: 2+ test cases
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
import torch
from datetime import datetime, timedelta
from pathlib import Path

from quantum_terminal.infrastructure.ml.forecast_engine import (
    EPSForecaster,
    MomentumSignalGenerator,
    ForecastResult,
    MomentumSignal,
    MomentumLSTM,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def eps_historical_data():
    """Generate mock historical EPS data (10 years quarterly)."""
    dates = pd.date_range(end=datetime.now(), periods=40, freq='Q')
    # Simulate EPS with trend and seasonality
    trend = np.linspace(1.0, 3.0, 40)
    seasonality = 0.2 * np.sin(np.arange(40) * 2 * np.pi / 4)
    noise = np.random.normal(0, 0.1, 40)
    eps = trend + seasonality + noise
    eps = np.abs(eps)  # Ensure positive

    return pd.DataFrame({
        'date': dates,
        'eps': eps
    })


@pytest.fixture
def revenue_historical_data():
    """Generate mock historical revenue data."""
    dates = pd.date_range(end=datetime.now(), periods=40, freq='Q')
    # Simulate revenue with growth and seasonality
    trend = np.linspace(10000, 50000, 40)
    seasonality = 5000 * np.sin(np.arange(40) * 2 * np.pi / 4)
    noise = np.random.normal(0, 500, 40)
    revenue = trend + seasonality + noise
    revenue = np.abs(revenue)

    return pd.DataFrame({
        'date': dates,
        'revenue': revenue
    })


@pytest.fixture
def price_historical_data():
    """Generate mock 60-day price data."""
    dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
    base_price = 150.0
    prices = base_price + np.cumsum(np.random.normal(0.5, 2, 60))

    return pd.DataFrame({
        'date': dates,
        'open': prices + np.random.normal(0, 1, 60),
        'high': prices + np.abs(np.random.normal(0, 1.5, 60)),
        'low': prices - np.abs(np.random.normal(0, 1.5, 60)),
        'close': prices,
        'volume': np.random.normal(10000000, 2000000, 60)
    })


@pytest.fixture
def short_eps_data():
    """Generate insufficient EPS data (only 5 quarters)."""
    dates = pd.date_range(end=datetime.now(), periods=5, freq='Q')
    eps = np.random.normal(2.0, 0.3, 5)
    eps = np.abs(eps)

    return pd.DataFrame({
        'date': dates,
        'eps': eps
    })


# ============================================================================
# EPSForecaster Tests
# ============================================================================

class TestEPSForecaster:
    """Tests for EPS/Revenue Prophet forecasting."""

    def test_eps_forecaster_initialization(self):
        """Test EPSForecaster initializes without error."""
        forecaster = EPSForecaster()
        assert forecaster is not None
        assert isinstance(forecaster.models, dict)
        assert isinstance(forecaster.scalers, dict)

    @pytest.mark.asyncio
    async def test_forecast_eps_basic(self, eps_historical_data):
        """Test basic EPS forecast generation."""
        forecaster = EPSForecaster()

        result = await forecaster.forecast_eps(
            ticker='AAPL',
            historical_data=eps_historical_data,
            periods=8
        )

        assert isinstance(result, ForecastResult)
        assert result.ticker == 'AAPL'
        assert result.metric == 'eps'
        assert len(result.forecast_dates) == 8
        assert len(result.forecast_values) == 8
        assert len(result.lower_bounds_80) == 8
        assert len(result.upper_bounds_80) == 8

    @pytest.mark.asyncio
    async def test_forecast_eps_periods_variation(self, eps_historical_data):
        """Test EPS forecast with different period counts."""
        forecaster = EPSForecaster()

        for periods in [4, 6, 8, 12]:
            result = await forecaster.forecast_eps(
                ticker='MSFT',
                historical_data=eps_historical_data,
                periods=periods
            )

            assert len(result.forecast_dates) == periods
            assert len(result.forecast_values) == periods

    @pytest.mark.asyncio
    async def test_forecast_eps_confidence_intervals(self, eps_historical_data):
        """Test that confidence intervals are properly ordered."""
        forecaster = EPSForecaster()

        result = await forecaster.forecast_eps(
            ticker='GOOG',
            historical_data=eps_historical_data,
            periods=8
        )

        # 95% intervals should be wider than 80%
        for i in range(len(result.forecast_dates)):
            width_95 = result.upper_bounds_95[i] - result.lower_bounds_95[i]
            width_80 = result.upper_bounds_80[i] - result.lower_bounds_80[i]
            assert width_95 > width_80

            # All bounds should be positive
            assert result.lower_bounds_80[i] >= 0
            assert result.upper_bounds_80[i] >= 0

    @pytest.mark.asyncio
    async def test_forecast_eps_insufficient_data(self, short_eps_data):
        """Test EPS forecast raises error with insufficient data."""
        forecaster = EPSForecaster()

        with pytest.raises(ValueError, match="at least 8 quarters"):
            await forecaster.forecast_eps(
                ticker='TEST',
                historical_data=short_eps_data,
                periods=4
            )

    @pytest.mark.asyncio
    async def test_forecast_eps_accuracy_metric(self, eps_historical_data):
        """Test that MAPE metric is calculated."""
        forecaster = EPSForecaster()

        result = await forecaster.forecast_eps(
            ticker='AAPL',
            historical_data=eps_historical_data,
            periods=8
        )

        assert result.mape is not None
        assert 0 <= result.mape <= 1000  # Should be a percentage
        assert result.rmse is None or result.rmse >= 0

    @pytest.mark.asyncio
    async def test_forecast_revenue_basic(self, revenue_historical_data):
        """Test basic revenue forecast generation."""
        forecaster = EPSForecaster()

        result = await forecaster.forecast_revenue(
            ticker='AAPL',
            historical_data=revenue_historical_data,
            periods=8
        )

        assert isinstance(result, ForecastResult)
        assert result.ticker == 'AAPL'
        assert result.metric == 'revenue'
        assert len(result.forecast_values) == 8

    @pytest.mark.asyncio
    async def test_forecast_revenue_insufficient_data(self, short_eps_data):
        """Test revenue forecast with insufficient data."""
        forecaster = EPSForecaster()

        with pytest.raises(ValueError):
            await forecaster.forecast_revenue(
                ticker='TEST',
                historical_data=short_eps_data,
                periods=4
            )

    def test_calculate_mape(self):
        """Test MAPE calculation."""
        forecaster = EPSForecaster()

        actual = np.array([10, 20, 30, 40])
        predicted = np.array([12, 18, 32, 38])

        mape = forecaster._calculate_mape(actual, predicted)

        # Expected: ((2+2+2+2)/4) / (10+20+30+40)/4 * 100
        expected = 8.33  # Approximate
        assert abs(mape - expected) < 1

    def test_calculate_mape_with_zero(self):
        """Test MAPE handles zero values."""
        forecaster = EPSForecaster()

        actual = np.array([0, 10, 20])
        predicted = np.array([1, 11, 21])

        mape = forecaster._calculate_mape(actual, predicted)

        # Should not crash and return reasonable value
        assert isinstance(mape, float)
        assert mape >= 0


# ============================================================================
# MomentumLSTM Tests
# ============================================================================

class TestMomentumLSTM:
    """Tests for LSTM neural network architecture."""

    def test_lstm_initialization(self):
        """Test LSTM model initializes correctly."""
        model = MomentumLSTM(input_size=7, hidden_size=64)

        assert isinstance(model, torch.nn.Module)
        assert hasattr(model, 'lstm1')
        assert hasattr(model, 'lstm2')
        assert hasattr(model, 'dense')
        assert hasattr(model, 'output')

    def test_lstm_forward_pass(self):
        """Test LSTM forward pass with correct shapes."""
        model = MomentumLSTM()
        model.eval()

        # Input: batch_size=2, seq_len=60, features=7
        x = torch.randn(2, 60, 7)
        with torch.no_grad():
            output = model(x)

        # Output should be (2, 1) with values in [0, 1]
        assert output.shape == (2, 1)
        assert torch.all(output >= 0)
        assert torch.all(output <= 1)

    def test_lstm_output_range(self):
        """Test LSTM output is properly bounded [0, 1]."""
        model = MomentumLSTM()
        model.eval()

        for _ in range(10):
            x = torch.randn(4, 60, 7)
            with torch.no_grad():
                output = model(x)

            assert torch.all(output >= 0)
            assert torch.all(output <= 1)

    def test_lstm_different_batch_sizes(self):
        """Test LSTM handles various batch sizes."""
        model = MomentumLSTM()
        model.eval()

        for batch_size in [1, 2, 8, 16]:
            x = torch.randn(batch_size, 60, 7)
            with torch.no_grad():
                output = model(x)

            assert output.shape == (batch_size, 1)


# ============================================================================
# MomentumSignalGenerator Tests
# ============================================================================

class TestMomentumSignalGenerator:
    """Tests for LSTM-based momentum signal generation."""

    def test_momentum_generator_initialization(self):
        """Test MomentumSignalGenerator initializes."""
        generator = MomentumSignalGenerator()

        assert generator is not None
        assert hasattr(generator, 'model')
        assert hasattr(generator, 'device')
        assert generator.model.training == False

    @pytest.mark.asyncio
    async def test_generate_signal_basic(self, price_historical_data):
        """Test basic momentum signal generation."""
        generator = MomentumSignalGenerator()

        signal = await generator.generate_signal(
            ticker='AAPL',
            price_data=price_historical_data
        )

        assert isinstance(signal, MomentumSignal)
        assert signal.ticker == 'AAPL'
        assert signal.signal in ['BUY', 'HOLD', 'SELL']
        assert 0 <= signal.probability <= 1
        assert signal.rsi > 0
        assert signal.sma_20 > 0
        assert signal.sma_50 > 0

    @pytest.mark.asyncio
    async def test_generate_signal_insufficient_data(self):
        """Test signal generation fails with insufficient data."""
        generator = MomentumSignalGenerator()

        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        prices = np.random.normal(150, 20, 30)

        price_data = pd.DataFrame({
            'date': dates,
            'open': prices,
            'high': prices + 2,
            'low': prices - 2,
            'close': prices,
            'volume': np.random.normal(10000000, 2000000, 30)
        })

        with pytest.raises(ValueError, match="at least 60 days"):
            await generator.generate_signal('TEST', price_data)

    @pytest.mark.asyncio
    async def test_generate_signal_uptrend(self):
        """Test signal generation with uptrend."""
        generator = MomentumSignalGenerator()

        # Create uptrend data
        dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
        prices = np.linspace(100, 150, 60)  # Clear uptrend
        prices += np.random.normal(0, 1, 60)  # Add small noise

        price_data = pd.DataFrame({
            'date': dates,
            'open': prices - 0.5,
            'high': prices + 1,
            'low': prices - 1,
            'close': prices,
            'volume': np.random.normal(10000000, 2000000, 60)
        })

        signal = await generator.generate_signal('TEST', price_data)

        # Should be more likely to generate BUY in uptrend
        assert signal.rsi > 40  # Should not be oversold
        assert signal.probability > 0.3

    @pytest.mark.asyncio
    async def test_generate_signal_downtrend(self):
        """Test signal generation with downtrend."""
        generator = MomentumSignalGenerator()

        # Create downtrend data
        dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
        prices = np.linspace(150, 100, 60)  # Clear downtrend
        prices += np.random.normal(0, 1, 60)

        price_data = pd.DataFrame({
            'date': dates,
            'open': prices + 0.5,
            'high': prices + 1,
            'low': prices - 1,
            'close': prices,
            'volume': np.random.normal(10000000, 2000000, 60)
        })

        signal = await generator.generate_signal('TEST', price_data)

        # Should be more likely to generate SELL in downtrend
        assert signal.rsi < 60  # Should not be overbought
        assert signal.probability > 0.2

    def test_calculate_rsi(self):
        """Test RSI calculation."""
        generator = MomentumSignalGenerator()

        # Uptrend: all increases
        prices = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109])
        rsi = generator._calculate_rsi(prices, period=5)
        assert rsi == 100.0  # Perfect uptrend

        # Downtrend: all decreases
        prices = np.array([100, 99, 98, 97, 96, 95, 94, 93, 92, 91])
        rsi = generator._calculate_rsi(prices, period=5)
        assert rsi == 0.0  # Perfect downtrend

        # Neutral: mixed
        prices = np.array([100, 101, 100, 101, 100, 101, 100, 101, 100, 101])
        rsi = generator._calculate_rsi(prices, period=5)
        assert 40 < rsi < 60  # Should be neutral

    def test_calculate_macd(self):
        """Test MACD calculation."""
        generator = MomentumSignalGenerator()

        # Uptrend should have positive MACD
        prices = np.linspace(100, 150, 50)
        macd = generator._calculate_macd(prices)
        assert macd > 0  # Positive in uptrend

        # Downtrend should have negative MACD
        prices = np.linspace(150, 100, 50)
        macd = generator._calculate_macd(prices)
        assert macd < 0  # Negative in downtrend

    def test_prepare_lstm_features(self):
        """Test feature preparation for LSTM."""
        generator = MomentumSignalGenerator()

        dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
        prices = np.random.normal(150, 20, 60)

        price_data = pd.DataFrame({
            'date': dates,
            'open': prices,
            'high': prices + 2,
            'low': prices - 2,
            'close': prices,
            'volume': np.random.normal(10000000, 2000000, 60)
        })

        features = generator._prepare_lstm_features(price_data)

        # Should return (60, 7) array
        assert features.shape == (60, 7)
        assert features.dtype == np.float32
        # All values should be in reasonable range
        assert np.all(features >= -2)
        assert np.all(features <= 2)


# ============================================================================
# ForecastResult Tests
# ============================================================================

class TestForecastResult:
    """Tests for ForecastResult data class."""

    def test_forecast_result_creation(self):
        """Test ForecastResult initialization."""
        dates = pd.date_range(end=datetime.now(), periods=8, freq='Q')
        values = [2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7]

        result = ForecastResult(
            ticker='AAPL',
            metric='eps',
            forecast_dates=list(dates),
            forecast_values=values,
            lower_bounds_80=[v * 0.9 for v in values],
            upper_bounds_80=[v * 1.1 for v in values],
            lower_bounds_95=[v * 0.8 for v in values],
            upper_bounds_95=[v * 1.2 for v in values],
            mape=5.5
        )

        assert result.ticker == 'AAPL'
        assert result.metric == 'eps'
        assert result.mape == 5.5
        assert result.generated_at is not None

    def test_forecast_result_to_dict(self):
        """Test ForecastResult JSON serialization."""
        dates = pd.date_range(end=datetime.now(), periods=2, freq='Q')
        result = ForecastResult(
            ticker='MSFT',
            metric='revenue',
            forecast_dates=list(dates),
            forecast_values=[50000, 55000],
            lower_bounds_80=[45000, 50000],
            upper_bounds_80=[55000, 60000],
            lower_bounds_95=[40000, 45000],
            upper_bounds_95=[60000, 65000],
            mape=3.2
        )

        result_dict = result.to_dict()

        assert result_dict['ticker'] == 'MSFT'
        assert result_dict['metric'] == 'revenue'
        assert len(result_dict['forecast_dates']) == 2
        assert isinstance(result_dict['generated_at'], str)


# ============================================================================
# MomentumSignal Tests
# ============================================================================

class TestMomentumSignal:
    """Tests for MomentumSignal data class."""

    def test_momentum_signal_creation(self):
        """Test MomentumSignal initialization."""
        signal = MomentumSignal(
            ticker='AAPL',
            signal='BUY',
            probability=0.75,
            rsi=65.5,
            macd=0.05,
            sma_20=155.2,
            sma_50=153.1,
            current_price=157.5,
            trend_strength=0.8
        )

        assert signal.ticker == 'AAPL'
        assert signal.signal == 'BUY'
        assert signal.probability == 0.75
        assert signal.generated_at is not None

    def test_momentum_signal_to_dict(self):
        """Test MomentumSignal JSON serialization."""
        signal = MomentumSignal(
            ticker='GOOG',
            signal='SELL',
            probability=0.42,
            rsi=35.0,
            macd=-0.03,
            sma_20=2800.0,
            sma_50=2850.0,
            current_price=2780.0,
            trend_strength=0.6
        )

        signal_dict = signal.to_dict()

        assert signal_dict['ticker'] == 'GOOG'
        assert signal_dict['signal'] == 'SELL'
        assert signal_dict['probability'] == 0.42
        assert isinstance(signal_dict['generated_at'], str)
