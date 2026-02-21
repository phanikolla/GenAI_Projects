"""
RAG Backend — Retrieval-Augmented Generation Pipeline

Loads a PDF document, splits it into chunks, creates vector embeddings,
stores them in a FAISS index, and answers questions using a retrieval chain
powered by AWS Bedrock (Titan Embed V2 + Claude 3 Sonnet).

Uses the modern LangChain Expression Language (LCEL) pipeline.
"""

import logging
import os

from dotenv import load_dotenv
from langchain_aws import BedrockEmbeddings, ChatBedrock
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# AWS
AWS_PROFILE = os.getenv("AWS_PROFILE", "default")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Models
EMBEDDING_MODEL_ID = os.getenv("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
LLM_MODEL_ID = os.getenv(
    "LLM_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0"
)

# Document source
PDF_SOURCE_URL = os.getenv(
    "PDF_SOURCE_URL",
    "https://www.upl-ltd.com/images/people/downloads/Leave-Policy-India.pdf",
)

# Chunking
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Retrieval
SEARCH_TYPE = os.getenv("SEARCH_TYPE", "mmr")
SEARCH_K = int(os.getenv("SEARCH_K", "4"))
SEARCH_FETCH_K = int(os.getenv("SEARCH_FETCH_K", "8"))

# RAG prompt
RAG_PROMPT_TEMPLATE = """\
Use the following context to answer the question. If the answer is not
contained in the context, say "I don't have enough information to answer
that question based on the provided document."

Context:
{context}

Question: {question}

Answer:"""


# ---------------------------------------------------------------------------
# Core Functions
# ---------------------------------------------------------------------------
def load_and_split_documents(
    pdf_url: str = PDF_SOURCE_URL,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list:
    """Load a PDF from *pdf_url* and split it into overlapping chunks."""
    logger.info("Loading PDF from %s", pdf_url)
    loader = PyPDFLoader(pdf_url)
    pages = loader.load()
    logger.info("Loaded %d page(s)", len(pages))

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents(pages)
    logger.info(
        "Split into %d chunk(s) (size=%d, overlap=%d)",
        len(chunks), chunk_size, chunk_overlap,
    )
    return chunks


def get_embeddings() -> BedrockEmbeddings:
    """Return a Bedrock embeddings client."""
    return BedrockEmbeddings(
        credentials_profile_name=AWS_PROFILE,
        region_name=AWS_REGION,
        model_id=EMBEDDING_MODEL_ID,
    )


def build_vector_index(
    chunks: list | None = None,
    embeddings: BedrockEmbeddings | None = None,
) -> FAISS:
    """Create a FAISS vector store from document *chunks*.

    If *chunks* is ``None`` the default PDF is loaded and split automatically.
    """
    if chunks is None:
        chunks = load_and_split_documents()
    if embeddings is None:
        embeddings = get_embeddings()

    logger.info("Building FAISS index with %d chunks …", len(chunks))
    vectorstore = FAISS.from_documents(chunks, embeddings)
    logger.info("FAISS index ready (%d vectors)", vectorstore.index.ntotal)
    return vectorstore


def get_llm() -> ChatBedrock:
    """Return a ChatBedrock LLM instance."""
    return ChatBedrock(
        credentials_profile_name=AWS_PROFILE,
        region_name=AWS_REGION,
        model_id=LLM_MODEL_ID,
        model_kwargs={
            "max_tokens": 3000,
            "temperature": 0.1,
            "top_p": 0.9,
        },
    )


def _format_docs(docs: list) -> str:
    """Join retrieved documents into a single context string."""
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


def get_rag_chain(vectorstore: FAISS):
    """Build an LCEL RAG chain backed by the given *vectorstore*.

    Returns a tuple of (chain, retriever) so the caller can also
    access the raw retrieved documents for source attribution.
    """
    retriever = vectorstore.as_retriever(
        search_type=SEARCH_TYPE,
        search_kwargs={"k": SEARCH_K, "fetch_k": SEARCH_FETCH_K},
    )

    prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

    chain = (
        {"context": retriever | _format_docs, "question": RunnablePassthrough()}
        | prompt
        | get_llm()
        | StrOutputParser()
    )

    return chain, retriever


def ask(chain, retriever, question: str) -> dict:
    """Send a *question* through the RAG chain and return the result.

    Returns a dict with keys ``answer`` and ``source_documents``.
    """
    logger.info("Question: %s", question)

    # Retrieve source documents separately for attribution
    source_docs = retriever.invoke(question)

    # Run the chain for the answer
    answer = chain.invoke(question)

    logger.info("Answer received (%d source docs)", len(source_docs))
    return {
        "answer": answer,
        "source_documents": source_docs,
    }