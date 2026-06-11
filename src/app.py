import sys
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent))
load_dotenv(Path(__file__).parent.parent / ".env")

from chain import build_chain, get_answer

# ================================
# PAGE CONFIG
# ================================
st.set_page_config(
    page_title="DaleelAI — FBR Tax Assistant",
    page_icon="⚖️",
    layout="wide"
)

# ================================
# CUSTOM CSS
# ================================
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 2rem;
    }
    .main-title {
        color: #e2b714;
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
    }
    .main-subtitle {
        color: #a0aec0;
        font-size: 1rem;
        margin-top: 0.5rem;
    }
    .confidence-high {
        background: #d4edda;
        color: #155724;
        padding: 8px 12px;
        border-radius: 6px;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 10px;
    }
    .confidence-medium {
        background: #fff3cd;
        color: #856404;
        padding: 8px 12px;
        border-radius: 6px;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 10px;
    }
    .confidence-low {
        background: #f8d7da;
        color: #721c24;
        padding: 8px 12px;
        border-radius: 6px;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 10px;
    }
    .source-card {
        background: #1e293b;
        border-left: 4px solid #e2b714;
        padding: 0.75rem 1rem;
        border-radius: 6px;
        margin: 0.4rem 0;
        font-size: 0.85rem;
        color: #94a3b8;
    }
    .disclaimer {
        background: #1e293b;
        border: 1px solid #e2b714;
        padding: 0.75rem;
        border-radius: 8px;
        font-size: 0.8rem;
        color: #94a3b8;
        margin-top: 1rem;
    }
    .stats-box {
        background: #0f3460;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        color: white;
    }
    .stats-number {
        font-size: 1.5rem;
        font-weight: bold;
        color: #e2b714;
    }
</style>
""", unsafe_allow_html=True)

# ================================
# LOAD CHAIN
# ================================
@st.cache_resource
def initialize_chain():
    with st.spinner("Loading DaleelAI Knowledge Base..."):
        vectorstore, llm, prompt, output_parser = build_chain()
    return vectorstore, llm, prompt, output_parser

# ================================
# HEADER
# ================================
st.markdown("""
<div class="main-header">
    <div class="main-title">⚖️ DaleelAI</div>
    <div class="main-subtitle">
        Evidence-Based FBR Tax & Business Compliance Assistant for Pakistan
    </div>
</div>
""", unsafe_allow_html=True)

# ================================
# STATS BAR
# ================================
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("""
    <div class="stats-box">
        <div class="stats-number">127</div>
        <div>Documents</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown("""
    <div class="stats-box">
        <div class="stats-number">111K+</div>
        <div>Chunks</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown("""
    <div class="stats-box">
        <div class="stats-number">100%</div>
        <div>Official FBR</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown("""
    <div class="stats-box">
        <div class="stats-number">24/7</div>
        <div>Available</div>
    </div>
    """, unsafe_allow_html=True)

# ================================
# LAYOUT
# ================================
col1, col2 = st.columns([2, 1])

with col2:
    st.markdown("### 💡 Suggested Questions")
    suggested = [
        "GST registration requirements?",
        "How to get NTN number?",
        "Sales tax filing procedure?",
        "Withholding tax rates?",
        "Income tax return deadline?",
        "Tax exemptions for startups?",
        "Petrol tax rate?",
        "Freelancer tax obligations?"
    ]
    
    for question in suggested:
        if st.button(question, key=question, use_container_width=True):
            st.session_state.selected_question = question
    
    st.markdown("""
    <div class="disclaimer">
        ⚠️ <b>Disclaimer:</b> DaleelAI provides guidance based on 
        official FBR documents. For legal advice, consult a 
        qualified tax consultant or CA.
        <br><br>
        📞 FBR Helpline: 051-111-772-772
    </div>
    """, unsafe_allow_html=True)

with col1:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "sources_history" not in st.session_state:
        st.session_state.sources_history = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Handle suggested question
    if "selected_question" in st.session_state:
        prompt_input = st.session_state.selected_question
        del st.session_state.selected_question
    else:
        prompt_input = None
    
    # Chat input
    user_input = st.chat_input(
        "Ask anything about FBR tax laws, GST, NTN, business registration..."
    )
    
    final_input = user_input or prompt_input
    
    if final_input:
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": final_input
        })
        
        with st.chat_message("user"):
            st.markdown(final_input)
        
        # Get answer
        with st.chat_message("assistant"):
            with st.spinner("Searching FBR documents..."):
                vectorstore, llm, prompt, output_parser = initialize_chain()
                result = get_answer(
                    final_input,
                    vectorstore,
                    llm,
                    prompt,
                    output_parser
                )
            
            # CONFIDENCE BADGE
            conf_class = "confidence-high" if "HIGH" in result['confidence_label'] else \
                        "confidence-medium" if "MEDIUM" in result['confidence_label'] else \
                        "confidence-low"
            
            st.markdown(f"""
            <div class="{conf_class}">
                {result['confidence_label']} — {result['confidence_message']}
            </div>
            """, unsafe_allow_html=True)
            
            # Answer
            st.markdown(result["answer"])
            
            # Sources
            if result["sources"]:
                st.markdown("**📚 Sources:**")
                for source in result["sources"]:
                    st.markdown(
                        f'<div class="source-card">📄 {source}</div>',
                        unsafe_allow_html=True
                    )
        
        # Save to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"]
        })