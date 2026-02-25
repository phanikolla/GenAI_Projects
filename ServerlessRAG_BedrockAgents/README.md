<p align="center">
  <img src="https://img.shields.io/badge/AWS-Serverless-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white" alt="AWS Serverless"/>
  <img src="https://img.shields.io/badge/Bedrock-Agents-232F3E?style=for-the-badge&logo=amazonaws&logoColor=white" alt="Bedrock Agents"/>
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11"/>
  <img src="https://img.shields.io/badge/IaC-CloudFormation-FF4F8B?style=for-the-badge&logo=amazonaws&logoColor=white" alt="CloudFormation"/>
</p>

<h1 align="center">🧠 ServerlessRAG</h1>

<p align="center">
  <strong>A production-grade, fully serverless Retrieval-Augmented Generation system<br/>powered by AWS Bedrock Agents, FAISS vector search, and Claude 3 Sonnet.</strong>
</p>

<p align="center">
  <a href="#-architecture">Architecture</a> •
  <a href="#-features">Features</a> •
  <a href="#-quickstart">Quickstart</a> •
  <a href="#-project-structure">Structure</a> •
  <a href="#-cost-analysis">Cost</a> •
  <a href="#-api-reference">API</a>
</p>

---

## 🏛️ Architecture

> **See [ARCHITECTURE.md](ARCHITECTURE.md) for the full end-to-end data flow, component deep-dive, and design rationale.**

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │                        S3 Static Website                            │
 │              index.html  │  styles.css  │  app.js                   │
 └─────────────────────────────┬────────────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │  Cognito       │  API Gateway   │
              │  (Auth)        │  (REST API)    │
              └────────────────┼────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
     ┌─────▼─────┐     ┌──────▼──────┐     ┌──────▼──────┐
     │  Document  │     │   Query     │     │  Indexing   │
     │  Mgmt λ   │     │   Lambda    │     │   Lambda    │
     └─────┬─────┘     └──────┬──────┘     └──────┬──────┘
           │                   │                   │
           ▼                   ▼                   ▼
     ┌───────────┐     ┌─────────────┐     ┌─────────────┐
     │  S3       │     │  Bedrock    │     │  Titan      │
     │  Bucket   │     │  Agent      │     │  Embeddings │
     └───────────┘     └──────┬──────┘     └──────┬──────┘
                              │                   │
                              ▼                   ▼
                       ┌─────────────┐     ┌─────────────┐
                       │  Claude 3   │     │  FAISS      │
                       │  Sonnet     │     │  on S3      │
                       └─────────────┘     └─────────────┘
```

## ✨ Features

| Category | Details |
|----------|---------|
| **🔐 Authentication** | AWS Cognito User Pools · JWT tokens · Signup/Login/Confirm flow |
| **📄 Document Management** | PDF upload · S3 storage · Metadata tracking · Delete support |
| **🔍 Vector Search** | FAISS index · Titan Embeddings v2 · Persisted to S3 |
| **🤖 AI Chat** | Bedrock Agent orchestration · Claude 3 Sonnet · Multi-turn sessions |
| **🌐 Static Hosting** | S3 website · No server required · Works from any browser |
| **🛡️ Security** | Cognito authorizer on all endpoints · CORS configured · Least-privilege IAM |
| **💰 Cost-Optimized** | FAISS instead of OpenSearch (saves ~$200/mo) · Pay-per-use Lambda · No idle costs |
| **📦 IaC** | 100% CloudFormation · Single `deploy.ps1` script · Reproducible |

## 🚀 Quickstart

### Prerequisites

- AWS CLI configured with credentials
- Docker Desktop running
- Python 3.11+
- Node.js (optional, for local dev)

### 1️⃣ Clone & Configure

```bash
git clone <repo-url>
cd ServerlessRAG_BedrockAgents

# Copy and edit environment config
cp .env.example .env
# Fill in: AWS_ACCOUNT_ID, AWS_REGION, BEDROCK_AGENT_ID, etc.
```

### 2️⃣ Deploy Infrastructure

```powershell
cd infrastructure
.\deploy.ps1
```

This deploys **5 CloudFormation stacks** in sequence:

| Step | Stack | Resources |
|------|-------|-----------|
| 1/5 | `serverless-rag-s3` | S3 bucket for documents + FAISS indexes |
| 2/5 | `serverless-rag-cognito` | User Pool, Client, Domain |
| 3/5 | `serverless-rag-lambda` | ECR repos, Docker images, 4 Lambda functions |
| 4/5 | `serverless-rag-lambda` | Deploy Lambda from ECR images |
| 5/5 | `serverless-rag-api` | REST API, Cognito authorizer, routes |

### 3️⃣ Create Bedrock Agent (Manual)

1. Open [Bedrock Console](https://console.aws.amazon.com/bedrock/home#/agents)
2. Create Agent → Model: **Claude 3 Sonnet**
3. Add Action Groups pointing to the Retrieval and Document Mgmt Lambdas
4. Create an alias → Copy Agent ID and Alias ID to `.env`

### 4️⃣ Deploy Frontend to S3

```powershell
$BUCKET = "serverless-rag-frontend-<your-account-id>"
aws s3 mb "s3://$BUCKET" --region us-east-1
aws s3 website "s3://$BUCKET" --index-document index.html
aws s3 sync frontend/ "s3://$BUCKET/"
```

### 5️⃣ Use It

Open: `http://<bucket>.s3-website-us-east-1.amazonaws.com`

