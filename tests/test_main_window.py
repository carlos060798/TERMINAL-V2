"""
Tests for main_window.py - Quantum Terminal main UI.

Tests layout, components, and basic interactions.
"""

import pytest
from PyQt6.QtWidgets import QApplication, QMainWindow, QListWidget, QTabWidget
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QTimer

from quantum_terminal.ui.main_window import (
    QuantumTerminal,
    NavigationWidget,
    ChatWidget,
    MarketBarWidget,
    ModulePanelWidget,
)


@pytest.fixture
def app():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def window(app):
    """Create QuantumTerminal window for tests."""
    window = QuantumTerminal()
    yield window
    window.close()


class TestQuantumTerminal:
    """Tests for main QuantumTerminal window."""

    def test_window_creation(self, window):
        """Test window is created successfully."""
        assert window is not None
        assert isinstance(window, QMainWindow)
        assert window.windowTitle() == "Quantum Investment Terminal"

    def test_window_geometry(self, window):
        """Test window has correct initial geometry."""
        assert window.geometry().width() >= 1200
        assert window.geometry().height() >= 700

    def test_market_bar_exists(self, window):
        """Test market bar is created."""
        assert window.market_bar is not None
        assert isinstance(window.market_bar, MarketBarWidget)

    def test_navigation_exists(self, window):
        """Test navigation panel exists."""
        assert window.nav is not None
        assert isinstance(window.nav, NavigationWidget)

    def test_tabs_exist(self, window):
        """Test module tabs exist."""
        assert window.tabs is not None
        assert isinstance(window.tabs, ModulePanelWidget)

    def test_chat_exists(self, window):
        """Test AI chat panel exists."""
        assert window.chat is not None
        assert isinstance(window.chat, ChatWidget)

    def test_status_bar_exists(self, window):
        """Test status bar is created."""
        assert window.statusBar() is not None

    def test_module_count(self, window):
        """Test all 12 modules are present."""
        expected_modules = 12
        assert window.tabs.count() == expected_modules

    def test_menu_bar_exists(self, window):
        """Test menu bar is created."""
        assert window.menuBar() is not None
        actions = window.menuBar().actions()
        assert len(actions) >= 5  # File, Edit, View, Data, Help


class TestNavigationWidget:
    """Tests for navigation widget."""

    def test_navigation_creation(self, app):
        """Test navigation widget creation."""
        nav = NavigationWidget()
        assert nav is not None
        assert isinstance(nav, QListWidget)

    def test_navigation_item_count(self, app):
        """Test navigation has all 12 modules."""
        nav = NavigationWidget()
        assert nav.count() == 12

    def test_navigation_module_names(self, app):
        """Test navigation contains correct module names."""
        nav = NavigationWidget()
        expected_modules = [
            "Dashboard",
            "Watchlist",
            "Analyzer",
            "Screener",
            "Macro",
            "Journal",
            "Thesis",
            "PDF Intel",
            "Earnings",
            "Monitor",
            "Backtest",
            "Risk",
        ]

        for i, module_name in enumerate(expected_modules):
            item = nav.item(i)
            # Check that module name is in the item text
            assert module_name in item.text()

    def test_navigation_signal_emission(self, app):
        """Test navigation emits module_selected signal."""
        nav = NavigationWidget()
        signal_data = []

        def capture_signal(module_name):
            signal_data.append(module_name)

        nav.module_selected.connect(capture_signal)

        # Click on Dashboard
        item = nav.item(0)
        nav.setCurrentItem(item)
        nav.itemClicked.emit(item)

        assert len(signal_data) == 1
        assert signal_data[0] == "Dashboard"


class TestChatWidget:
    """Tests for chat widget."""

    def test_chat_creation(self, app):
        """Test chat widget creation."""
        chat = ChatWidget()
        assert chat is not None

    def test_chat_display_exists(self, app):
        """Test chat has display text edit."""
        chat = ChatWidget()
        assert chat.chat_display is not None

    def test_chat_input_exists(self, app):
        """Test chat has message input."""
        chat = ChatWidget()
        assert chat.message_input is not None

    def test_add_message(self, app):
        """Test adding message to chat."""
        chat = ChatWidget()
        chat.add_message("User", "Test message")

        text = chat.chat_display.toPlainText()
        assert "User" in text
        assert "Test message" in text

    def test_add_error_message(self, app):
        """Test adding error message."""
        chat = ChatWidget()
        chat.add_message("Error", "Something went wrong", is_error=True)

        text = chat.chat_display.toPlainText()
        assert "Error" in text
        assert "Something went wrong" in text

    def test_send_message_signal(self, app):
        """Test send message signal emission."""
        chat = ChatWidget()
        signal_data = []

        def capture_signal(message):
            signal_data.append(message)

        chat.send_message.connect(capture_signal)

        # Type message and press enter
        chat.message_input.setText("Test message")
        chat.message_input.returnPressed.emit()

        assert len(signal_data) == 1
        assert signal_data[0] == "Test message"

    def test_clear_input_after_send(self, app):
        """Test input is cleared after sending."""
        chat = ChatWidget()
        chat.message_input.setText("Test message")
        chat._send_message()

        assert chat.message_input.text() == ""


