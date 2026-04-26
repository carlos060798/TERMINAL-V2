"""Plan Adherence Use Case - Evaluate trading plan compliance."""

from typing import Dict, List, Any
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class PlanAdherenceUseCase:
    """Evaluate adherence to trading plan."""

    def __init__(self):
        """Initialize PlanAdherenceUseCase."""
        pass

    async def execute(
        self, trades: List[Dict[str, Any]], trading_plan: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Evaluate adherence to trading plan.

        Args:
            trades: List of trades.
            trading_plan: Trading plan rules (optional).

        Returns:
            Dict with adherence metrics.
        """
        try:
            if not trades:
                return {
                    "adherence_score": 0.0,
                    "rules_followed": 0,
                    "rules_broken": 0,
                    "cost_of_violations": 0.0,
                    "violations": [],
                }

            # Count trades with plan adherence
            adhered_trades = [t for t in trades if t.get("plan_adherence")]
            violation_trades = [t for t in trades if not t.get("plan_adherence")]

            # Calculate adherence score
            total_trades = len(trades)
            adherence_score = (
                (len(adhered_trades) / total_trades * 100)
                if total_trades > 0
                else 0.0
            )

            # Calculate cost of violations
            cost_of_violations = self._calculate_violation_cost(
                violation_trades
            )

            return {
                "adherence_score": adherence_score,
                "rules_followed": len(adhered_trades),
                "rules_broken": len(violation_trades),
                "cost_of_violations": cost_of_violations,
                "violations": [
                    {
                        "trade_id": t.get("trade_id"),
                        "ticker": t.get("ticker"),
                        "reason": "Traded without clear plan",
                    }
                    for t in violation_trades
                ],
            }

        except Exception as e:
            logger.error(f"Error evaluating plan adherence: {e}", exc_info=True)
            return {"error": str(e)}

    def _calculate_violation_cost(
        self, violation_trades: List[Dict]
    ) -> float:
        """Calculate total P&L loss from plan violations."""
        total_cost = 0.0

        for trade in violation_trades:
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

            if pnl < 0:
                total_cost += abs(float(pnl))

        return total_cost
