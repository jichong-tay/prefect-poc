import os
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timezone


def get_authenticated_session(login_url, username, password):
    session = requests.Session()
    payload = {"username": username, "password": password}
    resp = session.post(login_url, data=payload)
    resp.raise_for_status()
    return session


def fetch_flows(api_url, session):
    resp = session.post(f"{api_url}/flows/filter", json={})
    resp.raise_for_status()
    return resp.json()


def fetch_flow_runs(api_url, session, flow_id, limit=5):
    body = {
        "flow_runs": {"flow_id": {"any_": [flow_id]}},
        "limit": limit,
        "sort": "START_TIME_DESC",
    }
    resp = session.post(f"{api_url}/flow_runs/filter", json=body)
    resp.raise_for_status()
    return resp.json()


def main():
    st.title("Prefect Flows Overview (REST API)")
    login_url = st.text_input("Workbench Login URL", "https://your-workbench/login")
    api_url = st.text_input("Prefect API URL", "http://localhost:4200/api")
    username = os.environ.get("WORKBENCH_USERNAME", "")
    password = os.environ.get("WORKBENCH_PASSWORD", "")
    limit = st.slider("Number of flows", 10, 200, 50)
    run_history = st.slider("Number of recent runs per flow", 1, 10, 5)

    with st.spinner("Authenticating and loading flows…"):
        try:
            if not username or not password:
                st.error(
                    "WORKBENCH_USERNAME and WORKBENCH_PASSWORD environment variables must be set."
                )
                return
            session = get_authenticated_session(login_url, username, password)
            flows = fetch_flows(api_url, session)

            def state_badge(name: str) -> str:
                color_map = {
                    "Completed": "#4BB543",  # green
                    "Running": "#007bff",  # blue
                    "Failed": "#d9534f",  # red
                    "Cancelled": "#f0ad4e",  # orange
                    "Pending": "#6c757d",  # gray
                }
                color = color_map.get(name, "#6c757d")
                return f'<span style="background-color:{color};color:white;padding:2px 8px;border-radius:8px;">{name}</span>'

            for f in flows:
                flow_id = f.get("id")
                flow_name = f.get("name")
                created = str(f.get("created", ""))
                flow_runs = fetch_flow_runs(api_url, session, flow_id, run_history)
                with st.expander(f"Flow: {flow_name}"):
                    st.markdown(f"**Flow ID:** {flow_id}")
                    st.markdown(f"**Created:** {created}")
                    if not flow_runs:
                        st.info("No recent runs found.")
                    else:
                        run_table = []
                        for run in flow_runs:
                            state = run.get("state", {})
                            name = state.get("name", "")
                            timestamp_raw = state.get(
                                "timestamp", run.get("start_time", "")
                            )
                            try:
                                dt = datetime.fromisoformat(
                                    timestamp_raw.replace("+00.00", "+00:00")
                                )
                                # Convert to local timezone
                                if dt.tzinfo is None:
                                    dt = dt.replace(tzinfo=timezone.utc)
                                local_dt = dt.astimezone()
                                timestamp_fmt = local_dt.strftime("%d-%m-%Y %H:%M:%S")
                            except Exception:
                                timestamp_fmt = timestamp_raw
                            message = state.get("message", "")
                            run_table.append(
                                {
                                    "State": state_badge(name),
                                    "Timestamp": timestamp_fmt,
                                    "Message": message,
                                }
                            )
                        df_table = pd.DataFrame(run_table)

                        def render_table(df):
                            cols = df.columns.tolist()
                            html = (
                                "<table style='width:100%;border-collapse:collapse;'>"
                            )
                            html += (
                                "<tr>"
                                + "".join(
                                    [
                                        f"<th style='border-bottom:1px solid #ddd;padding:6px;text-align:left'>{col}</th>"
                                        for col in cols
                                    ]
                                )
                                + "</tr>"
                            )
                            for _, row in df.iterrows():
                                html += (
                                    "<tr>"
                                    + "".join(
                                        [
                                            f"<td style='padding:6px;border-bottom:1px solid #eee'>{row[col] if col != 'State' else row[col]}</td>"
                                            for col in cols
                                        ]
                                    )
                                    + "</tr>"
                                )
                            html += "</table>"
                            st.markdown(html, unsafe_allow_html=True)

                        render_table(df_table)
        except Exception as e:
            st.error(f"Error: {e}")


if __name__ == "__main__":
    main()
