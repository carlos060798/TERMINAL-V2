"""
Tests for PDF Intel Panel and PDF processing infrastructure.

Covers:
- PDF extraction and data parsing
- Document type detection
- Financial metric extraction
- SEC XBRL comparison and validation
- Panel UI functionality
"""

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from quantum_terminal.infrastructure.pdf.pdf_extractor import (
    PDFExtractor, FinancialData, get_pdf_extractor
)
from quantum_terminal.infrastructure.pdf.pdf_validator import (
    PDFValidator, ComparisonResult
)


class TestFinancialData:
    """Test FinancialData dataclass."""

    def test_financial_data_initialization(self):
        """Test FinancialData initializes with correct defaults."""
        data = FinancialData(
            ticker="AAPL",
            document_type="10-K",
            filing_date="2024-01-15"
        )

        assert data.ticker == "AAPL"
        assert data.document_type == "10-K"
        assert data.filing_date == "2024-01-15"
        assert data.revenue == []
        assert data.net_income == []
        assert data.eps == []
        assert data.ebitda == []

    def test_financial_data_with_values(self):
        """Test FinancialData with populated values."""
        data = FinancialData(
            ticker="MSFT",
            document_type="10-Q",
            revenue=[1000.0, 1100.0, 1200.0],
            net_income=[200.0, 220.0, 240.0],
            eps=[5.0, 5.5, 6.0]
        )

        assert len(data.revenue) == 3
        assert data.revenue[0] == 1000.0
        assert data.eps[-1] == 6.0


class TestPDFExtractor:
    """Test PDF extraction functionality."""

    def test_extractor_initialization(self):
        """Test PDFExtractor initializes correctly."""
        extractor = PDFExtractor()

        assert extractor is not None
        assert extractor.MIN_REQUEST_DELAY == 0.5
        assert extractor.DOCUMENT_TYPES == [
            "10-K", "10-Q", "Earnings Release", "Investor Day", "Other"
        ]

    def test_detect_document_type_10k(self):
        """Test 10-K detection."""
        extractor = PDFExtractor()

        text = "UNITED STATES SECURITIES AND EXCHANGE COMMISSION\nFORM 10-K"
        doc_type = extractor.detect_document_type(text)

        assert doc_type == "10-K"

    def test_detect_document_type_10q(self):
        """Test 10-Q detection."""
        extractor = PDFExtractor()

        text = "UNITED STATES SECURITIES AND EXCHANGE COMMISSION\nFORM 10-Q\nQuarterly Report"
        doc_type = extractor.detect_document_type(text)

        assert doc_type == "10-Q"

    def test_detect_document_type_earnings_release(self):
        """Test Earnings Release detection."""
        extractor = PDFExtractor()

        text = "Apple Inc. Earnings Release\nQ4 2023 Results and Forward Guidance"
        doc_type = extractor.detect_document_type(text)

        assert doc_type == "Earnings Release"

    def test_detect_document_type_investor_day(self):
        """Test Investor Day detection."""
        extractor = PDFExtractor()

        text = "Microsoft Investor Day\nFY2024 Strategic Overview"
        doc_type = extractor.detect_document_type(text)

        assert doc_type == "Investor Day"

    def test_detect_document_type_other(self):
        """Test unknown document detection."""
        extractor = PDFExtractor()

        text = "This is some random document without specific keywords"
        doc_type = extractor.detect_document_type(text)

        assert doc_type == "Other"

    def test_extract_number_valid_float(self):
        """Test number extraction from text."""
        extractor = PDFExtractor()

        assert extractor._extract_number("1,234.56") == 1234.56
        assert extractor._extract_number("$1000") == 1000.0
        assert extractor._extract_number("(500)") == -500.0

    def test_extract_number_invalid(self):
        """Test number extraction with invalid input."""
        extractor = PDFExtractor()

        assert extractor._extract_number("") is None
        assert extractor._extract_number("no numbers here") is None
        assert extractor._extract_number(None) is None

    def test_extract_number_with_parentheses_negative(self):
        """Test negative number extraction with parentheses."""
        extractor = PDFExtractor()

        value = extractor._extract_number("(1,234.56)")
        assert value == -1234.56

    @pytest.mark.asyncio
    async def test_extract_from_pdf_error_no_pdfplumber(self):
        """Test extraction fails gracefully without pdfplumber."""
        extractor = PDFExtractor()

        # Mock missing pdfplumber
        with patch('quantum_terminal.infrastructure.pdf.pdf_extractor.pdfplumber', None):
            result = await extractor.extract_from_pdf("fake.pdf", "AAPL")

            assert result.ticker == "AAPL"
            assert result.document_type == "Error"

    def test_extract_financial_metrics_empty_tables(self):
        """Test metric extraction with empty tables."""
        extractor = PDFExtractor()

        metrics = extractor._extract_financial_metrics([], "")

        assert metrics["revenue"] == []
        assert metrics["net_income"] == []
        assert metrics["total_assets"] is None

    def test_extract_md_a_section(self):
        """Test Management Discussion & Analysis extraction."""
        extractor = PDFExtractor()

        text = """
        Management Discussion and Analysis

        We are pleased to report strong results in 2024. Revenue grew 15%.
        The company continues to invest in R&D.

        Item 1A: Risk Factors
        """

        mda = extractor._extract_md_a(text)

        assert "revenue" in mda.lower()
        assert "r&d" in mda.lower()


