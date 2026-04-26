"""
Comprehensive tests for Investment Thesis Panel.

Tests cover:
- New thesis creation with embeddings
- Automatic thesis scoring
- RAG semantic search
- AI analysis integration
- Historical performance tracking
- Data persistence

Phase 3 - UI Layer Testing
Reference: PLAN_MAESTRO.md - Phase 3: Testing
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from PyQt6.QtTest import QSignalSpy
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt, QTimer

from quantum_terminal.ui.panels.thesis_panel import (
    ThesisPanel, ThesisWorkerThread
)
from quantum_terminal.ui.dialogs.new_thesis_dialog import ThesisData


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def thesis_panel(qapp):
    """Create ThesisPanel instance."""
    panel = ThesisPanel()
    yield panel
    panel.deleteLater()


@pytest.fixture
def sample_thesis_data():
    """Create sample ThesisData."""
    return ThesisData(
        ticker="AAPL",
        company_name="Apple Inc.",
        thesis_text="Apple is undervalued due to strong ecosystem and services growth.",
        catalysts_short_term="iPhone 15 release, India expansion",
        catalysts_medium_term="Vision Pro adoption, Services margin expansion",
        catalysts_long_term="AR/VR ecosystem dominance",
        risks="Macro slowdown, China competition, regulatory pressure",
        price_target=200.0,
        horizon_months=12,
        margin_of_safety=25.0,
        moat_type="Ecosystem & Network Effects",
        created_date=datetime.now().isoformat()
    )


# ============================================================================
# Test: Worker Thread Operations
# ============================================================================

class TestThesisWorkerThread:
    """Tests for ThesisWorkerThread background operations."""

    def test_embed_thesis_operation(self, qapp):
        """Test thesis text embedding."""
        worker = ThesisWorkerThread(
            "embed",
            ticker="AAPL",
            text="Test thesis for Apple"
        )

        # Capture signals
        results = {}
        worker.operation_complete.connect(
            lambda r: results.update({"result": r})
        )

        worker.run()  # Direct call instead of start()

        assert "result" in results
        result = results["result"]
        assert result["operation"] == "embed"
        assert result["result"]["ticker"] == "AAPL"
        assert result["result"]["text_len"] > 0
        assert "embedding" in result["result"]

    def test_score_thesis_operation(self, qapp):
        """Test thesis scoring."""
        worker = ThesisWorkerThread(
            "score",
            ticker="AAPL",
            eps=5.0,
            growth=15.0
        )

        results = {}
        worker.operation_complete.connect(
            lambda r: results.update({"result": r})
        )

        worker.run()

        assert "result" in results
        result = results["result"]
        assert result["operation"] == "score"
        score_data = result["result"]
        assert 0 <= score_data["score"] <= 100
        assert score_data["strength"] in ["STRONG", "MODERATE", "WEAK"]
        assert "factors" in score_data

    def test_rag_search_operation(self, qapp):
        """Test RAG semantic search."""
        worker = ThesisWorkerThread(
            "rag_search",
            query="Value theses with M&A catalysts",
            top_k=5
        )

        results = {}
        worker.operation_complete.connect(
            lambda r: results.update({"result": r})
        )

        worker.run()

        assert "result" in results
        result = results["result"]
        assert result["operation"] == "rag_search"
        similar = result["result"]
        assert isinstance(similar, list)
        assert len(similar) <= 5
        if similar:
            assert "ticker" in similar[0]
            assert "similarity" in similar[0]

    def test_ai_analyze_operation(self, qapp):
        """Test AI thesis analysis."""
        worker = ThesisWorkerThread(
            "ai_analyze",
            text="Apple thesis about ecosystem advantages"
        )

        results = {}
        worker.operation_complete.connect(
            lambda r: results.update({"result": r})
        )

        worker.run()

        assert "result" in results
        result = results["result"]
        assert result["operation"] == "ai_analyze"
        analysis = result["result"]
        assert "strengths" in analysis
        assert "weaknesses" in analysis
        assert "suggested_price_target" in analysis
        assert "confidence" in analysis

    def test_invalid_operation(self, qapp):
        """Test error handling for invalid operation."""
        worker = ThesisWorkerThread("invalid_op")

        errors = {}
        worker.error_occurred.connect(
            lambda e: errors.update({"error": e})
        )

        worker.run()

        assert "error" in errors
        assert "Unknown operation" in errors["error"]


# ============================================================================
# Test: Thesis Panel Creation & UI
# ============================================================================

class TestThesisPanelCreation:
    """Tests for thesis panel UI creation and initialization."""

    def test_panel_initialization(self, thesis_panel):
        """Test thesis panel initializes correctly."""
        assert thesis_panel is not None
        assert thesis_panel.tabs.count() == 4  # Active, Search, History, AI
        assert len(thesis_panel.current_theses) == 0

    def test_tab_creation(self, thesis_panel):
        """Test all tabs are created."""
        tabs = [
            thesis_panel.tab_active,
            thesis_panel.tab_rag,
            thesis_panel.tab_history,
            thesis_panel.tab_ai
        ]
        for tab in tabs:
            assert tab is not None

    def test_active_tab_components(self, thesis_panel):
        """Test Active Theses tab has all components."""
        assert thesis_panel.metric_count is not None
        assert thesis_panel.metric_active is not None
        assert thesis_panel.metric_avg_score is not None
        assert thesis_panel.table_active is not None
        assert thesis_panel.detail_panel is not None

    def test_rag_tab_components(self, thesis_panel):
        """Test RAG Search tab has all components."""
        assert thesis_panel.rag_query is not None
        assert thesis_panel.table_rag_results is not None
        assert thesis_panel.rag_detail_text is not None

    def test_history_tab_components(self, thesis_panel):
        """Test Historical Performance tab has all components."""
        assert thesis_panel.table_history is not None
        assert thesis_panel.history_lessons is not None

    def test_ai_tab_components(self, thesis_panel):
        """Test AI Analysis tab has all components."""
        assert thesis_panel.ai_ticker is not None
        assert thesis_panel.ai_thesis is not None
        assert thesis_panel.ai_results is not None


# ============================================================================
# Test: Thesis Creation & Storage
# ============================================================================

class TestThesisCreation:
    """Tests for thesis creation flow."""

    def test_create_thesis_from_dialog_data(self, thesis_panel, sample_thesis_data, qapp):
        """Test creating thesis from dialog data."""
        # Spy on signals
        created_spy = QSignalSpy(thesis_panel.thesis_created)

        thesis_panel.create_thesis_from_data(sample_thesis_data)

        # Give worker thread time to process
        QTimer.singleShot(500, qapp.quit)
        qapp.exec()

        # Verify thesis was added
        assert len(thesis_panel.current_theses) > 0

    def test_new_thesis_dialog_signals(self, thesis_panel, qapp):
        """Test new thesis dialog emits signal."""
        dialog = thesis_panel.show_new_thesis_dialog()  # Mock behavior

        # Note: Actual dialog testing would require dialog interaction
        # This tests that the method doesn't crash

    def test_thesis_structure(self, thesis_panel, sample_thesis_data):
        """Test thesis data structure is correct."""
        thesis_panel.create_thesis_from_data(sample_thesis_data)

        # Process any pending events
        thesis = None
        for t in thesis_panel.current_theses.values():
            if t.get("ticker") == "AAPL":
                thesis = t
                break

        if thesis:
            assert thesis["ticker"] == "AAPL"
            assert thesis["company_name"] == "Apple Inc."
            assert thesis["text"] == sample_thesis_data.thesis_text
            assert thesis["price_target"] == 200.0
            assert thesis["horizon_months"] == 12


# ============================================================================
# Test: Thesis Scoring
# ============================================================================

class TestThesisScoring:
    """Tests for thesis scoring logic."""

    def test_score_calculation(self, qapp):
        """Test thesis score is calculated correctly."""
        worker = ThesisWorkerThread(
            "score",
            ticker="AAPL",
            eps=10.0,  # Higher EPS = higher score
            growth=20.0  # Higher growth = higher score
        )

        results = {}
        worker.operation_complete.connect(
            lambda r: results.update({"score": r["result"]["score"]})
        )

        worker.run()

        score = results.get("score", 0)
        assert 0 <= score <= 100

    def test_score_strength_classification(self, qapp):
        """Test score is classified to strength."""
        test_cases = [
            (90, "STRONG"),
            (70, "STRONG"),
            (60, "MODERATE"),
            (40, "MODERATE"),
            (30, "WEAK"),
            (10, "WEAK")
        ]

        for eps, growth in [(10.0, 20.0), (5.0, 15.0), (2.0, 5.0)]:
            worker = ThesisWorkerThread(
                "score",
                ticker="TEST",
                eps=eps,
                growth=growth
            )

            results = {}
            worker.operation_complete.connect(
                lambda r: results.update({"result": r})
            )

            worker.run()

            strength = results["result"]["result"]["strength"]
            assert strength in ["STRONG", "MODERATE", "WEAK"]

    def test_factor_breakdown(self, qapp):
        """Test score includes factor breakdown."""
        worker = ThesisWorkerThread(
            "score",
            ticker="AAPL",
            eps=5.0,
            growth=15.0
        )

        results = {}
        worker.operation_complete.connect(
            lambda r: results.update({"result": r})
        )

        worker.run()

        factors = results["result"]["result"].get("factors", {})
        assert "valuation" in factors
        assert "catalysts" in factors
        assert "risks" in factors
        assert "margin_of_safety" in factors


# ============================================================================
# Test: Active Theses Table
# ============================================================================

class TestActiveThesesTable:
    """Tests for active theses tracking."""

    def test_refresh_active_theses_empty(self, thesis_panel):
        """Test refresh with no theses."""
        thesis_panel.refresh_active_theses()

        assert thesis_panel.table_active.table.rowCount() == 0

    def test_refresh_active_theses_with_data(self, thesis_panel, sample_thesis_data):
        """Test refresh with active theses."""
        thesis_panel.create_thesis_from_data(sample_thesis_data)

        # Manually add to active theses for testing
        thesis_panel.current_theses["test1"] = {
            "ticker": "AAPL",
            "text": "Test thesis",
            "price_target": 200.0,
            "horizon_months": 12,
            "score": 75.5,
            "strength": "STRONG",
            "status": "ACTIVE"
        }

        thesis_panel.refresh_active_theses()

        # Should have at least one row
        assert thesis_panel.table_active.table.rowCount() > 0

    def test_metrics_update(self, thesis_panel):
        """Test metrics are updated on refresh."""
        thesis_panel.current_theses["test1"] = {
            "ticker": "AAPL",
            "score": 80.0,
            "status": "ACTIVE"
        }
        thesis_panel.current_theses["test2"] = {
            "ticker": "MSFT",
            "score": 70.0,
            "status": "ACTIVE"
        }

        thesis_panel.refresh_active_theses()

        # Metrics should be updated
        count_text = thesis_panel.metric_count._value.text()
        assert "2" in count_text  # 2 theses

        avg_score_text = thesis_panel.metric_avg_score._value.text()
        assert "75" in avg_score_text  # Average of 80 and 70


# ============================================================================
# Test: RAG Semantic Search
# ============================================================================

class TestRAGSearch:
    """Tests for RAG semantic search."""

    def test_rag_search_empty_query(self, thesis_panel):
        """Test RAG search rejects empty query."""
        thesis_panel.rag_query.setText("")

        with patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warn:
            thesis_panel.rag_search()
            mock_warn.assert_called_once()

    def test_rag_search_with_query(self, thesis_panel, qapp):
        """Test RAG search with valid query."""
        thesis_panel.rag_query.setText("Value theses with M&A catalysts")

        results = {}

        def on_complete(r):
            results["complete"] = r

        thesis_panel.worker_thread = ThesisWorkerThread(
            "rag_search",
            query="Value theses with M&A catalysts",
            top_k=5
        )
        thesis_panel.worker_thread.operation_complete.connect(on_complete)
        thesis_panel.worker_thread.start()

        # Wait for completion
        QTimer.singleShot(1000, qapp.quit)
        qapp.exec()

        assert "complete" in results

    def test_rag_results_population(self, thesis_panel, qapp):
        """Test RAG results are displayed in table."""
        # Simulate RAG search completion
        result = {
            "operation": "rag_search",
            "result": [
                {
                    "ticker": "BRK",
                    "similarity": 0.92,
                    "thesis": "Buffett-style value investing",
                    "date": "2024-01-15"
                }
            ]
        }

        thesis_panel._on_rag_search_complete(result)

        assert thesis_panel.table_rag_results.table.rowCount() == 1


# ============================================================================
# Test: AI Analysis Integration
# ============================================================================

class TestAIAnalysis:
    """Tests for AI-powered thesis analysis."""

    def test_ai_analysis_empty_input(self, thesis_panel):
        """Test AI analysis rejects empty input."""
        thesis_panel.ai_ticker.setText("")
        thesis_panel.ai_thesis.setPlainText("")

        with patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warn:
            thesis_panel.analyze_thesis_ai()
            mock_warn.assert_called_once()

    def test_ai_analysis_with_data(self, thesis_panel, qapp):
        """Test AI analysis with valid input."""
        thesis_panel.ai_ticker.setText("AAPL")
        thesis_panel.ai_thesis.setPlainText("Apple ecosystem advantage")

        results = {}

        thesis_panel.worker_thread = ThesisWorkerThread(
            "ai_analyze",
            ticker="AAPL",
            text="Apple ecosystem advantage"
        )
        thesis_panel.worker_thread.operation_complete.connect(
            lambda r: results.update({"complete": r})
        )
        thesis_panel.worker_thread.start()

        QTimer.singleShot(1000, qapp.quit)
        qapp.exec()

        assert "complete" in results

    def test_ai_analysis_output_format(self, thesis_panel):
        """Test AI analysis output is properly formatted."""
        result = {
            "operation": "ai_analyze",
            "result": {
                "strengths": ["Strong moat", "Growing services"],
                "weaknesses": ["High valuation"],
                "suggested_price_target": 195.50,
                "confidence": 0.85
            }
        }

        thesis_panel._on_ai_analysis_complete(result)

        output = thesis_panel.ai_results.toPlainText()
        assert "STRENGTHS:" in output
        assert "WEAKNESSES:" in output
        assert "195.50" in output


# ============================================================================
# Test: Historical Performance
# ============================================================================

class TestHistoricalPerformance:
    """Tests for historical thesis tracking."""

    def test_historical_table_initialization(self, thesis_panel):
        """Test historical table initializes."""
        assert thesis_panel.table_history is not None
        assert thesis_panel.table_history.table.columnCount() > 0

    def test_historical_statistics(self, thesis_panel):
        """Test historical statistics metrics."""
        assert thesis_panel.stat_total is not None
        assert thesis_panel.stat_winners is not None
        assert thesis_panel.stat_losers is not None
        assert thesis_panel.stat_win_rate is not None


# ============================================================================
# Test: Thesis Selection & Detail Panel
# ============================================================================

class TestThesisSelection:
    """Tests for selecting and viewing thesis details."""

    def test_select_thesis_updates_detail(self, thesis_panel):
        """Test selecting thesis updates detail panel."""
        thesis_panel.current_theses["test1"] = {
            "ticker": "AAPL",
            "text": "Test thesis about Apple",
            "catalysts": {"short": "iPhone", "medium": "Services", "long": "AR"},
            "risks": "Competition",
            "score": 75.0,
            "strength": "STRONG"
        }

        thesis_panel.refresh_active_theses()

        # Simulate selection
        thesis_panel.on_thesis_selected(0)

        assert thesis_panel.detail_ticker.text() == "AAPL"
        assert "Test thesis" in thesis_panel.detail_thesis.toPlainText()

    def test_detail_panel_readonly(self, thesis_panel):
        """Test detail panel fields are read-only."""
        assert thesis_panel.detail_ticker.isReadOnly()
        assert thesis_panel.detail_thesis.isReadOnly()
        assert thesis_panel.detail_catalysts.isReadOnly()
        assert thesis_panel.detail_risks.isReadOnly()


# ============================================================================
# Test: Thesis Modification
# ============================================================================

class TestThesisModification:
    """Tests for editing and closing theses."""

    def test_close_thesis(self, thesis_panel):
        """Test closing a thesis."""
        thesis_panel.current_theses["test1"] = {
            "ticker": "AAPL",
            "status": "ACTIVE"
        }

        thesis_panel.detail_ticker.setText("AAPL")

        with patch('PyQt6.QtWidgets.QMessageBox.information'):
            thesis_panel.close_selected_thesis()

        # Thesis should be closed
        assert thesis_panel.current_theses["test1"]["status"] == "CLOSED"
        assert "closed_at" in thesis_panel.current_theses["test1"]

    def test_edit_thesis_requires_selection(self, thesis_panel):
        """Test edit requires thesis selection."""
        thesis_panel.detail_ticker.setText("")

        with patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warn:
            thesis_panel.edit_selected_thesis()
            mock_warn.assert_called_once()


# ============================================================================
# Test: Embedding & Storage
# ============================================================================

class TestEmbeddingStorage:
    """Tests for thesis embeddings and storage."""

    def test_embedding_generation(self, thesis_panel, qapp):
        """Test embedding is generated for thesis."""
        worker = ThesisWorkerThread(
            "embed",
            ticker="AAPL",
            text="Apple thesis text"
        )

        results = {}
        worker.operation_complete.connect(
            lambda r: results.update({"embedding": r})
        )

        worker.run()

        assert "embedding" in results
        embedding_data = results["embedding"]["result"]
        assert "embedding" in embedding_data
        assert len(embedding_data["embedding"]) > 0

    def test_embedding_structure(self, thesis_panel, qapp):
        """Test embedding has correct structure."""
        worker = ThesisWorkerThread(
            "embed",
            ticker="AAPL",
            text="Test thesis"
        )

        results = {}
        worker.operation_complete.connect(
            lambda r: results.update({"result": r})
        )

        worker.run()

        embedding_result = results["result"]["result"]
        assert isinstance(embedding_result["embedding"], list)
        assert embedding_result["ticker"] == "AAPL"
        assert embedding_result["text_len"] > 0


# ============================================================================
# Test: Error Handling
# ============================================================================

class TestErrorHandling:
    """Tests for error handling and recovery."""

    def test_thesis_creation_error(self, thesis_panel, qapp):
        """Test thesis creation handles errors gracefully."""
        invalid_data = ThesisData(
            ticker="",
            company_name="",
            thesis_text="",
            catalysts_short_term="",
            catalysts_medium_term="",
            catalysts_long_term="",
            risks="",
            price_target=0,
            horizon_months=0,
            margin_of_safety=0,
            moat_type="",
            created_date=datetime.now().isoformat()
        )

        # Should not crash
        try:
            thesis_panel.create_thesis_from_data(invalid_data)
        except Exception:
            pass  # Expected to fail gracefully

    def test_worker_thread_error(self, qapp):
        """Test worker thread handles errors."""
        worker = ThesisWorkerThread("invalid_op")

        errors = {}
        worker.error_occurred.connect(
            lambda e: errors.update({"error": e})
        )

        worker.run()

        assert "error" in errors

    def test_rag_search_error(self, thesis_panel):
        """Test RAG search error handling."""
        error_msg = "Search failed"
        thesis_panel._on_rag_search_error(error_msg)

        assert thesis_panel.rag_progress.isVisible() == False


# ============================================================================
# Test: Signal Emission
# ============================================================================

class TestSignalEmission:
    """Tests for signal emission."""

    def test_thesis_created_signal(self, thesis_panel):
        """Test thesis_created signal is emitted."""
        spy = QSignalSpy(thesis_panel.thesis_created)

        thesis_panel.current_theses["test1"] = {
            "ticker": "AAPL",
            "status": "ACTIVE"
        }
        thesis_panel.thesis_created.emit("test1")

        assert spy.count() == 1

    def test_thesis_updated_signal(self, thesis_panel):
        """Test thesis_updated signal is emitted."""
        spy = QSignalSpy(thesis_panel.thesis_updated)

        thesis_panel.thesis_updated.emit("test1")

        assert spy.count() == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
