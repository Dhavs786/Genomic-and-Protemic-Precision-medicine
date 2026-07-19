# Stage 1: Build React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Serve with FastAPI Python Backend
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e .
COPY gdsc_drug_response/ ./gdsc_drug_response/
COPY dataset/ ./dataset/
COPY artifacts/ ./artifacts/
# Copy built React files
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Seed database
RUN python -m gdsc_drug_response.seed_data

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "gdsc_drug_response.api:app", "--host", "0.0.0.0", "--port", "8000"]
