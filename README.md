

## Project Context
This project uses Streamlit to build an app (`/streamlit/main.py`) that leverages the Prefect SDK for monitoring Prefect flows via a client object. Direct access to the Prefect server is unavailable, so all API interactions require authentication through a dedicated auth service. The Prefect Server sits on an Anaconda Enterprise environment, and requires a login using username and password to obtain a session.de 

The prefect script is `prefect-main.py` 

### Tech Stack
- Python
- Streamlit
- Prefect 2.13



## Setup Instructions

1. **Install Prefect and Griffe using [uv](https://github.com/astral-sh/uv):**
	```bash
	uv add -U prefect==2.13 griffe==0.49.0
	```

2. **Start Prefect server in Docker:**
	```bash
	docker run -d -p 4200:4200 prefecthq/prefect:2.13.8-python3.10 -- prefect server start --host 0.0.0.0
	```
	This launches the Prefect orchestration server on port 4200.

3. **Use PrefectClient directly in your scripts:**
	Instead of setting the `PREFECT_API_URL` environment variable, instantiate `PrefectClient` with the API URL:
	```python
	from prefect.client.orchestration import PrefectClient
	client = PrefectClient(api="http://localhost:4200/api")
	# ... use client (await client.method()) ...
	```

4. **Run your Prefect flow script locally:**
	```bash
	uv run python prefect-main.py
	```
	This executes your flow and registers/runs it against the Prefect server.