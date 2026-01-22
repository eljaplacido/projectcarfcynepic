# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.x.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

1. **Do NOT** create a public GitHub issue for security vulnerabilities
2. Send an email to the project maintainers with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Any suggested fixes (optional)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt within 48 hours
- **Initial Assessment**: Within 7 days, we will provide an initial assessment
- **Resolution Timeline**: Critical vulnerabilities will be addressed within 30 days
- **Disclosure**: We follow coordinated disclosure practices

## Security Best Practices for Deployment

### API Keys and Secrets

- Never commit API keys to version control
- Use environment variables for all secrets
- Rotate API keys regularly
- Use `.env` files locally (gitignored) and secure secret management in production

```bash
# Required environment variables
DEEPSEEK_API_KEY=sk-...        # Or OPENAI_API_KEY
NEO4J_URI=bolt://localhost:7687  # Optional
NEO4J_USER=neo4j                 # Optional
NEO4J_PASSWORD=...               # Optional
```

### Network Security

- Run behind a reverse proxy (nginx, Traefik) in production
- Enable HTTPS/TLS for all connections
- Configure CORS appropriately for your domain
- Consider rate limiting for public deployments

### Data Security

- Do not upload sensitive personal data (PII) to demo instances
- The dataset registry stores files locally in `var/datasets/`
- Consider encryption at rest for sensitive datasets
- Implement access controls for multi-tenant deployments

### LLM Security

- CARF uses LLMs for routing and context assembly only
- Deterministic engines (causal, Bayesian) do not use LLMs
- Review LLM outputs before acting on recommendations
- Monitor for prompt injection attempts in user queries

### Authentication (Production)

For production deployments, implement:

1. **API Authentication**: Add API key or OAuth2 middleware
2. **User Management**: Integrate with your identity provider
3. **Audit Logging**: Enable Kafka audit trail for compliance

Example FastAPI middleware:
```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != os.getenv("CARF_API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API Key")
```

### Guardian Policy Security

- Review Guardian policies before deployment (`config/policies/`)
- Use OPA (Open Policy Agent) for complex policy evaluation
- Log all policy decisions for audit trail
- Implement human approval workflows for high-risk actions

## Known Security Considerations

1. **Test Mode**: `CARF_TEST_MODE=1` disables LLM calls but should NOT be used in production
2. **SQLite**: Default dataset store is SQLite; consider PostgreSQL for production
3. **No Default Auth**: API endpoints are unauthenticated by default
4. **Local File Storage**: Uploaded datasets are stored locally without encryption

## Security Changelog

### v0.1.0 (2026-01-15)
- Initial security documentation
- Environment variable pattern for secrets
- Gitignore patterns for sensitive files

---

Thank you for helping keep CARF secure!
