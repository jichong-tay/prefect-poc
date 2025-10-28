<!-- .github/copilot-instructions.md
     Purpose: Give AI coding agents focused, actionable context about this repo so
     they can be productive without asking for basics. Keep this file short and
     concrete: reference real files, commands, patterns, and integration points.
-->

# Copilot instructions for prefect-poc

Scope

- This repository is a proof-of-concept demonstrating Prefect 2.13.7 orchestration with distributed workflow execution using work pools and workers.
- Primary components:
  - `streamlit/` — Streamlit app for authenticated Prefect flow inspection (`main.py`, `rest_api_app.py`, `playground.ipynb`).
  - `flows/` — Prefect flow definitions:
    - `prefect_flow.py` — Task-based parallel execution (simpler approach)
    - `prefect_flow-worker-flow.py` — Distributed subflow execution via work pools (production approach)
    - `prefect_flow-simple-subflows.py` — Alternative simple pattern (no deployment/workers needed)
  - `scripts/` — Utility scripts for setup, worker management, and testing.
  - `docs/` — Documentation for authentication, concurrency, and distributed workflows.
  - `pyproject.toml` — Declares runtime Python >=3.10 and dependencies (prefect==2.13.7, streamlit, httpx, griffe).

Big picture and why

- Demonstrates production-ready patterns for private/self-hosted Prefect 2.13.7 workflows including:
  - **Distributed subflow execution** using work pools and workers for horizontal scaling
  - Server-side concurrency control using task tags and work pool limits
  - Authentication support for both dev (local, no auth) and prod (private server with API keys)
  - Proper async flow patterns with `run_deployment()` for triggering subflows
  - Worker management for distributed execution across multiple processes/machines
- The repo shows TWO approaches:
  1. Task-based concurrency (simpler, single flow run)
  2. Distributed subflows (production, multiple flow runs across workers)
