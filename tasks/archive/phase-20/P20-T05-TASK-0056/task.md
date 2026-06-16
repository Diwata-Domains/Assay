# Task: Deployment config (Dockerfile, docker-compose, nginx, .env.example)

## Metadata
- **ID:** TASK-0056
- **Status:** done
- **Phase:** P20-T05
- **Backlog:** P20-T05 — Deployment config (Dockerfile, docker-compose, nginx, .env.example)
- **Packet Path:** tasks/P20-T05-TASK-0056/
- **Dependencies:** TASK-0054, TASK-0055
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Add deployment artifacts so assay can be run at a domain with HTTPS. Dockerfile for the Python app, docker-compose.yml with app + nginx, nginx.conf reverse proxy (certbot-ready), .env.example documenting all required vars, and a deploy guide.

## Scope
- deploy/Dockerfile — Python 3.12 slim, install assay-kit, run uvicorn
- deploy/docker-compose.yml — assay service + nginx service, volume mounts for data and certs
- deploy/nginx.conf — reverse proxy to app:8000, HTTPS with certbot path, HTTP→HTTPS redirect
- deploy/.env.example — all required env vars with descriptions
- docs/working/deploy_guide.md — step-by-step: clone, .env, docker compose up, certbot, DNS

## Constraints
- Data volume must persist across container restarts (SQLite + screenshots)
- No credentials baked into images
- Nginx config must be certbot-compatible (well-known path for ACME challenge)

## Escalation Conditions
- None
