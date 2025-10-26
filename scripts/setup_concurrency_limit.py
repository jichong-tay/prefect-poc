#!/usr/bin/env python3
"""
Setup script to configure Prefect server-side concurrency limits.

This creates a concurrency limit that restricts how many tasks with the
"database" tag can run simultaneously.

Usage:
    python setup_concurrency_limit.py
"""

import asyncio
import os
from prefect.client.orchestration import get_client
from prefect.settings import PREFECT_API_KEY


async def create_concurrency_limit(limit_name: str, max_concurrent: int, api_key: str = None):
    """
    Create a concurrency limit on the Prefect server.
    
    Args:
        limit_name: Name for the concurrency limit (e.g., "database")
        max_concurrent: Maximum number of concurrent tasks (e.g., 3)
        api_key: Optional API key for authentication (production)
    """
    # Set up httpx settings with auth headers if API key provided
    httpx_settings = {}
    if api_key:
        httpx_settings["headers"] = {"Authorization": f"Bearer {api_key}"}
    
    async with get_client(httpx_settings=httpx_settings) as client:
        try:
            # Create the concurrency limit
            await client.create_concurrency_limit(
                tag=limit_name,
                concurrency_limit=max_concurrent
            )
            print(f"✅ Created concurrency limit: '{limit_name}' = {max_concurrent}")
            print(f"   Tasks tagged with '{limit_name}' will be limited to {max_concurrent} concurrent runs")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"⚠️  Concurrency limit '{limit_name}' already exists")
                print(f"   To update it, delete the old one first via the UI or API")
            else:
                print(f"❌ Error creating concurrency limit: {e}")
                raise


async def list_concurrency_limits(api_key: str = None):
    """
    List all existing concurrency limits.
    
    Args:
        api_key: Optional API key for authentication (production)
    """
    # Set up httpx settings with auth headers if API key provided
    httpx_settings = {}
    if api_key:
        httpx_settings["headers"] = {"Authorization": f"Bearer {api_key}"}
    
    async with get_client(httpx_settings=httpx_settings) as client:
        try:
            limits = await client.read_concurrency_limits()
            if limits:
                print(f"\n📋 Existing Concurrency Limits:")
                for limit in limits:
                    print(f"   • {limit.tag}: max {limit.concurrency_limit} concurrent tasks")
            else:
                print("\n📋 No concurrency limits configured yet")
        except Exception as e:
            print(f"❌ Error reading concurrency limits: {e}")


async def main():
    """Main setup function."""
    print("=" * 70)
    print("PREFECT CONCURRENCY LIMIT SETUP")
    print("=" * 70)
    
    # Check Prefect server connection
    prefect_api_url = os.getenv("PREFECT_API_URL", "http://localhost:4200/api")
    prefect_api_key = os.getenv("PREFECT_API_KEY")
    
    print(f"\n🔗 Connecting to Prefect server: {prefect_api_url}")
    
    if prefect_api_key:
        print(f"🔐 Using API Key: {prefect_api_key[:8]}...")
    else:
        print("⚠️  No API key found (OK for development)")
        print("   For production, set PREFECT_API_KEY environment variable")
    
    # List existing limits
    await list_concurrency_limits(api_key=prefect_api_key)
    
    # Create concurrency limit for database tasks
    print("\n📝 Creating new concurrency limit...")
    await create_concurrency_limit(
        limit_name="database",
        max_concurrent=3,  # Only 3 database queries at a time
        api_key=prefect_api_key
    )
    
    # Show updated list
    await list_concurrency_limits(api_key=prefect_api_key)
    
    print("\n" + "=" * 70)
    print("✅ SETUP COMPLETE!")
    print("=" * 70)
    print("""
Your Prefect server is now configured to limit database tasks.

How it works:
  1. Tasks tagged with "database" will respect the limit
  2. Only 3 will run at a time
  3. Others will queue and wait their turn
  4. The server handles this automatically!

Your sql_query task is already tagged:
  @task(tags=["database"], ...)

Run your flow and watch the Prefect UI to see it in action!

For production with authentication:
  export PREFECT_API_URL=https://your-prefect-server.com/api
  export PREFECT_API_KEY=your_api_key_here
  python setup_concurrency_limit.py
""")


if __name__ == "__main__":
    asyncio.run(main())
