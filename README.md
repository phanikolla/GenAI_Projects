# ☁️ AWS GenAI Blueprints & Projects

[![AWS](https://img.shields.io/badge/AWS-Builder-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)](https://aws.amazon.com/)
[![GenAI](https://img.shields.io/badge/GenAI-Bedrock-232F3E?style=for-the-badge&logo=amazon&logoColor=white)](https://aws.amazon.com/bedrock/)
[![LangChain](https://img.shields.io/badge/LangChain-Integration-000000?style=for-the-badge&logo=chainlink&logoColor=white)](https://python.langchain.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](./LICENSE)

## 📖 Introduction
Welcome to my **AWS Generative AI Portfolio**. This repository serves as a collection of practical, serverless architectural patterns designed to help developers fast-track their journey with **Amazon Bedrock, LangChain, and Vector Databases**.

### 🎯 Goal & Community Impact
I built this repository to solve a specific problem: **Reducing the "Time-to-Hello-World" for GenAI on AWS.**
Each project in this repository acts as a standalone blueprint that other builders can fork, deploy, and modify to understand:
*   How to overcome Lambda timeout limits when calling LLMs.
*   How to implement RAG (Retrieval Augmented Generation) securely.
*   How to build cost-effective serverless inference pipelines.

---

## 📂 Project Directory

| Project Name | Difficulty | Tech Stack | Key Learning / Pattern |
|:--- |:--- |:--- |:--- |
| **1. [Image Generation API](./Image_Generation)** | 🟡 Intermediate | Bedrock (Stable Diffusion), Lambda, API Gateway | Exposing GenAI models via RESTful APIs using Serverless architecture. |
| **2. [Text Summarization](./Text%20Summarization)** | 🟢 Beginner | Bedrock (Titan/Claude), Lambda | Handling text inputs and prompt engineering for summarization tasks. |
| **3. [Llama 3 Chatbot](./BedrockChatbot)** | 🟡 Intermediate | Llama 3, LangChain, Streamlit | Managing chat memory and session state with open-source models on AWS. |
| **4. [HR Assistant (RAG)](./RAG_Project)** | 🔴 Advanced | Bedrock, LangChain, S3, FAISS/Chroma | Building a Knowledge Base to chat with internal PDF documents (RAG). |
| **5. [Serverless E-Learning](./Knowledgebase_Project)** | 🔴 Advanced | Knowledge Bases for Amazon Bedrock, OpenSearch | Full-stack implementation of a personalized learning agent with vector search. |

---

## 🏗️ Featured Architecture

*Visualizing the flow of data is critical for cloud development. Below is the architecture for the **Serverless Image Generator** included in this repo:*

![Image Generator Architecture](./Image_Generation/PosterDesign.gif)

*(Note: Detailed architecture diagrams for other solutions are available inside their respective project folders.)*

---

## 🛠️ Prerequisites & Setup

To run these projects, ensure your environment is ready:

1.  **AWS Account**: Active account with permissions for Lambda, S3, and Bedrock.
2.  **Model Access**: ⚠️ **Important:** You must manually enable model access (Claude, Titan, Llama 3) in the [AWS Bedrock Console](https://console.aws.amazon.com/bedrock/home?#/modelaccess) (usually in `us-east-1` or `us-west-2`).
3.  **Local Tools**:
    *   Python 3.9+
    *   AWS CLI (Configured)
    *   Streamlit (`pip install streamlit`)

```bash
# Quick Start
git clone https://github.com/phanikolla/GenAI_Projects.git
cd GenAI_Projects/BedrockChatbot
pip install -r requirements.txt
streamlit run app.py
```

---

## 🚀 Roadmap (Upcoming)

I am currently experimenting with Agentic workflows. Coming soon:
*   **Bedrock Agents:** Autonomous agents that can query APIs and perform actions.
*   **Amazon Q Business:** Marketing Manager application for enterprise strategy generation.

---

## 🤝 Contribution & Feedback

This is a community-driven project! If you find a bug or have a suggestion to optimize the Lambda cold starts or prompt templates:
1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/AmazingFeature`).
3.  Open a Pull Request.

---

## 📬 Connect with the Author

I love talking about Cloud, AI, and Serverless. Let's connect!

*   **LinkedIn**: [Phani Kumar Kolla](https://www.linkedin.com/in/phanikumarkolla/)
*   **GitHub**: [@phanikolla](https://github.com/phanikolla)

---
*Built with ❤️ by Phani Kolla*
---