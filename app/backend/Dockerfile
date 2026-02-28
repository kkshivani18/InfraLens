# build stage
FROM python:3.9-slim AS builder
WORKDIR /app
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc g++ git libffi-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir \
    --timeout 1000 \
    --retries 5 \
    torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir \
    --timeout 1000 \
    --retries 5 \
    -r requirements.txt

RUN find /usr/local/lib/python3.9/site-packages -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.9/site-packages -type d -name "test" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.9/site-packages -name "*.pyc" -delete && \
    find /usr/local/lib/python3.9/site-packages -name "*.pyo" -delete && \
    find /usr/local/lib/python3.9/site-packages -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# runtime stage
FROM python:3.9-slim
WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/temp_repos && \
    mkdir -p /home/appuser/.cache/huggingface && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /home/appuser
USER appuser
ENV HF_HOME=/home/appuser/.cache/huggingface

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]