"""
AIChatWidget: Chat panel with message history and user input.

Features: Multi-turn conversation, scrollable history, send button, typing indicator.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QScrollArea,
    QLabel,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QColor, QPixmap
from typing import List, Tuple, Optional
from datetime import datetime


class AIChatWidget(QWidget):
    """Chat widget for AI conversations with history."""

    message_sent = pyqtSignal(str)  # Emitted when message is sent

    def __init__(self):
        """Initialize AIChatWidget."""
        super().__init__()
        self.messages: List[Tuple[str, str, str]] = []  # (role, text, timestamp)
        self.is_loading = False

        self.initUI()

    def initUI(self) -> None:
        """Build chat UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Chat history (scrollable)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            """
            QScrollArea {
                background-color: #1E1E1E;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2A2A2A;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background-color: #505050;
                border-radius: 4px;
            }
        """
        )

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(8, 8, 8, 8)
        self.chat_layout.setSpacing(8)
        self.chat_layout.addStretch()
        self.scroll_area.setWidget(self.chat_container)
        layout.addWidget(self.scroll_area)

        # Input section
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(8, 8, 8, 8)
        input_layout.setSpacing(6)

        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Ask about portfolio, markets, thesis...")
        self.message_input.setFont(QFont("Inter", 11))
        self.message_input.setMaximumHeight(60)
        self.message_input.setStyleSheet(self._get_input_stylesheet())
        self.message_input.keyPressEvent = self._on_input_key_press
        input_layout.addWidget(self.message_input)

        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        self.send_button.setFixedSize(80, 40)
        self.send_button.setStyleSheet(self._get_button_stylesheet())
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.clicked.connect(self._on_send_clicked)
        input_layout.addWidget(self.send_button)

        layout.addLayout(input_layout)
        self.setLayout(layout)

    def add_message(
        self, role: str, text: str, timestamp: Optional[str] = None
    ) -> None:
        """
        Add message to chat history.

        Args:
            role: "user" or "assistant"
            text: Message text
            timestamp: Optional timestamp (default: now)
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M")

        self.messages.append((role, text, timestamp))

        # Create message widget
        msg_widget = self._create_message_widget(role, text, timestamp)
        self.chat_layout.insertWidget(
            self.chat_layout.count() - 1, msg_widget
        )

        # Scroll to bottom
        QTimer.singleShot(100, self._scroll_to_bottom)

    def add_typing_indicator(self) -> None:
        """Show typing indicator."""
        self.is_loading = True
        self.send_button.setEnabled(False)
        self.message_input.setEnabled(False)

        typing_label = QLabel("AI is thinking...")
        typing_label.setFont(QFont("Inter", 10))
        typing_label.setStyleSheet("color: #A0A0A0; font-style: italic;")
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, typing_label)

        # Store reference to remove later
        self._typing_indicator = typing_label

    def remove_typing_indicator(self) -> None:
        """Remove typing indicator."""
        if hasattr(self, "_typing_indicator"):
            self.chat_layout.removeWidget(self._typing_indicator)
            self._typing_indicator.deleteLater()
        self.is_loading = False
        self.send_button.setEnabled(True)
        self.message_input.setEnabled(True)

    def clear_history(self) -> None:
        """Clear all messages."""
        self.messages = []

        # Remove all message widgets
        while self.chat_layout.count() > 1:  # Keep stretch
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.message_input.clear()
        self.is_loading = False

    def get_history(self) -> List[Tuple[str, str, str]]:
        """Get all messages in chat history."""
        return self.messages.copy()

    def get_history_text(self) -> str:
        """Get chat history as formatted text."""
        lines = []
        for role, text, timestamp in self.messages:
            lines.append(f"[{timestamp}] {role.upper()}: {text}")
        return "\n".join(lines)

    def _create_message_widget(self, role: str, text: str, timestamp: str) -> QWidget:
        """Create message display widget."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Header: role + timestamp
        header_label = QLabel(f"{role.upper()} • {timestamp}")
        header_label.setFont(QFont("Inter", 9))
        header_label.setStyleSheet("color: #A0A0A0;")
        layout.addWidget(header_label)

        # Message text
        msg_label = QLabel(text)
        msg_label.setFont(QFont("Inter", 11))
        msg_label.setWordWrap(True)

        # Style based on role
        if role == "user":
            msg_label.setStyleSheet(
                """
                color: #00D26A;
                padding: 8px 12px;
                background-color: #2A3A2A;
                border-radius: 4px;
            """
            )
        else:  # assistant
            msg_label.setStyleSheet(
                """
                color: #FFFFFF;
                padding: 8px 12px;
                background-color: #2A2A3A;
                border-radius: 4px;
            """
            )

        layout.addWidget(msg_label)
        return container

    def _on_input_key_press(self, event):
        """Handle key press in message input."""
        if event.key() == Qt.Key.Key_Return and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._on_send_clicked()
        elif event.key() == Qt.Key.Key_Return:
            # Normal return = new line
            self.message_input.insertPlainText("\n")

    def _on_send_clicked(self) -> None:
        """Handle send button click."""
        text = self.message_input.toPlainText().strip()
        if not text or self.is_loading:
            return

        self.add_message("user", text)
        self.message_input.clear()
        self.message_sent.emit(text)

    def _scroll_to_bottom(self) -> None:
        """Scroll to bottom of chat."""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @staticmethod
    def _get_input_stylesheet() -> str:
        """Get stylesheet for message input."""
        return """
            QTextEdit {
                background-color: #2A2A2A;
                color: #FFFFFF;
                border: 1px solid #3A3A3A;
                border-radius: 4px;
                padding: 6px;
                font-family: 'Inter';
                font-size: 11px;
            }
            QTextEdit:focus {
                border: 1px solid #00D26A;
            }
        """

    @staticmethod
    def _get_button_stylesheet() -> str:
        """Get stylesheet for send button."""
        return """
            QPushButton {
                background-color: #00D26A;
                color: #000000;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00E673;
            }
            QPushButton:pressed {
                background-color: #00A850;
            }
            QPushButton:disabled {
                background-color: #3A3A3A;
                color: #606060;
            }
        """
