"""Decide whether retrieved scores are enough to answer. Thresholds are arguments.

SPECS gives the web-library floor (0.5) and says the verified library uses a
borderline band. It does not give that band's numbers, so callers pass them.
"""

from typing import Literal

Band = Literal["sufficient", "borderline", "insufficient"]

# v1 chain.py. SPECS says to keep this sentence.
ABSTAIN_SENTENCE = (
    "This information is not available in the provided FBR documents. "
    "Please consult FBR directly at 051-111-772-772"
)


def verified_band(top_score: float | None, *, sufficient_at: float, borderline_at: float) -> Band:
    """top_score >= sufficient_at is enough. Below borderline_at abstains. The gap is graded."""
    if sufficient_at < borderline_at:
        raise ValueError("sufficient_at must be >= borderline_at")
    if top_score is None:
        return "insufficient"
    if top_score >= sufficient_at:
        return "sufficient"
    if top_score < borderline_at:
        return "insufficient"
    return "borderline"


def web_is_sufficient(top_score: float | None, *, minimum: float = 0.5) -> bool:
    """Web library: score only, no LLM grading. Default floor is 0.5."""
    return top_score is not None and top_score >= minimum
