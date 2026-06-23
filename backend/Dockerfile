# Backend image: Python 3.12 (stable ML wheels) + OpenMP so XGBoost works.
FROM python:3.12-slim

# libgomp1 provides the OpenMP runtime XGBoost needs.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps (incl. XGBoost, enabled for the container build).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt "xgboost>=2.1" "psycopg2-binary>=2.9"

# Copy the backend source.
COPY . .

# Download historical data and train the model at build time so the image ships
# ready to serve. (Pre-trained artifacts are already copied in, so this is a
# refresh; it falls back gracefully if there's no network during the build.)
RUN mkdir -p data/raw && (curl -sL -o data/raw/results.csv \
      https://raw.githubusercontent.com/martj42/international_results/master/results.csv \
    && python pipelines/train.py) || echo "training skipped (no network at build)"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