Sign up → Upload PDF → Ask questions → Get AI answers with source citations.

---

## 📁 Project Structure

```
ServerlessRAG_BedrockAgents/
│
├── frontend/                    # Static web UI (S3-hosted)
│   ├── index.html               #   Auth + Dashboard + Chat
│   ├── styles.css               #   Dark theme, glassmorphism
│   └── app.js                   #   Cognito auth + API Gateway calls
│
├── lambda/                      # Lambda function source code
│   ├── indexing/                 #   PDF → chunks → FAISS → S3
│   │   ├── handler.py
│   │   └── Dockerfile
│   ├── retrieval/               #   Query → FAISS search → context
│   │   ├── handler.py
│   │   └── Dockerfile
│   ├── document_management/     #   S3 CRUD for documents
│   │   ├── handler.py
│   │   └── Dockerfile
│   └── query/                   #   Bedrock Agent invocation wrapper
│       ├── handler.py
│       └── Dockerfile
│
├── infrastructure/              # IaC and deployment
│   ├── cloudformation/
│   │   ├── s3.yaml              #   S3 bucket
│   │   ├── cognito.yaml         #   User Pool + Client
│   │   ├── lambda.yaml          #   Lambda functions + IAM roles
│   │   └── api-gateway.yaml     #   REST API + authorizer + routes
│   └── deploy.ps1               #   One-click deployment script
│
├── fastapi_backend/             # Local development server (optional)
│   ├── main.py                  #   FastAPI app
│   ├── rag_service.py           #   RAG business logic
│   └── models.py                #   Pydantic models
│
├── agent_config/                # Bedrock Agent configuration
│   ├── agent_instructions.txt
│   └── api_schema.json
│
├── .env.example                 # Environment template
├── ARCHITECTURE.md              # Detailed architecture documentation
└── README.md                    # You are here
```

## 💰 Cost Analysis

| Service | Pricing Model | Estimated Monthly (1K queries) |
|---------|--------------|-------------------------------|
| **Lambda** | $0.20 / 1M requests | ~$0.05 |
| **API Gateway** | $3.50 / 1M requests | ~$0.01 |
| **Cognito** | Free under 50K MAU | $0.00 |
| **S3** | $0.023 / GB | ~$0.05 |
| **Bedrock (Claude 3)** | $3 / 1M input tokens | ~$1.50 |
| **Bedrock (Titan Embed)** | $0.02 / 1M tokens | ~$0.01 |
| **S3 Website** | $0.023 / GB | ~$0.01 |
| | **Total** | **~$1.63/month** |

> **vs. Traditional RAG**: OpenSearch ($200+/mo) + EC2 ($50+/mo) = **$250+/month**

## 📡 API Reference

All endpoints (except `/health`) require a Cognito **ID Token** in the `Authorization` header.

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/health` | Health check | None |
| `POST` | `/query` | Ask a question (Bedrock Agent) | ✅ |
| `POST` | `/retrieve` | RAG retrieval (vector search) | ✅ |
| `GET` | `/documents` | List user's documents | ✅ |
| `POST` | `/documents` | Upload a document | ✅ |
| `DELETE` | `/documents/{id}` | Delete a document | ✅ |
| `POST` | `/index` | Trigger document indexing | ✅ |

### Example: Query

```bash
curl -X POST https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/query \
  -H "Authorization: <cognito-id-token>" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the key findings?", "session_id": null}'
```

**Response:**
```json
{
  "answer": "Based on the documents, the key findings are...",
  "session_id": "abc-123",
  "sources": ["document1.pdf", "document2.pdf"]
}
```

## 🧹 Cleanup

To tear down all AWS resources:

```powershell
# Delete S3 objects first
aws s3 rm s3://serverless-rag-<account-id>-us-east-1 --recursive
aws s3 rm s3://serverless-rag-frontend-<account-id> --recursive

# Delete stacks in reverse order
aws cloudformation delete-stack --stack-name serverless-rag-api
aws cloudformation delete-stack --stack-name serverless-rag-lambda
aws cloudformation delete-stack --stack-name serverless-rag-cognito
aws cloudformation delete-stack --stack-name serverless-rag-s3
```

---

<p align="center">
  Built with ❤️ using AWS Serverless · Bedrock Agents · Claude 3 Sonnet
</p>
