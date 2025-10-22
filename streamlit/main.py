import os
import asyncio
from datetime import datetime, timedelta, timezone
import pandas as pd
import streamlit as st
import requests

from prefect.client.orchestration import PrefectClient
from prefect.client.schemas.filters import FlowFilter


# --- Session-based authentication template ---
def get_authenticated_cookie(login_url, username, password):
    session = requests.Session()
    payload = {"username": username, "password": password}
    resp = session.post(login_url, data=payload)
    resp.raise_for_status()
    # Extract all cookies as a single string for the Cookie header
    cookies = session.cookies.get_dict()
    cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
    return cookie_str


async def get_recent_flows(limit=50, run_history=5, api_url=None, cookie=None):
    client = PrefectClient(
        api=api_url or "http://localhost:4200/api",
        httpx_settings={"headers": {"Cookie": cookie} if cookie else {}},
    )
    flows = await client.read_flows(limit=limit)
    data = []
    for f in flows:
        flow_runs = await client.read_flow_runs(
            flow_filter=FlowFilter(id={"any_": [str(f.id)]}),
            limit=run_history,
            sort="START_TIME_DESC",
        )
        run_states = [getattr(run.state, "name", None) for run in flow_runs]
        run_starts = [str(getattr(run, "start_time", None)) for run in flow_runs]
        data.append(
            {
                "Flow Name": f.name,
                "Flow ID": str(f.id),
                "Created": str(getattr(f, "created", "")),
                "Recent Run States": ", ".join([s for s in run_states if s]),
                "Recent Run Starts": ", ".join([s for s in run_starts if s]),
            }
        )
    return pd.DataFrame(data)


def main():
    st.title("Prefect Flows Overview (Authenticated)")
    login_url = st.text_input("Workbench Login URL", "https://your-workbench/login")
    api_url = st.text_input("Prefect API URL", "http://localhost:4200/api")
    # Get username and password from environment variables
    username = os.environ.get("WORKBENCH_USERNAME", "")
    password = os.environ.get("WORKBENCH_PASSWORD", "")
    limit = st.slider("Number of flows", 10, 200, 50)
    run_history = st.slider("Number of recent runs per flow", 1, 10, 5)
    st.caption("Auto-refreshes every 10 seconds.")
    st_autorefresh = getattr(st, "autorefresh", None)
    if st_autorefresh:
        st_autorefresh(interval=10_000, key="autorefresh")

    if st.button("Login & Fetch Flows"):
        with st.spinner("Authenticating and loading flows…"):
            try:
                if not username or not password:
                    st.error(
                        "WORKBENCH_USERNAME and WORKBENCH_PASSWORD environment variables must be set."
                    )
                    return
                cookie = get_authenticated_cookie(login_url, username, password)
                df = asyncio.run(get_recent_flows(limit, run_history, api_url, cookie))
                if df.empty:
                    st.info("No flows found.")
                else:
                    st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Error: {e}")


if __name__ == "__main__":
    main()
