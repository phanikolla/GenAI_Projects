# L&D App using AWS Bedrock KnowledgeBase

![AWS](https://img.shields.io/badge/AWS-Bedrock-orange) ![Python](https://img.shields.io/badge/Python-3.8%2B-blue) ![Status](https://img.shields.io/badge/Status-Completed-brightgreen)

## Project Overview

This project leverages AWS Bedrock KnowledgeBase to create an AI-powered Learning and Development (L&D) application. It demonstrates the integration of cloud-native architecture with generative AI to deliver personalized and adaptive learning experiences that evolve with each interaction.

## Features

🚀 **Personalized Learning Paths**: Tailored content recommendations based on individual needs and learning styles

🧠 **Intelligent Knowledge Retrieval**: Accurate answers extracted directly from company documents in seconds

💬 **24/7 AI Learning Coach**: Conversational interface powered by Claude models for continuous guidance

🔍 **Multi-format Content Processing**: Seamlessly handles text, images, and complex document layouts

🔄 **Continuous Learning System**: Platform gets smarter with every interaction

## Technical Implementation

- **Amazon Bedrock**: Utilized KnowledgeBase, Titan Text Embedding, and Claude 2 models
- **AWS Lambda**: Implemented serverless computing for backend logic
- **S3 Bucket**: Used for storing and organizing training documents and multimedia content
- **AWS API Gateway**: Created secure API endpoints for frontend communication
- **Vector Store**: Deployed OpenSearch by AWS for efficient embedding retrieval

## Architecture Overview

This project implements a Retrieval Augmented Generation (RAG) architecture that combines the power of large language models with information retrieval systems to provide accurate and contextually relevant responses.

<details>
<summary>RAG Workflow</summary>

1. **Indexing Pipeline** (offline process):
   - **Load**: Document loaders ingest data from S3 buckets
   - **Split**: Text splitters break documents into manageable chunks
   - **Store**: Chunks are converted to embeddings and stored in OpenSearch

2. **Retrieval and Generation** (runtime process):
   - User submits a query through the API
   - System retrieves relevant information from knowledge base
   - Retrieved context augments the original query
   - Claude model generates a response based on the augmented prompt
</details>

## Prerequisites

- AWS Account with appropriate permissions
- Python 3.8 or higher
- AWS CLI configured

## Setup and Deployment

### 1. Clone the repository

git clone https://github.com/your-username/Gen_AI_Projects.git
cd Gen_AI_Projects/Knowledgebase_Project


### 2. Set up a virtual environment

python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
pip install -r requirements.txt

### 3. Configure AWS credentials

aws configure

### 4. Create S3 bucket for knowledge base documents

aws s3 mb s3://your-knowledge-base-bucket

### 5. Upload documents to S3

aws s3 cp ./data/ s3://your-knowledge-base-bucket/ --recursive

### 6. Create Amazon Bedrock Knowledge Base

Navigate to Amazon Bedrock in AWS Console

Select Knowledge Base > Create Knowledge Base

Follow UI steps to connect your S3 bucket and configure settings

### 7. Deploy Lambda function

cd lambda
zip -r function.zip .
aws lambda create-function
--function-name L&D-KnowledgeBase-Function
--runtime python3.8
--zip-file fileb://function.zip
--handler app.lambda_handler
--role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-bedrock-role

### 8. Set up API Gateway

Create API Gateway REST API through AWS Console

Connect to Lambda function

Deploy API

## Usage Guidelines

### Querying the Knowledge Base

This application can be used to:

1. **Answer Questions**: Get precise answers from your organization's knowledge base
response = client.retrieve_and_generate(
knowledgeBaseId="your-kb-id",
input={
"text": "What are the key features of our new product?"
}
)

2. **Generate Summaries**: Create concise summaries of lengthy documents

response = client.retrieve_and_generate(
knowledgeBaseId="your-kb-id",
input={
"text": "Summarize our Q2 sales report"
}
)

3. **Create Learning Paths**: Generate personalized learning recommendations

response = client.retrieve_and_generate(
knowledgeBaseId="your-kb-id",
input={
"text": "Create a learning path for Python development"
}
)

## Key Learnings

This project demonstrates that combining cloud-native architecture with generative AI creates learning experiences that are not just automated but truly adaptive and personalized. The most powerful L&D systems don't just deliver content - they understand context, user needs, and evolve over time.

## Future Enhancements

- Integration with existing LMS platforms
- Multi-language support
- Advanced analytics dashboard for learning progress
- Mobile application for on-the-go learning

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For any queries or suggestions, please open an issue or contact [Phani Kumar](mailto:pkkolla24@gmail.com).
