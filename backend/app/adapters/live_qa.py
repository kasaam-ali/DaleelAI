"""Builds the live QA runner. Qdrant, FastEmbed, and Postgres connect on the first question."""

from app.adapters.fastembed_rerank import FastEmbedReranker
from app.adapters.postgres_sections import PostgresSections
from app.adapters.qdrant_search import QdrantHybridSearch
from app.agents.rag import RagRequest
from app.agents.rag_graph import run_qa_graph
from app.core.retrieval.action_links import load_action_links
from app.core.retrieval.live_web import fetch_official_snippets
from app.settings import CONFIG_DIR, Settings


class LiveQa:
    def __init__(self, settings: Settings, llm, classifier=None) -> None:
        self.settings = settings
        self.llm = llm
        self.classifier = classifier
        self.search = QdrantHybridSearch(
            settings.qdrant.url,
            settings.qdrant.api_key,
            settings.models.dense,
            settings.models.sparse,
        )
        self.rerank = FastEmbedReranker(settings.models.reranker)
        self.sections = PostgresSections(settings.database_url)
        self._rules = None

    async def __call__(
        self,
        body,
        routed,
        tax_year: str,
        corpus_date: str,
        budget,
        on_delta=None,
        on_sources=None,
        on_status=None,
    ):
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
        domain = None
        if self.classifier is not None:
            from app.core.classifier import retrieval_domain

            domain = retrieval_domain(self.classifier.predict(body.message))
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
            domain=domain,
            token_budget=retrieval.context_tokens,
            runner=self.settings.adapters.agent_runner,
            on_delta=on_delta,
            on_sources=on_sources,
            on_status=on_status,
            live_search=fetch_official_snippets,
        )

    def warm(self) -> None:
        """Load retrieval models and the graph library before the first question."""
        import sys
        import time
        from concurrent.futures import ThreadPoolExecutor

        from app.agents.rag_graph import preload_langgraph

        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [
                pool.submit(self.search.warm),
                pool.submit(self.rerank.warm),
                pool.submit(preload_langgraph),
            ]
            for future in futures:
                future.result()
        sys.stderr.write(
            f"retrieval models ready in {(time.perf_counter() - started) * 1000:.0f}ms\n"
        )
        sys.stderr.flush()
