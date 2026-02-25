<h1 align="center">🏛️ Architecture — ServerlessRAG</h1>

<p align="center">
  <em>A complete technical reference for the system design,<br/>component interactions, and end-to-end data flows.</em>
</p>

---

## Table of Contents

- [System Overview](#-system-overview)
- [Component Deep-Dive](#-component-deep-dive)
- [Data Flows](#-data-flows)
  - [Authentication Flow](#1-authentication-flow)
  - [Document Upload & Indexing Flow](#2-document-upload--indexing-flow)
  - [Query & RAG Retrieval Flow](#3-query--rag-retrieval-flow)
  - [Document Management Flow](#4-document-management-flow)
- [Security Architecture](#-security-architecture)
- [Infrastructure as Code](#-infrastructure-as-code)
- [Design Decisions & Trade-offs](#-design-decisions--trade-offs)
- [Scalability & Limits](#-scalability--limits)

---

## 🔭 System Overview

ServerlessRAG is a **zero-infrastructure** document intelligence platform. Users upload PDF documents, which are automatically chunked, embedded, and indexed. They can then ask natural-language questions and receive AI-generated answers grounded in their documents.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                          │
│                                                                                │
│    ┌──────────────────────────────────────────────────────────────────────┐     │
│    │                      S3 STATIC WEBSITE                              │     │
│    │         index.html   ·   styles.css   ·   app.js                    │     │
│    │                                                                     │     │
│    │   ┌─────────┐    ┌──────────────┐    ┌────────────────────┐        │     │
│    │   │  Auth   │───▶│   Cognito    │───▶│  JWT ID Token      │        │     │
│    │   │  Module │    │   REST API   │    │  (stored locally)  │        │     │
│    │   └─────────┘    └──────────────┘    └─────────┬──────────┘        │     │
│    │                                                │                    │     │
│    │   ┌─────────┐                                  │                    │     │
│    │   │  Data   │─── Authorization: <id_token> ────┘                    │     │
│    │   │  Module │                                                       │     │
│    │   └────┬────┘                                                       │     │
│    └────────┼────────────────────────────────────────────────────────────┘     │
│             │                                                                  │
│             ▼                                                                  │
│    ┌────────────────────────────────────────────────────────────────────┐      │
│    │                      API GATEWAY (REST)                            │      │
│    │                                                                    │      │
│    │   ┌──────────────────┐    Validates JWT against Cognito User Pool  │      │
│    │   │ Cognito          │    before forwarding to Lambda              │      │
│    │   │ Authorizer       │                                             │      │
│    │   └──────────────────┘                                             │      │
│    │                                                                    │      │
│    │   Routes:                                                          │      │
│    │   POST /query      ──▶  Query Lambda (Bedrock Agent)               │      │
│    │   POST /retrieve   ──▶  Retrieval Lambda (FAISS search)            │      │
│    │   GET  /documents  ──▶  Document Mgmt Lambda (list)                │      │
│    │   POST /documents  ──▶  Document Mgmt Lambda (upload)              │      │
│    │   DEL  /documents/ ──▶  Document Mgmt Lambda (delete)              │      │
│    │   POST /index      ──▶  Indexing Lambda (embed + index)            │      │
│    │   GET  /health     ──▶  Mock 200 (no Lambda)                       │      │
│    └────────────────────────────────────────────────────────────────────┘      │
│                                                                                │
└─────────────────────────────────────────────────────────────────────────────────┘

                              AWS CLOUD (us-east-1)

  ┌───────────────────────────────────────────────────────────────────────────┐
  │                          COMPUTE LAYER (Lambda)                           │
  │                                                                           │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
  │  │   Indexing    │  │  Retrieval   │  │  Document    │  │    Query     │  │
  │  │   Lambda     │  │  Lambda      │  │  Mgmt Lambda │  │   Lambda     │  │
  │  │              │  │              │  │              │  │              │  │
  │  │  PDF → chunk │  │  FAISS load  │  │  S3 CRUD    │  │  Bedrock     │  │
  │  │  → embed     │  │  → search    │  │  operations  │  │  Agent       │  │
  │  │  → FAISS     │  │  → rank      │  │              │  │  invocation  │  │
  │  │  → save S3   │  │  → return    │  │              │  │              │  │
  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
  │         │                 │                  │                 │          │
  └─────────┼─────────────────┼──────────────────┼─────────────────┼──────────┘
            │                 │                  │                 │
            ▼                 ▼                  ▼                 ▼
  ┌─────────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐
  │  Titan Embed v2 │  │   S3        │  │   S3        │  │  Bedrock Agent   │
  │  (Embeddings)   │  │  (FAISS)    │  │  (Documents) │  │  (Orchestrator)  │
  └─────────────────┘  └─────────────┘  └─────────────┘  └────────┬─────────┘
                                                                   │
                                                          ┌────────┴─────────┐
                                                          │  Claude 3 Sonnet │
                                                          │  (Foundation LLM)│
                                                          └──────────────────┘
```

---

## 🧩 Component Deep-Dive

### Frontend (S3 Static Website)

| Aspect | Detail |
|--------|--------|
| **Hosting** | S3 bucket with static website hosting enabled |
| **Files** | `index.html`, `styles.css`, `app.js` — single-page app |
| **Auth** | Calls Cognito REST API directly (no SDK) via `POST` to `cognito-idp.us-east-1.amazonaws.com` |
| **API Calls** | All data requests go to API Gateway with raw ID token in `Authorization` header |
| **Token Storage** | `localStorage` — session persists across page reloads |
| **Token Refresh** | Automatic via `REFRESH_TOKEN_AUTH` flow when a 401 is received |

### Amazon Cognito

| Aspect | Detail |
|--------|--------|
| **Resource** | User Pool + App Client |
| **Sign-in** | Email as username, password with complexity requirements |
| **Verification** | Email confirmation code |
| **Auth Flows** | `USER_PASSWORD_AUTH` for login, `REFRESH_TOKEN_AUTH` for renewal |
| **Token Types** | ID Token (used for API Gateway auth), Access Token, Refresh Token |
| **Integration** | API Gateway Cognito Authorizer validates ID tokens automatically |

### API Gateway

| Aspect | Detail |
|--------|--------|
| **Type** | REST API (regional endpoint) |
| **Auth** | `COGNITO_USER_POOLS` authorizer on all data endpoints |
| **Integration** | `AWS_PROXY` — Lambda receives full HTTP request, returns full HTTP response |
| **CORS** | `OPTIONS` methods on all resources with `Access-Control-Allow-Origin: *` |
| **Throttling** | 50 burst, 100 sustained requests/second |
| **Stage** | Single `prod` stage |

### Lambda Functions

| Function | Runtime | Memory | Timeout | Purpose |
|----------|---------|--------|---------|---------|
| `serverless-rag-indexing` | Python 3.11 (Docker) | 1024 MB | 300s | Parse PDF, chunk text, generate embeddings, build FAISS index |
| `serverless-rag-retrieval` | Python 3.11 (Docker) | 1024 MB | 60s | Load FAISS index from S3, search for relevant chunks |
| `serverless-rag-document-mgmt` | Python 3.11 (Docker) | 512 MB | 60s | List/upload/delete documents in S3 |
| `serverless-rag-query` | Python 3.11 (Docker) | 512 MB | 120s | Invoke Bedrock Agent, stream response |

### Amazon Bedrock

| Component | Model / Config |
|-----------|---------------|
| **Foundation Model** | Claude 3 Sonnet (`anthropic.claude-3-sonnet-20240229-v1:0`) |
| **Embedding Model** | Titan Embeddings v2 (`amazon.titan-embed-text-v2:0`) |
| **Agent** | Custom agent with retrieval + document action groups |
| **Agent Alias** | Production alias for stable invocations |

### Amazon S3

| Bucket | Purpose |
|--------|---------|
| `serverless-rag-<account>-<region>` | Document PDFs + FAISS indexes (`documents/`, `faiss_index/`) |
| `serverless-rag-frontend-<account>` | Static website files |

---

## 🔀 Data Flows

### 1. Authentication Flow

```
┌──────────┐         ┌──────────────────┐         ┌──────────────┐
│          │         │                  │         │              │
│  Browser │         │   Cognito REST   │         │  localStorage│
│          │         │   API            │         │              │
└────┬─────┘         └────────┬─────────┘         └──────┬───────┘
     │                        │                          │
     │  ① POST SignUp         │                          │
     │  {email, password}     │                          │
     │───────────────────────▶│                          │
     │                        │                          │
     │  ② Confirmation email  │                          │
     │◀───────────────────────│                          │
     │                        │                          │
     │  ③ POST ConfirmSignUp  │                          │
     │  {email, code}         │                          │
     │───────────────────────▶│                          │
     │                        │                          │
     │  ④ POST InitiateAuth   │                          │
     │  {email, password}     │                          │
     │───────────────────────▶│                          │
     │                        │                          │
     │  ⑤ {IdToken,           │                          │
     │     AccessToken,       │                          │
     │     RefreshToken}      │                          │
     │◀───────────────────────│                          │
     │                        │                          │
     │  ⑥ Store tokens ───────┼──────────────────────────▶│
     │                        │                          │
     │  ⑦ Show Dashboard      │                          │
     │                        │                          │
```

**Key details:**
- All auth calls go directly to `cognito-idp.us-east-1.amazonaws.com`
- Uses `X-Amz-Target` header to specify Cognito action
- No backend server involved in authentication
- ID Token is used for all subsequent API Gateway calls

---

### 2. Document Upload & Indexing Flow

```
┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────┐    ┌────────────┐
│  Browser │    │ API Gateway  │    │ Doc Mgmt λ   │    │   S3    │    │ Indexing λ │
└────┬─────┘    └──────┬───────┘    └──────┬───────┘    └────┬────┘    └─────┬──────┘
     │                 │                   │                  │              │
     │  ① POST /documents                 │                  │              │
     │  [PDF file + auth token]           │                  │              │
     │────────────────▶│                   │                  │              │
     │                 │                   │                  │              │
     │                 │  ② Validate       │                  │              │
     │                 │  ID Token         │                  │              │
     │                 │  (Cognito)        │                  │              │
     │                 │                   │                  │              │
     │                 │  ③ Forward to     │                  │              │
     │                 │  Lambda           │                  │              │
     │                 │──────────────────▶│                  │              │
     │                 │                   │                  │              │
     │                 │                   │  ④ Upload PDF    │              │
     │                 │                   │  to S3           │              │
     │                 │                   │  (documents/)    │              │
     │                 │                   │─────────────────▶│              │
     │                 │                   │                  │              │
     │                 │                   │  ⑤ Invoke        │              │
     │                 │                   │  Indexing Lambda │              │
     │                 │                   │  (async)         │              │
     │                 │                   │─────────────────────────────────▶│
     │                 │                   │                  │              │
     │  ⑥ 200 OK      │                   │                  │              │
     │  {doc_id,       │                   │                  │              │
     │   status:       │                   │                  │              │
     │   "indexing"}   │                   │                  │              │
     │◀────────────────│◀──────────────────│                  │              │
     │                 │                   │                  │              │
     │                 │                   │           ┌──────┴──────┐       │
     │                 │                   │           │  In the     │       │
     │                 │                   │           │  background │       │
     │                 │                   │           └──────┬──────┘       │
     │                 │                   │                  │              │
     │                 │                   │                  │  ⑦ Download  │
     │                 │                   │                  │◀─────────────│
     │                 │                   │                  │   PDF        │
     │                 │                   │                  │              │
     │                 │                   │                  │  ⑧ Chunk     │
     │                 │                   │                  │  text        │
     │                 │                   │                  │              │
     │                 │                   │         ┌────────┴───────┐      │
     │                 │                   │         │ Titan Embed v2 │      │
     │                 │                   │         │ (1024-dim)     │◀─────│
     │                 │                   │         └────────┬───────┘  ⑨   │
     │                 │                   │                  │              │
     │                 │                   │                  │  ⑩ Build     │
     │                 │                   │                  │  FAISS index │
     │                 │                   │                  │              │
     │                 │                   │                  │  ⑪ Save      │
     │                 │                   │                  │◀─────────────│
     │                 │                   │                  │  (faiss_index/│
     │                 │                   │                  │   on S3)     │
```

**Key details:**
- Document upload returns immediately; indexing happens **asynchronously**
- PDF is chunked with **1000-character windows** and **200-character overlap**
- Each chunk is embedded using **Titan Embeddings v2** (1024 dimensions)
- FAISS index (`IndexFlatIP` — inner product) is serialized and uploaded to S3
- Metadata mapping (chunk → source document) is stored alongside the index

---

### 3. Query & RAG Retrieval Flow

```
┌──────────┐   ┌─────────────┐   ┌──────────┐   ┌──────────────┐   ┌────────────┐
│  Browser │   │ API Gateway │   │ Query λ  │   │Bedrock Agent │   │ Claude 3   │
└────┬─────┘   └──────┬──────┘   └────┬─────┘   └──────┬───────┘   └─────┬──────┘
     │                │               │                 │                  │
     │  ① POST /query │               │                 │                  │
     │  {question,    │               │                 │                  │
     │   session_id}  │               │                 │                  │
     │───────────────▶│               │                 │                  │
     │                │               │                 │                  │
     │                │  ② Validate   │                 │                  │
     │                │  token        │                 │                  │
     │                │               │                 │                  │
     │                │  ③ Forward    │                 │                  │
     │                │──────────────▶│                 │                  │
     │                │               │                 │                  │
     │                │               │  ④ invoke_agent │                  │
     │                │               │  (agent_id,     │                  │
     │                │               │   alias_id,     │                  │
     │                │               │   session_id,   │                  │
     │                │               │   question)     │                  │
     │                │               │────────────────▶│                  │
     │                │               │                 │                  │
     │                │               │                 │  ⑤ Agent decides │
     │                │               │                 │  to call RAG     │
     │                │               │                 │  action group    │
     │                │               │                 │                  │
     │                │               │     ┌───────────┴──────────┐       │
     │                │               │     │  Retrieval Lambda    │       │
     │                │               │     │                      │       │
     │                │               │     │  ⑥ Load FAISS from   │       │
     │                │               │     │     S3               │       │
     │                │               │     │  ⑦ Embed question    │       │
     │                │               │     │     (Titan v2)       │       │
     │                │               │     │  ⑧ Search top-k=5   │       │
     │                │               │     │     chunks           │       │
     │                │               │     │  ⑨ Return context    │       │
     │                │               │     │     + sources        │       │
     │                │               │     └───────────┬──────────┘       │
     │                │               │                 │                  │
     │                │               │                 │  ⑩ Build prompt  │
     │                │               │                 │  with context    │
     │                │               │                 │─────────────────▶│
     │                │               │                 │                  │
     │                │               │                 │  ⑪ Generate      │
     │                │               │                 │  answer          │
     │                │               │                 │◀─────────────────│
     │                │               │                 │                  │
     │                │               │  ⑫ Stream      │                  │
     │                │               │  response      │                  │
     │                │               │◀───────────────│                  │
     │                │               │                 │                  │
     │  ⑬ {answer,   │               │                 │                  │
     │   session_id, │               │                 │                  │
     │   sources}    │               │                 │                  │
     │◀──────────────│◀──────────────│                 │                  │
```

**Key details:**
- Bedrock Agent **orchestrates** the entire RAG pipeline autonomously
- The Agent decides which action group to invoke based on the user's question
- Retrieval Lambda loads the FAISS index from S3 (cached in `/tmp` for warm invocations)
- Top-k chunks (k=5) are returned with similarity scores
- Claude 3 Sonnet generates answers **grounded in retrieved context**
- Session ID enables **multi-turn conversations** with memory

---

### 4. Document Management Flow

```
┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐
│  Browser │    │ API Gateway  │    │ Doc Mgmt λ   │    │    S3    │
└────┬─────┘    └──────┬───────┘    └──────┬───────┘    └────┬─────┘
     │                 │                   │                  │
     │  GET /documents │                   │                  │
     │────────────────▶│──────────────────▶│                  │
     │                 │                   │  list_objects_v2 │
     │                 │                   │─────────────────▶│
     │                 │                   │  head_object     │
     │                 │                   │  (each, for      │
     │                 │                   │   metadata)      │
     │                 │                   │─────────────────▶│
     │                 │                   │                  │
     │                 │                   │  Filter by       │
     │                 │                   │  user_id from    │
     │                 │                   │  JWT claims      │
     │  [{filename,    │                   │                  │
     │    size, date}] │                   │                  │
     │◀────────────────│◀──────────────────│                  │
     │                 │                   │                  │
     │  DELETE /docs/  │                   │                  │
     │  {doc_id}       │                   │                  │
     │────────────────▶│──────────────────▶│                  │
     │                 │                   │  delete_object   │
     │                 │                   │─────────────────▶│
     │  200 OK         │                   │                  │
     │◀────────────────│◀──────────────────│                  │
```

---

## 🔒 Security Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Security Layers                              │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Layer 1: Cognito Authentication                              │  │
│  │  · Email verification required                                │  │
│  │  · Password policy: 8+ chars, upper, lower, number, symbol   │  │
│  │  · JWT tokens with 1-hour expiry                              │  │
│  │  · Automatic token refresh                                    │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Layer 2: API Gateway Authorizer                              │  │
│  │  · Validates ID token signature against Cognito User Pool     │  │
│  │  · Rejects expired / malformed tokens automatically           │  │
│  │  · Extracts user claims (sub, email) for Lambda context       │  │
│  │  · Rate limiting: 50 burst / 100 sustained req/sec            │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Layer 3: IAM Least Privilege                                 │  │
│  │  · Lambda role: S3 (own bucket only), Bedrock (invoke only)   │  │
│  │  · API Gateway: execute-api only for specific REST API        │  │
│  │  · No wildcard resource permissions                           │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Layer 4: Data Isolation                                      │  │
│  │  · Documents tagged with user_id in S3 metadata               │  │
│  │  · Queries filtered by user_id from JWT claims                │  │
│  │  · No cross-user data access possible                         │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Infrastructure as Code

All infrastructure is defined in **4 CloudFormation templates**, deployed via a single script.

| Template | Resources | Outputs |
|----------|-----------|---------|
| `s3.yaml` | S3 Bucket with versioning | BucketName, BucketArn |
| `cognito.yaml` | UserPool, Client, Domain | PoolId, ClientId, PoolArn |
| `lambda.yaml` | 4 Lambda Functions, IAM Role | Function ARNs |
| `api-gateway.yaml` | REST API, Authorizer, 7 Routes, Stage | API URL, API ID |

**Dependency chain:**

```
s3.yaml ──▶ cognito.yaml ──▶ lambda.yaml ──▶ api-gateway.yaml
  (bucket)     (auth)         (functions)      (routes + auth)
```

---

## ⚖️ Design Decisions & Trade-offs

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **FAISS over OpenSearch** | $0/mo vs $200+/mo for managed vector DB | No real-time index updates; must rebuild full index per document |
| **Lambda over ECS/EC2** | Zero idle cost, auto-scaling, no ops | Cold starts (~3-5s), 15-min max timeout |
| **S3 over CloudFront** | Simpler setup, no distribution needed | HTTP only (no HTTPS), no edge caching |
| **Cognito direct auth** | No backend for auth, works from static site | Limited UI customization for hosted UI |
| **Docker Lambda** | Large dependencies (FAISS, LangChain, PyPDF) exceed 250MB ZIP limit | Larger cold starts than ZIP packages |
| **Single S3 bucket** | Simpler IAM, one place for all data | Must use prefixes to separate concerns |
| **Bedrock Agent** | Autonomous RAG orchestration, multi-turn memory | Less control over prompt engineering |

---

## 📊 Scalability & Limits

| Component | Limit | Mitigation |
|-----------|-------|------------|
| Lambda concurrent executions | 1,000 (default) | Request quota increase |
| Lambda memory | 10 GB max | FAISS index size must fit in memory |
| API Gateway throttle | 10,000 req/sec (account) | Configured at 100 req/sec |
| S3 request rate | 5,500 GET / 3,500 PUT per prefix | Partition prefixes by user |
| Cognito MAU | 50,000 (free tier) | Pay $0.0055/MAU beyond |
| Bedrock Claude 3 | Tokens per minute varies by region | Implement retry with backoff |
| FAISS index size | Limited by Lambda memory (10 GB) | Shard indexes per user |

---

<p align="center">
  <em>Architecture designed for cost efficiency, security, and operational simplicity.</em>
</p>
