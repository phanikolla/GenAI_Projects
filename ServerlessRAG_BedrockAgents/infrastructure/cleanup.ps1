# Cleanup script for Serverless RAG with Bedrock Agents (PowerShell)
# This script deletes all AWS resources created during deployment

# Configuration
$PROJECT_NAME = "serverless-rag"
$AWS_REGION = if ($env:AWS_REGION) { $env:AWS_REGION } else { "us-east-1" }
$AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Serverless RAG Cleanup Script" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Project: $PROJECT_NAME"
Write-Host "Region: $AWS_REGION"
Write-Host "Account: $AWS_ACCOUNT_ID"
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️  WARNING: This will delete ALL resources created for this project!" -ForegroundColor Yellow
Write-Host ""

$CONFIRM = Read-Host "Are you sure you want to continue? (yes/no)"

if ($CONFIRM -ne "yes") {
    Write-Host "Cleanup cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Starting cleanup..." -ForegroundColor Green
Write-Host ""

# Function to check if stack exists
function Test-StackExists {
    param($StackName)
    try {
        aws cloudformation describe-stacks --stack-name $StackName --region $AWS_REGION 2>$null | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Function to delete stack and wait
function Remove-Stack {
    param($StackName)
    
    $stackExists = $false
    try {
        aws cloudformation describe-stacks --stack-name $StackName --region $AWS_REGION 2>$null | Out-Null
        $stackExists = $true
    }
    catch {
        $stackExists = $false
    }
    
    if ($stackExists) {
        Write-Host "Deleting CloudFormation stack: $StackName..." -ForegroundColor Yellow
        aws cloudformation delete-stack --stack-name $StackName --region $AWS_REGION
        Write-Host "Waiting for stack deletion to complete..." -ForegroundColor Yellow
        
        # Wait for deletion (with timeout)
        $timeout = 300 # 5 minutes
        $elapsed = 0
        $interval = 10
        
        while ($elapsed -lt $timeout) {
            try {
                $status = aws cloudformation describe-stacks --stack-name $StackName --region $AWS_REGION --query 'Stacks[0].StackStatus' --output text 2>$null
                if ($status -eq "DELETE_COMPLETE" -or $null -eq $status) {
                    break
                }
            }
            catch {
                break
            }
            Start-Sleep -Seconds $interval
            $elapsed += $interval
        }
        
        Write-Host "✓ Stack $StackName deleted" -ForegroundColor Green
    }
    else {
        Write-Host "Stack $StackName does not exist, skipping..." -ForegroundColor Gray
    }
}

# Step 1: Delete Lambda Functions Stack
Write-Host ""
Write-Host "Step 1: Deleting Lambda Functions..." -ForegroundColor Cyan
Remove-Stack "${PROJECT_NAME}-lambda"

# Step 2: Delete ECR Repositories and Images
Write-Host ""
Write-Host "Step 2: Deleting ECR Repositories..." -ForegroundColor Cyan
$repos = @("indexing", "retrieval", "document-management")

foreach ($repo in $repos) {
    $repoName = "${PROJECT_NAME}-${repo}"
    try {
        aws ecr describe-repositories --repository-names $repoName --region $AWS_REGION 2>$null | Out-Null
        Write-Host "Deleting ECR repository: $repoName..." -ForegroundColor Yellow
        aws ecr delete-repository --repository-name $repoName --force --region $AWS_REGION
        Write-Host "✓ Repository $repoName deleted" -ForegroundColor Green
    }
    catch {
        Write-Host "Repository $repoName does not exist, skipping..." -ForegroundColor Gray
    }
}

# Step 3: Empty and Delete S3 Bucket
Write-Host ""
Write-Host "Step 3: Deleting S3 Bucket..." -ForegroundColor Cyan
$S3_BUCKET = "${PROJECT_NAME}-${AWS_ACCOUNT_ID}-${AWS_REGION}"

try {
    aws s3 ls "s3://${S3_BUCKET}" 2>$null | Out-Null
    Write-Host "Emptying S3 bucket: $S3_BUCKET..." -ForegroundColor Yellow
    aws s3 rm "s3://${S3_BUCKET}" --recursive --region $AWS_REGION
    Write-Host "Deleting S3 bucket stack..." -ForegroundColor Yellow
    Remove-Stack "${PROJECT_NAME}-s3"
    Write-Host "✓ S3 bucket deleted" -ForegroundColor Green
}
catch {
    Write-Host "S3 bucket $S3_BUCKET does not exist, skipping..." -ForegroundColor Gray
    try {
        Remove-Stack "${PROJECT_NAME}-s3"
    }
    catch {
        # Ignore errors
    }
}

# Step 4: Delete Cognito User Pool
Write-Host ""
Write-Host "Step 4: Deleting Cognito User Pool..." -ForegroundColor Cyan
Remove-Stack "${PROJECT_NAME}-cognito"

# Step 5: Delete Bedrock Agent (Manual - provide instructions)
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Step 5: Delete Bedrock Agent (Manual)" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️  Bedrock Agents must be deleted manually:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Go to AWS Console - Amazon Bedrock - Agents"
Write-Host "2. Find agent: ServerlessRAGAgent"
Write-Host "3. Delete all aliases"
Write-Host "4. Delete the agent"
Write-Host ""
Write-Host "Or use AWS CLI:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  # List agents"
Write-Host "  aws bedrock-agent list-agents --region $AWS_REGION"
Write-Host ""
Write-Host "  # Delete agent (replace AGENT_ID)"
Write-Host "  aws bedrock-agent delete-agent --agent-id AGENT_ID --region $AWS_REGION"
Write-Host ""

# Step 6: Clean up local Docker images (optional)
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Step 6: Clean Local Docker Images (Optional)" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
$DELETE_DOCKER = Read-Host "Do you want to delete local Docker images? (yes/no)"

if ($DELETE_DOCKER -eq "yes") {
    Write-Host "Deleting local Docker images..." -ForegroundColor Yellow
    docker rmi serverless-rag-indexing 2>$null
    docker rmi serverless-rag-retrieval 2>$null
    docker rmi serverless-rag-document-management 2>$null
    docker rmi "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/serverless-rag-indexing:latest" 2>$null
    docker rmi "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/serverless-rag-retrieval:latest" 2>$null
    docker rmi "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/serverless-rag-document-management:latest" 2>$null
    Write-Host "✓ Docker images deleted" -ForegroundColor Green
}

# Step 7: Clean up local files (optional)
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Step 7: Clean Local Files (Optional)" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
$DELETE_ENV = Read-Host "Do you want to delete local .env file? (yes/no)"

if ($DELETE_ENV -eq "yes") {
    $envPath = Join-Path $PSScriptRoot ".." ".env"
    if (Test-Path $envPath) {
        Remove-Item $envPath
        Write-Host "✓ Deleted .env file" -ForegroundColor Green
    }
}

# Step 8: Summary
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Cleanup Summary" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "✓ Lambda functions deleted" -ForegroundColor Green
Write-Host "✓ ECR repositories deleted" -ForegroundColor Green
Write-Host "✓ S3 bucket deleted" -ForegroundColor Green
Write-Host "✓ Cognito User Pool deleted" -ForegroundColor Green
Write-Host "⚠️  Bedrock Agent requires manual deletion" -ForegroundColor Yellow
Write-Host ""
Write-Host "Cleanup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Note: It may take a few minutes for all resources to be fully removed."
Write-Host "You can verify in the AWS Console or use:"
Write-Host "  aws cloudformation list-stacks --region $AWS_REGION"
Write-Host ""

# Pause to see results
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
