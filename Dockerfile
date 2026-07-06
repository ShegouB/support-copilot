# Use official Python slim image for minimal footprint
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for some native Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application source code
COPY app/ ./app/
COPY tests/ ./tests/

# Create a non-root user for security (least-privilege principle)
RUN useradd --no-create-home --shell /bin/false appuser && \
    chown -R appuser:appuser /app
USER appuser

# Cloud Run injects the PORT env variable; default to 8080
ENV PORT=8080

# Expose the application port
EXPOSE ${PORT}

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import app.config; print('OK')" || exit 1

# Default command: run the ADK API server for Cloud Run deployment
# Set GOOGLE_API_KEY via Cloud Run --set-env-vars flag (never bake into the image)
CMD ["sh", "-c", "python3 -m uvicorn app.server:app --host 0.0.0.0 --port ${PORT}"]
