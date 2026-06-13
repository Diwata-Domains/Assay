FROM python:3.12-slim

WORKDIR /app

# Install from local source — PyPI assay-kit is behind the monorepo
COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

RUN mkdir -p /data/assay-output

ENV ASSAY_ADMIN_EMAIL=""
ENV ASSAY_ADMIN_PASSWORD_HASH=""
ENV WARDEN_SECRET=""

COPY deploy/assay.container.toml /etc/assay/assay.toml

EXPOSE 8000

CMD ["assay", "--config", "/etc/assay/assay.toml", "serve", "--host", "0.0.0.0", "--port", "8000"]
