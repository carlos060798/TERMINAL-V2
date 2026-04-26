"""Trade Statistics Use Case - Calculate performance metrics."""

from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TradeStatisticsUseCase:
    """Calculate trading statistics from completed trades."""

    def __init__(self, trades_repository):
        """Initialize TradeStatisticsUseCase."""
        self.trades_repository = trades_repository

    async def execute(
        self, trades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate trading statistics.

        Args:
            trades: List of trade dictionaries.

        Returns:
            Dict with calculated statistics.
        """
        try:
            if not trades:
                return {
                    "win_rate": 0.0,
                    "profit_factor": 0.0,
                    "expectancy": 0.0,
                    "avg_r_multiple": 0.0,
                    "avg_duration_days": 0.0,
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                }

            # Separate winning and losing trades
            winning_trades = []
            losing_trades = []

            for trade in trades:
                if not trade.get("exit_price"):
                    continue

                entry = Decimal(str(trade.get("entry_price", 0)))
                exit_price = Decimal(str(trade.get("exit_price", 0)))
                size = Decimal(str(trade.get("size", 0)))
                direction = trade.get("direction", "Long").lower()

                # Calculate P&L
                if direction == "long" or direction == "buy":
                    pnl = (exit_price - entry) * size
                else:
                    pnl = (entry - exit_price) * size

                if pnl > 0:
                    winning_trades.append(
                        {"pnl": float(pnl), "trade": trade}
                    )
                else:
                    losing_trades.append(
                        {"pnl": float(pnl), "trade": trade}
                    )

            total_trades = len(winning_trades) + len(losing_trades)
            winning_trades_count = len(winning_trades)
            losing_trades_count = len(losing_trades)

            # Win rate
            win_rate = (
                (winning_trades_count / total_trades * 100)
                if total_trades > 0
                else 0.0
            )

            # Gross profit and loss
            gross_profit = (
                sum(t["pnl"] for t in winning_trades)
                if winning_trades
                else 0.0
            )
            gross_loss = (
                abs(sum(t["pnl"] for t in losing_trades))
                if losing_trades
                else 0.0
            )

            # Profit factor
            profit_factor = (
                gross_profit / gross_loss if gross_loss > 0 else 0.0
            )

            # Expectancy
            avg_win = (
                gross_profit / winning_trades_count
                if winning_trades_count > 0
                else 0.0
            )
            avg_loss = (
                gross_loss / losing_trades_count if losing_trades_count > 0
                else 0.0
            )

            expectancy = (
                (win_rate / 100) * avg_win
                - ((1 - win_rate / 100) * avg_loss)
            )

            # Average duration
            avg_duration_days = self._calculate_avg_duration(trades)

            # Average R multiple
            avg_r_multiple = self._calculate_avg_r_multiple(
                trades, avg_loss
            )

            return {
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "expectancy": expectancy,
                "avg_r_multiple": avg_r_multiple,
                "avg_duration_days": avg_duration_days,
                "total_trades": total_trades,
                "winning_trades": winning_trades_count,
                "losing_trades": losing_trades_count,
                "gross_profit": gross_profit,
                "gross_loss": gross_loss,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
            }

        except Exception as e:
            logger.error(f"Error calculating statistics: {e}", exc_info=True)
            return {"error": str(e)}

    def _calculate_avg_duration(self, trades: List[Dict]) -> float:
        """Calculate average trade duration in days."""
        durations = []

        for trade in trades:
            entry_date_str = trade.get("entry_date")
            exit_date_str = trade.get("exit_date")

            if not entry_date_str or not exit_date_str:
                continue

            try:
                entry = datetime.fromisoformat(entry_date_str)
                exit_dt = datetime.fromisoformat(exit_date_str)
                duration = (exit_dt - entry).days
                if duration >= 0:
                    durations.append(duration)
            except Exception:
                continue

        return (
            sum(durations) / len(durations) if durations else 0.0
        )

    def _calculate_avg_r_multiple(
        self, trades: List[Dict], avg_loss: float
    ) -> float:
        """Calculate average R multiple (gain/risk)."""
        if avg_loss == 0:
            return 0.0

        r_multiples = []

        for trade in trades:
            if not trade.get("stop_loss") or not trade.get("exit_price"):
                continue

            entry = Decimal(str(trade.get("entry_price", 0)))
            exit_price = Decimal(str(trade.get("exit_price", 0)))
            stop_loss = Decimal(str(trade.get("stop_loss", 0)))

            risk = abs(entry - stop_loss)
            if risk == 0:
                continue

            reward = abs(exit_price - entry)
            r_multiple = float(reward / risk)
            r_multiples.append(r_multiple)

        return (
            sum(r_multiples) / len(r_multiples)
            if r_multiples
            else 0.0
        )