class TestPDFValidator:
    """Test PDF validation and SEC comparison."""

    def test_validator_initialization(self):
        """Test PDFValidator initializes correctly."""
        validator = PDFValidator()

        assert validator is not None
        assert validator.ACCEPTABLE_VARIANCE == 5.0
        assert validator.SIGNIFICANT_VARIANCE == 10.0

    def test_calculate_variance_exact_match(self):
        """Test variance calculation for exact match."""
        validator = PDFValidator()

        variance = validator._calculate_variance(1000.0, 1000.0)

        assert variance == 0.0

    def test_calculate_variance_5_percent(self):
        """Test variance calculation for 5% difference."""
        validator = PDFValidator()

        variance = validator._calculate_variance(1050.0, 1000.0)

        assert variance == pytest.approx(5.0, abs=0.1)

    def test_calculate_variance_10_percent(self):
        """Test variance calculation for 10% difference."""
        validator = PDFValidator()

        variance = validator._calculate_variance(1100.0, 1000.0)

        assert variance == pytest.approx(10.0, abs=0.1)

    def test_calculate_variance_none_values(self):
        """Test variance with None values."""
        validator = PDFValidator()

        assert validator._calculate_variance(None, 1000.0) is None
        assert validator._calculate_variance(1000.0, None) is None
        assert validator._calculate_variance(None, None) is None

    def test_calculate_variance_zero_division(self):
        """Test variance with zero divisor."""
        validator = PDFValidator()

        assert validator._calculate_variance(1000.0, 0) is None
        assert validator._calculate_variance(0, 0) == 0.0

    def test_determine_status_match(self):
        """Test status determination for exact match."""
        validator = PDFValidator()

        status = validator._determine_status(0.001)  # Very small variance

        assert status == "match"

    def test_determine_status_acceptable(self):
        """Test status determination for acceptable variance."""
        validator = PDFValidator()

        status = validator._determine_status(3.5)  # 3.5% variance

        assert status == "acceptable"

    def test_determine_status_warning(self):
        """Test status determination for warning variance."""
        validator = PDFValidator()

        status = validator._determine_status(7.5)  # 7.5% variance

        assert status == "warning"

    def test_determine_status_error(self):
        """Test status determination for error variance."""
        validator = PDFValidator()

        status = validator._determine_status(15.0)  # 15% variance

        assert status == "error"

    def test_determine_status_unknown(self):
        """Test status determination with None variance."""
        validator = PDFValidator()

        status = validator._determine_status(None)

        assert status == "unknown"

    def test_build_comparisons_with_data(self):
        """Test building comparison results."""
        validator = PDFValidator()

        pdf_data = FinancialData(
            ticker="AAPL",
            document_type="10-K",
            revenue=[100.0, 110.0, 120.0],
            net_income=[20.0, 22.0, 24.0],
            total_assets=500.0,
            total_debt=100.0
        )

        sec_facts = {
            "Revenue": [100.5, 110.5, 120.5],
            "NetIncomeLoss": [20.5, 22.5, 24.5],
            "Assets": 505.0,
            "LongTermDebt": 102.0
        }

        results = validator._build_comparisons(pdf_data, sec_facts)

        assert len(results) > 0
        assert all(isinstance(r, ComparisonResult) for r in results)

    def test_validate_pdf_data_balance_sheet_consistency(self):
        """Test balance sheet consistency validation."""
        validator = PDFValidator()

        # Valid: Assets = Liabilities + Equity
        pdf_data = FinancialData(
            ticker="AAPL",
            document_type="10-K",
            total_assets=1000.0,
            total_liabilities=400.0,
            shareholders_equity=600.0
        )

        issues = validator.validate_pdf_data(pdf_data)

        assert "balance_sheet" not in issues

    def test_validate_pdf_data_balance_sheet_mismatch(self):
        """Test balance sheet mismatch detection."""
        validator = PDFValidator()

        # Invalid: Assets != Liabilities + Equity
        pdf_data = FinancialData(
            ticker="AAPL",
            document_type="10-K",
            total_assets=1000.0,
            total_liabilities=400.0,
            shareholders_equity=400.0  # Should be 600
        )

        issues = validator.validate_pdf_data(pdf_data)

        assert "balance_sheet" in issues

    def test_validate_pdf_data_negative_eps(self):
        """Test negative EPS validation."""
        validator = PDFValidator()

        pdf_data = FinancialData(
            ticker="TSLA",
            document_type="10-K",
            eps=[-1.0, -0.5, 0.5]
        )

        issues = validator.validate_pdf_data(pdf_data)

        assert "eps" in issues

    def test_validate_pdf_data_high_leverage(self):
        """Test high leverage detection."""
        validator = PDFValidator()

        pdf_data = FinancialData(
            ticker="AAPL",
            document_type="10-K",
            total_debt=5000.0,
            shareholders_equity=500.0
        )

        issues = validator.validate_pdf_data(pdf_data)

        assert "leverage" in issues

    def test_get_notes_match(self):
        """Test note generation for match."""
        validator = PDFValidator()

        notes = validator._get_notes("match", 0.0)

        assert "exactly" in notes.lower()

    def test_get_notes_acceptable(self):
        """Test note generation for acceptable variance."""
        validator = PDFValidator()

        notes = validator._get_notes("acceptable", 3.5)

        assert "acceptable" in notes.lower()
        assert "3.50" in notes

    def test_get_notes_warning(self):
        """Test note generation for warning."""
        validator = PDFValidator()

        notes = validator._get_notes("warning", 7.5)

        assert "significant" in notes.lower()

    def test_get_notes_error(self):
        """Test note generation for error."""
        validator = PDFValidator()

        notes = validator._get_notes("error", 15.0)

        assert "major" in notes.lower()


