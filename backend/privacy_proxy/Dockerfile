FROM python:3.11-slim
RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /service
COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y --only-upgrade \
      openssl libssl3 \
      libcap2 \
      libsystemd0 \
      libudev1 && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir wheel==0.46.2 "jaraco.context>=6.1.0" && \
    pip install --no-cache-dir -r requirements.txt && \
    find /usr/local/lib/python3.11/site-packages -name "wheel-0.45*" -type d -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.11/site-packages -name "jaraco.context-5*" -type d -exec rm -rf {} + 2>/dev/null || true && \
    python -m spacy download en_core_web_md && \
    python -m spacy download de_core_news_md && \
    pip cache purge
COPY app/ app/
RUN chown -R appuser:appuser /service
USER appuser
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]