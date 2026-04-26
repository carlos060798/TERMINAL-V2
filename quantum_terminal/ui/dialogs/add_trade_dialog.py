"""Dialog for adding new trades to the trading journal."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QComboBox,
    QDoubleSpinBox,
    QCheckBox,
    QFormLayout,
    QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TradeData:
    """Trade information."""

    ticker: str
    direction: str
    size: float
    entry_price: float
    exit_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    reason: str
    plan_adherence: bool
    entry_date: str


class AddTradeDialog(QDialog):
    """Dialog for registering new trades in the trading journal.

    Signals:
        trade_saved: Emitted when trade is saved successfully.
    """

    trade_saved = pyqtSignal(TradeData)

    def __init__(self, parent=None):
        """Initialize the Add Trade dialog.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Add New Trade")
        self.setGeometry(100, 100, 500, 650)
        self.setModal(True)
        self.trade_data: Optional[TradeData] = None
        self.initUI()

    def initUI(self) -> None:
        """Initialize UI components."""
        main_layout = QVBoxLayout()

        form_layout = QFormLayout()

        self.ticker_input = QLineEdit()
        self.ticker_input.setPlaceholderText("e.g., AAPL")
        form_layout.addRow("Ticker:", self.ticker_input)

        self.direction = QComboBox()
        self.direction.addItems(["Long", "Short"])
        form_layout.addRow("Direction:", self.direction)

        self.size_input = QDoubleSpinBox()
        self.size_input.setRange(0.01, 1000000)
        self.size_input.setValue(100)
        self.size_input.setSingleStep(10)
        form_layout.addRow("Size (shares):", self.size_input)

        self.entry_price_input = QDoubleSpinBox()
        self.entry_price_input.setRange(0.01, 1000000)
        self.entry_price_input.setValue(100.00)
        self.entry_price_input.setSingleStep(0.01)
        form_layout.addRow("Entry Price:", self.entry_price_input)

        self.exit_price_input = QDoubleSpinBox()
        self.exit_price_input.setRange(0, 1000000)
        self.exit_price_input.setValue(0)
        self.exit_price_input.setSingleStep(0.01)
        self.exit_price_input.setPrefix("(Optional) ")
        form_layout.addRow("Exit Price:", self.exit_price_input)

        self.stop_loss_input = QDoubleSpinBox()
        self.stop_loss_input.setRange(0, 1000000)
        self.stop_loss_input.setValue(0)
        self.stop_loss_input.setSingleStep(0.01)
        self.stop_loss_input.setPrefix("(Optional) ")
        form_layout.addRow("Stop Loss:", self.stop_loss_input)

        self.take_profit_input = QDoubleSpinBox()
        self.take_profit_input.setRange(0, 1000000)
        self.take_profit_input.setValue(0)
        self.take_profit_input.setSingleStep(0.01)
        self.take_profit_input.setPrefix("(Optional) ")
        form_layout.addRow("Take Profit:", self.take_profit_input)

        reason_group = QGroupBox("Trade Setup & Plan")
        reason_layout = QVBoxLayout()
        self.reason_input = QTextEdit()
        self.reason_input.setPlaceholderText(
            "Describe the setup and why you entered this trade..."
        )
        self.reason_input.setMaximumHeight(100)
        reason_layout.addWidget(QLabel("Setup Reason:"))
        reason_layout.addWidget(self.reason_input)

        self.plan_adherence = QCheckBox("I have a clear plan for this trade")
        self.plan_adherence.setChecked(True)
        reason_layout.addWidget(self.plan_adherence)
        reason_group.setLayout(reason_layout)
        main_layout.addLayout(form_layout)
        main_layout.addWidget(reason_group)

        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Trade")
        save_btn.setProperty("accent", True)
        save_btn.clicked.connect(self.save_trade)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def validate_inputs(self) -> tuple[bool, str]:
        """Validate all input fields.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.ticker_input.text().strip():
            return False, "Ticker is required"

        if self.size_input.value() <= 0:
            return False, "Size must be greater than 0"

        if self.entry_price_input.value() <= 0:
            return False, "Entry Price must be greater than 0"

        if (
            self.exit_price_input.value() > 0
            and self.entry_price_input.value() <= 0
        ):
            return False, "Entry Price is required if Exit Price is set"

        if not self.reason_input.toPlainText().strip():
            return False, "Trade setup reason is required"

        return True, ""

    def save_trade(self) -> None:
        """Validate and save the trade data."""
        is_valid, error_msg = self.validate_inputs()

        if not is_valid:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Validation Error", error_msg)
            return

        self.trade_data = TradeData(
            ticker=self.ticker_input.text().upper().strip(),
            direction=self.direction.currentText(),
            size=self.size_input.value(),
            entry_price=self.entry_price_input.value(),
            exit_price=(
                self.exit_price_input.value()
                if self.exit_price_input.value() > 0
                else None
            ),
            stop_loss=(
                self.stop_loss_input.value()
                if self.stop_loss_input.value() > 0
                else None
            ),
            take_profit=(
                self.take_profit_input.value()
                if self.take_profit_input.value() > 0
                else None
            ),
            reason=self.reason_input.toPlainText().strip(),
            plan_adherence=self.plan_adherence.isChecked(),
            entry_date=datetime.now().isoformat(),
        )

        self.trade_saved.emit(self.trade_data)
        self.accept()

    def get_trade_data(self) -> Optional[TradeData]:
        """Get the saved trade data.

        Returns:
            TradeData object or None if cancelled.
        """
        return self.trade_data
