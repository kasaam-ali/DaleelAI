"""Build and index a small official web seed into Qdrant collection web_pages.

This script creates or updates `web_pages` only. It refuses any other collection
and checks that the `documents` count is unchanged.
"""

import hashlib
import re
import time
import uuid
from datetime import UTC, datetime
from html import unescape

COLLECTION = "web_pages"
DOCUMENTS = "documents"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
MIN_FETCHED = 400

SEEDS = (
    {
        "url": "https://fbr.gov.pk/",
        "site": "fbr.gov.pk",
        "authority": "FBR",
        "title": "Federal Board of Revenue",
        "domain": "income_tax",
        "fallback": (
            "The Federal Board of Revenue (FBR) is Pakistan's federal tax authority. "
            "It administers income tax, sales tax, federal excise duty and customs duty. "
            "The FBR helpline is 051-111-772-772. Use the official website https://fbr.gov.pk/ "
            "for notices, tax rates and taxpayer guidance."
        ),
    },
    {
        "url": "https://iris.fbr.gov.pk/",
        "site": "iris.fbr.gov.pk",
        "authority": "FBR",
        "title": "IRIS",
        "domain": "income_tax",
        "fallback": (
            "IRIS is the Federal Board of Revenue portal at https://iris.fbr.gov.pk/. "
            "Taxpayers use IRIS to register for a National Tax Number (NTN), file an income "
            "tax return, and check the Active Taxpayers List (ATL), which shows filer status."
        ),
    },
    {
        "url": "https://kpra.gov.pk/",
        "site": "kpra.gov.pk",
        "authority": "KPRA",
        "title": "Khyber Pakhtunkhwa Revenue Authority",
        "domain": "sales_tax",
        "fallback": (
            "The Khyber Pakhtunkhwa Revenue Authority (KPRA) collects sales tax on services "
            "in Khyber Pakhtunkhwa. Its official website is https://kpra.gov.pk/. "
            "Provincial sales tax on services is not federal sales tax."
        ),
    },
    {
        "url": "http://e.pra.punjab.gov.pk/",
        "site": "e.pra.punjab.gov.pk",
        "authority": "PRA",
        "title": "Punjab Revenue Authority ePRA",
        "domain": "sales_tax",
        "fallback": (
            "The Punjab Revenue Authority portal is http://e.pra.punjab.gov.pk/. "
            "It is used for sales tax on services in Punjab. This is a provincial tax, "
            "separate from FBR federal sales tax."
        ),
    },
    {
        "url": "https://www.secp.gov.pk/",
        "site": "secp.gov.pk",
        "authority": "SECP",
        "title": "Securities and Exchange Commission of Pakistan",
        "domain": "corporate_secp",
        "replay_only": True,
        "fallback": (
            "The Securities and Exchange Commission of Pakistan (SECP) registers companies. "
            "Its public site is https://www.secp.gov.pk/. A live fetch from this image often "
            "stops at a browser check, so this saved page is used. It states no fee or tax rate."
        ),
    },
    {
        "url": "http://www.srb.gos.pk/",
        "site": "srb.gos.pk",
        "authority": "SRB",
        "title": "Sindh Revenue Board",
        "domain": "sales_tax",
        "replay_only": True,
        "fallback": (
            "The Sindh Revenue Board collects sales tax on services in Sindh. "
            "FBR's own site links to http://www.srb.gos.pk/. "
            "Provincial sales tax on services is not federal sales tax. This page states no rate."
        ),
    },
    {
        "url": "https://bra.gob.pk/",
        "site": "bra.gob.pk",
        "authority": "BRA",
        "title": "Balochistan Revenue Authority",
        "domain": "sales_tax",
        "replay_only": True,
        "fallback": (
            "The Balochistan Revenue Authority taxpayer portal is https://bra.gob.pk/. "
            "It covers sales tax on services in Balochistan. This page states no rate."
        ),
    },
)


def assert_safe_collection(name: str) -> None:
    if name != COLLECTION:
        raise RuntimeError(f"refusing to write collection {name}")


def html_to_text(html: str) -> str:
    stripped = re.sub(r"(?is)<(script|style)\b.*?>.*?</\1>", " ", html)
    stripped = re.sub(r"(?s)<[^>]+>", " ", stripped)
    return re.sub(r"\s+", " ", unescape(stripped)).strip()


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def page_key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:6]


