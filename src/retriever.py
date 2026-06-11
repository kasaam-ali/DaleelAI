from pathlib import Path
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi  # NAYA: pip install rank-bm25
import numpy as np

# ================================
# PATHS AND SETTINGS
# ================================
CHROMA_DB_PATH = str(Path(__file__).parent.parent / "chroma_db")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_K = 5

# ================================
# SYNONYM MAPPING — NAYA
# ================================
TAX_SYNONYMS = {
    "petrol": ["petrol", "diesel", "fuel", "gasoline", "petroleum", "fuel levy", "petroleum levy"],
    "car": ["vehicle", "motor vehicle", "automobile", "transport", "car"],
    "bike": ["motorcycle", "motorbike", "two wheeler", "scooter"],
    "salary": ["income", "wages", "remuneration", "pay", "salary", "earnings"],
    "business": ["company", "firm", "enterprise", "sole proprietorship", "aop", "business"],
    "freelancer": ["independent contractor", "self-employed", "service provider", "consultant"],
    "property": ["real estate", "immovable property", "land", "building", "house", "plot"],
    "ntn": ["national tax number", "tax registration", "taxpayer identification", "ntn number"],
    "gst": ["sales tax", "value added tax", "vat", "general sales tax", "gst registration"],
    "return": ["tax return", "income tax return", "itr", "declaration", "filing"],
    "penalty": ["fine", "surcharge", "default", "late filing fee", "penalty"],
    "withholding": ["advance tax", "deduction at source", "wht", "withholding tax"],
    "exemption": ["tax free", "zero tax", "relief", "rebate", "exemption"],
    "deduction": ["allowance", "expense", "write-off", "adjustment", "deduction"],
    "registration": ["enrollment", "signup", "apply", "register", "registration"],
    "deadline": ["due date", "last date", "timeline", "time limit", "deadline"],
    "rate": ["percentage", "tax rate", "levy", "duty", "rate"],
    "import": ["customs duty", "import duty", "tariff", "customs", "import"],
    "export": ["export rebate", "drawback", "export incentive", "export"],
    "bank": ["financial institution", "banking", "bank", "financial"],
    "dividend": ["profit distribution", "shareholder payment", "dividend"],
    "capital gain": ["property sale profit", "shares profit", "capital gains", "cgt"],
    "jewelry": ["gold", "silver", "precious metal", "ornament", "jewelry"],
    "cash": ["currency", "banknote", "money", "cash", "liquid funds"],
    "foreign": ["overseas", "abroad", "international", "foreign", "offshore"],
    "agriculture": ["farming", "crop", "livestock", "agricultural", "farm"],
    "pension": ["retirement benefit", "superannuation", "pension", "retirement"],
    "medical": ["health", "hospital", "treatment", "medical expense", "healthcare"],
    "education": ["school", "university", "tuition", "educational", "education"],
    "donation": ["charity", "zakat", "sadqa", "philanthropy", "donation"],
    "loan": ["borrowing", "credit", "debt", "financing", "loan", "mortgage"],
    "rent": ["lease", "tenancy", "rental income", "rent", "leasing"],
    "insurance": ["policy", "premium", "coverage", "insurance", "assurance"],
    "stock": ["shares", "equity", "securities", "stock market", "stock"],
    "profit": ["gain", "earnings", "net income", "bottom line", "profit"],
    "loss": ["deficit", "negative income", "write-off", "loss", "carry forward"],
}

def expand_query(query: str) -> str:
    """User ke query ko synonyms se expand karo"""
    query_lower = query.lower()
    expanded_terms = set([query_lower])  # Original query
    
    words = query_lower.split()
    for word in words:
        for key, synonyms in TAX_SYNONYMS.items():
            if word in synonyms or any(syn in query_lower for syn in synonyms):
                expanded_terms.update(s.lower() for s in synonyms)
    
    return " ".join(expanded_terms)


# ================================
# CONFIDENCE SCORE — NAYA
# ================================
def calculate_confidence(docs, query: str) -> tuple:
    """Confidence score calculate karo"""
    if not docs:
        return 0.0, "🔴 LOW", "No relevant documents found"
    
    # Similarity scores extract karo
    scores = []
    for doc in docs:
        # ChromaDB similarity score (if available)
        score = getattr(doc, 'score', 0.6)
        scores.append(score)
    
    avg_similarity = sum(scores) / len(scores)
    num_docs = len(docs)
    
    # Coverage: kitne docs mile
    coverage = min(num_docs / TOP_K, 1.0)
    
    # Final score
    confidence = (avg_similarity * 0.6) + (coverage * 0.4)
    
    if confidence > 0.75:
        return confidence, "🟢 HIGH", "Verified from multiple official sources"
    elif confidence > 0.5:
        return confidence, "🟡 MEDIUM", "Limited information available"
    else:
        return confidence, "🔴 LOW", "Please verify with FBR directly"


# ================================
# LOAD VECTORSTORE
# ================================
def load_vectorstore() -> Chroma:
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
# RETRIEVE WITH SYNONYMS + CONFIDENCE — UPGRADED
# ================================
def retrieve_chunks(query: str, vectorstore: Chroma) -> tuple:
    """
    UPGRADED: Synonym expansion + Confidence scoring
    """
    # Step 1: Query expand karo
    expanded_query = expand_query(query)
    print(f"Original: '{query}'")
    print(f"Expanded: '{expanded_query}'")
    
    # Step 2: Semantic search (ChromaDB)
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": TOP_K}
    )
    
    docs = retriever.invoke(expanded_query)
    
    # Step 3: Confidence calculate karo
    confidence_score, confidence_label, confidence_message = calculate_confidence(docs, query)
    
    # Step 4: Results format karo
    results = []
    for doc in docs:
        results.append({
            "text": doc.page_content,
            "source": doc.metadata.get("source", "Unknown"),
            "page": doc.metadata.get("page", "Unknown"),
            "extraction_method": doc.metadata.get("extraction_method", "text")
        })
    
    return results, confidence_score, confidence_label, confidence_message


# ================================
# TEST
# ================================
if __name__ == "__main__":
    vectorstore = load_vectorstore()
    
    test_queries = [
        "petrol tax",
        "fuel levy",
        "car registration tax",
        "salary tax rate",
        "freelancer tax",
        "property tax",
        "GST registration"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        
        results, conf_score, conf_label, conf_msg = retrieve_chunks(query, vectorstore)
        
        print(f"Confidence: {conf_label} ({conf_score:.2f})")
        print(f"Message: {conf_msg}")
        
        for i, result in enumerate(results, 1):
            print(f"\nResult {i}:")
            print(f"  Source: {result['source']} — Page: {result['page']}")
            print(f"  Text: {result['text'][:150]}...")