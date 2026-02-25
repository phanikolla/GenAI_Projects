# Deployment script for Serverless RAG with Bedrock Agents (Windows PowerShell)
# Run from the infrastructure/ directory

$ErrorActionPreference = "Continue"

# Configuration
$PROJECT_NAME = "serverless-rag"
$AWS_REGION = if ($env:AWS_REGION) { $env:AWS_REGION } else { "us-east-1" }

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Serverless RAG Deployment (Windows)" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Get AWS Account ID
try {
    $AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text 2>&1).Trim()
    if ($LASTEXITCODE -ne 0) { throw "AWS CLI failed" }
    Write-Host "Project : $PROJECT_NAME" -ForegroundColor White
    Write-Host "Region  : $AWS_REGION" -ForegroundColor White
    Write-Host "Account : $AWS_ACCOUNT_ID" -ForegroundColor White
    Write-Host "=========================================" -ForegroundColor Cyan
}
catch {
    Write-Host "ERROR: AWS CLI not configured or not installed." -ForegroundColor Red
    Write-Host "Run 'aws configure' first." -ForegroundColor Yellow
    exit 1
}

# Check Docker
$dockerCheck = docker info 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nERROR: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "`n[OK] Docker is running" -ForegroundColor Green

# ============================================================
# Step 1: Deploy S3 Bucket
# ============================================================
Write-Host "`n--- Step 1/5: Deploying S3 Bucket ---" -ForegroundColor Yellow

aws cloudformation deploy `
    --template-file cloudformation/s3-buckets.yaml `
    --stack-name "$PROJECT_NAME-s3" `
    --parameter-overrides "ProjectName=$PROJECT_NAME" `
    --region $AWS_REGION `
    --no-fail-on-empty-changeset

$S3_BUCKET = (aws cloudformation describe-stacks `
        --stack-name "$PROJECT_NAME-s3" `
        --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" `
        --output text `
        --region $AWS_REGION).Trim()

Write-Host "[OK] S3 Bucket: $S3_BUCKET" -ForegroundColor Green

# ============================================================
# Step 2: Deploy Cognito User Pool
# ============================================================
Write-Host "`n--- Step 2/5: Deploying Cognito User Pool ---" -ForegroundColor Yellow

aws cloudformation deploy `
    --template-file cloudformation/cognito.yaml `
    --stack-name "$PROJECT_NAME-cognito" `
    --parameter-overrides "ProjectName=$PROJECT_NAME" `
    --region $AWS_REGION `
    --no-fail-on-empty-changeset

$USER_POOL_ID = (aws cloudformation describe-stacks `
        --stack-name "$PROJECT_NAME-cognito" `
        --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" `
        --output text `
        --region $AWS_REGION).Trim()

$USER_POOL_CLIENT_ID = (aws cloudformation describe-stacks `
        --stack-name "$PROJECT_NAME-cognito" `
        --query "Stacks[0].Outputs[?OutputKey=='UserPoolClientId'].OutputValue" `
        --output text `
        --region $AWS_REGION).Trim()

Write-Host "[OK] Cognito User Pool: $USER_POOL_ID" -ForegroundColor Green
Write-Host "[OK] Client ID: $USER_POOL_CLIENT_ID" -ForegroundColor Green

$USER_POOL_ARN = (aws cloudformation describe-stacks `
        --stack-name "$PROJECT_NAME-cognito" `
        --query "Stacks[0].Outputs[?OutputKey=='UserPoolArn'].OutputValue" `
        --output text `
        --region $AWS_REGION).Trim()

# ============================================================
# Step 3: Build and Push Lambda Docker Images
# ============================================================
Write-Host "`n--- Step 3/5: Building & Pushing Lambda Docker Images ---" -ForegroundColor Yellow

# Create ECR repositories
$ECR_REPOS = @("indexing", "retrieval", "document-management")
foreach ($REPO in $ECR_REPOS) {
    $repoName = "$PROJECT_NAME-$REPO"
    $repoCheck = aws ecr describe-repositories --repository-names $repoName --region $AWS_REGION 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Creating ECR repo: $repoName" -ForegroundColor White
        aws ecr create-repository --repository-name $repoName --region $AWS_REGION 2>&1 | Out-Null
    }
    else {
        Write-Host "  ECR repo exists: $repoName" -ForegroundColor White
    }
}

# Login to ECR
Write-Host "  Logging in to ECR..." -ForegroundColor White
$ecrPassword = aws ecr get-login-password --region $AWS_REGION 2>&1 | Out-String
$ecrPassword = $ecrPassword.Trim()
$ecrLoginResult = $ecrPassword | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com" 2>&1 | Out-String
Write-Host "  [OK] ECR login successful" -ForegroundColor Green

