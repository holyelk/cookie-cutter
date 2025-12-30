# Production-Ready Kubernetes App Template

This is an opinionated, production-ready cookie-cutter template for building backend services with FastAPI and deploying them to Kubernetes using Helm. It prioritizes clarity, sensible defaults, and observability.

## Repository Structure

- `app/`: FastAPI application source code.
- `charts/backend-service/`: Helm chart for deploying the application.
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

We use **Helm** to manage deployments. The chart is located in `charts/backend-service`.

### Prerequisites
- A Kubernetes cluster
- Helm 3.x installed
- Kubectl configured

### Deploying Manually
To deploy to a `dev` namespace using the development values:

```bash
helm upgrade --install my-service ./charts/backend-service \
  --namespace dev --create-namespace \
  --values ./charts/backend-service/values.yaml \
  --values ./charts/backend-service/values-dev.yaml
```

### Configuration
Configuration is managed via `values.yaml` files.

- **`values.yaml`**: Contains shared defaults and production-ready settings.
- **`values-dev.yaml`**: Overrides for development (lower resources, debug logging).
- **`values-prod.yaml`**: Overrides for production (high availability, HPA enabled).

**Files you are expected to edit:**
- `app/main.py`: Add your business logic here.
- `charts/backend-service/values.yaml`: Change image repository, resource limits, and common env vars.
- `charts/backend-service/Chart.yaml`: Update the chart version and app version.

## Features & Integrations

### Enabling PostgreSQL
Support for **CloudNativePG** is built-in but disabled by default.

To enable it in production:
1.  Open `charts/backend-service/values-prod.yaml`.
2.  Set `postgres.enabled: true`.

```yaml
postgres:
  enabled: true
  instances: 3
  storage:
    size: 10Gi
```

This will create a `Cluster` resource defined in `templates/postgres.yaml`. Ensure the CloudNativePG operator is installed in your cluster.

### Standalone PostgreSQL
This chart can be used to deploy *only* a production-ready PostgreSQL cluster (CloudNativePG) without the application.

1.  **Disable the App**:
    In `values.yaml` (or your environment override), set:
    ```yaml
    app:
      enabled: false
    ```

2.  **Configure PostgreSQL**:
    Enable postgres and configure the cluster.
    ```yaml
    postgres:
      enabled: true
      instances: 3
      storage:
        size: 50Gi
      
      # Bootstrap a new DB
      bootstrap:
        initdb:
          database: mydb
          owner: myuser
      
      # Enable Backups
      backup:
        enabled: true
        retentionPolicy: "30d"
        barmanObjectStore:
           destinationPath: s3://...
    ```

### Enabling Observability
OpenTelemetry (OTel) is integrated directly into the app.

1.  **Tracing & Metrics**:
    The app pushes traces and metrics via OTLP gRPC.
    Configure the endpoint in `values.yaml` (under `env`):
    ```yaml
    env:
      OTLP_GRPC_ENDPOINT: "http://your-otel-collector:4317"
      ENABLE_TELEMETRY: "true"
    ```

2.  **Logging**:
    Logs are strictly structured JSON to stdout, compatible with Elastic/Logstash/Filebeat.

### CI/CD Pipeline (GitLab)
Included `.gitlab-ci.yml` handles:
1.  **Lint**: Checks code quality.
2.  **Test**: Runs pytest.
3.  **Build**: Builds Docker image and pushes to GitLab Registry.
4.  **Deploy**: Deploys to Kubernetes using Helm.

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
