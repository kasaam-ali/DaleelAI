"""Match curated official links to a question. Empty URLs are kept in the file but not returned."""

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

Authority = Literal["FBR", "SECP", "SRB", "PRA", "KPRA", "BRA"]
_MAX_LINKS = 3


class ActionLink(BaseModel):
    topic: str
    label: str
    label_ru: str
    url: str
    authority: Authority


class ActionLinkRule(ActionLink):
    domains: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


def load_action_links(path: Path) -> list[ActionLinkRule]:
    with open(path, encoding="utf-8") as file:
        rows = yaml.safe_load(file) or []
    return [ActionLinkRule.model_validate(row) for row in rows]


def match_action_links(
    question: str,
    rules: list[ActionLinkRule],
    *,
    domains: set[str] | None = None,
    limit: int = _MAX_LINKS,
) -> list[ActionLink]:
    """File order. A rule matches a domain or a whole-word keyword. Max `limit`."""
    wanted = {domain.lower() for domain in (domains or set())}
    matched: list[ActionLink] = []
    for rule in rules:
        if not rule.url.strip():
            continue
        domain_hit = any(domain.lower() in wanted for domain in rule.domains)
        if domain_hit or _keyword_hit(question, rule.keywords):
            matched.append(ActionLink.model_validate(rule.model_dump()))
        if len(matched) >= limit:
            break
    return matched


def _keyword_hit(question: str, keywords: list[str]) -> bool:
    lowered = question.lower()
    return any(re.search(rf"\b{re.escape(keyword.lower())}\b", lowered) for keyword in keywords)
