FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py Upstox_Generate_Access_Token.py Zerodha_Generate_Access_Token.py ./

# Dashboard keeps live state in memory -> exactly 1 worker (threads share that state).
# Long timeout: start-up downloads the instruments file + GCS/BigQuery data before the first request.
CMD exec gunicorn app:server --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 8 --timeout 300
