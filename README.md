# ⚖️ DaleelAI — AI-Powered FBR Tax Assistant

> Evidence-based AI for Pakistani Tax & Business Compliance

![Python](https://img.shields.io/badge/Python-3.13-blue)
![LangChain](https://img.shields.io/badge/LangChain-Latest-green)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Latest-orange)
![Groq](https://img.shields.io/badge/Groq-Llama3-purple)

---

## 🎯 Problem Statement

Every year, thousands of Pakistani entrepreneurs and freelancers 
struggle with FBR tax compliance. A single consultation with a 
Chartered Accountant costs PKR 20,000+. Most small business owners 
cannot afford this.

**DaleelAI solves this.**

---

## 💡 Solution

DaleelAI is an AI-powered RAG chatbot trained on official FBR 
documents. It provides accurate, source-cited answers to tax 
questions — completely free.

### Real Questions DaleelAI Can Answer
- How do I register for GST/Sales Tax?
- What are the NTN registration requirements?
- What is the withholding tax rate?
- What are the tax filing deadlines?
- What documents are needed for business registration?

---

## 🏗️ System Architecture
User Query
↓

Streamlit UI (app.py)
↓

Query Embedding (all-MiniLM-L6-v2)
↓

ChromaDB Similarity Search
↓

Top 5 Relevant FBR Document Chunks
↓

Groq LLM (Llama 3.3 70B)
↓

Source-Cited Answer
↓

User
---

---

## 📊 Knowledge Base Stats

| Metric | Value |
|--------|-------|
| Total FBR Documents | 80+ PDFs |
| Total Pages Indexed | 18,760 |
| Total Chunks | 103,093 |
| Embedding Model | all-MiniLM-L6-v2 |
| Vector Dimensions | 384 |
| Database | ChromaDB |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.13 |
| Orchestration | LangChain |
| Embeddings | HuggingFace — all-MiniLM-L6-v2 |
| Vector Store | ChromaDB |
| LLM | Groq — Llama 3.3 70B |
| UI | Streamlit |
| PDF Processing | PyMuPDF |

---

## 📁 Project Structure
DaleelAI/
├── data/
│   └── raw/              # 80+ FBR PDF documents
├── src/
│   ├── ingest.py         # PDF loading and chunking
│   ├── embeddings.py     # Vector embedding pipeline
│   ├── retriever.py      # Semantic search
│   ├── chain.py          # RAG chain with Groq LLM
│   └── app.py            # Streamlit web interface
├── chroma_db/            # Persistent vector database
├── .env                  # API keys (not in repo)
├── requirements.txt      # Dependencies
└── README.md

---

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/DaleelAI.git
cd DaleelAI
```

### 2. Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables
Create a `.env` file in root directory:
GROQ_API_KEY=your_groq_api_key_here
Get your free API key at: https://console.groq.com

### 5. Add FBR Documents
Place FBR PDF documents in `data/raw/` folder.
Download from: https://www.fbr.gov.pk

### 6. Build Knowledge Base
```bash
python src/embeddings.py
```
Note: This takes 20-40 minutes on first run.

### 7. Run DaleelAI
```bash
streamlit run src/app.py
```

---

## ✨ Key Features

### Evidence-Based Answers
Every answer comes directly from official FBR documents.
No hallucinations — if information is not found,
system explicitly says so.

### Source Citations
Every response includes exact document name and 
page number for verification.

### Responsible AI
System never guesses. When information is unavailable,
it directs users to FBR helpline: 051-111-772-772

### Comprehensive Coverage
Covers Income Tax, Sales Tax, Federal Excise,
Customs, NTN Registration, GST Filing and more.

---

## 📚 Data Sources

All data sourced from official FBR website:
https://www.fbr.gov.pk

- Income Tax Ordinance 2001
- Sales Tax Act 1990
- Sales Tax Rules 2006
- Income Tax Rules 2002
- Federal Excise Act 2005
- Tax Laws Amendment Ordinance 2025
- 80+ additional FBR documents

All documents are publicly available and open source.

---

## ⚠️ Disclaimer

DaleelAI provides guidance based on official FBR documents
for informational purposes only. This is not legal or 
financial advice. For complex matters, consult a qualified
tax consultant or CA.

FBR Official Helpline: 051-111-772-772
FBR Website: https://www.fbr.gov.pk

---

## 👨‍💻 Developer

Built with ❤️ for Pakistani entrepreneurs and freelancers.

*"Making tax compliance accessible for every Pakistani"*

