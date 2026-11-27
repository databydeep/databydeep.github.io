FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api.py core.py runs.json routing_scores.json ./
USER 65534:65534
CMD ["uvicorn","api:app","--host","0.0.0.0","--port","8010"]
