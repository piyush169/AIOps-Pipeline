# AIOps Pipeline — Adversarial CI/CD Chaos Simulator

A distributed CI/CD chaos engineering platform that uses an **Adversarial AI** to dynamically inject real-world failures into a production-grade Node.js pipeline, and an **AIOps Diagnoser AI** to automatically detect, classify, and recommend fixes — all powered by real-time Grafana telemetry.

## Architecture

The project is split across **two CI/CD platforms** simultaneously, chosen based on statistical analysis of 45,000+ real-world CI/CD failure logs from the [Kaggle CI/CD Pipeline Failures Dataset](https://www.kaggle.com/datasets/mirzayasirabdullah07/cicd-pipeline-failure-logs-dataset-for-aiops) and the [Zenodo LogChunks Dataset](https://zenodo.org/records/3632351).

### Travis CI (Dependency, Testing & Integration)
| Stage | Tool | Purpose |
|-------|------|---------|
| 1. Dependency Install | `npm` | Verify package resolution and module integrity |
| 2. Unit Testing | `Jest` (22 test cases) | Validate API logic, input validation, and error handling |
| 3. Integration Testing | `docker-compose` + `curl` | Spin up full stack (Node + Postgres + Redis) and verify endpoints |

### GitHub Actions (Linting, Security & Build)
| Stage | Tool | Purpose |
|-------|------|---------|
| 4. Code Quality | `ESLint` + `Prettier` | Enforce syntax and formatting standards |
| 5. Security Scanning | `Trivy` + `Gitleaks` + `npm audit` | Detect vulnerable dependencies and hardcoded secrets |
| 6. Container Build | `Docker` | Build and verify the production container image |

## The Base Application

A production-grade **Node.js Express REST API** with full CRUD operations, input validation, and health checks — connected to **PostgreSQL** and **Redis**.

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check (DB + Redis connectivity) |
| `GET` | `/api/data` | Returns sample data array |
| `GET` | `/api/config` | Returns app version and environment |
| `GET` | `/api/users` | List all users |
| `GET` | `/api/users/:id` | Get user by ID |
| `POST` | `/api/users` | Create a new user (with validation) |
| `DELETE` | `/api/users/:id` | Delete a user by ID |

## How the Adversarial AI Works

1. **Pick a Fault:** A random real-world failure log is selected from the Golden Dataset (ETL-processed from 45,000+ Kaggle + Zenodo entries).
2. **Inject Chaos:** An Adversarial AI (local LLM via Ollama) reads the historical log and dynamically mutates the codebase to reproduce a similar failure.
3. **Branch & Push:** The mutation is committed to a temporary `chaos-run-*` branch and pushed to GitHub.
4. **Pipeline Fails Natively:** Both Travis CI and GitHub Actions trigger on the branch. The pipeline crashes with real, authentic error logs.
5. **AI Diagnosis:** The AIOps Diagnoser AI ingests the Grafana Loki logs and identifies the root cause and recommended fix.
6. **Cleanup:** The chaos branch is deleted, restoring the codebase to its golden state on `main`.

## Tech Stack

| Category | Tools |
|----------|-------|
| **Runtime** | Node.js 18, Express |
| **Database** | PostgreSQL 14 |
| **Cache** | Redis |
| **Testing** | Jest, Supertest |
| **Linting** | ESLint, Prettier |
| **Security** | Trivy, Gitleaks, npm audit |
| **Containerization** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions, Travis CI |
| **Observability** | Grafana, Loki (planned) |
| **AI** | Ollama (local LLM) |

## Quick Start

```bash
# Clone the repository
git clone https://github.com/piyush169/AIOps-Pipeline.git
cd AIOps-Pipeline

# Install dependencies
npm install

# Run tests locally
npm test

# Start with Docker Compose
docker-compose up -d
```

## Project Status

- [x] Base Node.js API with CRUD + validation
- [x] 22 passing Jest test cases
- [x] Multi-platform CI/CD (GitHub Actions + Travis CI)
- [x] Security scanning (Trivy + Gitleaks)
- [ ] Golden Dataset ETL pipeline
- [ ] Adversarial AI Chaos Injector
- [ ] AIOps Diagnoser AI
- [ ] Grafana Loki observability dashboard
- [ ] Visual pipeline status dashboard

## License

MIT
