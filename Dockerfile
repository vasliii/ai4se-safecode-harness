FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY safecode ./safecode

RUN python -m pip install --upgrade pip \
    && python -m pip install -e . \
    && rm -rf /root/.cache/pip \
    && useradd --create-home --shell /usr/sbin/nologin safecode \
    && chown -R safecode:safecode /app

USER safecode

EXPOSE 8000

CMD ["safecode", "serve", "--host", "0.0.0.0", "--port", "8000"]
