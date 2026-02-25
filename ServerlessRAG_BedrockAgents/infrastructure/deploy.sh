#!/bin/bash

# Deployment script for Serverless RAG with Bedrock Agents
# This script deploys all infrastructure components

set -e

# Configuration
PROJECT_NAME="serverless-rag"
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "========================================="
echo "Serverless RAG Deployment"
echo "========================================="
echo "Project: $PROJECT_NAME"
echo "Region: $AWS_REGION"
echo "Account: $AWS_ACCOUNT_ID"
echo "========================================="

# Step 1: Deploy S3 Buckets
echo ""
echo "Step 1: Deploying S3 Buckets..."
aws cloudformation deploy \
  --template-file cloudformation/s3-buckets.yaml \
  --stack-name ${PROJECT_NAME}-s3 \
  --parameter-overrides ProjectName=$PROJECT_NAME \
  --region $AWS_REGION \
  --no-fail-on-empty-changeset

S3_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name ${PROJECT_NAME}-s3 \
  --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
  --output text \
  --region $AWS_REGION)

echo "✓ S3 Bucket created: $S3_BUCKET"

# Step 2: Deploy Cognito User Pool
echo ""
echo "Step 2: Deploying Cognito User Pool..."
aws cloudformation deploy \
  --template-file cloudformation/cognito.yaml \
  --stack-name ${PROJECT_NAME}-cognito \
  --parameter-overrides ProjectName=$PROJECT_NAME \
  --region $AWS_REGION \
  --no-fail-on-empty-changeset

USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name ${PROJECT_NAME}-cognito \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
  --output text \
  --region $AWS_REGION)

USER_POOL_CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name ${PROJECT_NAME}-cognito \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolClientId`].OutputValue' \
  --output text \
  --region $AWS_REGION)

echo "✓ Cognito User Pool created: $USER_POOL_ID"
echo "✓ User Pool Client ID: $USER_POOL_CLIENT_ID"

# Step 3: Build and Push Lambda Docker Images
echo ""
echo "Step 3: Building and pushing Lambda Docker images..."

# Create ECR repositories if they don't exist
for REPO in indexing retrieval document-management; do
  aws ecr describe-repositories --repository-names ${PROJECT_NAME}-${REPO} --region $AWS_REGION 2>/dev/null || \
    aws ecr create-repository --repository-name ${PROJECT_NAME}-${REPO} --region $AWS_REGION
done

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Build and push images
cd ../lambda

for LAMBDA_DIR in indexing retrieval document_management; do
  REPO_NAME=$(echo $LAMBDA_DIR | tr '_' '-')
  IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${PROJECT_NAME}-${REPO_NAME}:latest"
  
  echo "Building $LAMBDA_DIR..."
  cd $LAMBDA_DIR
  docker build -t ${PROJECT_NAME}-${REPO_NAME} .
  docker tag ${PROJECT_NAME}-${REPO_NAME}:latest $IMAGE_URI
  docker push $IMAGE_URI
  cd ..
  
  echo "✓ Pushed $IMAGE_URI"
done

cd ../infrastructure

# Step 4: Deploy Lambda Functions
echo ""
echo "Step 4: Deploying Lambda Functions..."

INDEXING_IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${PROJECT_NAME}-indexing:latest"
RETRIEVAL_IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${PROJECT_NAME}-retrieval:latest"
DOCUMENT_MGMT_IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${PROJECT_NAME}-document-management:latest"

aws cloudformation deploy \
  --template-file cloudformation/lambda.yaml \
  --stack-name ${PROJECT_NAME}-lambda \
  --parameter-overrides \
    ProjectName=$PROJECT_NAME \
    S3BucketName=$S3_BUCKET \
    IndexingImageUri=$INDEXING_IMAGE_URI \
    RetrievalImageUri=$RETRIEVAL_IMAGE_URI \
    DocumentMgmtImageUri=$DOCUMENT_MGMT_IMAGE_URI \
  --capabilities CAPABILITY_NAMED_IAM \
  --region $AWS_REGION \
  --no-fail-on-empty-changeset

RETRIEVAL_LAMBDA_ARN=$(aws cloudformation describe-stacks \
  --stack-name ${PROJECT_NAME}-lambda \
  --query 'Stacks[0].Outputs[?OutputKey==`RetrievalFunctionArn`].OutputValue' \
  --output text \
  --region $AWS_REGION)

DOCUMENT_MGMT_LAMBDA_ARN=$(aws cloudformation describe-stacks \
  --stack-name ${PROJECT_NAME}-lambda \
  --query 'Stacks[0].Outputs[?OutputKey==`DocumentMgmtFunctionArn`].OutputValue' \
  --output text \
  --region $AWS_REGION)

echo "✓ Lambda functions deployed"

# Step 5: Create Bedrock Agent (Manual step - provide instructions)
echo ""
echo "========================================="
echo "Step 5: Create Bedrock Agent (Manual)"
echo "========================================="
echo ""
echo "Please create the Bedrock Agent manually in the AWS Console:"
echo ""
echo "1. Go to Amazon Bedrock Console > Agents"
echo "2. Click 'Create Agent'"
echo "3. Use the following configuration:"
echo "   - Agent name: ServerlessRAGAgent"
echo "   - Foundation model: Claude 3 Sonnet"
echo "   - Instructions: (copy from agent_config/agent_definition.json)"
echo ""
echo "4. Add Action Groups:"
echo "   a) RAGRetrieval"
echo "      - Lambda: $RETRIEVAL_LAMBDA_ARN"
echo "      - API Schema: (copy from agent_config/agent_definition.json)"
echo ""
echo "   b) DocumentManagement"
echo "      - Lambda: $DOCUMENT_MGMT_LAMBDA_ARN"
echo "      - API Schema: (copy from agent_config/agent_definition.json)"
echo ""
echo "5. Create an alias (e.g., 'prod')"
echo "6. Note the Agent ID and Alias ID"
echo ""

# Step 6: Update .env file
echo ""
echo "========================================="
echo "Step 6: Update Configuration"
echo "========================================="
echo ""
echo "Update your .env file with the following values:"
echo ""
echo "AWS_REGION=$AWS_REGION"
echo "AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID"
echo "S3_BUCKET_NAME=$S3_BUCKET"
echo "COGNITO_USER_POOL_ID=$USER_POOL_ID"
echo "COGNITO_CLIENT_ID=$USER_POOL_CLIENT_ID"
echo "COGNITO_REGION=$AWS_REGION"
echo "# Add these after creating Bedrock Agent:"
echo "# BEDROCK_AGENT_ID=<your-agent-id>"
echo "# BEDROCK_AGENT_ALIAS_ID=<your-alias-id>"
echo ""

echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Create the Bedrock Agent (see instructions above)"
echo "2. Update .env file with all values"
echo "3. Run FastAPI backend: cd fastapi_backend && uvicorn main:app --reload"
echo ""
