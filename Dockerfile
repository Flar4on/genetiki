FROM python:3.11-slim

WORKDIR /app

RUN pip install --upgrade pip setuptools

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY alembic.ini .
COPY alembic/ alembic/
COPY src/ src/

CMD ["python", "-m", "src.main"]
