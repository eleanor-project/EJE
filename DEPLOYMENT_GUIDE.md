# EJC Production Deployment Guide

## Overview

This guide covers deploying the Eleanor Judicial Engine (EJC) with full Phase 3 Intelligence & Adaptation capabilities using Docker containers.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Dashboard     │────▶│    EJC API      │────▶│   PostgreSQL    │
│  (Port 8049)    │     │  (Port 8000)    │     │  (Port 5432)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌─────────────────┐
                        │     Redis       │
                        │  (Port 6379)    │
                        └─────────────────┘
```

## Prerequisites

- Docker Desktop (latest version)
- Docker Compose (v3.8+)
- 4GB RAM minimum
- 10GB disk space

## Quick Start (5 minutes)

### 1. Clone and Configure

```bash
cd /home/user/EJE
cp .env.example .env
```

### 2. Set API Keys

Edit `.env` and add your API keys:

```env
# LLM Provider API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...

# Database
POSTGRES_PASSWORD=your_secure_password_here

# Security
EJC_AUDIT_SIGNING_KEY=your_signing_key_here

# Optional: API Authentication
EJE_API_TOKEN=your_api_token_here
```

### 3. Build and Start

```bash
docker-compose up --build
```

Wait for all services to start (30-60 seconds).

### 4. Verify Deployment

```bash
# Check API health
curl http://localhost:8000/health

# Check dashboard
open http://localhost:8049

# View API docs
open http://localhost:8000/docs
```

## Service Endpoints

### FastAPI REST API (Port 8000)

**Core Endpoints:**
- `GET /` - API information
- `GET /health` - Health check
- `GET /metrics` - System metrics
- `POST /evaluate` - Evaluate case
- `POST /precedents/search` - Search precedents

**Phase 3: Calibration Endpoints:**
- `POST /calibration/feedback` - Submit ground truth feedback
- `GET /calibration/metrics/{critic_name}` - Get critic performance metrics
- `POST /calibration/tune/{critic_name}` - Auto-tune confidence thresholds

**Phase 3: Drift Detection Endpoints:**
- `GET /drift/health` - Get system drift health score
- `GET /drift/alerts` - Get recent drift alerts

**Phase 3: Context-Aware Evaluation:**
- `POST /evaluate/contextual` - Evaluate with jurisdiction/cultural/domain context

**Phase 3: Performance Monitoring:**
- `GET /performance/stats` - Get caching and parallelization statistics

### Dashboard (Port 8049)

- Web-based UI for monitoring decisions
- Real-time decision visualization
- Precedent browser
- Critic deliberation view

### PostgreSQL (Port 5432)

- Audit logs
- Ground truth feedback
- Drift alerts
- Precedent storage

### Redis (Port 6379)

- Optional distributed caching
- Task queue management

## Phase 3 Feature Usage

### 1. Critic Calibration

**Submit Feedback:**
```bash
curl -X POST http://localhost:8000/calibration/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "decision_id": "dec_12345",
    "reviewer_id": "reviewer_001",
    "verdict": "allowed",
    "confidence": 0.95,
    "critic_verdicts": {
      "rights_critic": "allowed",
      "equity_critic": "allowed"
    }
  }'
```

**Get Metrics:**
```bash
curl http://localhost:8000/calibration/metrics/rights_critic
```

**Auto-Tune Thresholds:**
```bash
curl -X POST "http://localhost:8000/calibration/tune/rights_critic?target_accuracy=0.90"
```

### 2. Drift Detection

**Check Health:**
```bash
curl "http://localhost:8000/drift/health?days=30"
```

**Get Alerts:**
```bash
curl "http://localhost:8000/drift/alerts?limit=10&severity=high"
```

### 3. Context-Aware Evaluation

**GDPR Compliance Check:**
```bash
curl -X POST http://localhost:8000/evaluate/contextual \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Store user email for marketing",
    "jurisdiction": "EU",
    "domain": "marketing",
    "context": {
      "user_consent": false
    }
  }'
```

**Healthcare Decision (HIPAA):**
```bash
curl -X POST http://localhost:8000/evaluate/contextual \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Share patient data with third-party",
    "jurisdiction": "US-HIPAA",
    "domain": "healthcare",
    "cultural_context": "western"
  }'
```

**Financial Decision (CCPA):**
```bash
curl -X POST http://localhost:8000/evaluate/contextual \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Sell customer data to data broker",
    "jurisdiction": "US-CA",
    "domain": "finance"
  }'
```

### 4. Performance Monitoring

```bash
curl http://localhost:8000/performance/stats
```

Expected response:
```json
{
  "cache_hit_rate": 0.65,
  "cache_size": 234,
  "avg_cache_speedup": 12.5,
  "avg_parallel_speedup": 4.2,
  "total_time_saved_ms": 45678.9
}
```

## Configuration

### Environment Variables

**Required:**
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `POSTGRES_PASSWORD` - PostgreSQL password

**Optional:**
- `EJE_API_TOKEN` - API authentication token
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `MAX_PARALLEL_CALLS` - Max parallel critic execution (default: 5)
- `ENABLE_CACHE` - Enable result caching (default: true)
- `CACHE_SIZE` - LRU cache size (default: 1000)

### Volume Mounts

```yaml
volumes:
  postgres_data:   # PostgreSQL data persistence
  eje_data:        # EJC data (precedents, audit logs)
  redis_data:      # Redis persistence
