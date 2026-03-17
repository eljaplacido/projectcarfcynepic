# Security Policy

Copyright (c) 2026 Cisuregen. All rights reserved.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.5.x   | :white_check_mark: |
| 0.4.x   | :white_check_mark: |
| < 0.4   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security
issue in CARF, please report it responsibly through the channels below.

### Contact

- **Email**: security@cisuregen.com
- **Response SLA**: Acknowledgment within 48 hours
- **Subject line**: `[CARF Security] <brief description>`

### What to Include

1. Description of the vulnerability
2. Steps to reproduce (proof of concept if possible)
3. Affected component(s) and version(s)
4. Potential impact assessment
5. Any suggested fixes (optional)

### What NOT to Do

- **Do NOT** create a public GitHub issue for security vulnerabilities
- **Do NOT** exploit the vulnerability beyond proof of concept
- **Do NOT** access or modify other users' data
- **Do NOT** perform denial-of-service testing on shared infrastructure

### Disclosure Timeline

| Phase | Timeline |
|-------|----------|
| Acknowledgment | Within 48 hours |
| Initial assessment | Within 7 business days |
| Fix development | Within 30 days (critical), 90 days (other) |
| Coordinated disclosure | After fix is released or 90 days, whichever first |

We follow coordinated disclosure practices and will credit reporters
in our security changelog unless anonymity is requested.

## Scope

The following components are in scope for security reports:

### In Scope

- **CARF backend** (`src/`): API endpoints, middleware, authentication
- **Guardian policy engine** (`src/workflows/guardian.py`): Policy bypass, escalation bypass
- **CSL policy service** (`src/services/csl_policy_service.py`): Rule evaluation, constraint bypass
- **Data handling** (`src/services/data_loader.py`, `src/api/routers/datasets.py`): Data exfiltration, injection
- **Causal/Bayesian engines** (`src/services/causal.py`, `src/services/bayesian.py`): Model poisoning, adversarial inputs
- **Authentication & authorization** (`src/api/middleware.py`): Auth bypass, privilege escalation
- **CYNEPIC Cockpit** (`carf-cockpit/src/`): XSS, CSRF, client-side injection
- **Configuration files** (`config/`): Policy tampering, unsafe defaults

### Out of Scope

- Third-party services (Neo4j, Kafka, OPA) — report to their maintainers
- LLM provider APIs (OpenAI, Anthropic, etc.) — report to the provider
- Demo/test data (`demo/data/`) — synthetic data, no real PII
- Development tooling (linters, test runners)

## Security Architecture

### API Access Controls

| Mode | Authentication | Rate Limiting | CORS |
|------|---------------|---------------|------|
| RESEARCH | None | Disabled | `*` (open) |
| STAGING | API Key (Bearer) | 300 req/min | `*` |
| PRODUCTION | API Key (Bearer) | 120 req/min | Restricted origins |

### Defense Layers

1. **Guardian Policy Engine**: All actions evaluated against safety policies before execution
2. **CSL-Core Verification**: Formal constraint verification with fail-closed safety
3. **Rate Limiting**: Per-IP sliding window in STAGING/PRODUCTION
4. **Input Validation**: Pydantic schema enforcement on all API inputs
5. **Audit Trail**: Optional Kafka-based decision logging

### Known Limitations

1. **RESEARCH mode** has no authentication — intended for local development only
2. **API key authentication** uses a single shared key, not per-user tokens
3. **No role-based access control** — all authenticated users have equal access
4. **Model artifacts** (`models/*.pkl`) are stored as Python pickles — deserialize only from trusted sources
5. **Uploaded datasets** are stored locally without encryption at rest

## Security Best Practices for Deployment

### Secrets Management

- Never commit API keys or credentials to version control
- Use `.env` files locally (gitignored) and secure secret management in production
- Rotate `CARF_API_KEY` regularly
- Set unique keys per environment (dev, staging, production)

```bash
# Required for STAGING/PRODUCTION
CARF_API_KEY=<strong-random-key>
CARF_CORS_ORIGINS=https://your-domain.com
```

### Network Security

- Run behind a reverse proxy (nginx, Traefik) in production
- Enable HTTPS/TLS for all connections
- Restrict CORS to your specific domain(s)
- Consider WAF (Web Application Firewall) for public deployments

### Data Security

- Do not upload sensitive personal data (PII) to shared instances
- Consider encryption at rest for datasets in production
- Implement access controls for multi-tenant deployments
- Audit data access through Kafka audit trail

### LLM Security

- CARF uses LLMs for routing and context assembly only
- Deterministic engines (causal, Bayesian) do not call LLMs
- Review LLM outputs before acting on high-stakes recommendations
- Monitor for prompt injection attempts in user queries
- Consider input sanitization for user-facing deployments

### Guardian Policy Security

- Review Guardian policies before deployment (`config/policies.yaml`)
- Use OPA (Open Policy Agent) for complex policy evaluation in production
- Enable Kafka audit trail for compliance tracking
- Implement human approval workflows for high-risk actions via HumanLayer

## Security Changelog

### v0.5.0 (2026-02-24)
- Added context-aware risk level checks in Guardian
- Added budget limit enforcement in proposed actions
- Added `budget_transfer`, `contract_sign`, `data_export`, `data_transfer`, `data_anonymize` to mandatory escalation list
- Improved financial risk scoring with critical severity detection
- Enhanced CORS middleware ordering for consistent header delivery
- Increased staging rate limit to 300 req/min to prevent false 429s

### v0.4.0 (2026-02-19)
- Added deployment profile system (RESEARCH / STAGING / PRODUCTION)
- Added API key authentication middleware
- Added rate limiting middleware
- Added CSL-Core formal policy verification
- Added federated governance policy service

### v0.1.0 (2026-01-15)
- Initial security documentation
- Environment variable pattern for secrets
- Gitignore patterns for sensitive files

---

## Inadvertent Disclosure

If you discover what appears to be proprietary information
(trained model weights, calibration data, production threshold
values, internal scoring matrices) that has been inadvertently
committed to this repository, please report it to
security@cisuregen.com rather than discussing it publicly.

Cisuregen treats certain implementation details as trade secrets
under EU Directive 2016/943. Responsible reporting of inadvertent
disclosures is appreciated and will be acknowledged.

---

Thank you for helping keep CARF secure.
