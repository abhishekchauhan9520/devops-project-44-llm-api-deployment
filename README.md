# Project 44 — Production LLM API Deployment

Production-style LLM serving gateway with provider abstraction, API authentication, bounded request sizes, rate limiting, token telemetry, Kubernetes deployment controls, and fail-closed security checks.

## Architecture

```text
Client
  |
  v
LLM API Gateway
  |-- API key auth
  |-- rate limiting
  |-- request validation
  |-- request ID
  |-- metrics
  v
Provider Adapter
  |-- Mock (tests/local)
  `-- OpenAI Responses API
          |
          v
      LLM Provider

Kubernetes
  |
  +-- 2 replicas
  +-- HPA
  +-- PDB
  +-- probes
  +-- non-root / read-only filesystem
  +-- NetworkPolicy
  `-- secrets injected outside Git
```

## What this demonstrates

- Production API boundary around an LLM provider
- Provider abstraction so the API contract is independent of a vendor
- OpenAI Responses API adapter
- API-key authentication
- Request size and output-token limits
- In-memory rate limiting for a single-process lab
- Request IDs and latency measurement
- Prometheus-compatible metrics
- Input/output token counters for cost telemetry
- Kubernetes rolling deployment
- HPA and PodDisruptionBudget
- Restricted pod security context
- NetworkPolicy
- Secret injection via Kubernetes Secret reference, with placeholders only in the example manifest
- GitHub Actions tests, Docker build, Trivy, and Gitleaks

OpenAI's current model documentation lists the Responses API as the API used by the latest model family. Model choice and pricing can change, so the deployment keeps `OPENAI_MODEL` configurable rather than hard-coding a pricing table. citeturn883547search0

## Local run

```bash
export SERVICE_API_KEY='local-only-secret'
docker compose up --build
```

The Compose environment uses the deterministic mock provider, so no external model credential is required.

Request:

```bash
curl -X POST http://localhost:8080/v1/chat \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: local-only-secret' \
  -H 'X-Client-Id: demo' \
  -d '{"prompt":"Explain blue-green deployment in one sentence."}'
```

## Real provider

Set:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=<secret from your runtime secret manager>
OPENAI_MODEL=<current supported model id>
```

Do not put provider keys into Git, Dockerfiles, images, or Kubernetes manifests. Use an external secret manager in production.

## Kubernetes

Create the secret out-of-band, then apply the manifests:

```bash
kubectl create namespace llm-api
kubectl -n llm-api create secret generic llm-api-secret \
  --from-literal=SERVICE_API_KEY='...' \
  --from-literal=OPENAI_API_KEY='...'
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service-hpa-pdb.yaml
kubectl apply -f k8s/networkpolicy.yaml
```

The example Secret manifest is documentation only and contains no usable credentials.

## Production hardening

- Replace in-memory rate limiting with a distributed limiter such as Redis-backed enforcement.
- Use a managed secret system such as Vault or a cloud secret manager instead of Kubernetes Secrets directly.
- Add an API gateway/WAF for global quotas, auth, and abuse controls.
- Add prompt/content safety controls appropriate to the application.
- Add provider-specific retry policy with bounded backoff for transient errors only.
- Track cost using the provider's current pricing outside the request path.
- Add request/response redaction and privacy retention policies.
- Use private networking where supported and restrict outbound access where practical.
- Pin production images by immutable digest after validating the digest in your registry.

## Validation

```bash
python -m unittest discover -s tests -v
```

Docker and live Kubernetes execution require those runtimes. GitHub Actions performs the container build and security scans.

## License

MIT
