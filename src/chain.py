from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from retriever import load_vectorstore, retrieve_chunks
from langchain_memory import ConversationBufferWindowMemory
import os

# ================================
# LOAD ENV
# ================================
load_dotenv(Path(__file__).parent.parent / ".env")
api_key = os.getenv("GROQ_API_KEY")
print(f"API Key loaded: {api_key[:10] if api_key else 'NOT FOUND'}")

# ================================
# UPGRADED PROMPT — CONFIDENCE + STRUCTURE
# ================================
PROMPT_TEMPLATE = """
You are DaleelAI — Pakistan's first evidence-based AI tax assistant powered by official FBR documents.

CONFIDENCE LEVEL: {confidence_label}
{confidence_message}

STRICT RULES:
1. Answer ONLY from the provided context below
2. If answer is not in context, say exactly: "This information is not available in the provided FBR documents. Please consult FBR directly at 051-111-772-772"
3. Always cite sources: [Source: filename.pdf — Page X]
4. Use SIMPLE language — user is not a tax expert
5. For calculations, show STEP-BY-STEP working
6. If question is about provincial tax, clarify: "FBR handles federal taxes only"
7. NEVER make up information

ANSWER STRUCTURE:
📌 DIRECT ANSWER: (2-3 simple sentences)

📖 DETAILED EXPLANATION:
(With source citations after each fact)

💡 RELATED TOPICS:
(What else user should know)

📋 NEXT STEPS:
(What user should do next)

⚠️ DISCLAIMER: This guidance is based on official FBR documents. For legal advice, consult a qualified tax professional.

---
CONTEXT FROM OFFICIAL FBR DOCUMENTS:
{context}

USER QUESTION:
{question}

ANSWER:
"""

# ================================
# FORMAT CONTEXT
# ================================
def format_context(chunks: list[dict]) -> str:
    formatted = []
    for i, chunk in enumerate(chunks, 1):
        formatted.append(
            f"[Source {i}: {chunk['source']} — Page {chunk['page']}]\n{chunk['text']}"
        )
    return "\n\n".join(formatted)


# ================================
# BUILD CHAIN
# ================================
def build_chain():
    vectorstore = load_vectorstore()
    
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )
    
    prompt = PromptTemplate(
        template=PROMPT_TEMPLATE,
        input_variables=["context", "question", "confidence_label", "confidence_message"]
    )
    
    output_parser = StrOutputParser()
    
    return vectorstore, llm, prompt, output_parser


# ================================
# GET ANSWER — UPGRADED
# ================================
def get_answer(question: str, vectorstore, llm, prompt, output_parser) -> dict:
    # Step 1: Retrieve chunks WITH confidence
    chunks, conf_score, conf_label, conf_msg = retrieve_chunks(question, vectorstore)
    
    # Step 2: Format context
    context = format_context(chunks)
    
    # Step 3: Get answer from LLM with confidence info
    chain = prompt | llm | output_parser
    answer = chain.invoke({
        "context": context,
        "question": question,
        "confidence_label": conf_label,
        "confidence_message": conf_msg
    })
    
    # Step 4: Prepare unique sources
    sources = []
    for chunk in chunks:
        source_str = f"{chunk['source']} — Page {chunk['page']}"
        if source_str not in sources:
            sources.append(source_str)
    
    return {
        "answer": answer,
        "sources": sources,
        "confidence_score": conf_score,
        "confidence_label": conf_label,
        "confidence_message": conf_msg
    }


# ================================
# TEST
# ================================
if __name__ == "__main__":
    print("DaleelAI - Testing UPGRADED RAG Chain...")
    print("=" * 60)
    
    vectorstore, llm, prompt, output_parser = build_chain()
    
    questions = [
        "What is the tax rate for salaried person in Pakistan?",
        "What are the requirements for sales tax registration?",
        "What is withholding tax rate?",
        "How much tax on petrol?",
        "Freelancer pe kitna tax hai?"
    ]
    
    for question in questions:
        print(f"\nQuestion: {question}")
        print("-" * 60)
        
        result = get_answer(
            question, vectorstore, llm, prompt, output_parser
        )
        
        print(f"Confidence: {result['confidence_label']} ({result['confidence_score']:.2f})")
        print(f"Answer:\n{result['answer'][:300]}...")
        print(f"\nSources:")
        for source in result['sources']:
            print(f"  — {source}")
        print("=" * 60)