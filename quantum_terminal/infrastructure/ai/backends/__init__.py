"""AI Backends for Quantum Investment Terminal.

Available backends:
- groq: Fast inference, Llama 3.3 70B
- deepseek: Reasoning-focused, R1
- qwen: Bulk processing, Qwen2.5-72B
- openrouter: Universal fallback
- hf: Local FinBERT sentiment analysis
"""

from quantum_terminal.infrastructure.ai.backends.deepseek_backend import (
    DeepSeekBackend,
    DeepSeekException,
)
from quantum_terminal.infrastructure.ai.backends.groq_backend import (
    GroqBackend,
    GroqException,
)
from quantum_terminal.infrastructure.ai.backends.hf_backend import (
    HFBackend,
    HFException,
)
from quantum_terminal.infrastructure.ai.backends.openrouter_backend import (
    OpenRouterBackend,
    OpenRouterException,
)
from quantum_terminal.infrastructure.ai.backends.qwen_backend import (
    QwenBackend,
    QwenException,
)

__all__ = [
    "GroqBackend",
    "GroqException",
    "DeepSeekBackend",
    "DeepSeekException",
    "QwenBackend",
    "QwenException",
    "OpenRouterBackend",
    "OpenRouterException",
    "HFBackend",
    "HFException",
]
