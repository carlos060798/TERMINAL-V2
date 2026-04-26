"""Log Trade Use Case - Register new trade in journal."""

from typing import Dict, Any
from datetime import datetime
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class LogTradeUseCase:
    """Registers a new trade in the trading journal."""

    def __init__(self, trades_repository):
        """
        Initialize LogTradeUseCase.

        Args:
            trades_repository: Repository for persisting trades.
        """
        self.trades_repository = trades_repository

    async def execute(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Log a new trade.

        Args:
            trade_data: Trade information including ticker, direction, size, entry, etc.

        Returns:
            Dict with trade_id and created_at timestamp.
        """
        try:
            # Validate trade data
            required_fields = [
                "ticker",
                "direction",
                "size",
                "entry_price",
                "reason",
            ]
            for field in required_fields:
                if field not in trade_data:
                    raise ValueError(f"Missing required field: {field}")

            # Prepare trade object
            trade = {
                "ticker": trade_data["ticker"].upper(),
                "direction": trade_data["direction"],
                "size": Decimal(str(trade_data["size"])),
                "entry_price": Decimal(str(trade_data["entry_price"])),
                "exit_price": (
                    Decimal(str(trade_data["exit_price"]))
                    if trade_data.get("exit_price")
                    else None
                ),
                "stop_loss": (
                    Decimal(str(trade_data["stop_loss"]))
                    if trade_data.get("stop_loss")
                    else None
                ),
                "take_profit": (
                    Decimal(str(trade_data["take_profit"]))
                    if trade_data.get("take_profit")
                    else None
                ),
                "reason": trade_data["reason"],
                "plan_adherence": trade_data.get("plan_adherence", True),
                "entry_date": (
                    trade_data["entry_date"]
                    if trade_data.get("entry_date")
                    else datetime.now().isoformat()
                ),
            }

            # Persist trade
            trade_id = await self.trades_repository.create(trade)

            return {
                "success": True,
                "trade_id": trade_id,
                "created_at": trade["entry_date"],
            }

        except Exception as e:
            logger.error(f"Error logging trade: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


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