# Build and push each Lambda image
$LAMBDA_DIRS = @(
    @{ Dir = "indexing"; Repo = "indexing" },
    @{ Dir = "retrieval"; Repo = "retrieval" },
    @{ Dir = "document_management"; Repo = "document-management" }
)

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$lambdaRoot = (Resolve-Path (Join-Path $scriptDir "..\lambda")).Path
Write-Host "  Lambda source: $lambdaRoot" -ForegroundColor White

foreach ($lambda in $LAMBDA_DIRS) {
    $dir = $lambda.Dir
    $repo = $lambda.Repo
    $IMAGE_URI = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-${repo}:latest"
    $buildPath = Join-Path $lambdaRoot $dir

    Write-Host "`n  Building $dir..." -ForegroundColor White
    docker build --provenance=false -t "$PROJECT_NAME-$repo" "$buildPath"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Docker build failed for $dir" -ForegroundColor Red
        exit 1
    }

    docker tag "$PROJECT_NAME-${repo}:latest" $IMAGE_URI
    Write-Host "  Pushing $IMAGE_URI..." -ForegroundColor White
    docker push $IMAGE_URI
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Docker push failed for $dir" -ForegroundColor Red
        exit 1
    }
    Write-Host "  [OK] Pushed $repo" -ForegroundColor Green
}

# ============================================================
# Step 4: Deploy Lambda Functions (CloudFormation)
# ============================================================
Write-Host "`n--- Step 4/4: Deploying Lambda Functions ---" -ForegroundColor Yellow

$INDEXING_IMAGE_URI = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-indexing:latest"
$RETRIEVAL_IMAGE_URI = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-retrieval:latest"
$DOCUMENT_MGMT_IMAGE_URI = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-document-management:latest"

aws cloudformation deploy `
    --template-file cloudformation/lambda.yaml `
    --stack-name "$PROJECT_NAME-lambda" `
    --parameter-overrides `
    "ProjectName=$PROJECT_NAME" `
    "S3BucketName=$S3_BUCKET" `
    "IndexingImageUri=$INDEXING_IMAGE_URI" `
    "RetrievalImageUri=$RETRIEVAL_IMAGE_URI" `
    "DocumentMgmtImageUri=$DOCUMENT_MGMT_IMAGE_URI" `
    --capabilities CAPABILITY_NAMED_IAM `
    --region $AWS_REGION `
    --no-fail-on-empty-changeset

# Get Lambda ARNs from stack outputs
$RETRIEVAL_LAMBDA_ARN = (aws cloudformation describe-stacks `
        --stack-name "$PROJECT_NAME-lambda" `
        --query "Stacks[0].Outputs[?OutputKey=='RetrievalFunctionArn'].OutputValue" `
        --output text `
        --region $AWS_REGION).Trim()

$DOCUMENT_MGMT_LAMBDA_ARN = (aws cloudformation describe-stacks `
        --stack-name "$PROJECT_NAME-lambda" `
        --query "Stacks[0].Outputs[?OutputKey=='DocumentMgmtFunctionArn'].OutputValue" `
        --output text `
        --region $AWS_REGION).Trim()

$INDEXING_LAMBDA_ARN = (aws cloudformation describe-stacks `
        --stack-name "$PROJECT_NAME-lambda" `
        --query "Stacks[0].Outputs[?OutputKey=='IndexingFunctionArn'].OutputValue" `
        --output text `
        --region $AWS_REGION).Trim()

Write-Host "[OK] Lambda functions deployed" -ForegroundColor Green

# ============================================================
# Step 5: Deploy API Gateway
# ============================================================
Write-Host "`n--- Step 5/5: Deploying API Gateway ---" -ForegroundColor Yellow

