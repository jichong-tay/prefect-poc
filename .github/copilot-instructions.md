<!-- .github/copilot-instructions.md
     Purpose: Give AI coding agents focused, actionable context about this repo so
     they can be productive without asking for basics. Keep this file short and
     concrete: reference real files, commands, patterns, and integration points.
-->

# Copilot instructions for prefect-poc

Scope

- This repository is a small proof-of-concept connecting Streamlit UI with Prefect orchestration.
- Primary components:
  - `streamlit/` — Streamlit app for authenticated Prefect flow inspection (`main.py`, `rest_api_app.py`).
  - `prefect-main.py` — Example Prefect flow and tasks used for local runs/registration.
  - `pyproject.toml` — Declares runtime Python >=3.13 and dependencies (prefect, streamlit, griffe).

Big picture and why

- The Streamlit app queries a Prefect Orchestration API that is usually behind an auth workbench.
  Instead of relying on env-only auth, the app demonstrates session-based cookie auth with a login form
  and then constructs a `PrefectClient` with custom http headers (Cookie) to read flows and flow runs.
- The repo favors runtime instantiation over environment-only configuration: see `streamlit/main.py` where
  `PrefectClient(api=...)` is created directly instead of only reading `PREFECT_API_URL`.

Key files to read first (in-order)

1. `streamlit/main.py` — shows authentication flow (requests.Session -> cookie header), uses
   `prefect.client.orchestration.PrefectClient` and `prefect.client.schemas.filters.FlowFilter` to query flows.
2. `prefect-main.py` — minimal sample Prefect flow/tasks used for local experimentation.
3. `pyproject.toml` — dependency and Python version pinning to match runtime expectations.

Developer workflows and commands

- Start Prefect server (2.13.7) with Docker:
  ```bash
  docker run -d -p 4200:4200 --name prefect-server prefecthq/prefect:2.13.7-python3.10 prefect server start --host 0.0.0.0
  ```
  - Access UI: http://localhost:4200
  - API endpoint: http://localhost:4200/api
  - Stop server: `docker stop prefect-server`
  - View logs: `docker logs prefect-server`
  - Restart: `docker start prefect-server`
  - Remove container: `docker rm -f prefect-server`
- Run Streamlit app locally from repo root:
  - Ensure Python >=3.13 and dependencies installed (see `pyproject.toml`).
  - Start: `streamlit run streamlit/main.py`
- Run the example Prefect flow locally (no server required for local execution):
  - `python prefect-main.py`
  - To run against the Docker server, ensure PREFECT_API_URL is set or use `PrefectClient(api="http://localhost:4200/api")` in code.

Project-specific conventions and patterns

- Auth: The Streamlit UI uses session-based login to produce a Cookie header string, then passes it into `PrefectClient(..., httpx_settings={"headers": {"Cookie": cookie}})`.
  - When editing or adding new Prefect calls, preserve this cookie->httpx header pattern when authentication is required.
- Prefect usage: The code uses `await client.read_flows()` and `await client.read_flow_runs(...)` inside asyncio contexts. Maintain async usage and wrap with `asyncio.run(...)` where needed in sync code (as shown in `streamlit/main.py`).
- Data frames: Flow/run query results are converted to a pandas DataFrame for Streamlit display. Keep returned data shapes tabular-friendly.

Integration points & external dependencies

- Prefect Orchestration API (default `http://localhost:4200/api` in code examples) — calls require authentication via the workbench. The app assumes a login endpoint that returns auth cookies.
- External services to mock or stub in tests: the login endpoint (POST form username/password -> cookies) and Prefect API endpoints (`/api/flows`, `/api/flow_runs`).

Examples of useful edits an AI agent can make

- Add a helper in `streamlit/_auth.py` to centralize login and cookie creation; update `main.py` to import and use it.
- Replace hard-coded defaults with `streamlit.secrets` or environment lookup for `WORKBENCH_USERNAME`/`WORKBENCH_PASSWORD` and `PREFECT_API_URL`.
- Add a small test that mocks `requests.Session.post` and `PrefectClient.read_flows` to validate `get_authenticated_cookie` and `get_recent_flows` return DataFrame columns.

What not to change without approval

- Don’t swap synchronous Prefect client patterns for entirely different orchestration client libraries.
- Don’t remove the cookie-in-header pattern — it reflects a real integration constraint: the Prefect server sits behind a workbench requiring session cookies.

Where to look for more context

- `README.md` (top-level) contains setup snippets used during development; follow its examples for running a Prefect server container.

If anything in this file is unclear or you want more examples (tests, refactors, or CI integration), ask and I will update this file.
