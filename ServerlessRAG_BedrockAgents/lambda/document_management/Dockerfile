FROM public.ecr.aws/lambda/python:3.11

# Copy requirements
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy handler
COPY handler.py ${LAMBDA_TASK_ROOT}/

# Set handler
CMD ["handler.lambda_handler"]
