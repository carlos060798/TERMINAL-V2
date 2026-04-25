"""
Tests for MetricCard widget.
"""

import pytest
from PyQt6.QtWidgets import QApplication
from quantum_terminal.ui.widgets import MetricCard


@pytest.fixture
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def metric_card(qapp):
    """Create MetricCard instance."""
    card = MetricCard(title="Test Metric", unit="$")
    return card


def test_metric_card_creation(metric_card):
    """Test MetricCard is created successfully."""
    assert metric_card is not None
    assert metric_card.title == "Test Metric"
    assert metric_card.unit == "$"


def test_set_value(metric_card):
    """Test setting metric value."""
    metric_card.set_value(1234.56, animate=False)
    assert metric_card.current_value == 1234.56
    assert "1234.56" in metric_card.value_label.text()
    assert "$" in metric_card.value_label.text()


def test_set_change_positive(metric_card):
    """Test setting positive change."""
    metric_card.set_change(5.5)
    assert "▲" in metric_card.change_label.text()
    assert "5.50%" in metric_card.change_label.text()
    assert "#00D26A" in metric_card.change_label.styleSheet()  # Green


def test_set_change_negative(metric_card):
    """Test setting negative change."""
    metric_card.set_change(-3.2)
    assert "▼" in metric_card.change_label.text()
    assert "3.20%" in metric_card.change_label.text()
    assert "#FF3B30" in metric_card.change_label.styleSheet()  # Red


def test_set_change_with_absolute(metric_card):
    """Test setting change with absolute value."""
    metric_card.set_change(2.5, absolute=150.75)
    assert "2.50%" in metric_card.change_label.text()
    assert "150.75" in metric_card.change_label.text()


def test_set_color(metric_card):
    """Test setting custom color."""
    metric_card.set_color("#FF9500")
    assert "#FF9500" in metric_card.value_label.styleSheet()


def test_warning_level(metric_card):
    """Test warning level styling."""
    metric_card.set_warning_level("warning")
    stylesheet = metric_card.styleSheet()
    assert "#FFA500" in stylesheet

    metric_card.set_warning_level("danger")
    stylesheet = metric_card.styleSheet()
    assert "#FF3B30" in stylesheet

    metric_card.set_warning_level("normal")
    stylesheet = metric_card.styleSheet()
    assert "#2A2A2A" in stylesheet


def test_clear(metric_card):
    """Test clearing metric card."""
    metric_card.set_value(999, animate=False)
    metric_card.set_change(10)

    metric_card.clear()

    assert metric_card.value_label.text() == "—"
    assert metric_card.change_label.text() == ""
    assert metric_card.current_value == 0.0


def test_value_clicked_signal(metric_card):
    """Test value_clicked signal emission."""
    signal_emitted = False
    received_value = None

    def on_signal(value):
        nonlocal signal_emitted, received_value
        signal_emitted = True
        received_value = value

    metric_card.value_clicked.connect(on_signal)
    metric_card.set_value(500, animate=False)
    metric_card._on_value_clicked(None)

    assert signal_emitted
    assert "500" in received_value
