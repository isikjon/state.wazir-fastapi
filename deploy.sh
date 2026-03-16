#!/bin/bash

set -e

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "=== Wazir FastAPI Deploy ==="

log "Stopping existing containers..."
docker compose -f docker-compose.prod.yml down --remove-orphans 2>/dev/null || true

log "Pulling latest changes..."
git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || log "Git pull skipped (no remote or already up to date)"

log "Building and starting containers..."
docker compose -f docker-compose.prod.yml up --build -d

log "Waiting for app to start (30s)..."
sleep 30

log "=== Container Status ==="
docker compose -f docker-compose.prod.yml ps

log "=== FastAPI Logs (last 50 lines) ==="
docker compose -f docker-compose.prod.yml logs wazir-api --tail=50

log "=== Nginx Logs (last 20 lines) ==="
docker compose -f docker-compose.prod.yml logs nginx --tail=20

log "=== Health Check ==="
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost/api/v1/health || echo "Health check failed"

log "Deploy complete!"
