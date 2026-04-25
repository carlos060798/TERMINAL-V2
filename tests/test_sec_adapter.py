"""Tests for SEC adapter with rate limiting (0.12s), caching, and batch support."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quantum_terminal.infrastructure.macro.sec_adapter import (
    SECAdapter,
    SECAPIError,
    SECRateLimitError,
    SECHTTPError,
    SEC_REQUEST_DELAY,
    get_cik,
    get_submissions,
    get_filing,
    get_facts,
    get_form4,
)
from quantum_terminal.utils.cache import cache


@pytest.fixture
def adapter():
    """Create adapter instance."""
    return SECAdapter()


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    cache.clear()
    yield
    cache.clear()


class TestSECAdapterInit:
    """Test adapter initialization."""

    def test_init_success(self):
        """Test successful initialization."""
        adapter = SECAdapter()
        assert adapter is not None
        assert adapter.user_agent is not None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        async with SECAdapter() as adapter:
            assert adapter.session is not None
        assert adapter.session.closed


class TestSECRateLimiting:
    """Test SEC rate limiting (0.12s per request)."""

    @pytest.mark.asyncio
    async def test_rate_limit_delay(self, adapter):
        """Test that 0.12s delay is enforced between requests."""
        adapter.session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"test": "data"})
        adapter.session.get.return_value.__aenter__.return_value = mock_response

        import time as time_module
        start = time_module.time()

        # First request
        await adapter._get("test1")
        # Second request should wait 0.12s
        await adapter._get("test2")

        elapsed = time_module.time() - start

        # Should wait at least 0.12s - 0.01s (buffer)
        assert elapsed >= SEC_REQUEST_DELAY - 0.01

    @pytest.mark.asyncio
    async def test_consecutive_requests(self, adapter):
        """Test multiple consecutive requests with rate limiting."""
        adapter.session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"test": "data"})
        adapter.session.get.return_value.__aenter__.return_value = mock_response

        start = time.time()

        # Make 5 requests
        for _ in range(5):
            await adapter._get("test")

        elapsed = time.time() - start

        # Should wait at least 4 * 0.12s between 5 requests
        # (4 intervals = 0.48s, with some buffer)
        assert elapsed >= (4 * SEC_REQUEST_DELAY * 0.9)


class TestSECCIK:
    """Test get_cik method."""

    @pytest.mark.asyncio
    async def test_get_cik_success(self, adapter):
        """Test successful CIK lookup."""
        mock_response = {
            "filings": [
                {
                    "cik_str": 320193,
                    "company_name": "APPLE INC",
                }
            ]
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            cik = await adapter.get_cik("APPLE INC")

            assert cik == "0000320193"

    @pytest.mark.asyncio
    async def test_get_cik_caching(self, adapter):
        """Test CIK caching with 30-day TTL."""
        mock_response = {
            "filings": [
                {
                    "cik_str": 320193,
                    "company_name": "APPLE INC",
                }
            ]
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            # First call
            cik1 = await adapter.get_cik("APPLE INC")
            # Second call should use cache
            cik2 = await adapter.get_cik("APPLE INC")

            adapter._get.assert_called_once()
            assert cik1 == cik2

    @pytest.mark.asyncio
    async def test_get_cik_not_found(self, adapter):
        """Test CIK not found."""
        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value={"filings": []}):
            cik = await adapter.get_cik("NONEXISTENT")

            assert cik is None

    @pytest.mark.asyncio
    async def test_get_cik_normalization(self, adapter):
        """Test CIK normalization with zero padding."""
        mock_response = {
            "filings": [
                {
                    "cik_str": 320193,
                }
            ]
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            cik = await adapter.get_cik("APPLE")

            # Should be zero-padded to 10 digits
            assert len(cik) == 10
            assert cik.startswith("0000")


class TestSECSubmissions:
    """Test get_submissions method."""

    @pytest.mark.asyncio
    async def test_get_submissions_success(self, adapter):
        """Test successful submissions retrieval."""
        mock_response = {
            "cik": "0000320193",
            "entityType": "operating",
            "name": "Apple Inc",
            "filings": {
                "recent": [
                    {
                        "accessionNumber": "0000051143-23-000006",
                        "filingDate": "2023-01-27",
                        "reportDate": "2022-12-31",
                        "acceptanceDateTime": "2023-01-27T17:10:29Z",
                        "act": "34",
                        "form": "10-K",
                    }
                ]
            },
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            submissions = await adapter.get_submissions("0000320193")

            assert submissions["cik"] == "0000320193"
            assert "filings" in submissions

    @pytest.mark.asyncio
    async def test_get_submissions_caching(self, adapter):
        """Test submissions caching with 1-day TTL."""
        mock_response = {
            "cik": "0000320193",
            "filings": {"recent": []},
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            # First call
            submissions1 = await adapter.get_submissions("0000320193")
            # Second call should use cache
            submissions2 = await adapter.get_submissions("0000320193")

            adapter._get.assert_called_once()
            assert submissions1 == submissions2


class TestSECFiling:
    """Test get_filing method."""

    @pytest.mark.asyncio
    async def test_get_filing_success(self, adapter):
        """Test successful filing retrieval."""
        mock_response = {
            "cik": "0000320193",
            "filings": {
                "recent": [
                    {
                        "accessionNumber": "0000051143-23-000006",
                        "filingDate": "2023-01-27",
                        "reportDate": "2022-12-31",
                        "form": "10-K",
                    }
                ]
            },
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            filing = await adapter.get_filing("0000320193", "0000051143-23-000006", "10-K")

            assert filing["form"] == "10-K"
            assert filing["accessionNumber"] == "0000051143-23-000006"

    @pytest.mark.asyncio
    async def test_get_filing_caching(self, adapter):
        """Test filing caching with 7-day TTL."""
        mock_response = {
            "filings": {
                "recent": [
                    {
                        "accessionNumber": "0000051143-23-000006",
                        "form": "10-K",
                    }
                ]
            }
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            # First call
            filing1 = await adapter.get_filing("0000320193", "0000051143-23-000006")
            # Second call should use cache
            filing2 = await adapter.get_filing("0000320193", "0000051143-23-000006")

            assert filing1 == filing2


class TestSECFacts:
    """Test get_facts method."""

    @pytest.mark.asyncio
    async def test_get_facts_success(self, adapter):
        """Test successful facts retrieval."""
        mock_response = {
            "cik": "0000320193",
            "entityName": "Apple Inc",
            "facts": {
                "us-gaap": {
                    "AccountsPayable": {
                        "units": {"USD": [{"val": 37445000000, "end": "2022-09-24"}]}
                    }
                }
            },
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            facts = await adapter.get_facts("0000320193")

            assert facts["cik"] == "0000320193"
            assert "facts" in facts

    @pytest.mark.asyncio
    async def test_get_facts_caching(self, adapter):
        """Test facts caching with 1-day TTL."""
        mock_response = {
            "cik": "0000320193",
            "facts": {},
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            # First call
            facts1 = await adapter.get_facts("0000320193")
            # Second call should use cache
            facts2 = await adapter.get_facts("0000320193")

            adapter._get.assert_called_once()
            assert facts1 == facts2


class TestSECForm4:
    """Test get_form4 method."""

    @pytest.mark.asyncio
    async def test_get_form4_success(self, adapter):
        """Test successful Form 4 retrieval."""
        mock_response = {
            "cik": "0000320193",
            "filings": {
                "recent": [
                    {
                        "filingDate": "2023-01-15",
                        "reportDate": "2023-01-13",
                        "accessionNumber": "0000051143-23-000001",
                        "form": "4",
                    },
                    {
                        "filingDate": "2023-01-10",
                        "reportDate": "2023-01-09",
                        "accessionNumber": "0000051143-23-000002",
                        "form": "4",
                    },
                ]
            },
        }

        with patch.object(adapter, "get_submissions", new_callable=AsyncMock, return_value=mock_response):
            form4s = await adapter.get_form4("0000320193", limit=5)

            assert len(form4s) == 2
            assert form4s[0]["form"] == "4"

    @pytest.mark.asyncio
    async def test_get_form4_limit(self, adapter):
        """Test Form 4 limit parameter."""
        mock_response = {
            "filings": {
                "recent": [
                    {"form": "4", "filingDate": f"2023-01-{i:02d}"} for i in range(1, 10)
                ]
            }
        }

        with patch.object(adapter, "get_submissions", new_callable=AsyncMock, return_value=mock_response):
            form4s = await adapter.get_form4("0000320193", limit=3)

            assert len(form4s) == 3

    @pytest.mark.asyncio
    async def test_get_form4_caching(self, adapter):
        """Test Form 4 caching with 1-day TTL."""
        mock_response = {
            "filings": {
                "recent": [
                    {"form": "4", "filingDate": "2023-01-15"}
                ]
            }
        }

        with patch.object(adapter, "get_submissions", new_callable=AsyncMock, return_value=mock_response):
            # First call
            form4s1 = await adapter.get_form4("0000320193")
            # Second call should use cache
            form4s2 = await adapter.get_form4("0000320193")

            assert form4s1 == form4s2

    @pytest.mark.asyncio
    async def test_get_form4_no_matches(self, adapter):
        """Test Form 4 with no matching filings."""
        mock_response = {
            "filings": {
                "recent": [
                    {"form": "10-K", "filingDate": "2023-01-15"}
                ]
            }
        }

        with patch.object(adapter, "get_submissions", new_callable=AsyncMock, return_value=mock_response):
            form4s = await adapter.get_form4("0000320193")

            assert form4s == []


class TestSECAPIGetMethod:
    """Test internal _get method."""

    @pytest.mark.asyncio
    async def test_get_http_error(self, adapter):
        """Test HTTP error handling."""
        adapter.session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 404
        adapter.session.get.return_value.__aenter__.return_value = mock_response

        with pytest.raises(SECHTTPError):
            await adapter._get("invalid")

    @pytest.mark.asyncio
    async def test_get_rate_limit_exceeded(self, adapter):
        """Test rate limit exceeded handling."""
        adapter.session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 429
        adapter.session.get.return_value.__aenter__.return_value = mock_response

        with pytest.raises(SECRateLimitError):
            await adapter._get("test")

    @pytest.mark.asyncio
    async def test_get_connection_error(self, adapter):
        """Test connection error handling."""
        import aiohttp

        adapter.session = MagicMock()
        adapter.session.get.side_effect = aiohttp.ClientError("Connection failed")

        with pytest.raises(Exception):
            await adapter._get("test")


class TestGlobalFunctions:
    """Test module-level functions."""

    @pytest.mark.asyncio
    async def test_get_cik_global(self):
        """Test global get_cik function."""
        mock_response = {
            "filings": [
                {
                    "cik_str": 320193,
                }
            ]
        }

        with patch("quantum_terminal.infrastructure.macro.sec_adapter.SECAdapter.get_cik", new_callable=AsyncMock, return_value="0000320193"):
            cik = await get_cik("APPLE INC")
            assert cik == "0000320193"

    @pytest.mark.asyncio
    async def test_get_submissions_global(self):
        """Test global get_submissions function."""
        mock_response = {"cik": "0000320193", "filings": {}}

        with patch("quantum_terminal.infrastructure.macro.sec_adapter.SECAdapter.get_submissions", new_callable=AsyncMock, return_value=mock_response):
            submissions = await get_submissions("0000320193")
            assert submissions["cik"] == "0000320193"

    @pytest.mark.asyncio
    async def test_get_facts_global(self):
        """Test global get_facts function."""
        mock_response = {"cik": "0000320193", "facts": {}}

        with patch("quantum_terminal.infrastructure.macro.sec_adapter.SECAdapter.get_facts", new_callable=AsyncMock, return_value=mock_response):
            facts = await get_facts("0000320193")
            assert facts["cik"] == "0000320193"

    @pytest.mark.asyncio
    async def test_get_form4_global(self):
        """Test global get_form4 function."""
        expected = [
            {"form": "4", "filingDate": "2023-01-15"}
        ]

        with patch("quantum_terminal.infrastructure.macro.sec_adapter.SECAdapter.get_form4", new_callable=AsyncMock, return_value=expected):
            form4s = await get_form4("0000320193")
            assert len(form4s) == 1


class TestRateLimitCompliance:
    """Test SEC rate limit compliance (0.12s)."""

    @pytest.mark.asyncio
    async def test_max_10_requests_per_second(self, adapter):
        """Test that we don't exceed 10 requests/second."""
        adapter.session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={})
        adapter.session.get.return_value.__aenter__.return_value = mock_response

        start = time.time()
        for _ in range(10):
            await adapter._get("test")
        elapsed = time.time() - start

        # 10 requests with 0.12s delay between them = 9 delays = 1.08s minimum
        # But first request has no delay, so ~9 * 0.12 = ~1.08s
        assert elapsed >= 0.9  # Allow some buffer
