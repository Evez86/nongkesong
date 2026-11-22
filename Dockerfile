FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --include=dev --no-audit --no-fund
COPY index.html ./
COPY public ./public
COPY src ./src
RUN VITE_API_BASE_URL=/ VITE_CAMPUS_API_BASE_URL='' npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY demo_server.py ./demo_server.py
COPY --from=frontend /build/dist ./dist
CMD ["sh", "-c", "exec uvicorn demo_server:app --host 0.0.0.0 --port \"${PORT:-10000}\""]
