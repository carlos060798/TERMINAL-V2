"""Postmortem Use Case - Generate weekly trade analysis."""

from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class PostmortemUseCase:
    """Generate postmortem analysis of trades."""

    def __init__(self, ai_gateway):
        """Initialize PostmortemUseCase."""
        self.ai_gateway = ai_gateway

    async def execute(
        self, trades: List[Dict[str, Any]], period: str = "weekly"
    ) -> Dict[str, Any]:
        """
        Generate postmortem analysis.

        Args:
            trades: List of trades in period.
            period: Period type (weekly, monthly, etc).

        Returns:
            Dict with analysis and insights.
        """
        try:
            if not trades:
                return {
                    "success": True,
                    "analysis": f"No trades in {period} period.",
                    "insights": [],
                }

            # Prepare prompt
            prompt = self._build_postmortem_prompt(trades, period)

            # Call AI gateway
            analysis = await self.ai_gateway.generate(
                prompt, tipo="reason"
            )

            return {
                "success": True,
                "analysis": analysis,
                "trade_count": len(trades),
                "period": period,
                "insights": self._extract_insights(analysis),
            }

        except Exception as e:
            logger.error(f"Error generating postmortem: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _build_postmortem_prompt(
        self, trades: List[Dict], period: str
    ) -> str:
        """Build prompt for postmortem analysis."""
        trade_summary = self._summarize_trades(trades)

        prompt = f"""
Analyze these {len(trades)} trading records from the {period} period.

Trade Summary:
{trade_summary}

Identify:
1. Common error patterns (if any)
2. Setup quality improvements
3. Execution issues
4. Risk management opportunities
5. Recommendations for next {period}

Be specific and actionable. Focus on process improvement.
"""
        return prompt

    def _summarize_trades(self, trades: List[Dict]) -> str:
        """Create summary of trades for analysis."""
        summary_lines = []

        for i, trade in enumerate(trades, 1):
            ticker = trade.get("ticker", "UNKNOWN")
            direction = trade.get("direction", "Unknown")
            entry = trade.get("entry_price", 0)
            exit_price = trade.get("exit_price", "Open")
            reason = trade.get("reason", "No reason")[:50]
            adherence = "Plan" if trade.get("plan_adherence") else "No plan"

            summary_lines.append(
                f"{i}. {ticker} {direction} @ {entry} -> {exit_price} | "
                f"Setup: {reason}... | {adherence}"
            )

        return "\n".join(summary_lines)

    def _extract_insights(self, analysis: str) -> List[str]:
        """Extract key insights from analysis."""
        insights = []

        # Simple parsing: look for numbered points or bullet points
        lines = analysis.split("\n")
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                insights.append(line)

        return insights[:5]  # Return top 5 insights
