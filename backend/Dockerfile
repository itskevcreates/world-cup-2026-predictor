FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt "psycopg2-binary>=2.9"

COPY . .

# Download training data and train model at build time (falls back gracefully)
RUN python -c "
import urllib.request, subprocess, sys, pathlib
pathlib.Path('data/raw').mkdir(parents=True, exist_ok=True)
try:
    urllib.request.urlretrieve(
        'https://raw.githubusercontent.com/martj42/international_results/master/results.csv',
        'data/raw/results.csv'
    )
    subprocess.run([sys.executable, 'pipelines/train.py'], check=True)
    print('Training complete')
except Exception as e:
    print(f'Training skipped: {e}')
"

EXPOSE 8000
CMD sh -c "python -m app.db.load 2>/dev/null; uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
