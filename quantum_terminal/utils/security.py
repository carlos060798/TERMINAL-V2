"""Security utilities for input validation and sanitization.

Provides validators for:
- Ticker symbols (format, character validation)
- SQL injection prevention (though SQLAlchemy ORM is used)
- URL validation
- Data format validation
"""

import re
from typing import Optional
from urllib.parse import urlparse

from quantum_terminal.utils.logger import get_logger

logger = get_logger(__name__)


class TickerValidator:
    """Validator for stock ticker symbols."""

    # Valid ticker format: 1-5 alphanumeric characters, may include dots/hyphens
    TICKER_PATTERN = re.compile(r"^[A-Z0-9\.\-]{1,5}$", re.IGNORECASE)

    # Common invalid patterns
    INVALID_PATTERNS = [
        r"[\x00-\x1f\x7f-\x9f]",  # Control characters
        r"['\";--/*\\]",  # SQL injection patterns
        r"[<>(){}[\]]",  # XSS patterns
    ]

    INVALID_REGEX = re.compile("|".join(INVALID_PATTERNS))

    @staticmethod
    def validate(ticker: str) -> bool:
        """Validate ticker symbol format.

        Args:
            ticker: Ticker symbol to validate.

        Returns:
            True if valid, False otherwise.

        Examples:
            >>> TickerValidator.validate("AAPL")
            True
            >>> TickerValidator.validate("BRK.B")
            True
            >>> TickerValidator.validate("INVALID'; DROP TABLE")
            False
        """
        if not isinstance(ticker, str):
            logger.warning(f"Ticker validation failed: not a string ({type(ticker)})")
            return False

        ticker = ticker.strip().upper()

        # Check format
        if not TickerValidator.TICKER_PATTERN.match(ticker):
            logger.debug(f"Ticker '{ticker}' does not match expected format")
            return False

        # Check for invalid patterns
        if TickerValidator.INVALID_REGEX.search(ticker):
            logger.warning(f"Ticker '{ticker}' contains invalid patterns")
            return False

        logger.debug(f"Ticker '{ticker}' validated successfully")
        return True

    @staticmethod
    def sanitize(ticker: str) -> str:
        """Sanitize ticker to safe format.

        Args:
            ticker: Raw ticker input.

        Returns:
            Sanitized ticker or empty string if invalid.

        Examples:
            >>> TickerValidator.sanitize("aapl")
            'AAPL'
            >>> TickerValidator.sanitize("  BRK.B  ")
            'BRK.B'
        """
        if not isinstance(ticker, str):
            logger.warning(f"Cannot sanitize non-string ticker: {type(ticker)}")
            return ""

        # Strip whitespace and convert to uppercase
        sanitized = ticker.strip().upper()

        # Validate after sanitization
        if TickerValidator.validate(sanitized):
            return sanitized

        logger.warning(f"Ticker '{ticker}' could not be sanitized to valid format")
        return ""


class SQLInjectionValidator:
    """SQL injection detection and prevention.

    Note: Project uses SQLAlchemy ORM which provides built-in protection,
    but this validator provides defense-in-depth.
    """

    # Common SQL injection patterns
    SQL_PATTERNS = [
        r"(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|\#|;|\/\*|\*\/)",  # SQL comments and terminators
        r"(('\s*OR\s*'|'\s*AND\s*')|(\"\s*OR\s*\"|(\"\s*AND\s*\")))",  # OR/AND injection
    ]

    SQL_REGEX = re.compile("|".join(SQL_PATTERNS), re.IGNORECASE)

    @staticmethod
    def is_suspicious(value: str) -> bool:
        """Check if value contains suspicious SQL patterns.

        Args:
            value: Value to check.

        Returns:
            True if suspicious patterns found, False otherwise.

        Examples:
            >>> SQLInjectionValidator.is_suspicious("AAPL")
            False
            >>> SQLInjectionValidator.is_suspicious("AAPL'; DROP TABLE--")
            True
        """
        if not isinstance(value, str):
            return False

        if SQLInjectionValidator.SQL_REGEX.search(value):
            logger.warning(f"Suspicious SQL pattern detected: {value[:50]}")
            return True

        return False

    @staticmethod
    def sanitize(value: str) -> str:
        """Sanitize value for safe database use.

        Args:
            value: Value to sanitize.

        Returns:
            Sanitized value (may be empty if too suspicious).

        Note:
            Use SQLAlchemy parameterized queries instead of this for production.
        """
        if not isinstance(value, str):
            return ""

        if SQLInjectionValidator.is_suspicious(value):
            logger.warning("Refused to sanitize suspicious value")
            return ""

        # Remove any remaining control characters
        sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", value)
        return sanitized


