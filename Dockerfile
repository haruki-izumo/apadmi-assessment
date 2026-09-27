FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Git checkouts on Windows may use CRLF. Bash rejects those scripts.
RUN sed -i 's/\r$//' scripts/*.sh \
    && chmod +x scripts/download_data.sh scripts/docker_entrypoint.sh \
    && mkdir -p data/raw/fhir data/staging warehouse

EXPOSE 8501

ENTRYPOINT ["bash", "scripts/docker_entrypoint.sh"]
