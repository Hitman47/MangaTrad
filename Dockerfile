FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      libgl1 \
      libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-dev.txt requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements-dev.txt

COPY pyproject.toml README.md ./
COPY src ./src
COPY tests ./tests
RUN pip install -e .

CMD ["pytest", "-q"]
