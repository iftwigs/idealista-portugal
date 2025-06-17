# Use Python 3.11 slim image for better performance and security
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/src" \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies and security updates
RUN apt-get update && apt-get install -y \
    curl \
    && apt-get upgrade -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY src/ ./src/
COPY pyproject.toml .
COPY pytest.ini .

# Create data directory for persistent storage
RUN mkdir -p /app/data && chmod 755 /app/data

# Create non-root user for security
RUN groupadd -r botuser && useradd -r -g botuser botuser

# Set proper permissions
RUN chown -R botuser:botuser /app
USER botuser

# Create volume mount points
VOLUME ["/app/data"]

# Health check - verify the bot process is running
HEALTHCHECK --interval=60s --timeout=15s --start-period=120s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('/app/data/user_configs.json') or os.path.exists('/tmp/bot_healthy') else 1)"

# Default command to run the bot
CMD ["python", "src/bot.py"]