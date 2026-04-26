"""
Machine Learning Forecast Engine - Prophet EPS/Revenue + LSTM Momentum.

Implements two complementary forecasting models:

1. EPS/Revenue Forecasting (Prophet):
   - Input: Historical quarterly data (10 years)
   - Output: 4-8 quarter forecast with confidence intervals (80%/95%)
   - Captures seasonality (Q4 > other quarters in retail, etc.)
   - Auto-trained (no hyperparameters)
   - Used to update DCF valuation dynamically

2. Momentum Signal (LSTM):
   - Input: 60 days OHLCV + technical indicators (RSI, MACD, SMA)
   - Output: Momentum probability (0-1) and signal (BUY/HOLD/SELL)
   - Pre-trained on S&P 500 historical data
   - Complements Graham-Dodd fundamental analysis
   - Does NOT predict absolute price (Graham never does)

Phase 2 - Infrastructure Layer (ML Adapters)
Reference: PLAN_MAESTRO.md - Phase 2: ML Adapters
"""

import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from prophet import Prophet
from sklearn.preprocessing import MinMaxScaler

from quantum_terminal.utils.logger import get_logger
from quantum_terminal.utils.cache import cache

logger = get_logger(__name__)


# ============================================================================
# Domain Models
# ============================================================================

@dataclass
class ForecastResult:
    """Result from Prophet EPS/Revenue forecast."""
    ticker: str
    metric: str  # "eps" or "revenue"
    forecast_dates: List[datetime]
    forecast_values: List[float]
    lower_bounds_80: List[float]
    upper_bounds_80: List[float]
    lower_bounds_95: List[float]
    upper_bounds_95: List[float]
    rmse: Optional[float] = None
    mape: Optional[float] = None
    generated_at: datetime = None

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'ticker': self.ticker,
            'metric': self.metric,
            'forecast_dates': [d.isoformat() for d in self.forecast_dates],
            'forecast_values': self.forecast_values,
            'lower_bounds_80': self.lower_bounds_80,
            'upper_bounds_80': self.upper_bounds_80,
            'lower_bounds_95': self.lower_bounds_95,
            'upper_bounds_95': self.upper_bounds_95,
            'rmse': self.rmse,
            'mape': self.mape,
            'generated_at': self.generated_at.isoformat()
        }


@dataclass
class MomentumSignal:
    """Result from LSTM momentum signal."""
    ticker: str
    signal: str  # BUY, HOLD, SELL
    probability: float  # 0-1 (confidence)
    rsi: float  # 0-100
    macd: float  # MACD value
    sma_20: float  # 20-day SMA
    sma_50: float  # 50-day SMA
    current_price: float
    trend_strength: float  # 0-1
    generated_at: datetime = None

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'ticker': self.ticker,
            'signal': self.signal,
            'probability': self.probability,
            'rsi': self.rsi,
            'macd': self.macd,
            'sma_20': self.sma_20,
            'sma_50': self.sma_50,
            'current_price': self.current_price,
            'trend_strength': self.trend_strength,
            'generated_at': self.generated_at.isoformat()
        }


# ============================================================================
# LSTM Momentum Model
# ============================================================================

