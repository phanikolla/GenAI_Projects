#!/usr/bin/env python3
"""
Production script to create and configure AWS Bedrock Agent
"""
import boto3
import json
import time
import argparse
import sys
import logging
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_agent(agent_name, model_id, stack_name, region='us-east-1'):
    """Create Bedrock Agent with action groups"""
    
    # Validate inputs
    if not all([agent_name, model_id, stack_name]):
        raise ValueError("agent_name, model_id, and stack_name are required")
    
    try:
        bedrock_agent = boto3.client('bedrock-agent', region_name=region)
        cloudformation = boto3.client('cloudformation', region_name=region)
        iam = boto3.client('iam', region_name=region)
        lambda_client = boto3.client('lambda', region_name=region)
        sts = boto3.client('sts')
        account_id = sts.get_caller_identity()['Account']
    except Exception as e:
        print(f"❌ Error initializing AWS clients: {e}")
        return None
    
    # Use system-defined cross-region inference profile for Bedrock Agents
    # Format: us.anthropic.claude-3-5-sonnet-20241022-v2:0 (for US regions)
    if model_id.startswith('anthropic.'):
        # Convert model ID to system-defined inference profile ID
        inference_profile_id = f"us.{model_id}"
        print(f"📋 Using inference profile: {inference_profile_id}")
    else:
        inference_profile_id = model_id
    
    print(f"🚀 Creating Bedrock Agent: {agent_name}")
    
    # Get CloudFormation outputs
    try:
        stack_response = cloudformation.describe_stacks(StackName=stack_name)
        outputs = stack_response['Stacks'][0]['Outputs']
        output_dict = {o['OutputKey']: o['OutputValue'] for o in outputs}
        
        action_group_lambda_arn = output_dict.get('ActionGroupLambdaArn')
        
        if not action_group_lambda_arn:
            print("❌ Could not find ActionGroupLambdaArn in stack outputs")
            return None
            
        print(f"✅ Found Lambda ARN: {action_group_lambda_arn}")
        
    except ClientError as e:
        print(f"❌ Error getting stack outputs: {e}")
        return None
    
    # Create IAM role for Bedrock Agent
    print("📝 Creating IAM role for Bedrock Agent...")
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": boto3.client('sts').get_caller_identity()['Account']
                    }
                }
            }
        ]
    }
    
    role_name = f"{agent_name}-role"
    
    try:
        role_response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=f"Role for Bedrock Agent {agent_name}"
        )
        role_arn = role_response['Role']['Arn']
        print(f"✅ Created IAM role: {role_arn}")
        
        # Attach policy for model invocation (foundation models + inference profiles)
        # System-defined inference profiles have a different ARN format
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModel",
                        "bedrock:InvokeModelWithResponseStream",
                        "bedrock:GetInferenceProfile",
                        "bedrock:ListInferenceProfiles"
                    ],
                    "Resource": "*"
                }
            ]
        }
        
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName='BedrockModelAccess',
            PolicyDocument=json.dumps(policy_document)
        )
        
        print("⏳ Waiting for IAM role to propagate...")
        time.sleep(10)
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            role_arn = iam.get_role(RoleName=role_name)['Role']['Arn']
            print(f"✅ Using existing IAM role: {role_arn}")
        else:
            print(f"❌ Error creating IAM role: {e}")
            return None
    
    # Load OpenAPI schema
    try:
        with open('openapi-schemas/actions_schema.json', 'r') as f:
            api_schema = json.load(f)
        print("✅ Loaded OpenAPI schema")
    except Exception as e:
        print(f"❌ Error loading OpenAPI schema: {e}")
        return None
    
    # Create agent instruction
    agent_instruction = """
You are a helpful customer support agent for a technology company. Your role is to:

1. Help customers create support tickets for their issues
2. Retrieve customer information and ticket history
3. Update ticket statuses as issues are resolved
4. Search for existing tickets
5. Escalate complex issues to human support when necessary

When a customer describes an issue:
- Ask clarifying questions if needed
- Categorize the issue appropriately (billing, technical, account, or other)
- Assign appropriate priority (high for urgent issues, medium for standard, low for minor)
- Create a ticket with a clear description
- Provide the ticket ID to the customer

Always be professional, empathetic, and solution-oriented. If an issue is beyond your capabilities or requires sensitive account changes, escalate it to human support.
"""
    
    # Check if agent already exists
    try:
        print("🔍 Checking for existing agent...")
        agents_response = bedrock_agent.list_agents()
        existing_agent = None
        
        for agent in agents_response.get('agentSummaries', []):
            if agent['agentName'] == agent_name:
                existing_agent = agent
                print(f"✅ Found existing agent: {agent['agentId']}")
                break
        
        if existing_agent:
            agent_id = existing_agent['agentId']
            print(f"🔄 Using existing agent with ID: {agent_id}")
        else:
            # Create the agent
            print("🤖 Creating new Bedrock Agent...")
            
            agent_response = bedrock_agent.create_agent(
                agentName=agent_name,
                agentResourceRoleArn=role_arn,
                foundationModel=inference_profile_id,
                instruction=agent_instruction,
                description="Customer support agent for ticket management"
            )
            
            agent_id = agent_response['agent']['agentId']
            print(f"✅ Created agent with ID: {agent_id}")
            
            # Wait for agent to be ready
            print("⏳ Waiting for agent to be ready...")
            max_attempts = 30
            for attempt in range(max_attempts):
                try:
                    agent_status = bedrock_agent.get_agent(agentId=agent_id)
                    current_status = agent_status['agent']['agentStatus']
                    
                    if current_status in ['PREPARED', 'NOT_PREPARED']:
                        print(f"✅ Agent is ready")
                        break
                    elif current_status == 'FAILED':
                        print(f"❌ Agent creation failed")
                        return None
                        
                    time.sleep(10)
                    
                except ClientError as e:
                    print(f"   Error checking agent status: {e}")
                    time.sleep(5)
                    
            else:
                print(f"❌ Agent did not become ready within timeout")
                return None
        
    except ClientError as e:
        print(f"❌ Error creating agent: {e}")
        return None
    
    # Create action group
    try:
        print("🔧 Creating action group...")
        
        # Check if action group already exists
        try:
            action_groups = bedrock_agent.list_agent_action_groups(
                agentId=agent_id,
                agentVersion='DRAFT'
            )
            
            existing_action_group = None
            for ag in action_groups.get('actionGroupSummaries', []):
                if ag['actionGroupName'] == 'customer-support-tools':
                    existing_action_group = ag
                    print(f"✅ Found existing action group: {ag['actionGroupId']}")
                    break
            
            if not existing_action_group:
                action_group_response = bedrock_agent.create_agent_action_group(
                    agentId=agent_id,
                    agentVersion='DRAFT',
                    actionGroupName='customer-support-tools',
                    description='Tools for managing customer support tickets',
                    actionGroupExecutor={
                        'lambda': action_group_lambda_arn
                    },
                    apiSchema={
                        'payload': json.dumps(api_schema)
                    },
                    actionGroupState='ENABLED'
                )
                
                print(f"✅ Created action group: {action_group_response['agentActionGroup']['actionGroupId']}")
            else:
                print(f"🔄 Using existing action group")
                
        except ClientError as list_error:
            # If listing fails, try to create anyway
            print(f"⚠️ Could not list action groups, attempting to create")
            action_group_response = bedrock_agent.create_agent_action_group(
                agentId=agent_id,
                agentVersion='DRAFT',
                actionGroupName='customer-support-tools',
                description='Tools for managing customer support tickets',
                actionGroupExecutor={
                    'lambda': action_group_lambda_arn
                },
                apiSchema={
                    'payload': json.dumps(api_schema)
                },
                actionGroupState='ENABLED'
            )
            
            print(f"✅ Created action group: {action_group_response['agentActionGroup']['actionGroupId']}")
        
    except ClientError as e:
        print(f"❌ Error creating action group: {e}")
        return None
    
    # Prepare the agent
    try:
        print("⚙️ Preparing agent...")
        
        prepare_response = bedrock_agent.prepare_agent(agentId=agent_id)
        
        # Wait for agent to be prepared
        print("⏳ Waiting for agent preparation...")
        max_prep_attempts = 20
        for prep_attempt in range(max_prep_attempts):
            try:
                agent_status = bedrock_agent.get_agent(agentId=agent_id)
                current_status = agent_status['agent']['agentStatus']
                
                if current_status == 'PREPARED':
                    print(f"✅ Agent prepared successfully")
                    break
                elif current_status == 'FAILED':
                    print(f"❌ Agent preparation failed")
                    return None
                    
                time.sleep(10)
                
            except ClientError as e:
                print(f"   Error checking preparation status: {e}")
                time.sleep(5)
        else:
            print(f"⚠️ Agent preparation timeout, continuing...")
        
    except ClientError as e:
        print(f"❌ Error preparing agent: {e}")
        return None
    
    # Create agent alias
    try:
        print("🏷️ Creating agent alias...")
        
        # Check if alias already exists
        try:
            aliases_response = bedrock_agent.list_agent_aliases(agentId=agent_id)
            existing_alias = None
            
            for alias in aliases_response.get('agentAliasSummaries', []):
                if alias['agentAliasName'] == 'production':
                    existing_alias = alias
                    print(f"✅ Found existing alias: {alias['agentAliasId']}")
                    break
            
            if existing_alias:
                agent_alias_id = existing_alias['agentAliasId']
                print(f"🔄 Using existing alias: {agent_alias_id}")
            else:
                alias_response = bedrock_agent.create_agent_alias(
                    agentId=agent_id,
                    agentAliasName='production',
                    description='Production alias for customer support agent'
                )
                
                agent_alias_id = alias_response['agentAlias']['agentAliasId']
                print(f"✅ Created agent alias: {agent_alias_id}")
                
        except ClientError as list_error:
            # If listing fails, try to create anyway
            print(f"⚠️ Could not list aliases, attempting to create")
            alias_response = bedrock_agent.create_agent_alias(
                agentId=agent_id,
                agentAliasName='production',
                description='Production alias for customer support agent'
            )
            
            agent_alias_id = alias_response['agentAlias']['agentAliasId']
            print(f"✅ Created agent alias: {agent_alias_id}")
        
    except ClientError as e:
        if "already exists" in str(e):
            print(f"⚠️ Alias already exists, continuing with existing alias")
            # Try to get the existing alias ID
            try:
                aliases_response = bedrock_agent.list_agent_aliases(agentId=agent_id)
                for alias in aliases_response.get('agentAliasSummaries', []):
                    if alias['agentAliasName'] == 'production':
                        agent_alias_id = alias['agentAliasId']
                        print(f"✅ Using existing alias: {agent_alias_id}")
                        break
                else:
                    print(f"❌ Could not find existing alias")
                    return None
            except Exception as get_error:
                print(f"❌ Error getting existing alias: {get_error}")
                return None
        else:
            print(f"❌ Error creating agent alias: {e}")
            return None
    
    # Update Lambda environment variables
    try:
        print("🔄 Updating Lambda environment variables...")
        
        query_lambda_name = f"bedrock-query-agent-dev"
        
        lambda_client.update_function_configuration(
            FunctionName=query_lambda_name,
            Environment={
                'Variables': {
                    'AGENT_ID': agent_id,
                    'AGENT_ALIAS_ID': agent_alias_id,
                    'ENVIRONMENT': 'dev'
                }
            }
        )
        
        print(f"✅ Updated Lambda environment variables")
        
    except ClientError as e:
        print(f"⚠️ Warning: Could not update Lambda: {e}")
    
    print("\n" + "="*60)
    print("🎉 SUCCESS! Agent created successfully!")
    print("="*60)
    print(f"\n📋 Agent Details:")
    print(f"   Agent ID: {agent_id}")
    print(f"   Agent Alias ID: {agent_alias_id}")
    print(f"   IAM Role: {role_arn}")
    print(f"\n💡 Next Steps:")
    print(f"   1. Test the agent via API Gateway")
    print(f"   2. Monitor CloudWatch logs")
    print(f"   3. Adjust agent instructions if needed")
    print("\n")
    
    return {
        'agent_id': agent_id,
        'agent_alias_id': agent_alias_id,
        'role_arn': role_arn
    }

def main():
    parser = argparse.ArgumentParser(description='Create AWS Bedrock Agent')
    parser.add_argument('--agent-name', default='customer-support-agent', help='Name for the agent')
    parser.add_argument('--model-id', default='anthropic.claude-3-5-sonnet-20241022-v2:0', help='Bedrock model ID')
    parser.add_argument('--stack-name', default='bedrock-agent-stack', help='CloudFormation stack name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    
    args = parser.parse_args()
    
    result = create_agent(
        agent_name=args.agent_name,
        model_id=args.model_id,
        stack_name=args.stack_name,
        region=args.region
    )
    
    if result:
        # Save configuration
        config = {
            'agent_id': result['agent_id'],
            'agent_alias_id': result['agent_alias_id'],
            'role_arn': result['role_arn'],
            'model_id': args.model_id,
            'region': args.region
        }
        
        with open('agent_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Configuration saved to agent_config.json")
        sys.exit(0)
    else:
        print("❌ Failed to create agent")
        sys.exit(1)

if __name__ == '__main__':
    main()
