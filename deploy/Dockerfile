FROM python:3.12-slim AS builder

# Build context must be repo root so packages/warden is accessible.
WORKDIR /build

COPY packages/warden ./packages/warden
RUN pip install --no-cache-dir ./packages/warden

COPY products/assay/pyproject.toml .
COPY products/assay/src ./src
RUN pip install --no-cache-dir .

FROM python:3.12-slim AS runtime

RUN useradd -m -s /bin/bash app
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY products/assay/src ./src
COPY products/assay/deploy/assay.container.toml /etc/assay/assay.toml

RUN mkdir -p /data/assay-output

ENV ASSAY_ADMIN_EMAIL=""
ENV ASSAY_ADMIN_PASSWORD_HASH=""
ENV WARDEN_SECRET=""

ENV PYTHONPATH=/app/src
USER app

EXPOSE 8000

CMD ["assay", "--config", "/etc/assay/assay.toml", "serve", "--host", "0.0.0.0", "--port", "8000"]
