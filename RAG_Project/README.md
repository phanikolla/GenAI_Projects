# 📚 Manual RAG System (LangChain + FAISS)

[![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock-FF9900?logo=amazonaws&style=for-the-badge)](https://aws.amazon.com/bedrock/)
[![LangChain](https://img.shields.io/badge/LangChain-Orchestration-blue?logo=chainlink&style=for-the-badge)](https://python.langchain.com/)
[![FAISS](https://img.shields.io/badge/Vector-FAISS-00C7B7?style=for-the-badge)](https://github.com/facebookresearch/faiss)

## 📖 Overview
This project implements a **Retrieval-Augmented Generation (RAG)** system from scratch using LangChain and FAISS. It is designed for scenarios where fine-grained control over document chunking and embedding strategies is required (e.g., complex HR documents or technical manuals).

### 🚀 Key Features
*   **Custom Chunking:** Implements specific splitting strategies (RecursiveCharacterTextSplitter) to maintain context overlap.
*   **Local Vector Store:** Uses FAISS for low-latency, cost-effective vector search without spinning up a dedicated database server.
*   **Source Attribution:** Returns the exact document and page number used to generate the answer.

## 🏗️ Architecture
![Architecture](./RAG.gif)

## 🛠️ Prerequisites
*   **AWS Bedrock Access:** Enabled for **Titan Embeddings G1 - Text** and **Claude Instant**.
*   **Python Libraries:** `langchain`, `faiss-cpu`, `boto3`, `streamlit`.

## 💻 Installation & Usage

```bash
# 1. Setup Environment
cd RAG_Project
pip install -r requirements.txt

# 2. Run the Streamlit UI
streamlit run app.py
```

**Configuration (Inside `app.py`):**
```python
# Adjust chunking parameters for better context
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200 # Crucial for keeping context across boundaries
)
```

## 🧠 Key Learnings & Challenges
*   **The "Lost in the Middle" Phenomenon:** I discovered that LLMs sometimes ignore context in the middle of long prompts. I improved accuracy by implementing a "Max Marginal Relevance" (MMR) search instead of simple similarity search to diversify the retrieved chunks.
*   **Token Limits:** Handling documents larger than the context window required implementing a strict chunking strategy.

---
*Maintained by Phani Kolla*

---
