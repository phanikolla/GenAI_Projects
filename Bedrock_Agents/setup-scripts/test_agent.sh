#!/bin/bash

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

STACK_NAME="bedrock-agent-stack"
REGION="us-east-1"

# Function to format JSON output
format_json() {
    local response="$1"
    # Try python first, then fallback to raw output
    if command -v python >/dev/null 2>&1; then
        echo "$response" | python -m json.tool 2>/dev/null || echo "$response"
    else
        echo "$response"
    fi
}

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Testing Bedrock Agent                                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

# Get API endpoint
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`APIEndpoint`].OutputValue' \
    --output text)

if [ -z "$API_ENDPOINT" ]; then
    echo -e "${RED}❌ Could not find API endpoint${NC}"
    exit 1
fi

echo -e "${GREEN}API Endpoint: ${API_ENDPOINT}${NC}\n"

# Test 1: Create a ticket
echo -e "${YELLOW}Test 1: Creating a support ticket...${NC}"
RESPONSE=$(curl -s -X POST $API_ENDPOINT \
    -H "Content-Type: application/json" \
    -d '{
        "message": "I cannot login to my account. The password reset link is not working.",
        "customer_id": "CUST-12345"
    }')

format_json "$RESPONSE"
echo ""

# Test 2: Check customer info
echo -e "${YELLOW}Test 2: Retrieving customer information...${NC}"
RESPONSE=$(curl -s -X POST $API_ENDPOINT \
    -H "Content-Type: application/json" \
    -d '{
        "message": "Show me my ticket history",
        "customer_id": "CUST-12345"
    }')

format_json "$RESPONSE"
echo ""

# Test 3: Escalation scenario
echo -e "${YELLOW}Test 3: Testing escalation...${NC}"
RESPONSE=$(curl -s -X POST $API_ENDPOINT \
    -H "Content-Type: application/json" \
    -d '{
        "message": "This is urgent! My business is down and I need immediate help!",
        "customer_id": "CUST-12345"
    }')

format_json "$RESPONSE"
echo ""

echo -e "${GREEN}✅ Tests complete!${NC}\n"