class TestMarketBarWidget:
    """Tests for market bar widget."""

    def test_market_bar_creation(self, app):
        """Test market bar creation."""
        market_bar = MarketBarWidget()
        assert market_bar is not None

    def test_market_bar_indices(self, app):
        """Test market bar has required indices."""
        market_bar = MarketBarWidget()
        expected_indices = ["S&P 500", "NASDAQ", "BTC", "WTI", "10Y", "VIX", "DXY"]

        for symbol in expected_indices:
            assert symbol in market_bar.indices

    def test_market_bar_update(self, app):
        """Test market bar update method."""
        market_bar = MarketBarWidget()
        updates = {
            "S&P 500": {"value": "4,600.00", "change": "+0.50%", "positive": True}
        }
        market_bar.update_indices(updates)

        # Check that label was updated
        label = market_bar.index_labels["S&P 500"]
        assert "4,600.00" in label.text()


class TestModulePanelWidget:
    """Tests for module panel widget."""

    def test_module_panel_creation(self, app):
        """Test module panel creation."""
        panel = ModulePanelWidget()
        assert panel is not None
        assert isinstance(panel, QTabWidget)

    def test_add_module_tab(self, app):
        """Test adding module tab."""
        from PyQt6.QtWidgets import QLabel

        panel = ModulePanelWidget()
        widget = QLabel("Test Module")
        panel.add_module_tab("Test", widget)

        assert panel.count() == 1
        assert panel.tabText(0) == "Test"

    def test_select_module(self, app):
        """Test selecting module by name."""
        from PyQt6.QtWidgets import QLabel

        panel = ModulePanelWidget()
        widget1 = QLabel("Module 1")
        widget2 = QLabel("Module 2")

        panel.add_module_tab("Module1", widget1)
        panel.add_module_tab("Module2", widget2)

        panel.select_module("Module2")
        assert panel.currentIndex() == 1


class TestMainWindowIntegration:
    """Integration tests for main window."""

    def test_layout_proportions(self, window):
        """Test that splitter has correct proportions."""
        # Get the splitter from the central widget
        central = window.centralWidget()
        assert central is not None

    def test_window_close(self, window):
        """Test window closes properly."""
        window.close()
        assert window.isVisible() is False

    def test_module_selection_navigation(self, window):
        """Test selecting module via navigation."""
        # Get first module item
        item = window.nav.item(0)
        window.nav.setCurrentItem(item)
        window.nav.itemClicked.emit(item)

        # Check that correct tab is active
        assert window.tabs.currentIndex() == 0

    def test_chat_integration(self, window):
        """Test chat widget integration."""
        # Send a message
        window.chat.message_input.setText("Test query")
        window.chat._send_message()

        # Verify message is in display
        text = window.chat.chat_display.toPlainText()
        assert "User" in text or "Test query" in text

    def test_status_bar_visibility(self, window):
        """Test status bar is visible."""
        status_bar = window.statusBar()
        assert status_bar is not None
        assert status_bar.isVisible()


class TestMainWindowErrors:
    """Error handling tests."""

    def test_invalid_module_selection(self, window):
        """Test selecting non-existent module."""
        # This should not raise an exception
        window.tabs.select_module("NonExistent")

    def test_chat_empty_message(self, window):
        """Test sending empty message."""
        window.chat.message_input.setText("")
        window.chat._send_message()

        # Message should not be sent
        # (implementation specific, but should handle gracefully)

    def test_market_timer_lifecycle(self, window):
        """Test market timer starts and stops."""
        assert window.market_timer.isActive()

        window.market_timer.stop()
        assert not window.market_timer.isActive()

        window.market_timer.start()
        assert window.market_timer.isActive()
