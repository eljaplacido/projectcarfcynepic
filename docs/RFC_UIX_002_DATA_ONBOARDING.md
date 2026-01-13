# RFC UIX-002: Data Onboarding (CSV Upload + Dataset Registry)

## Summary

Add a small dataset registry and CSV upload flow so users can run causal
analysis with their own data in the Streamlit cockpit. The backend stores
metadata + data files in a local registry and exposes lightweight APIs for
listing and previewing datasets.

## Motivation

- Provide a real "bring your data" path without dummy UI.
- Keep data ingestion synchronized with backend limits and context handling.
- Preserve traceability by recording dataset_id in request context.

## Scope

In scope:
- Dataset registry using SQLite + JSON files in `var/`.
- FastAPI endpoints for create/list/preview datasets.
- Streamlit UI for CSV upload, preview, and mapping.
- `/query` extension: accept dataset selection and map to causal_estimation.

Out of scope:
- External connectors (warehouses, APIs).
- Multi-tenant access controls.
- Large dataset ingestion (> 5000 rows).

## API Changes

New endpoints:
- `POST /datasets`
  - Body: name, description (optional), data
  - Returns dataset metadata and dataset_id.
- `GET /datasets`
  - Returns list of dataset metadata.
- `GET /datasets/{dataset_id}/preview?limit=10`
  - Returns preview rows.

Request extension:
- `/query` accepts `dataset_selection`:
```
{
  "dataset_id": "...",
  "treatment": "discount",
  "outcome": "churn",
  "covariates": ["region", "tenure"],
  "effect_modifiers": []
}
```
Backend converts this to `causal_estimation` with `data` and preserves
`dataset_selection` in `context` for traceability.

## Storage Model

- Metadata DB: `var/carf_datasets.db`
- Data files: `var/datasets/<dataset_id>.json`
- Index: `dataset_columns` table with index on `column_name`.

## UI Changes

Streamlit:
- Upload CSV -> preview -> store via `POST /datasets`.
- Select dataset -> map columns -> set dataset selection.
- Run analysis with dataset selection via `/query`.

## Testing

- Unit: dataset store create/list/load.
- Manual: upload CSV, map columns, run analysis.

## Rollout

- Backward compatible with existing `/query` payloads.
- Data stored locally in `var/` (ignored by git).
