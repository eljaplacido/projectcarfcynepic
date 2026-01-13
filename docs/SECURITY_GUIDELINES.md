# Security Guidelines (Demo to GitHub Release)

This project is a research demo. It is not production-hardened. Use this document
to assess risk, close gaps, and set expectations before publishing or deploying.

## Scope and Maturity
- No authentication or authorization is implemented for the API endpoints.
- External integrations (LLM, Neo4j, Kafka, OPA, HumanLayer) are optional and
  configured by environment variables.
- Default settings are optimized for local demos, not for public exposure.

## Data Handling
- Do not upload sensitive or regulated data in demo mode.
- Treat all LLM prompts as external data sharing; scrub PII before use.
- Use dataset registry only for small, non-sensitive demo datasets.

## Secrets and Configuration
- Store secrets in environment variables or a local `.env` file (not committed).
- Rotate keys before publishing the repository or sharing logs.
- Ensure `CARF_TEST_MODE` is unset in real runs to avoid stubbed LLM responses.

## API and Network Controls
- Bind API and Streamlit to localhost or a private network by default.
- Add authentication (API key, OAuth, or reverse proxy auth) before public use.
- Add request size limits and rate limiting at the proxy or app level.
- Configure CORS explicitly if the API is accessed from a browser.

## External Services
- Neo4j: change default credentials and enable TLS where possible.
- Kafka: enable TLS/SASL for any non-local deployment.
- OPA: use HTTPS and validate the policy endpoint with timeouts.
- HumanLayer: require explicit approval flows; avoid mock auto-approval in prod.

## LLM Safety and Validation
- Treat LLM outputs as untrusted; validate JSON strictly and bound field sizes.
- Avoid executing any LLM-provided paths or commands.
- Log only minimal summaries of prompts and responses.

## Logging and Audit
- Minimize logging of raw queries or dataset payloads.
- If Kafka audit is enabled, assume logs are permanent and access-controlled.
- Consider redaction of session identifiers and user inputs in shared logs.

## Release Readiness Checklist
- Add API authentication and authorization.
- Restrict local file access (block arbitrary `csv_path` reads).
- Enforce request size and payload limits on all endpoints.
- Remove or guard mock auto-approval paths.
- Provide a root-level `SECURITY.md` policy for responsible disclosure.
- Add a `LICENSE` file and verify dependency licenses.
- Document supported deployment modes and threat model assumptions.
