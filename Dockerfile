# Multi-stage Dockerfile for IndexTTS
# Optimized for production deployment with CUDA support

# Build stage for CUDA extensions
FROM nvidia/cuda:11.8-devel-ubuntu22.04 as builder

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_HOME=/usr/local/cuda

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
    git \
    wget \
    curl \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic link for python
RUN ln -s /usr/bin/python3.10 /usr/bin/python

# Upgrade pip
RUN python -m pip install --upgrade pip

# Set working directory
WORKDIR /app

# Copy requirements and setup files
COPY requirements.txt setup.py pyproject.toml MANIFEST.in ./
COPY indextts/ ./indextts/

# Install PyTorch with CUDA support first
RUN pip install torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118

# Install the package with CUDA extensions
RUN pip install -e . --no-build-isolation

# Runtime stage
FROM nvidia/cuda:11.8-runtime-ubuntu22.04 as runtime

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV CUDA_HOME=/usr/local/cuda

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic link for python
RUN ln -s /usr/bin/python3.10 /usr/bin/python

# Create app user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /models /outputs && \
    chown -R appuser:appuser /app /models /outputs

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Copy additional files
COPY --chown=appuser:appuser webui.py ./
COPY --chown=appuser:appuser tests/ ./tests/
COPY --chown=appuser:appuser tools/ ./tools/
COPY --chown=appuser:appuser assets/ ./assets/

# Install additional runtime dependencies
RUN pip install fastapi uvicorn[standard] python-multipart

# Create necessary directories
RUN mkdir -p /app/outputs /app/prompts /app/checkpoints && \
    chown -R appuser:appuser /app

# Switch to app user
USER appuser

# Expose ports
EXPOSE 7860 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (can be overridden)
CMD ["python", "api_server.py"]
