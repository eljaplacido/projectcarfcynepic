# Third-Party License Summary

CARF - Complex-Adaptive Reasoning Fabric
Copyright (c) 2026 Cisuregen

This document lists all direct third-party dependencies used by CARF,
grouped by license type. All dependencies use permissive open-source
licenses compatible with CARF's BSL 1.1 license and its eventual
Apache 2.0 conversion.

## License Compatibility Statement

CARF's dependency stack is **100% permissive** (MIT, Apache 2.0,
BSD-3-Clause, ISC). There are **no copyleft (GPL/AGPL) dependencies**
in the direct dependency tree. This ensures clean license compatibility
for the BSL 1.1 → Apache 2.0 transition on February 19, 2030.

---

## MIT License Dependencies

| Package | Version | Description |
|---------|---------|-------------|
| langgraph | >=0.2.0 | Agent orchestration framework |
| langchain | >=0.3.0 | LLM application framework |
| langchain-openai | >=0.2.0 | OpenAI provider for LangChain |
| langchain-anthropic | >=0.3.0 | Anthropic provider for LangChain |
| pydantic | >=2.5.0 | Data validation and settings |
| pydantic-settings | >=2.1.0 | Settings management |
| fastapi | >=0.109.0 | Web API framework |
| dowhy | >=0.11.0 | Causal inference library |
| econml | >=0.15.0 | Heterogeneous treatment effects |
| pyyaml | >=6.0 | YAML parser |
| sqlalchemy | >=2.0.0 | SQL toolkit and ORM |
| langsmith | >=0.1.0 | LLM observability |
| deepeval | >=1.0.0 | LLM evaluation framework |
| z3-solver | >=4.12.0 | SMT solver for formal verification |
| openpyxl | >=3.1.0 | Excel file parser |
| humanlayer | >=0.6.0 | Human-in-the-loop framework |
| react | ^18.3.1 | UI component library |
| react-dom | ^18.3.1 | React DOM renderer |
| reactflow | ^11.11.4 | Node-based graph UI |
| recharts | ^3.6.0 | Charting library |
| plotly.js | ^3.3.1 | Interactive plotting |
| react-plotly.js | ^2.6.0 | React bindings for Plotly |
| react-markdown | ^10.1.0 | Markdown renderer |
| remark-gfm | ^4.0.1 | GitHub Flavored Markdown |
| tailwindcss | ^3.4.17 | Utility-first CSS framework |
| vite | ^5.4.11 | Frontend build tool |

## Apache License 2.0 Dependencies

| Package | Version | Description |
|---------|---------|-------------|
| causal-learn | >=0.1.3 | Causal discovery algorithms |
| pymc | >=5.10.0 | Bayesian statistical modeling |
| arviz | >=0.17.0 | Bayesian visualization |
| neo4j | >=5.15.0 | Neo4j graph database driver |
| confluent-kafka | >=2.3.0 | Apache Kafka client |
| transformers | >=4.41.0 | NLP model hub |
| accelerate | >=0.27.0 | Training acceleration |
| datasets | >=2.19.0 | Dataset loading utilities |
| sentence-transformers | >=2.2.0 | Sentence embeddings |
| tenacity | >=8.2.0 | Retry library |
| opentelemetry-api | >=1.22.0 | Distributed tracing API |
| opentelemetry-sdk | >=1.22.0 | Distributed tracing SDK |
| langchain-google-genai | >=2.0.0 | Google AI provider |

## BSD-3-Clause License Dependencies

| Package | Version | Description |
|---------|---------|-------------|
| pandas | >=2.0.0 | Data analysis library |
| torch | >=2.1.0 | Deep learning framework |
| scikit-learn | >=1.4.0 | Machine learning library |
| uvicorn | >=0.27.0 | ASGI server |
| redis | >=5.0.0 | Redis client |
| pypdf | >=4.0.0 | PDF parser |
| python-dotenv | >=1.0.0 | Environment variable loader |

## ISC License Dependencies

| Package | Version | Description |
|---------|---------|-------------|
| lucide-react | ^0.563.0 | Icon library |

## Runtime Service Dependencies (Not Linked)

These are used as external services via network protocols and are NOT
distributed as part of CARF. Listed for completeness only.

| Service | License | Usage |
|---------|---------|-------|
| Neo4j Community | GPL v3 (FOSS Exception) | Graph database (network service) |
| Apache Kafka | Apache 2.0 | Event streaming (network service) |
| Open Policy Agent | Apache 2.0 | Policy evaluation (network service) |

---

## Full License Texts

The full text of each license type referenced above:

- **MIT License**: https://opensource.org/licenses/MIT
- **Apache License 2.0**: https://www.apache.org/licenses/LICENSE-2.0
- **BSD-3-Clause License**: https://opensource.org/licenses/BSD-3-Clause
- **ISC License**: https://opensource.org/licenses/ISC

For the complete license text of any specific dependency, consult its
upstream repository linked in the NOTICE file.
