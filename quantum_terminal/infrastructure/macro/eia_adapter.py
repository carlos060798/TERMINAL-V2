"""EIA (U.S. Energy Information Administration) adapter for energy market data.

Provides async/await interface to EIA API with:
- Token bucket rate limiting (120 req/hour)
- 24-hour caching for energy data
- Focus on crude oil, natural gas, refinery operations
- Specific exception handling

Key series:
- Crude Oil WTI: West Texas Intermediate (USD/barrel)
- Crude Oil Brent: Brent Blend (USD/barrel)
- Natural Gas: Henry Hub (USD/MMBtu)
- Petroleum Inventories: Strategic reserves
- Refinery Utilization: % capacity
"""

import asyncio
from datetime import datetime
from typing import Any, Optional

import aiohttp

from quantum_terminal.config import settings
from quantum_terminal.utils.cache import cache
from quantum_terminal.utils.logger import get_logger
from quantum_terminal.utils.rate_limiter import rate_limiter

logger = get_logger(__name__)

# Register EIA rate limiter (120 req/hour)
rate_limiter.register("eia", 120, 60)


class EIAException(Exception):
    """Base exception for EIA adapter errors."""
    pass


class EIARateLimitException(EIAException):
    """Raised when EIA API rate limit is exceeded."""
    pass


class EIAAuthException(EIAException):
    """Raised when EIA API key is missing or invalid."""
    pass


class EIASeriesException(EIAException):
    """Raised when requested series is not found."""
    pass


class EIADataException(EIAException):
    """Raised when data retrieval or parsing fails."""
    pass


