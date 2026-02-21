# 🎯 RAG Q&A System

[![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock-FF9900?logo=amazonaws&style=for-the-badge)](https://aws.amazon.com/bedrock/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3-blue?logo=chainlink&style=for-the-badge)](https://python.langchain.com/)
[![FAISS](https://img.shields.io/badge/FAISS-Vector_Search-00C7B7?style=for-the-badge)](https://github.com/facebookresearch/faiss)

A production-ready **Retrieval-Augmented Generation** system that answers questions about PDF documents using semantic search and LLM-powered generation.

## How It Works

```
PDF Document
     │
     ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  PDF Loader  │────▶│ Text Splitter │────▶│  Titan V2    │
│  (PyPDF)     │     │ (1000 chars)  │     │  Embeddings  │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                                                ▼
                                        ┌──────────────┐
                                        │  FAISS Index  │
                                        │ (Vector Store)│
                                        └──────┬──────┘
                                                │
User Question ──▶ Embed ──▶ MMR Search ─────────┘
                                                │
                                                ▼
                                        ┌──────────────┐
                                        │  Claude 3     │
                                        │  Sonnet (LLM) │
                                        └──────┬──────┘
                                                │
                                                ▼
                                          Answer + Sources
```

## Prerequisites

- **Python 3.10+**
- **AWS Account** with Bedrock access enabled for:
  - `amazon.titan-embed-text-v2:0` (embeddings)
  - `anthropic.claude-3-sonnet-20240229-v1:0` (LLM)
- **AWS CLI** configured with a named profile (default: `default`)

## Quick Start

```bash
# 1. Clone and navigate
cd RAG_Project

# 2. Create a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
# Edit .env with your AWS profile and preferences

# 5. Run the app
streamlit run rag_frontend.py
```

## Project Structure

```
RAG_Project/
├── rag_backend.py      # Core RAG pipeline (load → split → embed → index → query)
├── rag_frontend.py     # Streamlit chat interface
├── requirements.txt    # Pinned Python dependencies
├── .env.example        # Environment variable template
├── .gitignore          # Git ignore rules
├── RAG.gif             # Architecture animation
└── README.md
```

## Configuration

All settings are configurable via the `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_PROFILE` | `default` | AWS CLI profile name |
| `AWS_REGION` | `us-east-1` | AWS region for Bedrock |
| `EMBEDDING_MODEL_ID` | `amazon.titan-embed-text-v2:0` | Bedrock embedding model |
| `LLM_MODEL_ID` | `anthropic.claude-3-sonnet-20240229-v1:0` | Bedrock LLM model |
| `PDF_SOURCE_URL` | UPL Leave Policy PDF | URL of the PDF to index |
| `CHUNK_SIZE` | `1000` | Characters per text chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |
| `SEARCH_TYPE` | `mmr` | Retrieval strategy (`mmr` or `similarity`) |
| `SEARCH_K` | `4` | Number of chunks to retrieve |
| `SEARCH_FETCH_K` | `8` | Candidates for MMR diversity selection |

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Embeddings** | Amazon Titan Embed Text V2 (1024-dim) |
| **LLM** | Anthropic Claude 3 Sonnet via Bedrock |
| **Vector Store** | FAISS (in-memory, local) |
| **Orchestration** | LangChain 0.3 (`RetrievalQA` chain) |
| **Document Loader** | PyPDF via `langchain-community` |
| **Text Splitter** | `RecursiveCharacterTextSplitter` |
| **Retrieval** | MMR (Max Marginal Relevance) |
| **Frontend** | Streamlit with chat interface |

## Architecture Diagram

![RAG Architecture](./RAG.gif)

---
*Maintained by Phani Kolla*
