#!/bin/bash
set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

STACK_NAME="bedrock-agent-stack"
REGION="us-east-1"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   AWS Bedrock Agent - Cleanup Script                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${YELLOW}⚠️  WARNING: This will delete all resources!${NC}"
echo -e "This includes:"
echo -e "  - Bedrock Agent and aliases"
echo -e "  - Lambda functions"
echo -e "  - DynamoDB tables (and all data)"
echo -e "  - API Gateway"
echo -e "  - IAM roles"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo -e "${GREEN}Cleanup cancelled${NC}"
    exit 0
fi

# Load agent config if exists
if [ -f "agent_config.json" ]; then
    echo -e "\n${YELLOW}Step 1: Deleting Bedrock Agent...${NC}"
    
    AGENT_ID=$(cat agent_config.json | grep -o '"agent_id": "[^"]*' | cut -d'"' -f4)
    
    if [ ! -z "$AGENT_ID" ]; then
        echo "Deleting agent aliases..."
        aws bedrock-agent list-agent-aliases \
            --agent-id $AGENT_ID \
            --region $REGION \
            --query 'agentAliasSummaries[*].agentAliasId' \
            --output text | xargs -I {} aws bedrock-agent delete-agent-alias \
            --agent-id $AGENT_ID \
            --agent-alias-id {} \
            --region $REGION 2>/dev/null || true
        
        echo "Deleting agent..."
        aws bedrock-agent delete-agent \
            --agent-id $AGENT_ID \
            --region $REGION 2>/dev/null || true
        
        echo -e "${GREEN}✅ Agent deleted${NC}"
        
        # Delete IAM role
        ROLE_NAME="customer-support-agent-role"
        echo "Deleting IAM role policies..."
        aws iam delete-role-policy \
            --role-name $ROLE_NAME \
            --policy-name BedrockModelAccess 2>/dev/null || true
        
        echo "Deleting IAM role..."
        aws iam delete-role --role-name $ROLE_NAME 2>/dev/null || true
        
        echo -e "${GREEN}✅ IAM role deleted${NC}"
    fi
    
    rm -f agent_config.json
fi

# Delete CloudFormation stack
echo -e "\n${YELLOW}Step 2: Deleting CloudFormation stack...${NC}"

if aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION > /dev/null 2>&1; then
    aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION
    
    echo "Waiting for stack deletion..."
    aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME --region $REGION
    
    echo -e "${GREEN}✅ Stack deleted${NC}"
else
    echo "Stack not found, skipping..."
fi

# Clean up deployment artifacts
echo -e "\n${YELLOW}Step 3: Cleaning up local artifacts...${NC}"
rm -rf deployment/
echo -e "${GREEN}✅ Local artifacts cleaned${NC}"

echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Cleanup Complete!                                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${GREEN}All resources have been deleted.${NC}\n"
