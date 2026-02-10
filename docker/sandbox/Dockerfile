FROM python:3.12-slim

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash sandbox && \
    apt-get update && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install step-tracer package
WORKDIR /app
COPY dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && \
    rm /tmp/*.whl

# Copy sandbox execution script
COPY docker/sandbox/sandbox_executor.py /app/sandbox_executor.py

# Switch to non-root user
USER sandbox

# Set working directory for code execution
WORKDIR /workspace

ENTRYPOINT ["python", "/app/sandbox_executor.py"]
