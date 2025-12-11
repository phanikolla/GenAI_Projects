# 🎓 Intelligent L&D App (Bedrock Knowledge Bases)

[![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock_KB-FF9900?logo=amazonaws&style=for-the-badge)](https://aws.amazon.com/bedrock/)
[![OpenSearch](https://img.shields.io/badge/Vector-OpenSearch-005FD4?style=for-the-badge)](https://aws.amazon.com/opensearch-service/)
[![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python&style=for-the-badge)](https://python.org)

## 📖 Overview
This application transforms static PDF training documents into an interactive **Learning & Development (L&D) Coach**. Unlike traditional search, it uses **Amazon Bedrock Knowledge Bases** (a fully managed RAG service) to retrieve context and generate personalized learning paths.

### 🚀 Key Features
*   **Managed RAG Pipeline:** No need to manage LangChain splitters or vector stores manually; Bedrock handles the ingestion.
*   **Citation Support:** Responses include references to the specific source document (page numbers/sections).
*   **Hybrid Search:** Uses OpenSearch Serverless for accurate semantic retrieval.

## 🏗️ Architecture
![Architecture](./knowledgebase.gif)

## 🛠️ Prerequisites
1.  **AWS Bedrock Knowledge Base:** You must create a Knowledge Base in the AWS Console and sync it with an S3 bucket containing your PDFs.
2.  **OpenSearch Serverless:** (Automatically created during KB setup).
3.  **Model Access:** Enable **Claude 2.1** or **Titan Embeddings**.

## 💻 Installation & Usage

```bash
# Clone and Setup
git clone https://github.com/phanikolla/GenAI_Projects.git
cd Knowledgebase_Project
pip install -r requirements.txt
```

**Python Implementation:**
```python
import boto3

client = boto3.client('bedrock-agent-runtime')

response = client.retrieve_and_generate(
    input={'text': 'Create a 3-day learning path for Python beginners'},
    retrieveAndGenerateConfiguration={
        'type': 'KNOWLEDGE_BASE',
        'knowledgeBaseConfiguration': {
            'knowledgeBaseId': 'YOUR-KB-ID',
            'modelArn': 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-v2'
        }
    }
)

print(response['output']['text'])
```

## 🧠 Key Learnings
*   **Managed vs. Manual RAG:** In previous projects, I manually chunked text and stored it in FAISS. Using **Bedrock Knowledge Bases** reduced the code by ~60% and provided built-in auto-syncing with S3.
*   **Prompt Engineering:** To get a "Learning Path" rather than just a summary, I had to adjust the system prompt to act as an "Educational Coach" rather than a "Librarian."

---
*Maintained by Phani Kolla*

---
