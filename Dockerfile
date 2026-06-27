# ============================================================
# Build stage: install Python deps + Playwright Chromium browser
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps for building Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies (including playwright)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser into a known path
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.playwright-browsers
RUN python -m playwright install chromium

# ============================================================
# Runtime stage
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# System dependencies for Chromium browser execution
# (libnss3, libnspr4, etc. are required by the Playwright browser engine)
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
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

# Copy Python site-packages and binaries from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy Playwright Chromium browser from builder
COPY --from=builder /app/.playwright-browsers /app/.playwright-browsers
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.playwright-browsers

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck (uses python instead of curl since slim has no curl)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run FastAPI with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