```

## Database Schema

The PostgreSQL database includes tables for:

- **audit_log** - Decision audit trail with cryptographic signing
- **ground_truth_feedback** - Calibration feedback from reviewers
- **drift_alerts** - Constitutional drift and consistency alerts
- **precedent_records** - Historical decisions for precedent matching

See `init-db.sql` for full schema.

## Monitoring & Observability

### Health Checks

All services include health checks:

```bash
# API health
docker-compose ps

# Detailed component status
curl http://localhost:8000/health | jq
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f eje-api
docker-compose logs -f postgres
```

### Metrics

- **System Metrics**: `/metrics` endpoint
- **Performance Stats**: `/performance/stats` endpoint
- **Drift Health**: `/drift/health` endpoint
- **Calibration Metrics**: `/calibration/metrics/{critic_name}` endpoint

## Production Deployment

### 1. Security Hardening

**Set Strong Passwords:**
```env
POSTGRES_PASSWORD=$(openssl rand -base64 32)
EJC_AUDIT_SIGNING_KEY=$(openssl rand -base64 64)
EJE_API_TOKEN=$(openssl rand -base64 32)
```

**Enable API Authentication:**
```env
EJE_API_TOKEN=your_secret_token
```

All API requests must include:
```bash
curl -H "Authorization: Bearer your_secret_token" \
  http://localhost:8000/evaluate
```

**Network Isolation:**
```yaml
# In docker-compose.yml
networks:
  eje-network:
    internal: true  # Block external access
```

### 2. SSL/TLS

Use a reverse proxy (nginx, Traefik) for HTTPS:

```nginx
server {
    listen 443 ssl;
    server_name eje.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Scaling

**Horizontal Scaling (Multiple API Instances):**
```yaml
eje-api:
  deploy:
    replicas: 3
```

**Load Balancer:**
- Use nginx/HAProxy for load balancing
- Enable session affinity if needed
- Distribute across multiple hosts

**Database Scaling:**
- Use PostgreSQL read replicas
- Configure connection pooling
- Consider TimescaleDB for time-series audit data

### 4. Backup & Recovery

**Automated Backups:**
```bash
# Backup script (daily cron job)
#!/bin/bash
docker exec eje-postgres pg_dump -U eje_user eleanor > \
  /backups/eje_$(date +%Y%m%d).sql
```

**Restore:**
```bash
docker exec -i eje-postgres psql -U eje_user eleanor < \
  /backups/eje_20251127.sql
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs eje-api

# Restart specific service
docker-compose restart eje-api

# Rebuild if needed
docker-compose up --build --force-recreate eje-api
```

### Database Connection Issues

```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check database connectivity
docker exec eje-postgres psql -U eje_user -d eleanor -c "SELECT 1;"

# View PostgreSQL logs
docker-compose logs postgres
```

### API Errors

```bash
# Check API logs
docker-compose logs -f eje-api

# Verify configuration loaded
curl http://localhost:8000/health | jq '.components'

# Test with minimal request
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test", "context": {}}'
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Check cache performance
curl http://localhost:8000/performance/stats | jq

# Review slow queries in PostgreSQL
docker exec eje-postgres psql -U eje_user -d eleanor -c \
  "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

## Development Workflow

### Local Development

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f eje-api

# Run tests
docker-compose exec eje-api pytest tests/

# Stop services
docker-compose down
```

### Hot Reload

For development, mount source code:

```yaml
# docker-compose.override.yml
services:
  eje-api:
    volumes:
      - ./src:/app/src
    command: ["uvicorn", "src.ejc.server.api:app", "--reload", "--host", "0.0.0.0"]
```

### Testing Phase 3 Features

```bash
# Test calibration
pytest tests/test_calibration.py -v

# Test drift detection
pytest tests/test_drift_detection.py -v

# Test context system
pytest tests/test_context_system.py -v

# Test performance
pytest tests/test_performance.py -v
```

## Migration from Development to Production

1. **Export configuration**:
   ```bash
   cp config/global.yaml config/production.yaml
   ```

2. **Update environment**:
   ```env
   EJE_CONFIG_PATH=/app/config/production.yaml
   LOG_LEVEL=WARNING
   ```

3. **Enable monitoring**:
   - Set up Prometheus metrics export
   - Configure alerting (PagerDuty, Slack)
   - Enable audit log shipping (Elasticsearch, S3)

4. **Performance tuning**:
   ```env
   MAX_PARALLEL_CALLS=10
   CACHE_SIZE=5000
   ENABLE_CACHE=true
   ```

## Support & Resources

- **Documentation**: `/docs` directory
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **GitHub**: https://github.com/eleanor-project/EJE
- **Issues**: https://github.com/eleanor-project/EJE/issues

## Next Steps

1. **Create Pull Request** for Phase 3
2. **CI/CD Testing** - Full test suite on merge
3. **Staging Deployment** - Test in production-like environment
4. **Production Rollout** - Gradual rollout with monitoring
5. **Phase 4 Planning** - Advanced features and optimizations

---

**Version**: 1.0.0 (Phase 3 Complete)
**Last Updated**: 2025-11-27
**Status**: Production Ready 🚀
