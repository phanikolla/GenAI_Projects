# Contributing to AWS Bedrock Agents Project

Thank you for your interest in contributing to this project! This guide will help you get started.

## 🚀 Getting Started

### Prerequisites

- AWS Account with Bedrock access
- Python 3.11 or higher
- AWS CLI configured
- Git installed

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/bedrock-agents.git
   cd bedrock-agents/Bedrock_Agents
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Deploy Development Environment**
   ```bash
   ./setup-scripts/deploy.sh
   ```

## 📝 Development Guidelines

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and small (< 50 lines when possible)

### Commit Messages

Use conventional commit format:
```
type(scope): description

feat(agent): add new ticket escalation logic
fix(lambda): resolve timeout issue in action group
docs(readme): update deployment instructions
test(integration): add customer info retrieval tests
```

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `test/description` - Test improvements

## 🧪 Testing

### Running Tests

```bash
# Run all tests
./setup-scripts/test_agent.sh

# Run local unit tests
python tests/test_local.py
```

### Adding Tests

When adding new functionality:

1. **Unit Tests** - Test individual functions
2. **Integration Tests** - Test end-to-end workflows
3. **Performance Tests** - Ensure scalability

Example test structure:
```python
def test_create_ticket():
    """Test ticket creation functionality"""
    # Arrange
    customer_id = "TEST-001"
    description = "Test issue"
    
    # Act
    result = create_support_ticket({
        'customer_id': customer_id,
        'issue_description': description
    })
    
    # Assert
    assert result['statusCode'] == 200
    assert 'ticket_id' in result['body']
```

## 📋 Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write code following style guidelines
   - Add tests for new functionality
   - Update documentation as needed

3. **Test Locally**
   ```bash
   ./setup-scripts/test_agent.sh
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat(scope): description of changes"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **PR Requirements**
   - Clear description of changes
   - Link to related issues
   - Screenshots/examples if applicable
   - All tests passing

## 🏗️ Architecture Guidelines

### Adding New Action Groups

1. **Define OpenAPI Schema**
   ```json
   // In openapi-schemas/actions_schema.json
   "/new-endpoint": {
     "post": {
       "summary": "Description",
       "operationId": "newOperation",
       "parameters": [...]
     }
   }
   ```

2. **Implement Handler**
   ```python
   # In lambda-functions/action_group_executor/lambda_function.py
   def handle_new_operation(params):
       """Handle new operation"""
       # Implementation here
       return {
           'statusCode': 200,
           'body': json.dumps(result)
       }
   ```

3. **Update Router**
   ```python
   # Add to lambda_handler routing logic
   elif '/new-endpoint' in api_path:
       result = handle_new_operation(params)
   ```

4. **Add Tests**
   ```python
   def test_new_operation():
       # Test implementation
       pass
   ```

### Infrastructure Changes

- Update `infrastructure/cloudformation.yaml` for new AWS resources
- Follow least-privilege IAM principles
- Add appropriate tags and naming conventions
- Consider cost implications

## 🐛 Bug Reports

When reporting bugs, include:

1. **Environment Details**
   - AWS region
   - Python version
   - Deployment method used

2. **Steps to Reproduce**
   - Exact commands run
   - Input data used
   - Expected vs actual behavior

3. **Logs and Errors**
   - CloudWatch logs
   - Error messages
   - Stack traces

4. **Additional Context**
   - Screenshots if applicable
   - Related issues or PRs

## 💡 Feature Requests

For new features:

1. **Check Existing Issues** - Avoid duplicates
2. **Describe Use Case** - Why is this needed?
3. **Propose Solution** - How should it work?
4. **Consider Alternatives** - Other approaches?
5. **Implementation Plan** - Break down into steps

## 📚 Documentation

### Types of Documentation

- **Code Comments** - Explain complex logic
- **Docstrings** - Function/class documentation
- **README Updates** - User-facing changes
- **Architecture Docs** - Design decisions

### Documentation Standards

- Use clear, concise language
- Include code examples
- Keep up-to-date with changes
- Consider different skill levels

## 🔒 Security

### Security Guidelines

- Never commit AWS credentials
- Use IAM roles, not access keys
- Follow least-privilege principles
- Validate all inputs
- Use encryption for sensitive data

### Reporting Security Issues

For security vulnerabilities:
1. **Do NOT** create public issues
2. Email maintainers directly
3. Include detailed description
4. Allow time for fix before disclosure

## 🎯 Project Goals

This project aims to:

- Demonstrate AWS Bedrock best practices
- Provide production-ready serverless architecture
- Showcase AI agent capabilities
- Enable community learning and contribution

## 📞 Getting Help

- **GitHub Issues** - Bug reports and feature requests
- **Discussions** - General questions and ideas
- **AWS Documentation** - Service-specific questions
- **Community Forums** - Broader AWS community support

## 🏆 Recognition

Contributors will be:
- Listed in project acknowledgments
- Credited in release notes
- Invited to maintainer discussions (for significant contributions)

Thank you for contributing to the AWS community! 🚀