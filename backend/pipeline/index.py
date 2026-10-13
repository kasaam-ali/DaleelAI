"""Index chunk files into the Qdrant `documents` collection.

Run inside the backend container:
    python scripts/index_qdrant.py

Dense vectors are BAAI/bge-small-en-v1.5 and sparse vectors are Qdrant/bm25.
The embedded string is the contextual header plus the chunk text. The payload
text stays the raw chunk. Only active catalog rows are indexed. Points already
in the collection are skipped, then new chunks are upserted in batches.
"""

import argparse
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path

from pipeline.catalog import CATALOG_PATH, DATA_DIR, CatalogEntry, read_catalog
from pipeline.chunk import CHUNK_VERSION, jurisdiction_for

DENSE_MODEL = "BAAI/bge-small-en-v1.5"
SPARSE_MODEL = "Qdrant/bm25"
DENSE_SIZE = 384
COLLECTION = "documents"
BATCH = 64
PROGRESS_EVERY = 2000
PAYLOAD_INDEXES = ("doc_id", "work_id", "domain", "doc_type", "tax_years")


def embed_input(chunk: dict) -> str:
    header = chunk.get("header", "").strip()
    text = chunk.get("text", "").strip()
    if header and text:
        return f"{header}\n\n{text}"
    return header or text


def point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


def corpus_version(entries: list[CatalogEntry]) -> str:
    digest = hashlib.sha256()
    for entry in sorted((e for e in entries if e.searchable), key=lambda e: e.doc_id):
        digest.update(entry.doc_id.encode())
        digest.update(entry.sha256.encode())
    digest.update(f"{CHUNK_VERSION}|{DENSE_MODEL}|{SPARSE_MODEL}".encode())
    return digest.hexdigest()[:16]


def payload_for(chunk: dict, entry: CatalogEntry, version: str) -> dict:
    return {
        "chunk_id": chunk["chunk_id"],
        "doc_id": entry.doc_id,
        "work_id": entry.work_id,
        "doc_title": entry.title,
        "doc_type": entry.doc_type,
        "domain": entry.domain,
        "jurisdiction": chunk.get("jurisdiction") or jurisdiction_for(entry),
        "section": chunk.get("section", ""),
        "section_title": chunk.get("section_title", ""),
        "parent_id": chunk.get("parent_id", ""),
        "page_start": chunk["page_start"],
        "page_end": chunk["page_end"],
        "header": chunk.get("header", ""),
        "text": chunk.get("text", ""),
        "tax_years": entry.tax_year_list,
        "source_url": entry.source_url,
        "corpus_version": version,
    }


def load_chunks(entry: CatalogEntry, data_dir: Path = DATA_DIR) -> list[dict]:
    path = data_dir / "chunks" / f"{entry.doc_id}.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    if saved.get("sha256") != entry.sha256:
        raise ValueError(f"{entry.doc_id}: chunks are stale, rerun pipeline.chunk")
    return [chunk for chunk in saved["chunks"] if embed_input(chunk)]


def _client(url: str, api_key: str):
    from qdrant_client import QdrantClient

    return QdrantClient(url=url, api_key=api_key or None, timeout=60, check_compatibility=False)


