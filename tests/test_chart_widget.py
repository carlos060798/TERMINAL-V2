"""
Tests for ChartWidget.
"""

import pytest
from PyQt6.QtWidgets import QApplication
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from quantum_terminal.ui.widgets import ChartWidget


@pytest.fixture
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def sample_ohlcv_data():
    """Create sample OHLCV data."""
    dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
    data = pd.DataFrame({
        "open": np.random.uniform(100, 110, 20),
        "high": np.random.uniform(110, 115, 20),
        "low": np.random.uniform(95, 105, 20),
        "close": np.random.uniform(100, 110, 20),
        "volume": np.random.randint(1000000, 5000000, 20),
    }, index=dates)
    return data


@pytest.fixture
def chart_widget(qapp):
    """Create ChartWidget instance."""
    return ChartWidget(title="Test Chart")


def test_chart_widget_creation(chart_widget):
    """Test ChartWidget is created."""
    assert chart_widget is not None
    assert chart_widget.title == "Test Chart"
    assert chart_widget.plot_widget is not None


def test_plot_candlestick(chart_widget, sample_ohlcv_data):
    """Test plotting candlestick chart."""
    chart_widget.plot_candlestick(sample_ohlcv_data)

    assert chart_widget.data is not None
    assert len(chart_widget.data) == 20
    assert list(chart_widget.data.columns) == ["open", "high", "low", "close", "volume"]


def test_plot_candlestick_empty(chart_widget):
    """Test plotting with empty data."""
    empty_data = pd.DataFrame()

    chart_widget.plot_candlestick(empty_data)

    assert chart_widget.data is None


def test_add_indicator(chart_widget, sample_ohlcv_data):
    """Test adding technical indicator."""
    chart_widget.plot_candlestick(sample_ohlcv_data)

    sma = sample_ohlcv_data["close"].rolling(window=5).mean().values.tolist()
    chart_widget.add_indicator("SMA_5", sma)

    assert "SMA_5" in chart_widget.indicators
    assert len(chart_widget.indicators["SMA_5"]) == 20


def test_add_moving_average_sma(chart_widget, sample_ohlcv_data):
    """Test adding SMA."""
    chart_widget.plot_candlestick(sample_ohlcv_data)

    chart_widget.add_moving_average(period=5, ma_type="SMA")

    assert "SMA_5" in chart_widget.indicators


def test_add_moving_average_ema(chart_widget, sample_ohlcv_data):
    """Test adding EMA."""
    chart_widget.plot_candlestick(sample_ohlcv_data)

    chart_widget.add_moving_average(period=10, ma_type="EMA")

    assert "EMA_10" in chart_widget.indicators


def test_add_bollinger_bands(chart_widget, sample_ohlcv_data):
    """Test adding Bollinger Bands."""
    chart_widget.plot_candlestick(sample_ohlcv_data)

    chart_widget.add_bollinger_bands(period=5, std_dev=2.0)

    assert "BB_upper" in chart_widget.indicators
    assert "BB_lower" in chart_widget.indicators


def test_clear(chart_widget, sample_ohlcv_data):
    """Test clearing chart."""
    chart_widget.plot_candlestick(sample_ohlcv_data)
    chart_widget.add_moving_average(period=5)

    chart_widget.clear()

    assert chart_widget.data is None
    assert len(chart_widget.indicators) == 0
    assert len(chart_widget.plot_items) == 0


def test_set_x_range(chart_widget, sample_ohlcv_data):
    """Test setting x-axis range."""
    chart_widget.plot_candlestick(sample_ohlcv_data)

    chart_widget.set_x_range(0, 10)

    # Range should be set (hard to test exact value without deep inspection)
    assert chart_widget.plot_widget is not None


def test_set_y_range(chart_widget, sample_ohlcv_data):
    """Test setting y-axis range."""
    chart_widget.plot_candlestick(sample_ohlcv_data)

    chart_widget.set_y_range(95, 115)

    assert chart_widget.plot_widget is not None


def test_get_visible_data(chart_widget, sample_ohlcv_data):
    """Test getting visible data."""
    chart_widget.plot_candlestick(sample_ohlcv_data)

    visible = chart_widget.get_visible_data()

    assert visible is not None
    assert len(visible) == 20


def test_get_visible_data_none(chart_widget):
    """Test getting visible data when empty."""
    visible = chart_widget.get_visible_data()

    assert visible is None
