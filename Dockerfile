# =============================================================================
# OmniSight — Production Playwright Docker Container
#
# Base image: Official Microsoft Playwright image with pre-bundled Chromium,
# chromium-headless-shell, and required Linux system libraries.
# Tag pinned to match playwright==1.64.1 in requirements.txt.
# Runtime user: pwuser (UID 1001, GID 1001 pre-configured in official image)
# =============================================================================

FROM mcr.microsoft.com/playwright/python:v1.64.1-noble

# Prevent Python from writing .pyc files and enable unbuffered output for live logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    HOME=/home/pwuser

WORKDIR /app

# 1. Install gosu for secure root-to-pwuser privilege dropping in entrypoint
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python dependencies as root (cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy application source code into container with pwuser ownership
COPY --chown=pwuser:pwuser . .

# 4. Prepare /app/artifacts with pwuser ownership and 0750 permissions
RUN mkdir -p /app/artifacts \
    && chown -R pwuser:pwuser /app \
    && chmod -R u+rwX /app \
    && chmod 0750 /app/artifacts

# 5. Install entrypoint script to fix mounted persistent disk permissions and drop privileges
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]

# 6. Production web service startup (executed as pwuser via entrypoint)
# Binds Uvicorn to 0.0.0.0 on the port dynamically assigned by Render ($PORT).
# --proxy-headers enables reading X-Forwarded-Proto and client IPs from Render edge.
# NOTE: Migrations are not executed automatically on startup.
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
