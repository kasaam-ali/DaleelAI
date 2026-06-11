from pathlib import Path
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# ================================
# PATHS AND SETTINGS
# ================================
CHROMA_DB_PATH = str(Path(__file__).parent.parent / "chroma_db")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_K = 5

# ================================
# LOAD VECTORSTORE
# ================================
def load_vectorstore() -> Chroma:
    """
    Load existing ChromaDB vectorstore.
    Already built — no need to rebuild.
    """
    print("Loading ChromaDB vectorstore...")

    embedding_model = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

    vectorstore = Chroma(
        persist_directory=CHROMA_DB_PATH,
        embedding_function=embedding_model
    )

    print("Vectorstore loaded successfully!")
    return vectorstore


# ================================
# RETRIEVE RELEVANT CHUNKS
# ================================
def retrieve_chunks(query: str, vectorstore: Chroma) -> list[dict]:
    """
    Take user query.
    Find top 5 most relevant chunks from ChromaDB.
    Return chunks with source metadata.
    """
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": TOP_K}
    )

    docs = retriever.invoke(query)

    results = []
    for doc in docs:
        results.append({
            "text": doc.page_content,
            "source": doc.metadata.get("source", "Unknown"),
            "page": doc.metadata.get("page", "Unknown")
        })

    return results


# ================================
# TEST
# ================================
if __name__ == "__main__":
    vectorstore = load_vectorstore()

    test_query = "GST registration requirements documents needed"
    print(f"\nTest Query: {test_query}")
    print("-" * 50)

    results = retrieve_chunks(test_query, vectorstore)

    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(f"Source: {result['source']} — Page: {result['page']}")
        print(f"Text: {result['text'][:200]}...")