def records_for(page: dict, text: str, fetched_at: str, version: str) -> list[dict]:
    pieces = chunk_text(text)
    key = page_key(page["url"])
    page_id = str(uuid.uuid5(uuid.NAMESPACE_URL, page["url"]))
    records = []
    for index, piece in enumerate(pieces):
        heading = "Overview" if index == 0 else f"Part {index + 1}"
        records.append(
            {
                "chunk_id": f"web:{page['site']}:{key}:c{index}",
                "page_id": page_id,
                "url": page["url"],
                "site": page["site"],
                "authority": page["authority"],
                "title": page["title"],
                "heading": heading,
                "header": f"{page['site']} > {page['title']} > {heading}",
                "text": piece,
                "content_type": "html",
                "fetched_at": fetched_at,
                "domain": page["domain"],
                "corpus_version": version,
            }
        )
    return records


def fetch_text(url: str, timeout: float = 15.0) -> str:
    import httpx

    response = httpx.get(
        url,
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "DaleelAI-crawler/1.0 (+https://github.com/kasaam-ali/DaleelAI)"},
    )
    response.raise_for_status()
    kind = response.headers.get("content-type", "")
    if "html" not in kind and "text" not in kind and kind:
        return ""
    return html_to_text(response.text)


def page_is_usable(title: str, text: str) -> bool:
    """Reject a browser-check page so it cannot replace a saved official page."""
    if len(text) < 80:
        return False
    blob = f"{title}\n{text}".casefold()
    return "just a moment" not in blob and "checking your browser" not in blob


def replay_pages() -> list[dict]:
    """Saved official text. Used by replay mode and by the missing-page indexer."""
    pages = []
    for page in SEEDS:
        text = page["fallback"]
        pages.append(
            {
                "url": page["url"],
                "title": page["title"],
                "site": page["site"],
                "authority": page["authority"],
                "domain": page["domain"],
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                "text": text,
                "status": "new",
                "content_type": "html",
                "replay_only": bool(page.get("replay_only")),
            }
        )
    return pages


def pages_to_index(pages: tuple[dict, ...] = SEEDS) -> list[tuple[dict, str, str]]:
    """Return (seed, text, status) for each page. A short fetch keeps the fallback text."""
    chosen = []
    for page in pages:
        status = "fallback"
        text = page["fallback"]
        if page.get("replay_only"):
            chosen.append((page, text, "replay"))
            continue
        try:
            fetched = fetch_text(page["url"])
            if len(fetched) >= MIN_FETCHED and page_is_usable(page["title"], fetched):
                text = fetched[:8000]
                status = "fetched"
        except Exception as exc:
            status = f"fallback: {type(exc).__name__}"
        chosen.append((page, text, status))
    return chosen


def point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


def main() -> int:
    import os

    from qdrant_client import QdrantClient
    from qdrant_client.http import models

    from app.version import INDEXED_CORPUS_VERSION
    from pipeline.index import DENSE_MODEL, DENSE_SIZE, SPARSE_MODEL

    assert_safe_collection(COLLECTION)
    started = time.monotonic()
    url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
    client = QdrantClient(
        url=url,
        api_key=os.environ.get("QDRANT_API_KEY") or None,
        timeout=60,
        check_compatibility=False,
    )
    before = _count(client, DOCUMENTS)
    _ensure_web(client, DENSE_SIZE)
    fetched_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    prepared = pages_to_index()
    records = []
    summary = []
    for page, text, status in prepared:
        batch = records_for(page, text, fetched_at, INDEXED_CORPUS_VERSION)
        records.extend(batch)
        summary.append((page["url"], len(batch), status))
        print(f"{page['url']} chunks={len(batch)} {status}", flush=True)
    if not records:
        print("no web pages to index", flush=True)
        return 1
    from fastembed import SparseTextEmbedding, TextEmbedding

    dense = TextEmbedding(model_name=DENSE_MODEL)
    sparse = SparseTextEmbedding(model_name=SPARSE_MODEL)
    texts = [f"{row['header']}\n\n{row['text']}" for row in records]
    dense_vecs = list(dense.embed(texts))
    sparse_vecs = list(sparse.embed(texts))
    points = []
    for row, dense_vec, sparse_vec in zip(records, dense_vecs, sparse_vecs, strict=True):
        points.append(
            models.PointStruct(
                id=point_id(row["chunk_id"]),
                vector={
                    "dense": dense_vec.tolist(),
                    "bm25": models.SparseVector(
                        indices=sparse_vec.indices.tolist(),
                        values=sparse_vec.values.tolist(),
                    ),
                },
                payload=row,
            )
        )
    assert_safe_collection(COLLECTION)
    client.upsert(collection_name=COLLECTION, points=points)
    after = _count(client, DOCUMENTS)
    web_count = _count(client, COLLECTION)
    elapsed = round(time.monotonic() - started, 1)
    print("summary", flush=True)
    print(f"{'url':48} {'chunks':8} status", flush=True)
    for page_url, count, status in summary:
        print(f"{page_url:48} {count:<8} {status}", flush=True)
    print(f"web_pages count {web_count}", flush=True)
    print(f"documents before {before} after {after}", flush=True)
    print(f"seconds {elapsed}", flush=True)
    if before != after:
        print("documents count changed; refusing to treat this run as successful", flush=True)
        return 1
    return 0


