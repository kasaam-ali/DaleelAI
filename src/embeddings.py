from pathlib import Path
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
import fitz
import sys

# ================================
# PATHS AND SETTINGS
# ================================
RAW_DATA_PATH = Path(__file__).parent.parent / "data" / "raw"
CHROMA_DB_PATH = str(Path(__file__).parent.parent / "chroma_db")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# ================================
# STEP 1 - LOAD PDFS
# ================================
def load_pdfs(data_path: Path) -> list[dict]:
    all_documents = []
    pdf_files = list(data_path.glob("*.pdf"))
    print(f"\n Total PDFs found: {len(pdf_files)}")

    for pdf_path in pdf_files:
        print(f" Processing: {pdf_path.name}")
        try:
            doc = fitz.open(pdf_path)
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                if len(text.strip()) < 50:
                    continue
                all_documents.append({
                    "text": text,
                    "metadata": {
                        "source": pdf_path.name,
                        "page": page_num,
                        "total_pages": len(doc)
                    }
                })
            doc.close()
        except Exception as e:
            print(f" Error in {pdf_path.name}: {e}")
            continue

    print(f" Total pages extracted: {len(all_documents)}")
    return all_documents

# ================================
# STEP 2 - CREATE CHUNKS
# ================================
def chunk_documents(documents: list[dict]) -> tuple[list[str], list[dict]]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "]
    )

    all_texts = []
    all_metadata = []

    for doc in documents:
        chunks = splitter.split_text(doc["text"])
        for i, chunk in enumerate(chunks):
            all_texts.append(chunk)
            all_metadata.append({
                **doc["metadata"],
                "chunk_id": i
            })

    print(f" Total chunks created: {len(all_texts)}")
    return all_texts, all_metadata

# ================================
# STEP 3 - EMBED AND SAVE TO CHROMADB
# ================================
def embed_and_store(texts: list[str], metadatas: list[dict]):
    print(f"\n Loading embedding model: {EMBEDDING_MODEL}")
    print(" This may take a few minutes on first run...")

    embedding_model = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

    print(f"\n Starting embedding process...")
    print(f" Total chunks to embed: {len(texts)}")
    print(" Please wait — this will take 20 to 40 minutes...")

    # Process in batches to show progress
    BATCH_SIZE = 500
    total_batches = len(texts) // BATCH_SIZE + 1

    vectorstore = None

    for i in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[i:i + BATCH_SIZE]
        batch_metadata = metadatas[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1

        print(f" Batch {batch_num}/{total_batches} — chunks {i} to {i + len(batch_texts)}")

        if vectorstore is None:
            # First batch — create new vectorstore
            vectorstore = Chroma.from_texts(
                texts=batch_texts,
                metadatas=batch_metadata,
                embedding=embedding_model,
                persist_directory=CHROMA_DB_PATH
            )
        else:
            # Subsequent batches — add to existing
            vectorstore.add_texts(
                texts=batch_texts,
                metadatas=batch_metadata
            )

    print(f"\n All chunks embedded and saved to ChromaDB!")
    print(f" Location: {CHROMA_DB_PATH}")
    return vectorstore

# ================================
# MAIN
# ================================
if __name__ == "__main__":
    print("DaleelAI - Starting Embedding Pipeline...")

    # Step 1 - Load PDFs
    documents = load_pdfs(RAW_DATA_PATH)

    # Step 2 - Create chunks
    texts, metadatas = chunk_documents(documents)

    # Step 3 - Embed and store
    embed_and_store(texts, metadatas)

    print("\n PHASE 2 COMPLETE - Vector Database Ready!")
    print(" DaleelAI knowledge base has been built successfully.")