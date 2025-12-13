#!/bin/bash
set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STACK_NAME="bedrock-agent-stack"
ENVIRONMENT="dev"
REGION="us-east-1"
MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0"

# Detect script directory and change to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "Working directory: $(pwd)"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   AWS Bedrock Agent - Customer Support Platform           ║${NC}"
echo -e "${BLUE}║   Deployment Script                                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

# Step 1: Validate AWS credentials
echo -e "${YELLOW}Step 1: Validating AWS credentials...${NC}"
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    echo "Please run: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✅ AWS Account: ${ACCOUNT_ID}${NC}\n"

# Step 2: Check Bedrock model access
echo -e "${YELLOW}Step 2: Checking Bedrock model access...${NC}"
echo "Note: If this fails, enable model access in AWS Console:"
echo "https://console.aws.amazon.com/bedrock/home?region=${REGION}#/modelaccess"
echo ""

# Step 3: Package Lambda functions
echo -e "${YELLOW}Step 3: Packaging Lambda functions...${NC}"

# Debug: Show current directory and list files
echo "Current working directory: $(pwd)"
echo "Checking for required files..."
if [ -f "lambda-functions/action_group_executor/lambda_function.py" ]; then
    echo "✅ Found action_group_executor/lambda_function.py"
else
    echo "❌ Missing action_group_executor/lambda_function.py"
    ls -la lambda-functions/action_group_executor/ || echo "Directory doesn't exist"
    exit 1
fi

if [ -f "lambda-functions/query_agent/lambda_function.py" ]; then
    echo "✅ Found query_agent/lambda_function.py"
else
    echo "❌ Missing query_agent/lambda_function.py"
    ls -la lambda-functions/query_agent/ || echo "Directory doesn't exist"
    exit 1
fi

# Create deployment directory
mkdir -p deployment/action_group
mkdir -p deployment/query_agent

# Package action group lambda
echo "Packaging action group executor..."
cp lambda-functions/action_group_executor/lambda_function.py deployment/action_group/
cp lambda-functions/action_group_executor/requirements.txt deployment/action_group/
cd deployment/action_group
pip install -r requirements.txt -t . --quiet --upgrade

# Create zip using Python (cross-platform)
python -c "
import zipfile
import os
with zipfile.ZipFile('../action_group.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk('.'):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, '.')
            zipf.write(file_path, arcname)
print('✅ Action group packaged')
"
cd ../..

# Package query agent lambda
echo "Packaging query agent..."
cp lambda-functions/query_agent/lambda_function.py deployment/query_agent/
cp lambda-functions/query_agent/requirements.txt deployment/query_agent/
cd deployment/query_agent
pip install -r requirements.txt -t . --quiet --upgrade

# Create zip using Python (cross-platform)
python -c "
import zipfile
import os
with zipfile.ZipFile('../query_agent.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk('.'):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, '.')
            zipf.write(file_path, arcname)
print('✅ Query agent packaged')
"
cd ../..

echo -e "${GREEN}✅ Lambda functions packaged successfully${NC}\n"

# Step 4: Deploy CloudFormation stack
echo -e "${YELLOW}Step 4: Deploying CloudFormation stack...${NC}"

# Check if stack exists
if aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION > /dev/null 2>&1; then
    echo "Stack exists, updating..."
    aws cloudformation update-stack \
        --stack-name $STACK_NAME \
        --template-body file://infrastructure/cloudformation.yaml \
        --capabilities CAPABILITY_NAMED_IAM \
        --parameters ParameterKey=Environment,ParameterValue=$ENVIRONMENT \
        --region $REGION 2>/dev/null || echo "No updates needed"
    
    echo "Waiting for stack update..."
    aws cloudformation wait stack-update-complete --stack-name $STACK_NAME --region $REGION 2>/dev/null || true
else
    echo "Creating new stack..."
    aws cloudformation create-stack \
        --stack-name $STACK_NAME \
        --template-body file://infrastructure/cloudformation.yaml \
        --capabilities CAPABILITY_NAMED_IAM \
        --parameters ParameterKey=Environment,ParameterValue=$ENVIRONMENT \
        --region $REGION
    
    echo "Waiting for stack creation..."
    aws cloudformation wait stack-create-complete --stack-name $STACK_NAME --region $REGION
fi

echo -e "${GREEN}✅ CloudFormation stack deployed${NC}\n"

# Step 5: Get stack outputs
echo -e "${YELLOW}Step 5: Retrieving stack outputs...${NC}"

API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`APIEndpoint`].OutputValue' \
    --output text)

TICKETS_TABLE=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`TicketsTableName`].OutputValue' \
    --output text)

