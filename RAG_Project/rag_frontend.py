"""
RAG Frontend — Streamlit UI for the RAG Q&A System

A polished chat interface that lets users ask questions about the loaded
PDF document and displays answers with source attribution.
"""

import streamlit as st

import rag_backend as backend

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="RAG Q&A System",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuration")
    st.caption("Current settings loaded from `.env`")
    st.markdown(f"**Embedding Model:** `{backend.EMBEDDING_MODEL_ID}`")
    st.markdown(f"**LLM:** `{backend.LLM_MODEL_ID}`")
    st.markdown(f"**Chunk Size:** `{backend.CHUNK_SIZE}` / Overlap: `{backend.CHUNK_OVERLAP}`")
    st.markdown(f"**Search:** `{backend.SEARCH_TYPE}` (k={backend.SEARCH_K})")
    st.divider()
    st.markdown(
        "📄 **Document Source:**\n\n"
        f"[View PDF]({backend.PDF_SOURCE_URL})"
    )
    st.divider()
    st.caption("Built with LangChain · FAISS · AWS Bedrock")

# ---------------------------------------------------------------------------
# Main Content
# ---------------------------------------------------------------------------
st.title("🎯 RAG Question & Answer")
st.markdown(
    "Ask any question about the loaded document. "
    "The system retrieves relevant passages and generates an answer using **Claude 3 Sonnet**."
)
st.divider()

# --- Index Initialization (cached in session state) ---
if "rag_chain" not in st.session_state:
    with st.spinner("📀 Building vector index — this only happens once …"):
        try:
            vectorstore = backend.build_vector_index()
            chain, retriever = backend.get_rag_chain(vectorstore)
            st.session_state.rag_chain = chain
            st.session_state.rag_retriever = retriever
        except Exception as exc:
            st.error(f"❌ Failed to build index: {exc}")
            st.stop()

# --- Chat History ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- User Input ---
if user_input := st.chat_input("Ask a question about the document …"):
    # Display user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Generate answer
    with st.chat_message("assistant"):
        with st.spinner("🔍 Searching and generating answer …"):
            try:
                result = backend.ask(
                    st.session_state.rag_chain,
                    st.session_state.rag_retriever,
                    user_input,
                )
                answer = result["answer"]
                sources = result["source_documents"]

                st.markdown(answer)

                # Show source documents
                if sources:
                    with st.expander(f"📚 Source Documents ({len(sources)} chunks)"):
                        for i, doc in enumerate(sources, 1):
                            page = doc.metadata.get("page", "N/A")
                            st.markdown(f"**Chunk {i}** — Page {page}")
                            st.code(doc.page_content[:500], language=None)

                st.session_state.messages.append(
                    {"role": "assistant", "content": answer}
                )
            except Exception as exc:
                st.error(f"❌ Error generating answer: {exc}")