- All patterns target self-hosted Prefect servers, not Prefect Cloud.
- **Key Pattern (Prefect 2.13.7)**: Use `await run_deployment()` to trigger subflows, NOT `flow.submit()` (which doesn't exist)

Key files to read first (in-order)

1. `docs/flow_execution_patterns.md` — **START HERE**: Comparison of all execution patterns (`run_deployment()` vs direct calls vs tasks).
2. `flows/prefect_flow-worker-flow.py` — **Production**: Distributed ETL using work pools, workers, and `run_deployment()` for subflows.
3. `flows/prefect_flow-simple-subflows.py` — **Development**: Simple alternative without deployment/workers (direct task execution).
4. `flows/prefect_flow.py` — **Simple**: Task-based parallel execution with server-side concurrency control via tags.
5. `docs/prefect_2.13.7_patterns.md` — **CRITICAL**: Explains `run_deployment()` vs `flow.submit()` patterns.
6. `docs/distributed_workflow_guide.md` — Complete guide to distributed workflows with work pools.
7. `docs/QUICKSTART_DISTRIBUTED.md` — 5-minute quick start for distributed flows.
8. `scripts/setup_prefect_server.py` — Server setup with work pools and concurrency limits.
9. `scripts/start_workers.py` — Manages multiple Prefect workers for distributed execution.
10. `streamlit/main.py` — Streamlit UI with authentication flow (cookie-based auth with PrefectClient).
11. `docs/authentication_guide.md` — Complete guide to dev/prod authentication.

Developer workflows and commands

- Use Makefile for common operations:

  ```bash
  make help                 # Show all available commands
  make setup                # Install dependencies
  make prefect-server       # Start Prefect server (first time)
  make prefect-start        # Start existing server
  make prefect-stop         # Stop server
  make prefect-logs         # View logs
  make prefect-setup        # Complete server setup (work pools + concurrency)
  make setup-concurrency    # Configure concurrency limits
  make test-auth           # Test authentication

  # Distributed workflows (production approach)
  make deploy-flows        # Deploy flows to work pool
  make start-workers       # Start 3 workers
  make start-workers N=5   # Start 5 workers
  make run-distributed     # Run distributed ETL flow

  # Simple workflows (development/testing)
  make run-flow            # Run task-based flow
  make run-ui              # Start Streamlit UI
  ```

- Or use Docker commands directly:

  ```bash
  docker run -d -p 4200:4200 --name prefect-server prefecthq/prefect:2.13.7-python3.10 prefect server start --host 0.0.0.0
  ```

  - Access UI: http://localhost:4200
  - API endpoint: http://localhost:4200/api
  - Stop server: `docker stop prefect-server`
  - View logs: `docker logs prefect-server`
  - Restart: `docker start prefect-server`
  - Remove container: `docker rm -f prefect-server`

- Setup server-side concurrency limits:

  ```bash
  make setup-concurrency
  # Or manually:
  export PREFECT_API_URL=http://localhost:4200/api
  python scripts/setup_concurrency_limit.py
  ```

- Run flows:

  ```bash
  make run-flow
  # Or manually:
  python flows/prefect_flow.py
  ```

- Test authentication (for production with private server):

  ```bash
  make test-auth
  # Or manually:
  export PREFECT_API_URL=https://your-private-server.com/api
  export PREFECT_API_KEY=pnu_your_key
  python scripts/test_prefect_auth.py
  ```

- Run Streamlit app:
  ```bash
  make run-ui
  # Or manually:
  streamlit run streamlit/main.py
  ```

Project-specific conventions and patterns

- Environment: This project targets **self-hosted/private Prefect servers only**, not Prefect Cloud.
- Auth: The Streamlit UI uses session-based login to produce a Cookie header string, then passes it into `PrefectClient(..., httpx_settings={"headers": {"Cookie": cookie}})`.
  - When editing or adding new Prefect calls, preserve this cookie->httpx header pattern when authentication is required.
  - In production, the private Prefect server requires API key authentication via `PREFECT_API_KEY` environment variable.
- Prefect usage: The code uses `await client.read_flows()` and `await client.read_flow_runs(...)` inside asyncio contexts. Maintain async usage and wrap with `asyncio.run(...)` where needed in sync code (as shown in `streamlit/main.py`).
- Data frames: Flow/run query results are converted to a pandas DataFrame for Streamlit display. Keep returned data shapes tabular-friendly.
- **Distributed Flows (Prefect 2.13.7)**:
  - Use `await run_deployment()` to trigger subflows, NOT `flow.submit()` (doesn't exist)
  - Orchestrator flow must be `async` when using `run_deployment()`
  - Use `wait_for_flow_runs()` helper to poll for completion
  - Subflows must be deployed before they can be triggered
  - Workers must be running to execute subflows

Integration points & external dependencies

- Private Prefect Server API (dev: `http://localhost:4200/api`, prod: private server URL) — calls require authentication via workbench session cookies or API keys.
- The Streamlit app assumes a login endpoint that returns auth cookies for the private Prefect server.
- External services to mock or stub in tests: the login endpoint (POST form username/password -> cookies) and Prefect API endpoints (`/api/flows`, `/api/flow_runs`).

Examples of useful edits an AI agent can make

- Add a helper in `streamlit/_auth.py` to centralize login and cookie creation; update `main.py` to import and use it.
- Replace hard-coded defaults with `streamlit.secrets` or environment lookup for `WORKBENCH_USERNAME`/`WORKBENCH_PASSWORD` and `PREFECT_API_URL`.
- Add a small test that mocks `requests.Session.post` and `PrefectClient.read_flows` to validate `get_authenticated_cookie` and `get_recent_flows` return DataFrame columns.
- Create new distributed flows following the `prefect_flow-worker-flow.py` pattern using `await run_deployment()` for subflow triggering.
- Add worker management scripts or systemd service files for production deployment.

What not to change without approval

- Don't swap synchronous Prefect client patterns for entirely different orchestration client libraries.
- Don't remove the cookie-in-header pattern — it reflects a real integration constraint: the private Prefect server sits behind a workbench requiring session cookies.
- Don't add Prefect Cloud specific features or dependencies — this project targets self-hosted servers only.
- **Don't use `flow.submit()` for subflows** — it doesn't exist in Prefect 2.13.7. Always use `await run_deployment()` instead.

Where to look for more context

- `README.md` (top-level) contains setup snippets used during development; follow its examples for running a Prefect server container.
- `docs/prefect_2.13.7_patterns.md` — Critical reference for correct Prefect 2.13.7 patterns (run_deployment, async flows, etc.)
- `docs/distributed_workflow_guide.md` — Complete guide to work pools, workers, and distributed execution.
- `docs/QUICKSTART_DISTRIBUTED.md` — 5-minute quick start guide for distributed flows.

If anything in this file is unclear or you want more examples (tests, refactors, or CI integration), ask and I will update this file.

```

```
