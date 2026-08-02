FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /service
RUN apt-get update \
    && apt-get install -y --no-install-recommends git postgresql-client \
    && git --version \
    && rm -rf /var/lib/apt/lists/*
COPY backend/pyproject.toml ./pyproject.toml
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./alembic.ini
RUN pip install .
COPY docs/digital-asset-custody-guide-2.1.zh-TW.md ./docs/digital-asset-custody-guide-2.1.zh-TW.md
COPY docs/workspace-hosting-developer-standard-2.2.zh-TW.md ./docs/workspace-hosting-developer-standard-2.2.zh-TW.md
COPY docs/workspace-hosting-contract-2.2.json ./docs/workspace-hosting-contract-2.2.json
COPY frontend/v2 /frontend/v2

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]
