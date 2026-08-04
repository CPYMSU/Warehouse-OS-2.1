FROM postgres:18.4-bookworm AS postgresql-client

FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /service
RUN apt-get update \
    && apt-get install -y --no-install-recommends git liblz4-1 libpq5 libzstd1 \
    && git --version \
    && rm -rf /var/lib/apt/lists/*
COPY --from=postgresql-client /usr/lib/postgresql/18 /usr/lib/postgresql/18
ENV PATH="/usr/lib/postgresql/18/bin:${PATH}" \
    WAREHOUSE_POSTGRESQL_CLIENT_BIN=/usr/lib/postgresql/18/bin
RUN pg_dump --version | grep -Eq '^pg_dump \(PostgreSQL\) 18\.' \
    && pg_restore --version | grep -Eq '^pg_restore \(PostgreSQL\) 18\.'
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
