FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir assay-kit

RUN mkdir -p /data/assay-output

ENV ASSAY_ADMIN_EMAIL=""
ENV ASSAY_ADMIN_PASSWORD_HASH=""
ENV ASSAY_JWT_SECRET=""

# assay.toml picks these up via [keys], [store], [output] sections
# Override by mounting a config or setting env ASSAY_CONFIG
COPY assay.container.toml /etc/assay/assay.toml

EXPOSE 8000

CMD ["assay", "--config", "/etc/assay/assay.toml", "serve", "--host", "0.0.0.0", "--port", "8000"]
