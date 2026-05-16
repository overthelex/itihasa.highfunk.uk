FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git curl wget \
        # Playwright Chromium runtime deps
        libnss3 libnspr4 libatk1.0-0t64 libatk-bridge2.0-0t64 \
        libcups2t64 libdrm2 libxcomposite1 libxdamage1 libxrandr2 \
        libgbm1 libpango-1.0-0 libcairo2 libasound2t64 \
        libxshmfence1 libx11-xcb1 libxkbcommon0 libxfixes3 \
        fonts-liberation fonts-noto-core xdg-utils && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium

COPY . .
CMD ["python", "-u", "main.py"]
