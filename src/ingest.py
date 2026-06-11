from pathlib import Path
import fitz
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from langchain_text_splitters import RecursiveCharacterTextSplitter
import io

# ================================
# PATHS AND SETTINGS
# ================================
RAW_DATA_PATH = Path(__file__).parent.parent / "data" / "raw"
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\Program Files\poppler-26.02.0\Library\bin"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
MIN_TEXT_LENGTH = 50
OCR_THRESHOLD = 100

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# ================================
# STEP 1 - CHECK IF PAGE NEEDS OCR
# ================================
def needs_ocr(text: str) -> bool:
    """
    Check if extracted text is too short.
    If yes, page is likely a scanned image.
    """
    return len(text.strip()) < OCR_THRESHOLD


# ================================
# STEP 2 - OCR A SINGLE PAGE
# ================================
def ocr_page(pdf_path: Path, page_num: int) -> str:
    """
    Convert PDF page to image and run OCR.
    Returns extracted text from scanned page.
    """
    try:
        images = convert_from_path(
            pdf_path,
            first_page=page_num,
            last_page=page_num,
            dpi=300,
            poppler_path=POPPLER_PATH
        )

        if not images:
            return ""

        text = pytesseract.image_to_string(
            images[0],
            lang="eng",
            config="--psm 6"
        )

        return text.strip()

    except Exception as e:
        print(f"    OCR error on page {page_num}: {e}")
        return ""


# ================================
# STEP 3 - LOAD ALL PDFS
# ================================
def load_pdfs(data_path: Path) -> list[dict]:
    """
    Load all PDFs from directory.
    Use PyMuPDF for text PDFs.
    Use OCR for scanned image pages.
    """
    all_documents = []
    pdf_files = list(data_path.glob("*.pdf"))

    print(f"\nTotal PDFs found: {len(pdf_files)}")

    total_text_pages = 0
    total_ocr_pages = 0
    total_skipped = 0

    for pdf_path in pdf_files:
        print(f"\nProcessing: {pdf_path.name}")

        try:
            doc = fitz.open(pdf_path)
            pdf_text_pages = 0
            pdf_ocr_pages = 0

            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()

                if needs_ocr(text):
                    ocr_text = ocr_page(pdf_path, page_num)

                    if len(ocr_text.strip()) < MIN_TEXT_LENGTH:
                        total_skipped += 1
                        continue

                    all_documents.append({
                        "text": ocr_text,
                        "metadata": {
                            "source": pdf_path.name,
                            "page": page_num,
                            "total_pages": len(doc),
                            "extraction_method": "ocr"
                        }
                    })
                    pdf_ocr_pages += 1
                    total_ocr_pages += 1

                else:
                    all_documents.append({
                        "text": text,
                        "metadata": {
                            "source": pdf_path.name,
                            "page": page_num,
                            "total_pages": len(doc),
                            "extraction_method": "text"
                        }
                    })
                    pdf_text_pages += 1
                    total_text_pages += 1

            doc.close()
            print(f"  Text pages: {pdf_text_pages} | OCR pages: {pdf_ocr_pages}")

        except Exception as e:
            print(f"  Error in {pdf_path.name}: {e}")
            continue

    print(f"\nTotal text pages: {total_text_pages}")
    print(f"Total OCR pages: {total_ocr_pages}")
    print(f"Total skipped pages: {total_skipped}")
    print(f"Total pages extracted: {len(all_documents)}")

    return all_documents


# ================================
# STEP 4 - CREATE CHUNKS
# ================================
def chunk_documents(documents: list[dict]) -> tuple[list[str], list[dict]]:
    """
    Split documents into smaller chunks.
    500 characters with 100 overlap for better context.
    """
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
            if len(chunk.strip()) < 30:
                continue

            all_texts.append(chunk)
            all_metadata.append({
                **doc["metadata"],
                "chunk_id": i
            })

    print(f"Total chunks created: {len(all_texts)}")
    return all_texts, all_metadata


# ================================
# MAIN
# ================================
if __name__ == "__main__":
    print("DaleelAI - Enhanced Ingestion with OCR Support")
    print("=" * 55)

    documents = load_pdfs(RAW_DATA_PATH)

    if not documents:
        print("No documents found!")
        exit()

    texts, metadatas = chunk_documents(documents)

    print("\nSample chunk:")
    print("-" * 50)
    print(texts[0])
    print("\nSample metadata:")
    print(metadatas[0])

    print("\nIngestion Complete!")
    print(f"Ready to embed {len(texts)} chunks")