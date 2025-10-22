"""
Example Prefect flow for deployment with work pools
"""

from prefect import flow, task
from datetime import datetime
import time


@task
def fetch_data(source: str):
    """Simulate fetching data from a source"""
    print(f"📥 Fetching data from {source}...")
    time.sleep(2)  # Simulate API call
    data = [f"{source}_item_{i}" for i in range(5)]
    print(f"✅ Fetched {len(data)} items from {source}")
    return data


@task
def process_data(data: list):
    """Process the fetched data"""
    print(f"⚙️  Processing {len(data)} items...")
    time.sleep(1)
    processed = [item.upper() for item in data]
    print(f"✅ Processed {len(processed)} items")
    return processed


@task
def save_results(data: list, destination: str):
    """Save processed data"""
    print(f"💾 Saving {len(data)} items to {destination}...")
    time.sleep(1)
    print(f"✅ Saved to {destination}")
    return f"Saved {len(data)} items"


@flow(name="data-pipeline", log_prints=True)
def data_pipeline(source: str = "api", destination: str = "database"):
    """
    A data pipeline flow that can be deployed and scheduled.

    This flow:
    1. Fetches data from a source
    2. Processes the data
    3. Saves results to a destination
    """
    print(f"🚀 Starting data pipeline at {datetime.now()}")
    print(f"   Source: {source}")
    print(f"   Destination: {destination}")

    # Execute tasks in sequence
    raw_data = fetch_data(source)
    processed_data = process_data(raw_data)
    result = save_results(processed_data, destination)

    print(f"🎉 Pipeline completed: {result}")
    return result


if __name__ == "__main__":
    # Run the flow locally for testing
    data_pipeline(source="test-api", destination="test-db")
