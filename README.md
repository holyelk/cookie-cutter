# Production-Ready Kubernetes App Template

This is an opinionated, production-ready cookie-cutter template for building backend services with FastAPI and deploying them to Kubernetes using Helm. It prioritizes clarity, sensible defaults, and observability.

## Repository Structure

- `app/`: FastAPI application source code.

- `app/`: FastAPI application source code.
- `k8s/`: Kustomize configuration for Kubernetes.
    - `base/`: Shared base resources (Deployment, Service, etc.).
    - `components/`: Optional components (Postgres, Backup).
    - `overlays/`: Environment-specific patches (dev, staging, prod).
- `.gitlab-ci.yml`: CI/CD pipeline configuration.
- `.gitlab-ci.yml`: CI/CD pipeline configuration.
- `docker-compose.yaml`: Local development environment.
- `Dockerfile`: Production container image definition.

## Quick Start

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-folder>
    ```

2.  **Local Setup (Docker Compose):**
    Run the application and Jaeger (for tracing) locally.
    ```bash
    docker-compose up --build
    ```
    - API: [http://localhost:8000](http://localhost:8000)
    - Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
    - Jaeger UI: [http://localhost:16686](http://localhost:16686)

## Local Development

The project uses `docker-compose` to mirror the production environment locally.

1.  **Environment Variables:**
    Copy `.env.example` to `.env` to configure local settings.
    ```bash
    cp .env.example .env
    ```

2.  **Running Locally:**
    ```bash
    docker-compose up
    ```
    This starts the FastAPI app and a local Jaeger instance for creating and viewing traces.

## Deploying to Kubernetes

We use **Kustomize** to manage deployments. The configuration is located in `k8s/`.

### Prerequisites
- A Kubernetes cluster
- Kubectl installed (supports Kustomize natively)

### Deploying Manually
To deploy to a `dev` environment:

```bash
# Preview changes
kubectl kustomize k8s/overlays/dev

# Apply changes
kubectl apply -k k8s/overlays/dev
```

### Configuration
Configuration is managed via **Overlays** and **Patches**.

- **`k8s/base/`**: Contains shared defaults.
- **`k8s/overlays/dev/`**: Patches `replicas=1`, disables telemetry, uses `dev.example.com`.
- **`k8s/overlays/prod/`**: Patches `replicas=3`, enables telemetry, enables Postgres/Backup components.

**Files you are expected to edit:**
- `k8s/base/deployment.yaml`: Change base image or common container settings.
- `k8s/base/configmap.yaml`: Update shared environment variables.
- `k8s/overlays/{env}/kustomization.yaml`: Update environment-specific patches (e.g. CPU/Memory limits).

## Features & Integrations

### Enabling PostgreSQL
Support for **CloudNativePG** is provided as a Kustomize Component.

To enable it in an environment (already enabled in `prod`):
1.  Open `k8s/overlays/{env}/kustomization.yaml`.
2.  Uncomment `- ../../components/postgres` in the `resources` list.

This will deploy the `Cluster` resource defined in `k8s/components/postgres/cluster.yaml`.

### Enabling Logical Backups
To enable the S3 backup CronJob:
1.  Open `k8s/overlays/{env}/kustomization.yaml`.
2.  Uncomment `- ../../components/backup`.
3.  You may need to add a `configMapGenerator` or `secretGenerator` in the overlay to provide the S3 bucket details (see `k8s/components/backup/cronjob.yaml` for required env vars).

### Enabling Observability
OpenTelemetry (OTel) is integrated directly into the app.

1.  **Tracing & Metrics**:
    The app pushes traces and metrics via OTLP gRPC.
    Configure the endpoint in `k8s/base/configmap.yaml` or patch it in `k8s/overlays/{env}/kustomization.yaml`.

2.  **Logging**:
    Logs are strictly structured JSON to stdout.

### CI/CD Pipeline (GitLab)
Included `.gitlab-ci.yml` handles:
1.  **Lint**: Checks code quality.
2.  **Test**: Runs pytest.
3.  **Build**: Builds Docker image and pushes to GitLab Registry.
4.  **Deploy**: Deploys to Kubernetes using `kubectl apply -k`.

**Unique Feature**: The pipeline uses `kustomize edit set image` to inject the exact image version (`$APP_VERSION`) into the manifests before applying.

**How to Rollback:**
Default `kubectl` rollbacks work for Deployments:
```bash
kubectl rollout undo deployment/backend-service
```
Note: This reverts the Pod specs, but does not revert Kustomize configmaps or other resources unless you use a more advanced GitOps controller.

**Required GitLab CI Variables:**
The pipeline assumes standard GitLab variables (`CI_REGISTRY`, etc.) are available. No manual variables are strictly required unless you need to inject secrets.

**Environments:**
- `develop` branch -> Deploys to `dev` environment.
- `main` branch -> Deploys to `staging` environment.
- Manually trigger `deploy_prod` on `main` -> Deploys to `prod`.

### Adding a New Environment
1.  Create a new values file: `charts/backend-service/values-qa.yaml`.
2.  Add a deploy job to `.gitlab-ci.yml`:
    ```yaml
    deploy_qa:
      stage: deploy
      environment:
        name: qa
      script:
        - helm upgrade --install backend-service ./charts/backend-service \
          --namespace qa --create-namespace \
          --values ./charts/backend-service/values.yaml \
          --values ./charts/backend-service/values-qa.yaml
    ```

### Versioning & Releases (Automated)
The pipeline automatically versions every build:
*   **Git Tags**: If you push a tag (e.g., `v1.0.1`), the Docker image and Helm appVersion use this tag.
*   **Commits**: If no tag is present, a deterministic version is generated: `0.0.0-rev[short-sha]`.

**How releases work:**
1.  **Dev**: Pushes to `develop` deploy `0.0.0-rev...` to Dev.
2.  **Staging**: Pushes to `main` deploy `0.0.0-rev...` to Staging.
3.  **Prod**: To release to Prod, you trigger the manual job on `main`.
4.  **Stable Release**: To create a stable named release:
    *   Tag your commit: `git tag v1.2.0; git push origin v1.2.0`
    *   The pipeline will build `v1.2.0`.
    *   Deploying this artifact ensures you are running exactly that version.

**Rollbacks:**
Since every deployment is versioned, you can roll back via Helm:
```bash
helm rollback backend-service [revision] -n prod
```

### Logical Backups (S3)
A CronJob can be enabled to perform `pg_dumpall` and upload to S3. This provides a portable SQL-based backup.

**Enable in `values-prod.yaml`:**
```yaml
logicalBackup:
  enabled: true
  schedule: "0 2 * * *"
  s3:
    bucket: "my-backup-bucket"
    endpoint: "https://s3.us-east-1.amazonaws.com"
    region: "us-east-1"
  existingSecret: "backup-secrets"
```

**Secrets Required:**
Create a secret named `backup-secrets` with:
*   `AWS_ACCESS_KEY_ID`
*   `AWS_SECRET_ACCESS_KEY`
*   `PGPASSWORD` (for the backup user, usually `postgres`)

**When to use:**
*   **CNPG Backups**: Primary method. Physical, incremental, point-in-time recovery.
*   **Logical Backups**: Secondary "last resort". Portable, simple SQL format, easiest for restoring to a different environment or database engine.
