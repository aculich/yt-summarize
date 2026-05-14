"""
Preset model ladders for --cheap / --deep with context-aware selection.

Context sizes follow OpenAI-style advertised limits (verify on vendor docs).
Selection picks the first ladder entry whose context fits required tokens.
"""

from __future__ import annotations

# (model_id, context_window_tokens) — ordered by preference within each preset.
# Cheap: lowest cost first (first that fits wins).
CHEAP_LADDER: tuple[tuple[str, int], ...] = (
    ("gpt-5-nano", 400_000),  # developers.openai.com GPT-5 nano
    ("gpt-4.1-nano", 1_048_576),  # GPT-4.1 family 1M window
    ("gpt-5.4-nano", 272_000),  # GPT-5.4-class ~272K tier (pricing table family)
    ("gpt-5-mini", 272_000),
    ("gpt-4.1-mini", 1_048_576),
    ("gpt-4.1", 1_048_576),
)

# Deep ladder: stronger models before wider-context fallbacks (gpt-5.5/gpt-4.1 for >272K-tier estimates).
DEEP_LADDER: tuple[tuple[str, int], ...] = (
    ("gpt-5.2", 272_000),
    ("gpt-5", 272_000),
    ("gpt-5.1", 400_000),
    ("gpt-5.4", 272_000),
    ("gpt-5.5", 1_048_576),
    ("gpt-4.1", 1_048_576),
)

# Template instructions + system text + wrappers (conservative).
_PROMPT_OVERHEAD: dict[str, int] = {
    "whole": 4_096,
    "chapter": 4_256,  # includes -p title ...
    "merge": 4_096,
}

# Reserved space for completion (markdown summary can grow with long videos).
_OUTPUT_RESERVE: dict[str, int] = {
    "whole": 12_288,
    "chapter": 8_192,
    "merge": 24_576,
}


def estimate_tokens(text: str) -> int:
    """Upper-bound token estimate without tokenizer deps (English-heavy transcripts)."""
    if not text:
        return 0
    chars = len(text)
    words = max(len(text.split()), 1)
    # ~4 chars/token typical; use /3 to bias conservative; also word-based bound.
    return max(chars // 3, int(words * 1.6))


def required_context_tokens(payload: str, job_kind: str) -> int:
    """Total context window needed: payload + prompt overhead + output budget."""
    kind = job_kind if job_kind in _PROMPT_OVERHEAD else "whole"
    return estimate_tokens(payload) + _PROMPT_OVERHEAD[kind] + _OUTPUT_RESERVE[kind]


def pick_preset_model(deep: bool, required_tokens: int) -> str:
    """
    Choose a model from the cheap or deep ladder.
    Raises ValueError if no candidate fits.
    """
    ladder = DEEP_LADDER if deep else CHEAP_LADDER
    for model_id, ctx in ladder:
        if ctx >= required_tokens:
            return model_id
    max_ctx = max(c for _, c in ladder)
    raise ValueError(
        f"No preset model fits: need ~{required_tokens:,} token context "
        f"(payload + prompt + output reserve), max in ladder is {max_ctx:,}. "
        "Pass an explicit --model with a larger context or shorten the input."
    )