def ensure_collection(client) -> None:
    from qdrant_client.http import models

    if not client.collection_exists(COLLECTION):
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config={
                "dense": models.VectorParams(size=DENSE_SIZE, distance=models.Distance.COSINE)
            },
            sparse_vectors_config={
                "bm25": models.SparseVectorParams(modifier=models.Modifier.IDF)
            },
        )
    for field in PAYLOAD_INDEXES:
        try:
            client.create_payload_index(
                collection_name=COLLECTION,
                field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
        except Exception as exc:
            if "already exists" not in str(exc).lower():
                raise


def _models():
    from fastembed import SparseTextEmbedding, TextEmbedding

    dense = TextEmbedding(model_name=DENSE_MODEL)
    sparse = SparseTextEmbedding(model_name=SPARSE_MODEL)
    return dense, sparse


def _points(chunks: list[dict], entry: CatalogEntry, version: str, dense, sparse):
    from qdrant_client.http import models

    texts = [embed_input(chunk) for chunk in chunks]
    dense_vecs = list(dense.embed(texts, batch_size=BATCH))
    sparse_vecs = list(sparse.embed(texts, batch_size=BATCH))
    points = []
    for chunk, dense_vec, sparse_vec in zip(chunks, dense_vecs, sparse_vecs, strict=True):
        points.append(
            models.PointStruct(
                id=point_id(chunk["chunk_id"]),
                vector={
                    "dense": dense_vec.tolist(),
                    "bm25": models.SparseVector(
                        indices=sparse_vec.indices.tolist(),
                        values=sparse_vec.values.tolist(),
                    ),
                },
                payload=payload_for(chunk, entry, version),
            )
        )
    return points


def chunks_to_index(chunks: list[dict], done: set[str]) -> list[dict]:
    return [chunk for chunk in chunks if point_id(chunk["chunk_id"]) not in done]


def crossed_progress(before: int, after: int, every: int = PROGRESS_EVERY) -> bool:
    return after // every != before // every


def stored_point_ids(client) -> set[str]:
    found: set[str] = set()
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION,
            limit=1000,
            offset=offset,
            with_payload=False,
            with_vectors=False,
        )
        found.update(str(point.id) for point in points)
        if offset is None or not points:
            break
    return found


def index_entries(entries: list[CatalogEntry], client, dense, sparse, version: str, data_dir: Path):
    done = stored_point_ids(client)
    print(f"resume: {len(done)} points already in {COLLECTION}", flush=True)
    rows = []
    visited = 0
    upserted = 0

    def report(doc_id: str) -> None:
        print(
            f"progress {visited} chunks visited, {upserted} upserted this run, "
            f"{len(done)} points known, last {doc_id}",
            flush=True,
        )

    for entry in entries:
        started = time.monotonic()
        try:
            chunks = load_chunks(entry, data_dir)
            pending = chunks_to_index(chunks, done)
            skipped = len(chunks) - len(pending)
            before = visited
            visited += skipped
            if crossed_progress(before, visited):
                report(entry.doc_id)
            for offset in range(0, len(pending), BATCH):
                batch = pending[offset : offset + BATCH]
                client.upsert(
                    collection_name=COLLECTION,
                    points=_points(batch, entry, version, dense, sparse),
                )
                done.update(point_id(chunk["chunk_id"]) for chunk in batch)
                upserted += len(batch)
                before = visited
                visited += len(batch)
                if crossed_progress(before, visited):
                    report(entry.doc_id)
            rows.append(
                {
                    "doc_id": entry.doc_id,
                    "points": len(pending),
                    "skipped": skipped,
                    "seconds": round(time.monotonic() - started, 1),
                    "status": "indexed",
                }
            )
        except Exception as exc:
            print(f"failed {entry.doc_id}: {exc}", flush=True)
            rows.append(
                {
                    "doc_id": entry.doc_id,
                    "points": 0,
                    "skipped": 0,
                    "seconds": 0,
                    "status": f"failed: {exc}",
                }
            )
        print(
            f"{entry.doc_id} {rows[-1]['status']} new={rows[-1]['points']} "
            f"skipped={rows[-1]['skipped']} in {rows[-1]['seconds']}s",
            flush=True,
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    import os

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--doc", action="append", help="only this doc_id (repeatable)")
    args = parser.parse_args(argv)

    entries = [entry for entry in read_catalog(CATALOG_PATH) if entry.searchable]
    if args.doc:
        wanted = set(args.doc)
        entries = [entry for entry in entries if entry.doc_id in wanted]
    if not entries:
        print("no documents selected", flush=True)
        return 2

    url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
    client = _client(url, os.environ.get("QDRANT_API_KEY", ""))
    ensure_collection(client)
    version = corpus_version(read_catalog(CATALOG_PATH))
    print(f"{len(entries)} documents, corpus {version}", flush=True)
    dense, sparse = _models()
    rows = index_entries(entries, client, dense, sparse, version, DATA_DIR)
    indexed = sum(row["points"] for row in rows if row["status"] == "indexed")
    failed = sum(1 for row in rows if row["status"] != "indexed")
    count = client.count(collection_name=COLLECTION, exact=True).count
    print(
        f"indexed {indexed} points this run, failed {failed}, collection count {count}",
        flush=True,
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
