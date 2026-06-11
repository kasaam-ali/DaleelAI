from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from retriever import load_vectorstore, retrieve_chunks
import os

# ================================
# LOAD ENV
# ================================
# Debug - check if key loaded
load_dotenv(Path(__file__).parent.parent / ".env")
api_key = os.getenv("GROQ_API_KEY")
print(f"API Key loaded: {api_key[:10] if api_key else 'NOT FOUND'}")

# ================================
# STRICT PROMPT TEMPLATE
# ================================
PROMPT_TEMPLATE = """
You are DaleelAI — an expert AI assistant for Pakistani tax and business compliance.
You have access to official FBR documents, tax laws, and business registration guides.

STRICT RULES:
1. Answer ONLY from the provided context below
2. If answer is not in context, say exactly: "This information is not available in the provided FBR documents. Please consult FBR directly at 051-111-772-772"
3. Always mention which document your answer comes from
4. Keep answers clear and simple
5. Highlight important amounts, dates, and deadlines

CONTEXT FROM FBR DOCUMENTS:
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
        input_variables=["context", "question"]
    )

    output_parser = StrOutputParser()

    return vectorstore, llm, prompt, output_parser


# ================================
# GET ANSWER
# ================================
def get_answer(question: str, vectorstore, llm, prompt, output_parser) -> dict:
    # Step 1 - Retrieve chunks
    chunks = retrieve_chunks(question, vectorstore)

    # Step 2 - Format context
    context = format_context(chunks)

    # Step 3 - Get answer from LLM
    chain = prompt | llm | output_parser
    answer = chain.invoke({
        "context": context,
        "question": question
    })

    # Step 4 - Prepare unique sources
    sources = []
    for chunk in chunks:
        source_str = f"{chunk['source']} — Page {chunk['page']}"
        if source_str not in sources:
            sources.append(source_str)

    return {
        "answer": answer,
        "sources": sources
    }


# ================================
# TEST
# ================================
if __name__ == "__main__":
    print("DaleelAI - Testing RAG Chain...")
    print("=" * 60)

    vectorstore, llm, prompt, output_parser = build_chain()

    questions = [
    "What is the tax rate for salaried person in Pakistan?",
    "What are the requirements for sales tax registration?",
    "What is withholding tax rate?"
]

    for question in questions:
        print(f"\nQuestion: {question}")
        print("-" * 60)

        result = get_answer(
            question, vectorstore, llm, prompt, output_parser
        )

        print(f"Answer:\n{result['answer']}")
        print(f"\nSources:")
        for source in result['sources']:
            print(f"  — {source}")
        print("=" * 60)