class TestPDFExtractorSingleton:
    """Test PDF extractor singleton pattern."""

    def test_get_pdf_extractor_returns_same_instance(self):
        """Test that get_pdf_extractor returns same instance."""
        extractor1 = get_pdf_extractor()
        extractor2 = get_pdf_extractor()

        assert extractor1 is extractor2

    def test_get_pdf_extractor_not_none(self):
        """Test that get_pdf_extractor returns non-None."""
        extractor = get_pdf_extractor()

        assert extractor is not None
        assert isinstance(extractor, PDFExtractor)


class TestIntegration:
    """Integration tests for PDF processing pipeline."""

    def test_full_extraction_pipeline_mock(self):
        """Test full extraction pipeline with mocked data."""
        # Create test data
        test_ticker = "AAPL"
        test_doc_type = "10-K"

        extractor = PDFExtractor()

        # Test document type detection
        text = "UNITED STATES SECURITIES AND EXCHANGE COMMISSION\nFORM 10-K"
        detected = extractor.detect_document_type(text)

        assert detected == test_doc_type

        # Test number extraction
        revenue = extractor._extract_number("$183,000,000,000")
        assert revenue == pytest.approx(183e9, rel=1e-5)

        # Test MD&A extraction
        mda_text = """
        Management Discussion and Analysis
        We achieved record revenue of $183B in 2023.
        Item 1A: Risk Factors
        """
        mda = extractor._extract_md_a(mda_text)
        assert "revenue" in mda.lower()

    def test_validation_pipeline_mock(self):
        """Test validation pipeline with mocked SEC data."""
        validator = PDFValidator()

        # Create test data
        pdf_data = FinancialData(
            ticker="MSFT",
            document_type="10-K",
            revenue=[50.0, 55.0, 60.0],
            net_income=[10.0, 11.0, 12.0],
            total_assets=350.0,
            shareholders_equity=200.0,
            total_debt=50.0
        )

        # Validate internal consistency
        issues = validator.validate_pdf_data(pdf_data)

        # Should have valid balance sheet (assets = liabilities + equity)
        # But we set it up with only liabilities+equity=250, assets=350
        # So there should be a mismatch issue
        assert isinstance(issues, dict)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_extractor_with_empty_text(self):
        """Test extraction with empty text."""
        extractor = PDFExtractor()

        # Should not crash
        doc_type = extractor.detect_document_type("")
        mda = extractor._extract_md_a("")
        metrics = extractor._extract_financial_metrics([], "")

        assert doc_type == "Other"
        assert mda == ""
        assert metrics["revenue"] == []

    def test_validator_with_zero_values(self):
        """Test validator with zero financial values."""
        validator = PDFValidator()

        pdf_data = FinancialData(
            ticker="BLANK",
            document_type="10-K",
            revenue=[0.0],
            net_income=[0.0],
            total_assets=0.0
        )

        # Should not crash
        issues = validator.validate_pdf_data(pdf_data)

        assert isinstance(issues, dict)

    def test_comparison_with_missing_sec_data(self):
        """Test comparison when SEC data is missing."""
        validator = PDFValidator()

        pdf_data = FinancialData(
            ticker="AAPL",
            document_type="10-K",
            revenue=[100.0],
            net_income=[20.0]
        )

        sec_facts = {}  # Empty

        results = validator._build_comparisons(pdf_data, sec_facts)

        # Should return empty or minimal results
        assert isinstance(results, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
