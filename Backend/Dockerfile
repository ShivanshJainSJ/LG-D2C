# ==============================================================================
# Production / Staging Container for Livguard Quotation Management Backend
# Base image: Python 3.11 Slim (Debian-based)
# ==============================================================================

FROM python:3.11-slim

# Prevent bytecode generation and ensure immediate unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Install system libraries required by headless Chromium and SSL/networking utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium binary into PLAYWRIGHT_BROWSERS_PATH
RUN playwright install chromium

# Copy application code into container (filtered by .dockerignore)
COPY . .

# Expose default HTTP port
EXPOSE 8000

# Start command: Dynamically binds to host-assigned $PORT (default 8000) with a single worker
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
