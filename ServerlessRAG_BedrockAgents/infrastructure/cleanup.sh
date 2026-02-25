#!/bin/bash

# Cleanup script for Serverless RAG with Bedrock Agents
# This script deletes all AWS resources created during deployment

set -e

# Configuration
PROJECT_NAME="serverless-rag"
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "========================================="
echo "Serverless RAG Cleanup Script"
echo "========================================="
echo "Project: $PROJECT_NAME"
echo "Region: $AWS_REGION"
echo "Account: $AWS_ACCOUNT_ID"
echo "========================================="
echo ""
echo "⚠️  WARNING: This will delete ALL resources created for this project!"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Starting cleanup..."
echo ""

# Function to check if stack exists
stack_exists() {
    aws cloudformation describe-stacks --stack-name $1 --region $AWS_REGION &>/dev/null
    return $?
}

# Function to delete stack and wait
delete_stack() {
    local stack_name=$1
    if stack_exists $stack_name; then
        echo "Deleting CloudFormation stack: $stack_name..."
        aws cloudformation delete-stack --stack-name $stack_name --region $AWS_REGION
        echo "Waiting for stack deletion to complete..."
        aws cloudformation wait stack-delete-complete --stack-name $stack_name --region $AWS_REGION 2>/dev/null || true
        echo "✓ Stack $stack_name deleted"
    else
        echo "Stack $stack_name does not exist, skipping..."
    fi
}

# Step 1: Delete Lambda Functions Stack
echo ""
echo "Step 1: Deleting Lambda Functions..."
delete_stack "${PROJECT_NAME}-lambda"

# Step 2: Delete ECR Repositories and Images
echo ""
echo "Step 2: Deleting ECR Repositories..."
for REPO in indexing retrieval document-management; do
    REPO_NAME="${PROJECT_NAME}-${REPO}"
    if aws ecr describe-repositories --repository-names $REPO_NAME --region $AWS_REGION &>/dev/null; then
        echo "Deleting ECR repository: $REPO_NAME..."
        aws ecr delete-repository --repository-name $REPO_NAME --force --region $AWS_REGION
        echo "✓ Repository $REPO_NAME deleted"
    else
        echo "Repository $REPO_NAME does not exist, skipping..."
    fi
done

# Step 3: Empty and Delete S3 Bucket
echo ""
echo "Step 3: Deleting S3 Bucket..."
S3_BUCKET="${PROJECT_NAME}-${AWS_ACCOUNT_ID}-${AWS_REGION}"
if aws s3 ls "s3://${S3_BUCKET}" 2>/dev/null; then
    echo "Emptying S3 bucket: $S3_BUCKET..."
    aws s3 rm "s3://${S3_BUCKET}" --recursive --region $AWS_REGION
    echo "Deleting S3 bucket: $S3_BUCKET..."
    delete_stack "${PROJECT_NAME}-s3"
    echo "✓ S3 bucket deleted"
else
    echo "S3 bucket $S3_BUCKET does not exist, skipping..."
    delete_stack "${PROJECT_NAME}-s3" 2>/dev/null || true
fi

# Step 4: Delete Cognito User Pool
echo ""
echo "Step 4: Deleting Cognito User Pool..."
delete_stack "${PROJECT_NAME}-cognito"

# Step 5: Delete Bedrock Agent (Manual - provide instructions)
echo ""
echo "========================================="
echo "Step 5: Delete Bedrock Agent (Manual)"
echo "========================================="
echo ""
echo "⚠️  Bedrock Agents must be deleted manually:"
echo ""
echo "1. Go to AWS Console > Amazon Bedrock > Agents"
echo "2. Find agent: ServerlessRAGAgent"
echo "3. Delete all aliases"
echo "4. Delete the agent"
echo ""
echo "Or use AWS CLI:"
echo ""
echo "  # List agents"
echo "  aws bedrock-agent list-agents --region $AWS_REGION"
echo ""
echo "  # Delete agent (replace AGENT_ID)"
echo "  aws bedrock-agent delete-agent --agent-id AGENT_ID --region $AWS_REGION"
echo ""

# Step 6: Clean up local files (optional)
echo ""
echo "========================================="
echo "Step 6: Clean Local Files (Optional)"
echo "========================================="
echo ""
read -p "Do you want to delete local .env file? (yes/no): " DELETE_ENV

if [ "$DELETE_ENV" = "yes" ]; then
    if [ -f "../.env" ]; then
        rm ../.env
        echo "✓ Deleted .env file"
    fi
fi

# Step 7: Summary
echo ""
echo "========================================="
echo "Cleanup Summary"
echo "========================================="
echo ""
echo "✓ Lambda functions deleted"
echo "✓ ECR repositories deleted"
echo "✓ S3 bucket deleted"
echo "✓ Cognito User Pool deleted"
echo "⚠️  Bedrock Agent requires manual deletion"
echo ""
echo "Cleanup complete!"
echo ""
echo "Note: It may take a few minutes for all resources to be fully removed."
echo "You can verify in the AWS Console or use:"
echo "  aws cloudformation list-stacks --region $AWS_REGION"
echo ""