class EIAAdapter:
    """Async adapter for EIA API.

    Provides methods to fetch energy market data with caching and rate limiting.

    Examples:
        >>> adapter = EIAAdapter()
        >>> wti = await adapter.get_crude_oil_wti()
        >>> gas = await adapter.get_natural_gas()
        >>> refinery = await adapter.get_refinery_utilization()
    """

    BASE_URL = "https://api.eia.gov/v2"
    TIMEOUT = 30

    # Series IDs for common energy data
    SERIES = {
        "crude_oil_wti": {
            "route": "petroleum/pri/spt",
            "data": "DCOILWTICO",
        },
        "crude_oil_brent": {
            "route": "petroleum/pri/spt",
            "data": "DCOILBRENTEU",
        },
        "natural_gas": {
            "route": "naturalgas/pri/fut",
            "data": "DHHNGSP",
        },
        "crude_inventories": {
            "route": "petroleum/stoc/wstis",
            "data": "WCSSTCR",
        },
        "refinery_utilization": {
            "route": "petroleum/refmyc/refinerymyc",
            "data": "MCRRTUS",
        },
    }

    def __init__(self, api_key: Optional[str] = None):
        """Initialize EIA adapter.

        Args:
            api_key: EIA API key. Defaults to settings.eia_api_key.

        Raises:
            EIAAuthException: If API key is not provided.
        """
        self.api_key = api_key or settings.eia_api_key
        if not self.api_key:
            raise EIAAuthException("EIA_API_KEY not configured in .env")

        self.session: Optional[aiohttp.ClientSession] = None
        logger.info("EIAAdapter initialized")

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure session exists, create if needed."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _request(
        self,
        route: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Make HTTP request to EIA API.

        Args:
            route: API route (e.g., "petroleum/pri/spt").
            params: Query parameters.

        Returns:
            Response JSON.

        Raises:
            EIARateLimitException: If rate limited.
            EIADataException: If request fails.
        """
        # Check rate limit
        if not rate_limiter.allow_request("eia"):
            raise EIARateLimitException("EIA rate limit exceeded (120 req/hour)")

        session = await self._ensure_session()

        url = f"{self.BASE_URL}/{route}"
        params = params or {}
        params["api_key"] = self.api_key

        try:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.TIMEOUT),
            ) as response:
                if response.status == 401:
                    raise EIAAuthException("Invalid API key")
                elif response.status == 429:
                    raise EIARateLimitException("Rate limit exceeded")
                elif response.status == 404:
                    raise EIASeriesException("Series not found")
                elif response.status >= 400:
                    raise EIADataException(f"HTTP {response.status}")

                data = await response.json()
                logger.debug(f"EIA request successful: {route}")
                return data

        except asyncio.TimeoutError:
            raise EIADataException(f"Request timeout to {route}")
        except EIAException:
            raise
        except Exception as e:
            logger.error(f"EIA request failed: {e}")
            raise EIADataException(f"Request failed: {str(e)}")

    async def get_crude_oil_wti(self) -> Optional[float]:
        """Get latest WTI crude oil price (USD/barrel).

        Returns:
            Latest price or None if unavailable.

        Examples:
            >>> wti = await adapter.get_crude_oil_wti()
            >>> print(f"WTI: ${wti}/barrel")
        """
        cache_key = "eia_crude_oil_wti_latest"

        def fetch_fn():
            return asyncio.run(self._fetch_latest("crude_oil_wti"))

        try:
            return cache.get_macro(cache_key, fetch_fn)
        except EIAException:
            raise
        except Exception as e:
            logger.error(f"Error fetching WTI: {e}")
            return None

    async def get_crude_oil_brent(self) -> Optional[float]:
        """Get latest Brent crude oil price (USD/barrel).

        Returns:
            Latest price or None if unavailable.

        Examples:
            >>> brent = await adapter.get_crude_oil_brent()
            >>> print(f"Brent: ${brent}/barrel")
        """
        cache_key = "eia_crude_oil_brent_latest"

        def fetch_fn():
            return asyncio.run(self._fetch_latest("crude_oil_brent"))

        try:
            return cache.get_macro(cache_key, fetch_fn)
        except EIAException:
            raise
        except Exception as e:
            logger.error(f"Error fetching Brent: {e}")
            return None

    async def get_natural_gas(self) -> Optional[float]:
        """Get latest natural gas price (USD/MMBtu).

        Returns:
            Latest price or None if unavailable.

        Examples:
            >>> gas = await adapter.get_natural_gas()
            >>> print(f"Natural Gas: ${gas}/MMBtu")
        """
        cache_key = "eia_natural_gas_latest"

        def fetch_fn():
            return asyncio.run(self._fetch_latest("natural_gas"))

        try:
            return cache.get_macro(cache_key, fetch_fn)
        except EIAException:
            raise
        except Exception as e:
            logger.error(f"Error fetching natural gas: {e}")
            return None

    async def get_inventories(self) -> Optional[float]:
        """Get crude oil inventory levels (million barrels).

        Returns:
            Latest inventory level or None if unavailable.

        Examples:
            >>> inv = await adapter.get_inventories()
            >>> print(f"Crude inventories: {inv}M barrels")
        """
        cache_key = "eia_crude_inventories_latest"

        def fetch_fn():
            return asyncio.run(self._fetch_latest("crude_inventories"))

        try:
            return cache.get_macro(cache_key, fetch_fn)
        except EIAException:
            raise
        except Exception as e:
            logger.error(f"Error fetching inventories: {e}")
            return None

    async def get_refinery_utilization(self) -> Optional[float]:
        """Get refinery utilization rate (% of capacity).

        Returns:
            Latest utilization percentage or None if unavailable.

        Examples:
            >>> util = await adapter.get_refinery_utilization()
            >>> print(f"Refinery utilization: {util}%")
        """
        cache_key = "eia_refinery_utilization_latest"

        def fetch_fn():
            return asyncio.run(self._fetch_latest("refinery_utilization"))

        try:
            return cache.get_macro(cache_key, fetch_fn)
        except EIAException:
            raise
        except Exception as e:
            logger.error(f"Error fetching refinery utilization: {e}")
            return None

    async def _fetch_latest(self, series_name: str) -> Optional[float]:
        """Fetch latest value for a series.

        Args:
            series_name: Key in SERIES dict.

        Returns:
            Latest numeric value or None.

        Raises:
            EIASeriesException: If series not found.
        """
        if series_name not in self.SERIES:
            raise EIASeriesException(f"Unknown series: {series_name}")

        config = self.SERIES[series_name]

        try:
            data = await self._request(
                config["route"],
                {
                    "data": config["data"],
                    "sort": [{"column": "period", "direction": "desc"}],
                    "length": 1,
                },
            )

            # Extract value from response
            if "response" in data and "data" in data["response"]:
                rows = data["response"]["data"]
                if rows and len(rows) > 0:
                    value = rows[0].get("value")
                    if value:
                        try:
                            return float(value)
                        except ValueError:
                            logger.warning(f"Invalid value for {series_name}: {value}")
                            return None

            return None

        except EIAException:
            raise
        except Exception as e:
            logger.error(f"Error parsing {series_name} data: {e}")
            return None

    async def batch_latest(
        self,
        series_names: list[str],
    ) -> dict[str, Optional[float]]:
        """Get latest values for multiple series.

        Args:
            series_names: List of series keys (from SERIES).

        Returns:
            Dictionary mapping series name to latest value.

        Examples:
            >>> prices = await adapter.batch_latest([
            ...     "crude_oil_wti",
            ...     "natural_gas",
            ...     "refinery_utilization",
            ... ])
        """
        results = {}

        for series_name in series_names:
            try:
                if series_name == "crude_oil_wti":
                    value = await self.get_crude_oil_wti()
                elif series_name == "crude_oil_brent":
                    value = await self.get_crude_oil_brent()
                elif series_name == "natural_gas":
                    value = await self.get_natural_gas()
                elif series_name == "crude_inventories":
                    value = await self.get_inventories()
                elif series_name == "refinery_utilization":
                    value = await self.get_refinery_utilization()
                else:
                    raise EIASeriesException(f"Unknown series: {series_name}")

                results[series_name] = value
            except Exception as e:
                logger.warning(f"Failed to fetch {series_name}: {e}")
                results[series_name] = None

        return results


# Global adapter instance
_eia_adapter: Optional[EIAAdapter] = None


async def get_eia_adapter() -> EIAAdapter:
    """Get or create global EIA adapter.

    Returns:
        EIAAdapter instance.

    Raises:
        EIAAuthException: If API key not configured.
    """
    global _eia_adapter
    if _eia_adapter is None:
        _eia_adapter = EIAAdapter()
    return _eia_adapter
