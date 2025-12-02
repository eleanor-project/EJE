# Continuous Delivery Pipeline

This repository ships a GitHub Actions workflow that automates delivery to staging on every merge to `main` and supports a manually approved promotion to production.

## Workflow overview

- **File**: `.github/workflows/cd.yml`
- **Triggers**:
  - `push` to `main`: builds/pushes an image and deploys to **staging** automatically.
  - `workflow_dispatch`: deploys to staging or production on demand, or performs a rollback.
- **Artifacts**: Docker images are published to `ghcr.io/eleanor-project/eje` with tags `latest` and the short commit SHA.
- **Environments**:
  - `staging`: auto-deploy on merge; uses `deploy/k8s/overlays/staging`.
  - `production`: manual run; uses `deploy/k8s/overlays/production` and can be protected by environment approvals.

## Required secrets

| Secret | Purpose |
| --- | --- |
| `CR_PAT` | GitHub token (with `packages:write`) to push to GHCR. Falls back to `GITHUB_TOKEN` if unset. |
| `KUBE_CONFIG_STAGING` | Base64-encoded kubeconfig granting access to the staging cluster. |
| `KUBE_CONFIG_PRODUCTION` | Base64-encoded kubeconfig for production. |
| `SLACK_WEBHOOK` (optional) | Incoming webhook for deployment notifications. |

## Deploying

### Automatic staging deploy
1. Merge to `main`.
2. The workflow builds and pushes an image tagged `latest` and `<short-sha>`.
3. The staging overlay is applied via Kustomize, and the image is rolled out with zero-downtime settings.

### Manual production deploy
1. In GitHub Actions, run **Continuous Delivery** → **Run workflow**.
2. Choose `production` for `target_environment` and optionally specify an `image_tag`.
3. Approve the deployment when prompted by the protected `production` environment.
4. The workflow updates the image in the production namespace and waits for rollout.

### Rollback
1. Trigger the workflow manually with `rollback` set to `true`.
2. Select the `rollback_environment` (staging or production) and optionally a `rollback_revision`.
3. The workflow issues `kubectl rollout undo` and reports the result.

## Kubernetes configuration

- Base manifests live in `deploy/k8s/base`.
- Environment overlays supply namespaces, config maps, and replica/limit tuning under `deploy/k8s/overlays/<environment>`.
- Deployments use rolling updates with `maxUnavailable: 0` and `maxSurge: 1` for zero-downtime rollouts.
- Readiness and liveness probes hit `/health` on port `8080`.