aws cloudformation deploy `
    --template-file cloudformation/api-gateway.yaml `
    --stack-name "$PROJECT_NAME-api" `
    --parameter-overrides `
    "ProjectName=$PROJECT_NAME" `
    "CognitoUserPoolArn=$USER_POOL_ARN" `
    "RetrievalFunctionArn=$RETRIEVAL_LAMBDA_ARN" `
    "DocumentMgmtFunctionArn=$DOCUMENT_MGMT_LAMBDA_ARN" `
    "IndexingFunctionArn=$INDEXING_LAMBDA_ARN" `
    --capabilities CAPABILITY_NAMED_IAM `
    --region $AWS_REGION `
    --no-fail-on-empty-changeset

$API_GATEWAY_URL = (aws cloudformation describe-stacks `
        --stack-name "$PROJECT_NAME-api" `
        --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" `
        --output text `
        --region $AWS_REGION).Trim()

Write-Host "[OK] API Gateway: $API_GATEWAY_URL" -ForegroundColor Green

# ============================================================
# Summary & Next Steps
# ============================================================
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Deployed Resources:" -ForegroundColor White
Write-Host "  S3 Bucket       : $S3_BUCKET" -ForegroundColor White
Write-Host "  Cognito Pool    : $USER_POOL_ID" -ForegroundColor White
Write-Host "  Cognito Client  : $USER_POOL_CLIENT_ID" -ForegroundColor White
Write-Host "  Indexing Lambda : $INDEXING_LAMBDA_ARN" -ForegroundColor White
Write-Host "  Retrieval Lambda: $RETRIEVAL_LAMBDA_ARN" -ForegroundColor White
Write-Host "  Doc Mgmt Lambda : $DOCUMENT_MGMT_LAMBDA_ARN" -ForegroundColor White
Write-Host "  API Gateway     : $API_GATEWAY_URL" -ForegroundColor White
Write-Host ""
Write-Host "=========================================" -ForegroundColor Yellow
Write-Host " MANUAL STEP: Create Bedrock Agent" -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Go to AWS Console > Amazon Bedrock > Agents" -ForegroundColor White
Write-Host "2. Click 'Create Agent'" -ForegroundColor White
Write-Host "3. Agent name       : ServerlessRAGAgent" -ForegroundColor White
Write-Host "4. Foundation model : anthropic.claude-3-sonnet-20240229-v1:0" -ForegroundColor White
Write-Host "5. Instructions     : Copy from agent_config/agent_definition.json" -ForegroundColor White
Write-Host ""
Write-Host "6. Add Action Group: RAGRetrieval" -ForegroundColor White
Write-Host "   Lambda ARN: $RETRIEVAL_LAMBDA_ARN" -ForegroundColor Cyan
Write-Host "   API Schema: Copy RAGRetrieval section from agent_config/agent_definition.json" -ForegroundColor White
Write-Host ""
Write-Host "7. Add Action Group: DocumentManagement" -ForegroundColor White
Write-Host "   Lambda ARN: $DOCUMENT_MGMT_LAMBDA_ARN" -ForegroundColor Cyan
Write-Host "   API Schema: Copy DocumentManagement section from agent_config/agent_definition.json" -ForegroundColor White
Write-Host ""
Write-Host "8. Create alias: 'prod'" -ForegroundColor White
Write-Host "9. Note the Agent ID and Alias ID" -ForegroundColor White
Write-Host ""
Write-Host "=========================================" -ForegroundColor Yellow
Write-Host " UPDATE .env FILE" -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "AWS_REGION=$AWS_REGION" -ForegroundColor White
Write-Host "AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID" -ForegroundColor White
Write-Host "S3_BUCKET_NAME=$S3_BUCKET" -ForegroundColor White
Write-Host "COGNITO_USER_POOL_ID=$USER_POOL_ID" -ForegroundColor White
Write-Host "COGNITO_CLIENT_ID=$USER_POOL_CLIENT_ID" -ForegroundColor White
Write-Host "COGNITO_REGION=$AWS_REGION" -ForegroundColor White
Write-Host "BEDROCK_AGENT_ID=<your-agent-id>" -ForegroundColor Yellow
Write-Host "BEDROCK_AGENT_ALIAS_ID=<your-alias-id>" -ForegroundColor Yellow
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Next: Run FastAPI backend" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  cd ..\fastapi_backend" -ForegroundColor White
Write-Host "  pip install -r requirements.txt" -ForegroundColor White
Write-Host "  uvicorn main:app --reload --port 8000" -ForegroundColor White
Write-Host ""

# Auto-update .env file with deployed values
$envFile = (Resolve-Path (Join-Path $scriptDir "..\.env") -ErrorAction SilentlyContinue).Path
if (-not $envFile) {
    $envFile = Join-Path (Split-Path $scriptDir -Parent) ".env"
}

if (Test-Path $envFile) {
    Write-Host "Updating .env file with deployed values..." -ForegroundColor Yellow
    $envContent = Get-Content $envFile -Raw
    $envContent = $envContent -replace "AWS_ACCOUNT_ID=.*", "AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID"
    $envContent = $envContent -replace "S3_BUCKET_NAME=.*", "S3_BUCKET_NAME=$S3_BUCKET"
    $envContent = $envContent -replace "COGNITO_USER_POOL_ID=.*", "COGNITO_USER_POOL_ID=$USER_POOL_ID"
    $envContent = $envContent -replace "COGNITO_CLIENT_ID=.*", "COGNITO_CLIENT_ID=$USER_POOL_CLIENT_ID"
    $envContent = $envContent -replace "COGNITO_REGION=.*", "COGNITO_REGION=$AWS_REGION"
    $envContent = $envContent -replace "AWS_REGION=.*", "AWS_REGION=$AWS_REGION"
    $envContent = $envContent -replace "API_GATEWAY_URL=.*", "API_GATEWAY_URL=$API_GATEWAY_URL"
    Set-Content -Path $envFile -Value $envContent -NoNewline
    Write-Host "[OK] .env updated (add BEDROCK_AGENT_ID manually after creating agent)" -ForegroundColor Green
}
