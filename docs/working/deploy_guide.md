# Assay Deploy Guide

Deploy the hosted dashboard to a VPS with HTTPS at your domain.

## Prerequisites

- A VPS with Docker + Docker Compose installed
- A domain pointed at the VPS IP (A record)
- SSH access to the VPS

---

## Steps

### 1. Clone and configure

```bash
git clone https://github.com/Diwata-Labs/Assay.git
cd Assay/deploy
cp .env.example .env
```

Edit `.env`:

```bash
# Hash your password first (run this on your local machine with assay-kit installed)
assay admin set-password
# Copy the printed ASSAY_ADMIN_PASSWORD_HASH=... line into .env

# Generate a JWT secret
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
# Copy the output as ASSAY_JWT_SECRET in .env

# Set your admin email
ASSAY_ADMIN_EMAIL=you@yourdomain.com
```

### 2. Set your domain in nginx.conf

Replace all occurrences of `YOUR_DOMAIN` with your actual domain:

```bash
sed -i 's/YOUR_DOMAIN/assay.yourdomain.com/g' nginx.conf
```

### 3. Start the stack (HTTP only first, for certbot)

```bash
docker compose up -d assay nginx
```

### 4. Get your SSL certificate

```bash
docker compose run --rm certbot certonly \
  --webroot \
  --webroot-path /var/www/certbot \
  -d assay.yourdomain.com \
  --email you@yourdomain.com \
  --agree-tos \
  --no-eff-email
```

### 5. Start certbot auto-renewal and reload nginx

```bash
docker compose up -d
docker compose exec nginx nginx -s reload
```

### 6. Visit your dashboard

Go to `https://assay.yourdomain.com` — you should see the login page.

Log in with the email and password you set in `.env`.

### 7. Create your first API key

From the dashboard, go to **API Keys** → fill in a label (e.g. `crm-prod`) → **Create key**.

Copy the key — it's shown once. Add it to your CRM app's environment:

```bash
VITE_ASSAY_KEY=<the key>
VITE_ASSAY_ENDPOINT=https://assay.yourdomain.com
```

---

## Data

All data persists in Docker volumes:
- `assay-data` — SQLite DB + screenshot PNGs (at `/data` inside the container)

To back up: `docker run --rm -v assay_assay-data:/data -v $(pwd):/backup alpine tar czf /backup/assay-backup.tar.gz /data`

---

## Updating

```bash
git pull
docker compose build assay
docker compose up -d assay
```
