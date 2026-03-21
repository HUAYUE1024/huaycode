FROM python:3.12-slim

LABEL maintainer="HUAYCODE"
LABEL description="HUAYCODE - Python Code Execution Visualization Engine"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV FLASK_DEBUG=false

# Version info - injected at build time
ARG GIT_BRANCH=unknown
ARG GIT_COMMIT=unknown
ENV CHRONOTRACE_GIT_BRANCH=${GIT_BRANCH}
ENV CHRONOTRACE_GIT_COMMIT=${GIT_COMMIT}

# Create app directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY chronotrace/ ./chronotrace/
COPY templates/ ./templates/
COPY static/ ./static/

# Create data directory for SQLite
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/')" || exit 1

# Run application
CMD ["python", "-m", "chronotrace.web.app"]
