# Use a slim, stable, and secure Python base image
FROM python:3.11-slim

# Set environment variables
# - PYTHONUNBUFFERED: Prevents Python from buffering stdout and stderr, critical for MCP stdio transport
# - PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create a non-privileged user and group to run the application securely
RUN groupadd -g 10001 mcpuser && \
    useradd -u 10001 -g mcpuser -m -s /sbin/nologin mcpuser

# Set working directory inside the container
WORKDIR /app

# Copy dependency definitions first to leverage Docker layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server implementation and other necessary code
# We exclude files in .dockerignore (like __pycache__, test_server.py if not needed, etc.)
COPY server.py .

# Change ownership of /app to the non-root user
RUN chown -R mcpuser:mcpuser /app

# Switch to the non-privileged user
USER mcpuser

# Expose port 8000 in case the server is launched with SSE (HTTP) transport
EXPOSE 8000

# Default command runs the server via python3 on stdio transport
ENTRYPOINT ["python", "server.py"]
