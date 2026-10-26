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
    max_block_tokens: int | None = None,
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
        text = _labeled_text(hit.payload, sections.get(parent_id, str(hit.payload.get("text", ""))))
        trimmed = False
        if max_block_tokens and estimate_tokens(text) > max_block_tokens:
            text = text[: max_block_tokens * _CHARS_PER_TOKEN]
            trimmed = True
        if used >= token_budget:
            break
        tokens = estimate_tokens(text)
        if used + tokens <= token_budget:
            blocks.append(ContextBlock(parent_id=parent_id, text=text, trimmed=trimmed))
            used += tokens
            continue
        room = (token_budget - used) * _CHARS_PER_TOKEN
        blocks.append(ContextBlock(parent_id=parent_id, text=text[:room], trimmed=True))
        break
    return blocks


def _labeled_text(payload: dict, text: str) -> str:
    section = str(payload.get("section") or "").strip()
    if not section:
        return text
    header = str(payload.get("header") or "")
    kind = "Rule" if " > Rule " in header else "Section"
    title = str(payload.get("section_title") or "").strip()
    label = f"{kind} {section}"
    if title:
        label += f" {title}"
    if text.startswith(label) or text.startswith(f"Section {section}"):
        return text
    return f"{label}.\n{text}"
