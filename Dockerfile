FROM python:3.10
WORKDIR /app

RUN python -m pip install poetry==2.3.2 --no-cache-dir
COPY pyproject.toml poetry.lock .
RUN poetry install --no-cache

COPY . .
