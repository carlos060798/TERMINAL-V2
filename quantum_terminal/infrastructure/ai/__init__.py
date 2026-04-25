"""AI backends and gateway coordinator.

Provides unified access to multiple AI backends:
- AIGateway: Master coordinator with intelligent routing
  - Groq: Fast inference (30 req/min free)
  - DeepSeek: Reasoning tasks
  - Qwen: High-throughput bulk analysis
  - OpenRouter: Universal fallback
  - Hugging Face: Local sentiment analysis
"""

from quantum_terminal.infrastructure.ai.ai_gateway import (
    AIGateway,
    get_gateway,
    AIGatewayError,
    AIBackendError,
    AIRateLimitError,
    TokenCounter,
    generate,
    batch_process,
)

__all__ = [
    # AI Gateway
    "AIGateway",
    "get_gateway",
    "AIGatewayError",
    "AIBackendError",
    "AIRateLimitError",
    "TokenCounter",
    "generate",
    "batch_process",
]
