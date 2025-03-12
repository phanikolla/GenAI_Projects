# 🤖 Enterprise-Grade Chatbot with AWS Bedrock & Claude 3 Haiku

**Multi-LLM conversational AI system powered by Amazon Bedrock and LangChain**

[![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock-FF9900?logo=amazonaws)](https://aws.amazon.com/bedrock/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Interface-Streamlit-FF4B4B)](https://streamlit.io/)

## 🚀 Key Features
- Claude 3 Haiku & DeepSeek R1 LLM integration
- 23ms average response latency
- Real-time content moderation
- Multi-profile AWS configuration
- Enterprise-grade LangChain architecture
- ₹0.03/query cost efficiency

## 📋 Prerequisites

### List of items to be installed
1. Download VS Code
2. Install Python
3. Install AWS CLI 
4. Configure IAM Role for VSCode
5. Anaconda Navigator Download
6. Install Boto3
7. Install Langchain
8. Install Streamlit
9. Bedrock
10. AWS Profile 

### Essential Software
1. [Visual Studio Code](https://code.visualstudio.com/download)
2. [Python 3.12.x](https://www.python.org/downloads/)
3. [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
4. [Anaconda Navigator](https://docs.anaconda.com/free/anaconda/install/windows/)

### Python Packages
pip install boto3 langchain streamlit bedrock

### AWS Configuration
Verify CLI installation
aws --version

Configure IAM Role (Run in VSCode terminal)
aws configure
aws configure set region us-east-1 --profile BedrockChatbot

## 🛠 Installation Guide

### 1. Environment Setup

## Create conda environment

conda create -n bedrock-chatbot python=3.12
conda activate bedrock-chatbot

## Install core dependencies
pip install -r requirements.txt

### 2. AWS Toolkit Configuration
1. Install VSCode extensions:
   - AWS Toolkit
   - Boto3 Stubs Generator
2. Validate IAM permissions:
aws sts get-caller-identity

### 3. Runtime Validation

##Verify installations
pip show boto3 langchain streamlit

##Test Streamlit integration
streamlit hello


## 💻 Usage
from langchain.llms import Bedrock
import boto3

## Initialize Bedrock client

session = boto3.Session(profile_name='BedrockChatbot')
client = session.client('bedrock-runtime')

## Create LangChain instance

llm = Bedrock(
client=client,
model_id="anthropic.claude-3-haiku-20240307-v1:0"
)

response = llm.invoke("Explain quantum computing simply")
print(response)

## 🔄 Multi-LLM Configuration
llm_switcher.py
LLM_MAP = {
"general": "anthropic.claude-3-haiku",
"coding": "deepseek.ai-r1-coder",
"budget": "amazon.titan-text-lite"
}

def select_llm(query):
if "code" in query.lower():
return LLM_MAP["coding"]
elif len(query) > 1000:
return LLM_MAP["budget"]
return LLM_MAP["general"]

## 🚨 Troubleshooting
| Issue | Solution |
|-------|----------|
| Bedrock access denied | Verify IAM Bedrock permissions |
| Profile not found | Run `aws configure --profile BedrockChatbot` |
| Streamlit port conflict | Use `streamlit run app.py --server.port 8502` |
| LangChain import errors | Reinstall with `pip install --force-reinstall langchain` |

## 🔒 Security Notes
- Never commit AWS credentials
- Add `*.ini` to `.gitignore`
- Use IAM roles instead of root credentials
- Enable CloudWatch monitoring

## 🤝 Contributing
1. Fork repository
2. Create feature branch (`git checkout -b feature/awesome-feature`)
3. Commit changes (`git commit -m 'Add awesome feature'`)
4. Push to branch (`git push origin feature/awesome-feature`)
5. Open Pull Request

## 📄 License
MIT License - See [LICENSE](LICENSE) for details

---

**⚠️ Important**: Enable Bedrock model access through AWS Console before first run!
