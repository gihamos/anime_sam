FROM node:20-slim AS shop-build

WORKDIR /shop_app

COPY shop_app/package.json shop_app/package-lock.json ./
RUN npm ci

COPY shop_app/ ./

ARG VITE_API_URL=https://shop.gihamos.fr
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build


FROM python:3.12-slim

WORKDIR /app

COPY shop_backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shop_backend/ .
COPY --from=shop-build /shop_app/dist ./shop_app_dist

EXPOSE 8010

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010"]
