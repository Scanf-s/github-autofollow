# Use AWS Lambda Python 3.12 base image
FROM public.ecr.aws/lambda/python:3.12

# Copy requirements file first for better layer caching
# LAMBDA_TASK_ROOT=/var/task (Lambda에서 자동으로 설정되는 환경변수)
COPY pyproject.toml ${LAMBDA_TASK_ROOT}/

# Install dependencies using pip
RUN pip install --no-cache-dir -e ${LAMBDA_TASK_ROOT}

# Copy application code
COPY service/ ${LAMBDA_TASK_ROOT}/service/
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

# Set the CMD to handler
CMD ["lambda_function.lambda_handler"]