def _count(client, name: str) -> int | None:
    if not client.collection_exists(name):
        return None
    return client.count(collection_name=name, exact=True).count


def _ensure_web(client, dense_size: int) -> None:
    from qdrant_client.http import models

    assert_safe_collection(COLLECTION)
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config={
                "dense": models.VectorParams(size=dense_size, distance=models.Distance.COSINE)
            },
            sparse_vectors_config={"bm25": models.SparseVectorParams(modifier=models.Modifier.IDF)},
        )
    for field in ("site", "authority", "domain", "page_id"):
        try:
            client.create_payload_index(
                collection_name=COLLECTION,
                field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
        except Exception as exc:
            if "already exists" not in str(exc).lower():
                raise


def existing_urls(client) -> set[str]:
    found: set[str] = set()
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION,
            limit=64,
            offset=offset,
            with_payload=["url"],
        )
        for point in points:
            url = (point.payload or {}).get("url")
            if url:
                found.add(url)
        if offset is None:
            break
    return found


def index_missing_official() -> int:
    """Upsert saved SECP, SRB, and BRA pages that are not in web_pages yet.

    Does not delete points and refuses to continue if the documents count changes.
    """
    import os

    from qdrant_client import QdrantClient

    from app.version import INDEXED_CORPUS_VERSION
    from pipeline.index import DENSE_SIZE

    assert_safe_collection(COLLECTION)
    client = QdrantClient(
        url=os.environ.get("QDRANT_URL", "http://qdrant:6333"),
        api_key=os.environ.get("QDRANT_API_KEY") or None,
        timeout=60,
        check_compatibility=False,
    )
    before = _count(client, DOCUMENTS)
    _ensure_web(client, DENSE_SIZE)
    have = existing_urls(client)
    missing = [page for page in replay_pages() if page["replay_only"] and page["url"] not in have]
    if not missing:
        print(f"official pages already present; documents {before}", flush=True)
        return 0
    from datetime import UTC, datetime

    from fastembed import SparseTextEmbedding, TextEmbedding
    from qdrant_client.http import models

    from pipeline.index import DENSE_MODEL, SPARSE_MODEL

    fetched_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    records = []
    for page in missing:
        records.extend(records_for(page, page["text"], fetched_at, INDEXED_CORPUS_VERSION))
    dense = TextEmbedding(model_name=DENSE_MODEL)
    sparse = SparseTextEmbedding(model_name=SPARSE_MODEL)
    texts = [f"{row['header']}\n\n{row['text']}" for row in records]
    dense_vecs = list(dense.embed(texts))
    sparse_vecs = list(sparse.embed(texts))
    points = []
    for row, dense_vec, sparse_vec in zip(records, dense_vecs, sparse_vecs, strict=True):
        points.append(
            models.PointStruct(
                id=point_id(row["chunk_id"]),
                vector={
                    "dense": dense_vec.tolist(),
                    "bm25": models.SparseVector(
                        indices=sparse_vec.indices.tolist(),
                        values=sparse_vec.values.tolist(),
                    ),
                },
                payload=row,
            )
        )
    assert_safe_collection(COLLECTION)
    client.upsert(collection_name=COLLECTION, points=points)
    after = _count(client, DOCUMENTS)
    print(f"added {len(points)} chunks for {len(missing)} pages", flush=True)
    print(f"documents before {before} after {after}", flush=True)
    if before != after:
        print("documents count changed", flush=True)
        return 1
    return 0