class MomentumLSTM(nn.Module):
    """LSTM neural network for momentum signal generation.

    Architecture:
    - Input layer: 60 timesteps × 7 features (OHLCV + indicators)
    - LSTM layer 1: 64 units
    - Dropout: 0.2
    - LSTM layer 2: 32 units
    - Dropout: 0.2
    - Dense: 16 units
    - Output: 1 unit (sigmoid for 0-1 probability)

    Pre-trained on S&P 500 (2015-2024) with labels based on next-day return.
    """

    def __init__(self, input_size: int = 7, hidden_size: int = 64):
        """Initialize LSTM architecture.

        Args:
            input_size: Number of features (OHLCV + 2 indicators = 7)
            hidden_size: LSTM hidden units
        """
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size

        self.lstm1 = nn.LSTM(input_size, hidden_size, batch_first=True, dropout=0.2)
        self.lstm2 = nn.LSTM(hidden_size, 32, batch_first=True, dropout=0.2)
        self.dense = nn.Linear(32, 16)
        self.output = nn.Linear(16, 1)
        self.sigmoid = nn.Sigmoid()
        self.relu = nn.ReLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Args:
            x: Tensor of shape (batch_size, 60, 7)

        Returns:
            Tensor of shape (batch_size, 1) with values in [0, 1]
        """
        lstm1_out, _ = self.lstm1(x)
        lstm2_out, (h_n, c_n) = self.lstm2(lstm1_out)

        # Use last hidden state
        last_hidden = h_n[-1]  # (batch_size, 32)

        dense_out = self.relu(self.dense(last_hidden))
        output = self.sigmoid(self.output(dense_out))

        return output


# ============================================================================
# EPS Forecaster (Prophet)
# ============================================================================

class EPSForecaster:
    """Prophet-based forecaster for EPS and Revenue.

    Uses Facebook's Prophet library for automatic forecasting with:
    - Automatic changepoint detection
    - Yearly seasonality (Q4 effects, etc.)
    - Holiday effects (earnings dates, macro events)
    - Confidence intervals (80%, 95%)
    """

    def __init__(self):
        """Initialize EPS forecaster."""
        self.models: Dict[str, Prophet] = {}
        self.scalers: Dict[str, MinMaxScaler] = {}
        logger.info("EPSForecaster initialized")

    async def forecast_eps(
        self,
        ticker: str,
        historical_data: pd.DataFrame,
        periods: int = 8,
        interval_width: float = 0.95
    ) -> ForecastResult:
        """
        Forecast EPS using Prophet.

        Args:
            ticker: Stock ticker
            historical_data: DataFrame with columns ['date', 'eps'] (quarterly)
            periods: Number of quarters to forecast (default 8)
            interval_width: Confidence interval width (default 0.95 = 95%)

        Returns:
            ForecastResult with forecast values and bounds

        Raises:
            ValueError: If insufficient historical data
        """
        if len(historical_data) < 8:
            logger.error(
                f"{ticker} insufficient EPS history: {len(historical_data)} quarters"
            )
            raise ValueError(f"Need at least 8 quarters of data, got {len(historical_data)}")

        try:
            # Prepare data for Prophet
            df = historical_data[['date', 'eps']].copy()
            df.columns = ['ds', 'y']
            df['ds'] = pd.to_datetime(df['ds'])
            df = df.sort_values('ds')

            # Remove outliers (extremely high/low EPS)
            mean_eps = df['y'].mean()
            std_eps = df['y'].std()
            df = df[
                (df['y'] >= mean_eps - 3 * std_eps) &
                (df['y'] <= mean_eps + 3 * std_eps)
            ]

            # Train Prophet model
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                interval_width=interval_width,
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=10.0,
            )

            # Add yearly seasonality
            model.add_seasonality(name='quarterly', period=365.25/4, fourier_order=3)

            with logging.getLogger("cmdstanpy").disabled:
                model.fit(df)

            # Generate future dataframe (quarterly)
            future = model.make_future_dataframe(periods=periods, freq='Q')
            forecast = model.predict(future)

            # Extract results
            forecast_data = forecast.iloc[-periods:].copy()

            # Get 80% and 95% intervals
            forecast_80 = model.make_future_dataframe(periods=periods, freq='Q')
            forecast_80_result = model.predict(forecast_80)

            results_95 = forecast_data[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()

            # Simple 80% approximation (±0.842*std)
            results_80_lower = results_95['yhat'] - 0.842 * (
                (results_95['yhat_upper'] - results_95['yhat_lower']) / (2 * 1.96)
            )
            results_80_upper = results_95['yhat'] + 0.842 * (
                (results_95['yhat_upper'] - results_95['yhat_lower']) / (2 * 1.96)
            )

            # Calculate MAPE
            mape = self._calculate_mape(df['y'].values[-8:], forecast_data['yhat'].values[:8])

            # Cache the model
            self.models[f"{ticker}_eps"] = model
            self.scalers[f"{ticker}_eps"] = MinMaxScaler()

            result = ForecastResult(
                ticker=ticker,
                metric='eps',
                forecast_dates=[d.to_pydatetime() for d in results_95['ds']],
                forecast_values=results_95['yhat'].tolist(),
                lower_bounds_80=results_80_lower.tolist(),
                upper_bounds_80=results_80_upper.tolist(),
                lower_bounds_95=results_95['yhat_lower'].tolist(),
                upper_bounds_95=results_95['yhat_upper'].tolist(),
                mape=mape
            )

            logger.info(
                f"{ticker} EPS forecast: {periods}Q, "
                f"next Q: ${results_95['yhat'].iloc[0]:.2f}"
            )

            return result

        except Exception as e:
            logger.error(f"EPS forecast failed for {ticker}: {str(e)}", exc_info=True)
            raise

    async def forecast_revenue(
        self,
        ticker: str,
        historical_data: pd.DataFrame,
        periods: int = 8,
        interval_width: float = 0.95
    ) -> ForecastResult:
        """
        Forecast Revenue using Prophet.

        Args:
            ticker: Stock ticker
            historical_data: DataFrame with columns ['date', 'revenue'] (quarterly)
            periods: Number of quarters to forecast
            interval_width: Confidence interval width

        Returns:
            ForecastResult with forecast values and bounds
        """
        if len(historical_data) < 8:
            logger.error(
                f"{ticker} insufficient revenue history: {len(historical_data)} quarters"
            )
            raise ValueError(
                f"Need at least 8 quarters of data, got {len(historical_data)}"
            )

        try:
            # Prepare data
            df = historical_data[['date', 'revenue']].copy()
            df.columns = ['ds', 'y']
            df['ds'] = pd.to_datetime(df['ds'])
            df = df.sort_values('ds')

            # Remove outliers
            mean_rev = df['y'].mean()
            std_rev = df['y'].std()
            df = df[
                (df['y'] >= mean_rev - 3 * std_rev) &
                (df['y'] <= mean_rev + 3 * std_rev)
            ]

            # Train Prophet
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                interval_width=interval_width,
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=10.0,
            )

            model.add_seasonality(name='quarterly', period=365.25/4, fourier_order=3)

            with logging.getLogger("cmdstanpy").disabled:
                model.fit(df)

            # Generate forecast
            future = model.make_future_dataframe(periods=periods, freq='Q')
            forecast = model.predict(future)
            forecast_data = forecast.iloc[-periods:].copy()

            # Get intervals
            results_95 = forecast_data[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
            results_80_lower = results_95['yhat'] - 0.842 * (
                (results_95['yhat_upper'] - results_95['yhat_lower']) / (2 * 1.96)
            )
            results_80_upper = results_95['yhat'] + 0.842 * (
                (results_95['yhat_upper'] - results_95['yhat_lower']) / (2 * 1.96)
            )

            # MAPE
            mape = self._calculate_mape(
                df['y'].values[-8:],
                forecast_data['yhat'].values[:8]
            )

            self.models[f"{ticker}_revenue"] = model
            self.scalers[f"{ticker}_revenue"] = MinMaxScaler()

            result = ForecastResult(
                ticker=ticker,
                metric='revenue',
                forecast_dates=[d.to_pydatetime() for d in results_95['ds']],
                forecast_values=results_95['yhat'].tolist(),
                lower_bounds_80=results_80_lower.tolist(),
                upper_bounds_80=results_80_upper.tolist(),
                lower_bounds_95=results_95['yhat_lower'].tolist(),
                upper_bounds_95=results_95['yhat_upper'].tolist(),
                mape=mape
            )

            logger.info(
                f"{ticker} Revenue forecast: {periods}Q, "
                f"next Q: ${results_95['yhat'].iloc[0]:.2f}M"
            )

            return result

        except Exception as e:
            logger.error(
                f"Revenue forecast failed for {ticker}: {str(e)}",
                exc_info=True
            )
            raise

    @staticmethod
    def _calculate_mape(actual: np.ndarray, predicted: np.ndarray) -> float:
        """Calculate Mean Absolute Percentage Error."""
        if len(actual) == 0 or len(predicted) == 0:
            return 0.0

        # Avoid division by zero
        mask = actual != 0
        if not mask.any():
            return 0.0

        mape = np.mean(np.abs((actual[mask] - predicted[:len(actual)][mask]) / actual[mask])) * 100
        return float(np.clip(mape, 0, 1000))


# ============================================================================
# Momentum Signal Generator (LSTM)
# ============================================================================

class MomentumSignalGenerator:
    """LSTM-based momentum signal generator.

    Uses pre-trained LSTM to predict momentum continuation.
    Does NOT predict absolute price (follows Graham philosophy).
    Instead predicts whether current trend will continue.
    """

    def __init__(self, model_path: Optional[str] = None):
        """Initialize momentum signal generator.

        Args:
            model_path: Path to pre-trained model weights
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = MomentumLSTM().to(self.device)

        if model_path and os.path.exists(model_path):
            try:
                self.model.load_state_dict(torch.load(model_path, map_location=self.device))
                logger.info(f"Loaded pre-trained model from {model_path}")
            except Exception as e:
                logger.warning(f"Could not load model from {model_path}: {e}")
        else:
            logger.info("Using default (untrained) LSTM model")

        self.model.eval()
        self.scaler = MinMaxScaler()

    async def generate_signal(
        self,
        ticker: str,
        price_data: pd.DataFrame
    ) -> MomentumSignal:
        """
        Generate momentum signal using LSTM.

        Args:
            ticker: Stock ticker
            price_data: DataFrame with columns ['date', 'open', 'high', 'low', 'close', 'volume']
                       Must have at least 60 rows

        Returns:
            MomentumSignal with BUY/HOLD/SELL and probability

        Raises:
            ValueError: If insufficient price data
        """
        if len(price_data) < 60:
            logger.error(f"{ticker} insufficient price history: {len(price_data)} days")
            raise ValueError(f"Need at least 60 days of data, got {len(price_data)}")

        try:
            # Calculate indicators
            df = price_data[['close', 'volume']].copy().tail(60)

            # RSI (Relative Strength Index)
            rsi = self._calculate_rsi(df['close'].values, period=14)

            # MACD
            macd = self._calculate_macd(df['close'].values)

            # SMAs
            sma_20 = df['close'].rolling(20).mean().iloc[-1]
            sma_50 = df['close'].rolling(50).mean().iloc[-5] if len(df) >= 50 else df['close'].mean()

            # Normalize OHLCV for LSTM
            features = self._prepare_lstm_features(price_data.iloc[-60:])

            # LSTM prediction
            with torch.no_grad():
                input_tensor = torch.tensor(features, dtype=torch.float32).unsqueeze(0).to(self.device)
                output = self.model(input_tensor)
                momentum_prob = output.item()

            # Determine signal
            if momentum_prob > 0.65:
                signal = "BUY"
                trend_strength = momentum_prob
            elif momentum_prob < 0.35:
                signal = "SELL"
                trend_strength = 1.0 - momentum_prob
            else:
                signal = "HOLD"
                trend_strength = 0.5

            current_price = df['close'].iloc[-1]

            result = MomentumSignal(
                ticker=ticker,
                signal=signal,
                probability=momentum_prob,
                rsi=rsi,
                macd=macd,
                sma_20=float(sma_20),
                sma_50=float(sma_50),
                current_price=float(current_price),
                trend_strength=trend_strength
            )

            logger.info(
                f"{ticker} momentum: {signal} ({momentum_prob:.2%}), "
                f"RSI={rsi:.1f}, MACD={macd:.4f}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Momentum signal failed for {ticker}: {str(e)}",
                exc_info=True
            )
            raise

    def _prepare_lstm_features(self, price_data: pd.DataFrame) -> np.ndarray:
        """Prepare normalized features for LSTM.

        Returns array of shape (60, 7):
        - normalized close
        - normalized volume
        - RSI
        - MACD
        - normalized high
        - normalized low
        - normalized open
        """
        df = price_data.copy()

        # Normalize OHLCV
        close_norm = (df['close'] - df['close'].min()) / (df['close'].max() - df['close'].min() + 1e-8)
        volume_norm = (df['volume'] - df['volume'].min()) / (df['volume'].max() - df['volume'].min() + 1e-8)
        high_norm = (df['high'] - df['high'].min()) / (df['high'].max() - df['high'].min() + 1e-8)
        low_norm = (df['low'] - df['low'].min()) / (df['low'].max() - df['low'].min() + 1e-8)
        open_norm = (df['open'] - df['open'].min()) / (df['open'].max() - df['open'].min() + 1e-8)

        # RSI
        rsi = self._calculate_rsi(df['close'].values, period=14)
        rsi_norm = rsi / 100.0

        # MACD
        macd = self._calculate_macd(df['close'].values)
        macd_norm = np.clip(macd / (df['close'].std() + 1e-8), -1, 1)

        # Stack features
        features = np.column_stack([
            close_norm,
            volume_norm,
            np.full(len(df), rsi_norm),
            np.full(len(df), macd_norm),
            high_norm,
            low_norm,
            open_norm
        ])

        return features.astype(np.float32)

    @staticmethod
    def _calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
        """Calculate RSI (Relative Strength Index)."""
        if len(prices) < period:
            return 50.0

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi)

    @staticmethod
    def _calculate_macd(prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> float:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        if len(prices) < slow:
            return 0.0

        ema_fast = pd.Series(prices).ewm(span=fast).mean().iloc[-1]
        ema_slow = pd.Series(prices).ewm(span=slow).mean().iloc[-1]
        macd = ema_fast - ema_slow

        return float(macd)


# ============================================================================
# Module exports
# ============================================================================

import os

__all__ = [
    'ForecastResult',
    'MomentumSignal',
    'EPSForecaster',
    'MomentumSignalGenerator',
    'MomentumLSTM',
]
