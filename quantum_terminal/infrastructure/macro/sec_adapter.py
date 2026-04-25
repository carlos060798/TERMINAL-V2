"""SEC EDGAR API adapter for regulatory filings and facts.

Provides access to SEC company information, filings, and financial facts
via the SEC EDGAR API. Implements rate limiting (0.12s delay per request)
and configurable TTL caching.

Rate Limit: 1 request per 0.12 seconds (10 requests/second limit)
Cache TTL:
- CIK lookups: 30 days
- Submissions: 1 day
- Filings: 7 days
- Facts: 1 day
- Form 4: 1 day
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

import aiohttp
import pandas as pd

from quantum_terminal.utils.cache import cache
from quantum_terminal.utils.logger import get_logger

logger = get_logger(__name__)

# SEC rate limit: 10 requests per second (delay of 0.1 second minimum)
# We use 0.12s to be conservative
SEC_REQUEST_DELAY = 0.12


class SECAPIError(Exception):
    """Base exception for SEC API errors."""

    pass


class SECRateLimitError(SECAPIError):
    """Exception raised when rate limit is exceeded."""

    pass


class SECHTTPError(SECAPIError):
    """Exception raised for HTTP errors."""

    pass


class SECConnectionError(SECAPIError):
    """Exception raised for connection errors."""

    pass


class SECAdapter:
    """Adapter for SEC EDGAR API.

    Provides methods for:
    - CIK lookup by company name or ticker
    - Company submissions and filings
    - Financial facts (XBRL)
    - Form 4 insider trading data
    - Batch operations with rate limit management
    """

    BASE_URL = "https://data.sec.gov"

    def __init__(self):
        """Initialize SEC adapter."""
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_request_time: float = 0
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        logger.info("SECAdapter initialized (rate limit: 0.12s per request)")

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _rate_limit_wait(self) -> None:
        """Enforce SEC rate limit (0.12s between requests)."""
        elapsed = time.time() - self.last_request_time
        if elapsed < SEC_REQUEST_DELAY:
            wait_time = SEC_REQUEST_DELAY - elapsed
            logger.debug(f"Rate limit wait: {wait_time:.3f}s")
            await asyncio.sleep(wait_time)
        self.last_request_time = time.time()

    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Make GET request to SEC API with rate limiting.

        Args:
            endpoint: API endpoint.
            params: Query parameters.

        Returns:
            JSON response as dictionary or list.

        Raises:
            SECHTTPError: If HTTP error occurs.
            SECConnectionError: If connection fails.
        """
        # Enforce rate limit
        await self._rate_limit_wait()

        if params is None:
            params = {}

        url = f"{self.BASE_URL}/{endpoint}"

        if not self.session:
            self.session = aiohttp.ClientSession()

        headers = {"User-Agent": self.user_agent}

        try:
            async with self.session.get(
                url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status == 429:
                    raise SECRateLimitError(f"SEC rate limit: {response.reason}")
                elif response.status >= 400:
                    raise SECHTTPError(f"SEC HTTP {response.status}: {response.reason}")

                data = await response.json()
                logger.debug(f"SEC GET {endpoint}: {response.status}")
                return data

        except aiohttp.ClientError as e:
            raise SECConnectionError(f"SEC connection error: {str(e)}") from e

    async def get_cik(self, company_name: str) -> Optional[str]:
        """Get CIK number for company by name or ticker.

        Args:
            company_name: Company name or ticker symbol.

        Returns:
            CIK number as string (padded with zeros) or None if not found.

        Raises:
            SECHTTPError: If API error occurs.

        Examples:
            >>> adapter = SECAdapter()
            >>> cik = await adapter.get_cik("APPLE INC")
            >>> print(cik)
            0000320193
        """
        cache_key = f"sec_cik_{company_name.upper()}"

        # Try cache (30 day TTL for CIK lookups)
        cached = cache.get_with_ttl(cache_key, ttl_minutes=30 * 24 * 60)
        if cached:
            logger.debug(f"CIK cache HIT: {company_name}")
            return cached

        try:
            # Use company ticker endpoint
            data = await self._get(f"files/fall{company_name.lower()}.json")

            if not data:
                logger.warning(f"No CIK found for {company_name}")
                return None

            # Parse the JSON to find CIK
            for entry in data.get("filings", []):
                if entry.get("cik_str"):
                    cik = str(entry["cik_str"]).zfill(10)
                    cache.set_with_ttl(cache_key, cik, ttl_minutes=30 * 24 * 60)
                    logger.debug(f"CIK cache SET: {company_name} = {cik}")
                    return cik

            logger.warning(f"No CIK found for {company_name}")
            return None

        except SECHTTPError:
            raise
        except Exception as e:
            logger.error(f"Error getting CIK for {company_name}: {e}")
            raise SECAPIError(f"Failed to get CIK for {company_name}") from e

    async def get_submissions(self, cik: str) -> Dict[str, Any]:
        """Get company submissions and filings.

        Args:
            cik: CIK number (with or without zero padding).

        Returns:
            Dictionary with filing information.

        Raises:
            SECHTTPError: If API error occurs.

        Examples:
            >>> adapter = SECAdapter()
            >>> submissions = await adapter.get_submissions("0000320193")
            >>> print(len(submissions["filings"]["recent"]))
        """
        # Normalize CIK
        cik_normalized = cik.lstrip("0") or "0"
        cache_key = f"sec_submissions_{cik_normalized}"

        # Try cache (1 day TTL)
        cached = cache.get_with_ttl(cache_key, ttl_minutes=60 * 24)
        if cached:
            logger.debug(f"Submissions cache HIT: {cik}")
            return cached

        try:
            data = await self._get(f"submissions/CIK{cik_normalized}.json")

            # Cache for 1 day
            cache.set_with_ttl(cache_key, data, ttl_minutes=60 * 24)
            logger.debug(f"Submissions cache SET: {cik}")

            return data

        except Exception as e:
            logger.error(f"Error getting submissions for CIK {cik}: {e}")
            raise SECAPIError(f"Failed to get submissions for CIK {cik}") from e

    async def get_filing(
        self, cik: str, accession_number: str, filing_type: str = "10-K"
    ) -> Dict[str, Any]:
        """Get specific filing information.

        Args:
            cik: CIK number.
            accession_number: Accession number (format: 0000000000-00-000000).
            filing_type: Type of filing (10-K, 10-Q, 8-K, etc.).

        Returns:
            Dictionary with filing data.

        Raises:
            SECHTTPError: If API error occurs.

        Examples:
            >>> adapter = SECAdapter()
            >>> filing = await adapter.get_filing("0000320193", "0000051143-23-000006")
            >>> print(filing["reportDate"])
        """
        cik_normalized = cik.lstrip("0") or "0"
        cache_key = f"sec_filing_{cik_normalized}_{accession_number}"

        # Try cache (7 day TTL for filings)
        cached = cache.get_with_ttl(cache_key, ttl_minutes=7 * 24 * 60)
        if cached:
            logger.debug(f"Filing cache HIT: {accession_number}")
            return cached

        try:
            # Accession number format: 0000000000-00-000000 -> 0000000000/00-000000
            accession_url = accession_number.replace("-", "/", 1)
            data = await self._get(
                f"cgi-bin/browse-edgar?action=getcompany&CIK={cik_normalized}"
                f"&type={filing_type}&dateb=&owner=exclude&count=100&output=json"
            )

            # Filter to the specific accession
            filings = data.get("filings", {}).get("recent", [])
            filing_data = None
            for filing in filings:
                if filing.get("accessionNumber") == accession_number:
                    filing_data = filing
                    break

            if filing_data:
                cache.set_with_ttl(cache_key, filing_data, ttl_minutes=7 * 24 * 60)
                logger.debug(f"Filing cache SET: {accession_number}")
                return filing_data

            raise SECAPIError(f"Filing {accession_number} not found for CIK {cik}")

        except Exception as e:
            logger.error(f"Error getting filing {accession_number}: {e}")
            raise SECAPIError(f"Failed to get filing {accession_number}") from e

    async def get_facts(self, cik: str, taxonomy: str = "us-gaap") -> Dict[str, Any]:
        """Get financial facts (XBRL) for company.

        Args:
            cik: CIK number.
            taxonomy: Taxonomy type ("us-gaap", "ifrs-full", "dei").

        Returns:
            Dictionary with financial facts.

        Raises:
            SECHTTPError: If API error occurs.

        Examples:
            >>> adapter = SECAdapter()
            >>> facts = await adapter.get_facts("0000320193")
            >>> print(facts["facts"]["us-gaap"].keys())
        """
        cik_normalized = cik.lstrip("0") or "0"
        cache_key = f"sec_facts_{cik_normalized}_{taxonomy}"

        # Try cache (1 day TTL)
        cached = cache.get_with_ttl(cache_key, ttl_minutes=60 * 24)
        if cached:
            logger.debug(f"Facts cache HIT: {cik}")
            return cached

        try:
            data = await self._get(f"api/xbrl/companyfacts/CIK{cik_normalized}.json")

            # Cache for 1 day
            cache.set_with_ttl(cache_key, data, ttl_minutes=60 * 24)
            logger.debug(f"Facts cache SET: {cik}")

            return data

        except Exception as e:
            logger.error(f"Error getting facts for CIK {cik}: {e}")
            raise SECAPIError(f"Failed to get facts for CIK {cik}") from e

    async def get_form4(self, cik: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get Form 4 insider trading filings.

        Note: This endpoint has stricter rate limits. Use sparingly.

        Args:
            cik: CIK number.
            limit: Maximum number of Form 4 filings to return.

        Returns:
            List of Form 4 filings.

        Raises:
            SECHTTPError: If API error occurs.

        Examples:
            >>> adapter = SECAdapter()
            >>> form4s = await adapter.get_form4("0000320193", limit=5)
            >>> for form4 in form4s:
            ...     print(form4["filingDate"])
        """
        cache_key = f"sec_form4_{cik}"

        # Try cache (1 day TTL)
        cached = cache.get_with_ttl(cache_key, ttl_minutes=60 * 24)
        if cached:
            logger.debug(f"Form4 cache HIT: {cik}")
            return cached

        try:
            submissions = await self.get_submissions(cik)

            # Filter Form 4 filings
            form4_filings = []
            for filing in submissions.get("filings", {}).get("recent", []):
                if filing.get("form") == "4":
                    form4_filings.append(
                        {
                            "filingDate": filing.get("filingDate"),
                            "reportDate": filing.get("reportDate"),
                            "accessionNumber": filing.get("accessionNumber"),
                            "form": filing.get("form"),
                        }
                    )
                    if len(form4_filings) >= limit:
                        break

            # Cache for 1 day
            cache.set_with_ttl(cache_key, form4_filings, ttl_minutes=60 * 24)
            logger.debug(f"Form4 cache SET: {cik} ({len(form4_filings)} filings)")

            return form4_filings

        except Exception as e:
            logger.error(f"Error getting Form 4 for CIK {cik}: {e}")
            raise SECAPIError(f"Failed to get Form 4 for CIK {cik}") from e


# Global adapter instance
_sec_adapter: Optional[SECAdapter] = None


async def get_cik(company_name: str) -> Optional[str]:
    """Get CIK using global adapter."""
    global _sec_adapter
    if _sec_adapter is None:
        _sec_adapter = SECAdapter()
    return await _sec_adapter.get_cik(company_name)


async def get_submissions(cik: str) -> Dict[str, Any]:
    """Get submissions using global adapter."""
    global _sec_adapter
    if _sec_adapter is None:
        _sec_adapter = SECAdapter()
    return await _sec_adapter.get_submissions(cik)


async def get_filing(cik: str, accession_number: str, filing_type: str = "10-K") -> Dict[str, Any]:
    """Get filing using global adapter."""
    global _sec_adapter
    if _sec_adapter is None:
        _sec_adapter = SECAdapter()
    return await _sec_adapter.get_filing(cik, accession_number, filing_type)


async def get_facts(cik: str, taxonomy: str = "us-gaap") -> Dict[str, Any]:
    """Get facts using global adapter."""
    global _sec_adapter
    if _sec_adapter is None:
        _sec_adapter = SECAdapter()
    return await _sec_adapter.get_facts(cik, taxonomy)


async def get_form4(cik: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get Form 4 filings using global adapter."""
    global _sec_adapter
    if _sec_adapter is None:
        _sec_adapter = SECAdapter()
    return await _sec_adapter.get_form4(cik, limit)
