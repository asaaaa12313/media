FROM python:3.11-slim

# Playwright Chromium 의존성 + FFmpeg 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
        libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
        libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
        libcairo2 libasound2 libatspi2.0-0 libxshmfence1 \
        fonts-noto-cjk fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium

COPY backend/fonts/ /app/fonts/
RUN mkdir -p /app/assets

COPY backend/ .

EXPOSE 8000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
