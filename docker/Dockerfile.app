FROM python:3.12-slim

LABEL maintainer="Katiadje <github.com/Katiadje>"

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir streamlit requests

COPY app/ ./app/

# Config thème dark
RUN mkdir -p /root/.streamlit
COPY app/.streamlit/config.toml /root/.streamlit/config.toml

RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app
RUN mkdir -p /home/appuser/.streamlit && \
    cp /root/.streamlit/config.toml /home/appuser/.streamlit/config.toml && \
    chown -R appuser:appuser /home/appuser/.streamlit
USER appuser

EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

CMD ["streamlit", "run", "app/streamlit_app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]