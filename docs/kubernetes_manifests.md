# Kubernetes Manifests

This directory contains Kustomize-ready manifests for deploying the EJE API to Kubernetes with autoscaling, ingress, and persistent storage.

## Layout
- `deploy/k8s/base/`: Reusable building blocks (Deployment, Service, Ingress, HPA, PVC, ConfigMap, Secret, ServiceAccount, PodDisruptionBudget).
- `deploy/k8s/overlays/staging/`: Staging overrides (namespace, image tag, ingress host/TLS issuer, environment variables, secrets).
- `deploy/k8s/overlays/production/`: Production overrides (namespace, ingress host/TLS issuer, scaled replica count, environment variables, secrets).

## Key Features
- **Zero-downtime rollouts** via rolling updates (`maxUnavailable: 0`, `maxSurge: 1`) and a PodDisruptionBudget ensuring at least one pod remains available.
- **Autoscaling** with a HorizontalPodAutoscaler (CPU target 70%, minReplicas 2, maxReplicas 5).
- **Health checks** using readiness and liveness probes against `/health`.
- **Ingress** configured for NGINX with TLS secrets patched per environment.
- **Stateful storage** through a 10Gi PersistentVolumeClaim mounted at `/var/lib/eje`.
- **Load balancing** via a ClusterIP service by default, with the production overlay patching it to `LoadBalancer` for external traffic.
- **Configuration and secrets** wired through ConfigMap (`APP_ENV`, `LOG_LEVEL`, `HEALTHCHECK_PATH`, etc.) and Secret (`DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`).

## Usage
Build and apply the desired overlay (replace hosts, secrets, and storage class values as needed):

```bash
kustomize build deploy/k8s/overlays/staging | kubectl apply -f -
# or
kustomize build deploy/k8s/overlays/production | kubectl apply -f -
```

To inspect the rendered manifests without applying:

```bash
kustomize build deploy/k8s/overlays/staging
```

## Customization Tips
- Update `deploy/k8s/base/ingress.yaml` and the overlay ingress patches to match your domains and TLS issuers.
- Adjust resource requests/limits in `deploy/k8s/base/deployment.yaml` and HPA bounds in `deploy/k8s/base/hpa.yaml` to fit your cluster capacity.
- Change `storageClassName` or PVC size in `deploy/k8s/base/pvc.yaml` if your storage backend differs.
- Override database/Redis endpoints and secrets via the Secret patches in each overlay before applying to a cluster.
