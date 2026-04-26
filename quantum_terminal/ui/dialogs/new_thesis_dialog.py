"""Dialog for creating new investment theses."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QFormLayout,
    QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class ThesisData:
    """Investment thesis information."""

    ticker: str
    company_name: str
    thesis_text: str
    catalysts_short_term: str
    catalysts_medium_term: str
    catalysts_long_term: str
    risks: str
    price_target: float
    horizon_months: int
    margin_of_safety: float
    moat_type: str
    created_date: str


class NewThesisDialog(QDialog):
    """Dialog for creating new investment theses.

    Signals:
        thesis_saved: Emitted when thesis is saved successfully.
    """

    thesis_saved = pyqtSignal(ThesisData)

    def __init__(self, parent=None):
        """Initialize the New Thesis dialog.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Create New Investment Thesis")
        self.setGeometry(100, 100, 700, 900)
        self.setModal(True)
        self.thesis_data: Optional[ThesisData] = None
        self.initUI()

    def initUI(self) -> None:
        """Initialize UI components."""
        main_layout = QVBoxLayout()

        form_layout = QFormLayout()

        self.ticker_input = QLineEdit()
        self.ticker_input.setPlaceholderText("e.g., AAPL")
        form_layout.addRow("Ticker:", self.ticker_input)

        self.company_name_input = QLineEdit()
        self.company_name_input.setPlaceholderText("e.g., Apple Inc.")
        form_layout.addRow("Company Name:", self.company_name_input)

        thesis_group = QGroupBox("Investment Thesis")
        thesis_layout = QVBoxLayout()
        self.thesis_input = QTextEdit()
        self.thesis_input.setPlaceholderText(
            "Describe your investment thesis, key reasons for the position, and fundamentals..."
        )
        self.thesis_input.setMinimumHeight(120)
        thesis_layout.addWidget(self.thesis_input)
        thesis_group.setLayout(thesis_layout)
        main_layout.addLayout(form_layout)
        main_layout.addWidget(thesis_group)

        catalysts_group = QGroupBox("Catalysts (Timeline for Value Realization)")
        catalysts_layout = QVBoxLayout()

        catalysts_form = QFormLayout()

        self.catalysts_short = QTextEdit()
        self.catalysts_short.setPlaceholderText(
            "Short-term catalysts (0-6 months)"
        )
        self.catalysts_short.setMaximumHeight(60)
        catalysts_form.addRow("Short-term (0-6 months):", self.catalysts_short)

        self.catalysts_medium = QTextEdit()
        self.catalysts_medium.setPlaceholderText("Medium-term catalysts (6-18 months)")
        self.catalysts_medium.setMaximumHeight(60)
        catalysts_form.addRow(
            "Medium-term (6-18 months):", self.catalysts_medium
        )

        self.catalysts_long = QTextEdit()
        self.catalysts_long.setPlaceholderText("Long-term catalysts (18+ months)")
        self.catalysts_long.setMaximumHeight(60)
        catalysts_form.addRow("Long-term (18+ months):", self.catalysts_long)

        catalysts_layout.addLayout(catalysts_form)
        catalysts_group.setLayout(catalysts_layout)
        main_layout.addWidget(catalysts_group)

        risks_group = QGroupBox("Risks & Concerns")
        risks_layout = QVBoxLayout()
        self.risks_input = QTextEdit()
        self.risks_input.setPlaceholderText(
            "What could go wrong? List key risks, competitors, macro headwinds..."
        )
        self.risks_input.setMaximumHeight(80)
        risks_layout.addWidget(self.risks_input)
        risks_group.setLayout(risks_layout)
        main_layout.addWidget(risks_group)

        valuation_form = QFormLayout()

        self.price_target_input = QDoubleSpinBox()
        self.price_target_input.setRange(0.01, 10000)
        self.price_target_input.setValue(100.00)
        self.price_target_input.setSingleStep(1.0)
        self.price_target_input.setPrefix("$")
        valuation_form.addRow("Price Target:", self.price_target_input)

        self.horizon_input = QSpinBox()
        self.horizon_input.setRange(1, 60)
        self.horizon_input.setValue(12)
        self.horizon_input.setSuffix(" months")
        valuation_form.addRow("Investment Horizon:", self.horizon_input)

        self.mos_input = QDoubleSpinBox()
        self.mos_input.setRange(0, 100)
        self.mos_input.setValue(25)
        self.mos_input.setSingleStep(5)
        self.mos_input.setSuffix("%")
        valuation_form.addRow("Margin of Safety:", self.mos_input)

        self.moat_type = QComboBox()
        self.moat_type.addItems(
            [
                "None",
                "Cost Advantage",
                "Network Effects",
                "Intangible Assets",
                "Switching Costs",
                "Scale",
                "Multiple Moats",
            ]
        )
        valuation_form.addRow("Economic Moat Type:", self.moat_type)

        main_layout.addLayout(valuation_form)

        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Thesis")
        save_btn.setProperty("accent", True)
        save_btn.clicked.connect(self.save_thesis)

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

        if not self.company_name_input.text().strip():
            return False, "Company name is required"

        if not self.thesis_input.toPlainText().strip():
            return False, "Investment thesis is required"

        if self.price_target_input.value() <= 0:
            return False, "Price target must be greater than 0"

        if not self.risks_input.toPlainText().strip():
            return False, "Risk description is required"

        return True, ""

    def save_thesis(self) -> None:
        """Validate and save the thesis data."""
        is_valid, error_msg = self.validate_inputs()

        if not is_valid:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Validation Error", error_msg)
            return

        self.thesis_data = ThesisData(
            ticker=self.ticker_input.text().upper().strip(),
            company_name=self.company_name_input.text().strip(),
            thesis_text=self.thesis_input.toPlainText().strip(),
            catalysts_short_term=self.catalysts_short.toPlainText().strip(),
            catalysts_medium_term=self.catalysts_medium.toPlainText().strip(),
            catalysts_long_term=self.catalysts_long.toPlainText().strip(),
            risks=self.risks_input.toPlainText().strip(),
            price_target=self.price_target_input.value(),
            horizon_months=self.horizon_input.value(),
            margin_of_safety=self.mos_input.value(),
            moat_type=self.moat_type.currentText(),
            created_date=datetime.now().isoformat(),
        )

        self.thesis_saved.emit(self.thesis_data)
        self.accept()

    def get_thesis_data(self) -> Optional[ThesisData]:
        """Get the saved thesis data.

        Returns:
            ThesisData object or None if cancelled.
        """
        return self.thesis_data
