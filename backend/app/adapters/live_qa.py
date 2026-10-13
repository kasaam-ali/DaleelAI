"""Builds the live QA runner. Qdrant, FastEmbed, and Postgres connect on the first question."""

from app.adapters.fastembed_rerank import FastEmbedReranker
from app.adapters.postgres_sections import PostgresSections
from app.adapters.qdrant_search import QdrantHybridSearch
from app.agents.rag import RagRequest
from app.agents.rag_graph import run_qa_graph
from app.core.retrieval.action_links import load_action_links
from app.settings import CONFIG_DIR, Settings


class LiveQa:
    def __init__(self, settings: Settings, llm) -> None:
        self.settings = settings
        self.llm = llm
        self.search = QdrantHybridSearch(
            settings.qdrant.url,
            settings.qdrant.api_key,
            settings.models.dense,
            settings.models.sparse,
        )
        self.rerank = FastEmbedReranker(settings.models.reranker)
        self.sections = PostgresSections(settings.database_url)
        self._rules = None

    async def __call__(self, body, routed, tax_year: str, corpus_date: str, budget):
        if self._rules is None:
            self._rules = load_action_links(CONFIG_DIR / "action_links.yaml")
        request = RagRequest(
            question=body.message,
            search_query=routed.search_query or body.message,
            language=routed.language,
            tax_year=tax_year,
            corpus_date=corpus_date,
        )
        retrieval = self.settings.retrieval
        web = self.settings.web_fallback
        band = self.settings.sufficiency
        return await run_qa_graph(
            self.llm,
            self.search,
            self.rerank,
            request,
            sections=self.sections,
            link_rules=self._rules,
            budget=budget,
            sufficient_at=band.sufficient_at,
            borderline_at=band.borderline_at,
            web_minimum=web.min_rerank_score,
            web_enabled=web.enabled,
            k=retrieval.prefetch_k,
            keep=retrieval.rerank_keep,
            web_keep=web.rerank_keep,
            domain_boost=retrieval.domain_boost,
            token_budget=retrieval.context_tokens,
            runner=self.settings.adapters.agent_runner,
        )
