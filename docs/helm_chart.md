# EJE Helm Chart

This chart packages the ELEANOR Justice Engine (EJE) for Kubernetes using Helm. It supports PostgreSQL and Redis dependencies, migration hooks, and environment-specific values files.

## Contents
- Application Deployment (Deployment + Service)
- Optional Ingress
- ConfigMap-driven application settings
- Database and cache credentials sourced from secrets
- Pre-install/upgrade migration Job hook
- Bitnami PostgreSQL and Redis sub-charts

## Getting Started

Add the Bitnami repository for chart dependencies:

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm dependency build deploy/helm/eje
```

Install the chart with the default (staging-like) settings:

```bash
helm install eje deploy/helm/eje
```

Pick a values file for your environment:

```bash
# Development
helm install eje-dev deploy/helm/eje -f deploy/helm/eje/values-dev.yaml

# Staging
helm install eje-staging deploy/helm/eje -f deploy/helm/eje/values-staging.yaml

# Production
helm install eje-prod deploy/helm/eje -f deploy/helm/eje/values-prod.yaml
```

Upgrade an existing release while running migrations:

```bash
helm upgrade eje-prod deploy/helm/eje \
  -f deploy/helm/eje/values-prod.yaml \
  --set migrations.command="{bash,-c,python tools/db_migrate.py}"
```

## Configuration

### Core settings
| Key | Description | Default |
| --- | ----------- | ------- |
| `image.repository` | Container image repository | `ghcr.io/eleanor-project/eje` |
| `image.tag` | Image tag | `latest` |
| `replicaCount` | Number of replicas | `2` |
| `service.type` | Service type | `ClusterIP` |
| `ingress.enabled` | Enable ingress | `false` |
| `config.appEnv` | Application environment string | `staging` |
| `config.healthcheckPath` | Path used by probes | `/health` |

### Database (PostgreSQL)
- Enabled by default via the Bitnami sub-chart.
- Override to use an external database:

```yaml
postgresql:
  enabled: false
  external:
    host: db.example.com
    port: 5432
    user: eje
    database: eje
    passwordSecretName: external-db-secret
    passwordSecretKey: password
```

### Cache (Redis)
- Enabled by default via the Bitnami sub-chart.
- Example external configuration:

```yaml
redis:
  enabled: false
  external:
    host: redis.example.com
    port: 6379
    passwordSecretName: external-redis-secret
    passwordSecretKey: redis-password
```

### Migrations
The chart ships with a pre-install and pre-upgrade Job hook. Customize the command to run real migrations:

```yaml
migrations:
  enabled: true
  command:
    - bash
    - -c
    - python tools/db_migrate.py
```

The default command is a no-op so installations succeed even without migration tooling.

## Dependency Notes
- PostgreSQL: Bitnami chart `postgresql` (default) with optional persistence (enabled in `values-prod.yaml`).
- Redis: Bitnami chart `redis` (default) with optional password protection (`values-prod.yaml`).

## Uninstall

```bash
helm uninstall eje-prod
```

This removes the release but keeps any persistent volumes created by sub-charts.
