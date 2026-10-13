"""Replace retrieved chunks with their parent section, inside a token budget."""

from pydantic import BaseModel

from app.core.retrieval.fusion import RankedHit

# Rough stand-in until a real tokenizer is wired. 4 characters per token.
_CHARS_PER_TOKEN = 4


class ContextBlock(BaseModel):
    parent_id: str
    text: str
    trimmed: bool = False


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // _CHARS_PER_TOKEN)


def expand_parents(
    hits: list[RankedHit],
    sections: dict[str, str],
    *,
    token_budget: int = 6000,
) -> list[ContextBlock]:
    """One block per parent, in hit order. Unknown parents fall back to the chunk text."""
    seen: set[str] = set()
    used = 0
    blocks: list[ContextBlock] = []
    for hit in hits:
        parent_id = str(hit.payload.get("parent_id") or hit.chunk_id)
        if parent_id in seen:
            continue
        seen.add(parent_id)
        text = sections.get(parent_id, str(hit.payload.get("text", "")))
        if used >= token_budget:
            break
        tokens = estimate_tokens(text)
        if used + tokens <= token_budget:
            blocks.append(ContextBlock(parent_id=parent_id, text=text))
            used += tokens
            continue
        room = (token_budget - used) * _CHARS_PER_TOKEN
        blocks.append(ContextBlock(parent_id=parent_id, text=text[:room], trimmed=True))
        break
    return blocks
