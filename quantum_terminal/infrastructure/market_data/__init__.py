"""Market data providers and coordinators.

Provides unified access to multiple market data sources:
- FinnhubAdapter: Real-time quotes and company profiles
- DataProvider: Master coordinator with intelligent fallback chains
  - Quotes: Finnhub → yfinance → Tiingo → AlphaVantage
  - Fundamentals: FMP → SEC XBRL
  - Macro: FRED
"""

from quantum_terminal.infrastructure.market_data.finnhub_adapter import (
    FinnhubAdapter,
    FinnhubAPIError,
    FinnhubRateLimitError,
    get_quote,
    batch_quotes,
)
from quantum_terminal.infrastructure.market_data.data_provider import (
    DataProvider,
    get_data_provider,
    AllProvidersFailedError,
    DataProviderError,
)

__all__ = [
    # Finnhub
    "FinnhubAdapter",
    "FinnhubAPIError",
    "FinnhubRateLimitError",
    "get_quote",
    "batch_quotes",
    # Data Provider
    "DataProvider",
    "get_data_provider",
    "AllProvidersFailedError",
    "DataProviderError",
]
