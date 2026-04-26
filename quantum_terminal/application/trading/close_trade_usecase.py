"""Close Trade Use Case."""

from typing import Dict, Any
from datetime import datetime
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class CloseTradeUseCase:
    """Close an open trade."""

    def __init__(self, trades_repository):
        """Initialize CloseTradeUseCase."""
        self.trades_repository = trades_repository

    async def execute(
        self, trade_id: str, exit_price: float, exit_date: str = None
    ) -> Dict[str, Any]:
        """
        Close an open trade.

        Args:
            trade_id: ID of trade to close.
            exit_price: Exit price.
            exit_date: Exit date (optional, defaults to now).

        Returns:
            Dict with trade_id and pnl information.
        """
        try:
            result = await self.trades_repository.update(
                trade_id,
                {
                    "exit_price": Decimal(str(exit_price)),
                    "exit_date": exit_date or datetime.now().isoformat(),
                    "status": "closed",
                },
            )

            return {
                "success": True,
                "trade_id": trade_id,
                "updated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error closing trade: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