class URLValidator:
    """Validator for URLs."""

    ALLOWED_SCHEMES = {"http", "https"}
    ALLOWED_DOMAINS = {
        # Market data
        "finnhub.io",
        "api.example.com",  # Placeholder
        "yahoo.com",
        "marketwatch.com",
        # Macro data
        "fred.stlouisfed.org",
        "data.eia.gov",
        # News
        "newsapi.org",
        # Company info
        "sec.gov",
    }

    @staticmethod
    def validate(url: str, allowed_domains: Optional[set[str]] = None) -> bool:
        """Validate URL format and domain.

        Args:
            url: URL to validate.
            allowed_domains: Set of allowed domains. Uses defaults if None.

        Returns:
            True if valid, False otherwise.

        Examples:
            >>> URLValidator.validate("https://finnhub.io/api")
            True
            >>> URLValidator.validate("javascript:alert('xss')")
            False
        """
        if not isinstance(url, str):
            logger.warning(f"URL validation failed: not a string ({type(url)})")
            return False

        try:
            parsed = urlparse(url)

            # Check scheme
            if parsed.scheme not in URLValidator.ALLOWED_SCHEMES:
                logger.warning(f"Invalid URL scheme: {parsed.scheme}")
                return False

            # Check netloc exists
            if not parsed.netloc:
                logger.warning(f"Invalid URL: no netloc")
                return False

            # Check domain if allowed_domains specified
            domains = allowed_domains or URLValidator.ALLOWED_DOMAINS
            if domains and parsed.netloc not in domains:
                # Check for subdomain match
                if not any(parsed.netloc.endswith(f".{domain}") for domain in domains):
                    logger.warning(f"Domain not in whitelist: {parsed.netloc}")
                    return False

            logger.debug(f"URL '{url}' validated successfully")
            return True

        except Exception as e:
            logger.warning(f"URL validation error: {e}")
            return False


class EmailValidator:
    """Validator for email addresses."""

    # Simplified email pattern (RFC 5322 compliant)
    EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    )

    @staticmethod
    def validate(email: str) -> bool:
        """Validate email format.

        Args:
            email: Email address to validate.

        Returns:
            True if valid format, False otherwise.

        Note:
            Does not verify email existence, only format.

        Examples:
            >>> EmailValidator.validate("user@example.com")
            True
            >>> EmailValidator.validate("invalid@")
            False
        """
        if not isinstance(email, str):
            logger.warning(f"Email validation failed: not a string ({type(email)})")
            return False

        if len(email) > 254:  # RFC 5321
            logger.warning(f"Email too long: {len(email)} chars")
            return False

        if EmailValidator.EMAIL_PATTERN.match(email):
            logger.debug(f"Email '{email}' validated successfully")
            return True

        logger.warning(f"Email '{email}' failed validation")
        return False


class DataFormatValidator:
    """Validator for common data formats."""

    @staticmethod
    def validate_date(date_str: str, format: str = "%Y-%m-%d") -> bool:
        """Validate date string format.

        Args:
            date_str: Date string to validate.
            format: Expected date format (default: YYYY-MM-DD).

        Returns:
            True if valid format, False otherwise.

        Examples:
            >>> DataFormatValidator.validate_date("2024-01-15")
            True
            >>> DataFormatValidator.validate_date("15/01/2024")
            False
        """
        from datetime import datetime

        try:
            datetime.strptime(date_str, format)
            return True
        except ValueError:
            logger.warning(f"Invalid date format: '{date_str}' (expected {format})")
            return False

    @staticmethod
    def validate_numeric(value: str, allow_negative: bool = True) -> bool:
        """Validate numeric string.

        Args:
            value: Value to validate.
            allow_negative: Whether negative numbers are allowed.

        Returns:
            True if valid numeric format, False otherwise.

        Examples:
            >>> DataFormatValidator.validate_numeric("123.45")
            True
            >>> DataFormatValidator.validate_numeric("-50")
            True
            >>> DataFormatValidator.validate_numeric("abc")
            False
        """
        try:
            num = float(value)
            if not allow_negative and num < 0:
                return False
            return True
        except (ValueError, TypeError):
            logger.warning(f"Invalid numeric format: '{value}'")
            return False

    @staticmethod
    def validate_percentage(value: str) -> bool:
        """Validate percentage value (0-100).

        Args:
            value: Percentage value to validate.

        Returns:
            True if valid percentage, False otherwise.

        Examples:
            >>> DataFormatValidator.validate_percentage("50")
            True
            >>> DataFormatValidator.validate_percentage("150")
            False
        """
        try:
            num = float(value)
            return 0 <= num <= 100
        except (ValueError, TypeError):
            logger.warning(f"Invalid percentage format: '{value}'")
            return False
