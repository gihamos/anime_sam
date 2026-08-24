FROM node:20-slim AS admin-build

WORKDIR /admin_app

COPY admin_app/package.json admin_app/package-lock.json ./
RUN npm ci

COPY admin_app/ ./

ARG VITE_API_URL=https://anime.gihamos.fr
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build


FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 \
    libatspi2.0-0 libwayland-client0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && playwright install chromium

COPY . .
COPY --from=admin-build /admin_app/dist ./admin_app/dist

EXPOSE 8000 8001

CMD ["python", "start.py"]