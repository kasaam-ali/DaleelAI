import os
from pathlib import Path
import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ================================
# PATHS
# ================================
RAW_DATA_PATH = Path(__file__).parent.parent / "data" / "raw"

# ================================
# STEP 1 - EXTRACT TEXT FROM PDFS
# ================================
def load_pdfs(data_path: Path) -> list[dict]:
    """S
    Open each PDF and extract text page by page.
    Store text along with source metadata.
    """
    all_documents = []
    pdf_files = list(data_path.glob("*.pdf"))
    
    print(f"\n Total PDFs found: {len(pdf_files)}")
    
    for pdf_path in pdf_files:
        print(f" Processing: {pdf_path.name}")
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                
                # Skip pages with very little text (likely images)
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
    
    print(f"\n Total pages extracted: {len(all_documents)}")
    return all_documents


# ================================
# STEP 2 - CREATE CHUNKS
# ================================
def chunk_documents(documents: list[dict]) -> list[dict]:
    """
    Split each page text into smaller chunks.
    500 characters per chunk with 50 character overlap.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " "]
    )
    
    all_chunks = []
    
    for doc in documents:
        chunks = splitter.split_text(doc["text"])
        
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "text": chunk,
                "metadata": {
                    **doc["metadata"],
                    "chunk_id": i
                }
            })
    
    print(f" Total chunks created: {len(all_chunks)}")
    return all_chunks


# ================================
# MAIN - RUN PIPELINE
# ================================
if __name__ == "__main__":
    print("DaleelAI - Starting Data Ingestion...")
    
    # Step 1 - Load PDFs
    documents = load_pdfs(RAW_DATA_PATH)
    
    # Step 2 - Create chunks
    chunks = chunk_documents(documents)
    
    # Preview first chunk
    print("\n Sample Chunk:")
    print("-" * 50)
    print(chunks[0]["text"])
    print("\n Sample Metadata:")
    print(chunks[0]["metadata"])
    
    print("\n Ingestion Complete!")