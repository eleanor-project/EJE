# ELEANOR Moral Ops Center

This directory packages a lightweight operations layer that wraps the core EJE adjudication pipeline with a FastAPI service, a SQLite-backed escalation log, and a Streamlit dashboard.

## Components
- `eje/api/app.py` – FastAPI application factory with CORS + bearer-token hooks
- `eje/api/endpoints.py` – `/evaluate`, `/escalate`, and `/health` routes
- `eje/api/models.py` – Pydantic request/response schemas
- `eje/config/settings.py` – Feature toggles and environment-driven settings
- `eje/db/escalation_log.py` – SQLite storage for precedents and manual escalations
- `eje/learning/context_model.py` – Adaptive critic weighting based on dissent history
- `eje/dashboard/app.py` – Streamlit dashboard for visibility and exports

## Quickstart
1. Install dependencies (from repo root):
   ```bash
   pip install -r requirements.txt
   ```
2. Launch the API:
   ```bash
   uvicorn eje.api.app:create_app --factory --reload
   ```
3. Launch the dashboard in a separate terminal:
   ```bash
   streamlit run src/eje/dashboard/app.py
   ```

Environment variables prefixed with `EJE_` (e.g., `EJE_API_TOKEN`, `EJE_DB_PATH`, `EJE_ALLOWED_ORIGINS`) override defaults in `eje/config/settings.py`.