ACTION_LAMBDA_ARN=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ActionGroupLambdaArn`].OutputValue' \
    --output text)

QUERY_LAMBDA_ARN=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`QueryAgentLambdaArn`].OutputValue' \
    --output text)

echo -e "${GREEN}✅ Stack outputs retrieved${NC}\n"

# Step 6: Update Lambda function code
echo -e "${YELLOW}Step 6: Updating Lambda function code...${NC}"

# Update action group lambda
ACTION_LAMBDA_NAME=$(echo $ACTION_LAMBDA_ARN | awk -F: '{print $NF}')
aws lambda update-function-code \
    --function-name $ACTION_LAMBDA_NAME \
    --zip-file fileb://deployment/action_group.zip \
    --region $REGION > /dev/null

echo "Waiting for action group lambda update..."
aws lambda wait function-updated --function-name $ACTION_LAMBDA_NAME --region $REGION

# Update environment variables
aws lambda update-function-configuration \
    --function-name $ACTION_LAMBDA_NAME \
    --environment "Variables={TICKETS_TABLE=${TICKETS_TABLE},CUSTOMERS_TABLE=customers-${ENVIRONMENT},ENVIRONMENT=${ENVIRONMENT}}" \
    --region $REGION > /dev/null

echo -e "${GREEN}✅ Action group lambda updated${NC}"

# Update query agent lambda
QUERY_LAMBDA_NAME=$(echo $QUERY_LAMBDA_ARN | awk -F: '{print $NF}')
aws lambda update-function-code \
    --function-name $QUERY_LAMBDA_NAME \
    --zip-file fileb://deployment/query_agent.zip \
    --region $REGION > /dev/null

echo "Waiting for query agent lambda update..."
aws lambda wait function-updated --function-name $QUERY_LAMBDA_NAME --region $REGION

echo -e "${GREEN}✅ Query agent lambda updated${NC}\n"

# Step 7: Install dependencies and Create Bedrock Agent
echo -e "${YELLOW}Step 7: Installing dependencies and creating Bedrock Agent...${NC}"

# Install required Python packages for agent creation
echo "Installing boto3 for agent creation..."
pip install boto3 --quiet --upgrade

# Create Bedrock Agent
echo "Creating Bedrock Agent..."
python setup-scripts/create_bedrock_agent.py \
    --agent-name "customer-support-agent" \
    --model-id "$MODEL_ID" \
    --stack-name "$STACK_NAME" \
    --region "$REGION"

echo ""

# Step 8: Display summary
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Deployment Complete!                                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${GREEN}📋 Deployment Summary:${NC}"
echo -e "   API Endpoint: ${BLUE}${API_ENDPOINT}${NC}"
echo -e "   Tickets Table: ${BLUE}${TICKETS_TABLE}${NC}"
echo -e "   Region: ${BLUE}${REGION}${NC}"
echo ""

echo -e "${GREEN}🧪 Test the agent:${NC}"
echo -e "   curl -X POST ${API_ENDPOINT} \\"
echo -e "     -H 'Content-Type: application/json' \\"
echo -e "     -d '{\"message\": \"I need help with my account\", \"customer_id\": \"CUST-001\"}'"
echo ""

echo -e "${GREEN}📊 Monitor logs:${NC}"
echo -e "   aws logs tail /aws/lambda/${ACTION_LAMBDA_NAME} --follow --region ${REGION}"
echo ""

echo -e "${GREEN}🧹 Cleanup (when done):${NC}"
echo -e "   ./setup-scripts/cleanup.sh"
echo ""
