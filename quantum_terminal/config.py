"""Global configuration for Quantum Investment Terminal."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseSettings, Field


# Load .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Debug and logging
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Paths
    project_root: Path = Path(__file__).parent.parent
    database_path: Path = Field(default=Path("investment_data.db"), env="DATABASE_PATH")
    cache_dir: Path = Field(default=Path(".cache"), env="CACHE_DIR")

    # IA Backends
    groq_api_key: Optional[str] = Field(default=None, env="GROQ_API_KEY")
    deepseek_api_key: Optional[str] = Field(default=None, env="DEEPSEEK_API_KEY")
    openrouter_api_key: Optional[str] = Field(default=None, env="OPENROUTER_API_KEY")
    kami_ia: Optional[str] = Field(default=None, env="KAMI_IA")
    hf_token: Optional[str] = Field(default=None, env="HF_TOKEN")
    qwen_api_key: Optional[str] = Field(default=None, env="QWEN_API_KEY")

    # Market Data
    finnhub_api_key: Optional[str] = Field(default=None, env="FINNHUB_API_KEY")
    alpha_vantage_api_key: Optional[str] = Field(default=None, env="ALPHA_VANTAGE_API_KEY")
    fmp_api_key: Optional[str] = Field(default=None, env="FMP_API_KEY")
    tiingo_api_key: Optional[str] = Field(default=None, env="TIINGO_API_KEY")
    market_stock_api_key: Optional[str] = Field(default=None, env="MARKET_STOCK_API_KEY")

    # Macro
    fred_api_key: Optional[str] = Field(default=None, env="FRED_API_KEY")
    eia_api_key: Optional[str] = Field(default=None, env="EIA_API_KEY")
    sec_user_agent: str = Field(
        default="QuantumTerminal (carlosdaniloangaritagarcia@gmail.com)",
        env="SEC_USER_AGENT",
    )

    # Sentiment
    newsapi_key: Optional[str] = Field(default=None, env="NEWSAPI_KEY")
    reddit_client_id: Optional[str] = Field(default=None, env="REDDIT_CLIENT_ID")
    reddit_client_secret: Optional[str] = Field(default=None, env="REDDIT_CLIENT_SECRET")

    # Crypto
    messari_api_key: Optional[str] = Field(default=None, env="MESSARI_API_KEY")
    coinbase_api_key: Optional[str] = Field(default=None, env="COINBASE_API_KEY")

    class Config:
        env_file = ".env"
        case_sensitive = False

    def validate_api_keys(self) -> dict[str, bool]:
        """Check which API keys are configured."""
        return {
            "groq": bool(self.groq_api_key),
            "deepseek": bool(self.deepseek_api_key),
            "openrouter": bool(self.openrouter_api_key),
            "kami": bool(self.kami_ia),
            "huggingface": bool(self.hf_token),
            "qwen": bool(self.qwen_api_key),
            "finnhub": bool(self.finnhub_api_key),
            "fmp": bool(self.fmp_api_key),
            "tiingo": bool(self.tiingo_api_key),
            "fred": bool(self.fred_api_key),
            "newsapi": bool(self.newsapi_key),
            "messari": bool(self.messari_api_key),
        }


# Global settings instance
settings = Settings()

# Create cache directory if it doesn't exist
settings.cache_dir.mkdir(exist_ok=True)

# Create database path
settings.database_path.parent.mkdir(exist_ok=True)
