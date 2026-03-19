FROM python:3.12.9-slim

WORKDIR /app

COPY backend/pyproject.toml .
RUN pip install --no-cache-dir .

COPY backend/ .
RUN pip install --no-cache-dir --no-deps .

RUN useradd -r -s /bin/false appuser
USER appuser

CMD ["bash", "start.sh"]
