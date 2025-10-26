#!/usr/bin/env python3
"""
Test script to verify Prefect server authentication.

Usage:
    # Development (no auth)
    export PREFECT_API_URL=http://localhost:4200/api
    python test_prefect_auth.py

    # Production (with auth)
    export PREFECT_API_URL=https://your-server.com/api
    export PREFECT_API_KEY=pnu_your_key_here
    python test_prefect_auth.py
"""

import asyncio
import os
from prefect.client.orchestration import get_client


async def test_connection():
    """Test connection and authentication to Prefect server."""

    api_url = os.getenv("PREFECT_API_URL", "http://localhost:4200/api")
    api_key = os.getenv("PREFECT_API_KEY")

    print("=" * 70)
    print("PREFECT AUTHENTICATION TEST")
    print("=" * 70)
    print(f"\n🔗 API URL: {api_url}")

    if api_key:
        print(f"🔐 API Key: {api_key[:8]}... (length: {len(api_key)})")
    else:
        print("⚠️  No API key (development mode)")

    print("\n" + "-" * 70)
    print("Testing connection...")
    print("-" * 70)

    # Set up authentication if API key is provided
    httpx_settings = {}
    if api_key:
        httpx_settings["headers"] = {"Authorization": f"Bearer {api_key}"}

    try:
        async with get_client(httpx_settings=httpx_settings) as client:
            # Test 1: Read flows
            print("\n1️⃣  Testing: Read flows...")
            flows = await client.read_flows(limit=5)
            print(f"   ✅ Success! Found {len(flows)} flows")
            if flows:
                for flow in flows[:3]:
                    print(f"      • {flow.name}")

            # Test 2: Read work pools
            print("\n2️⃣  Testing: Read work pools...")
            work_pools = await client.read_work_pools(limit=5)
            print(f"   ✅ Success! Found {len(work_pools)} work pools")
            if work_pools:
                for pool in work_pools[:3]:
                    print(f"      • {pool.name} (type: {pool.type})")

            # Test 3: Read concurrency limits
            print("\n3️⃣  Testing: Read concurrency limits...")
            limits = await client.read_concurrency_limits()
            print(f"   ✅ Success! Found {len(limits)} concurrency limits")
            if limits:
                for limit in limits:
                    print(
                        f"      • {limit.tag}: max {limit.concurrency_limit} concurrent"
                    )

            print("\n" + "=" * 70)
            print("✅ ALL TESTS PASSED!")
            print("=" * 70)
            print(
                """
Your Prefect connection is working correctly.

You can now:
  1. Run setup_concurrency_limit.py to configure limits
  2. Run streamlit/prefect_flow.py to start your flow
  3. Monitor at: {url}
""".format(
                    url=api_url.replace("/api", "")
                )
            )

            return True

    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ CONNECTION FAILED!")
        print("=" * 70)
        print(f"\nError: {e}")
        print("\nTroubleshooting:")

        if "Unauthorized" in str(e) or "401" in str(e):
            print("  • API key is invalid or expired")
            print("  • Generate a new API key from Prefect UI")
            print("  • Ensure PREFECT_API_KEY is set correctly")

        elif "Forbidden" in str(e) or "403" in str(e):
            print("  • API key lacks necessary permissions")
            print("  • Check API key permissions in Prefect UI")
            print("  • Contact your Prefect admin")

        elif "Connection" in str(e) or "refused" in str(e).lower():
            print("  • Cannot reach Prefect server")
            print("  • Check PREFECT_API_URL is correct")
            print("  • Verify server is running")
            print("  • Check network connectivity")

        else:
            print("  • Check your configuration")
            print("  • Verify PREFECT_API_URL and PREFECT_API_KEY")

        return False


def check_environment():
    """Check environment variables."""
    print("\n" + "=" * 70)
    print("ENVIRONMENT CHECK")
    print("=" * 70)

    api_url = os.getenv("PREFECT_API_URL")
    api_key = os.getenv("PREFECT_API_KEY")

    if not api_url:
        print("\n⚠️  PREFECT_API_URL not set!")
        print("   Using default: http://localhost:4200/api")
    else:
        print(f"\n✅ PREFECT_API_URL: {api_url}")

    if not api_key:
        print("⚠️  PREFECT_API_KEY not set (OK for local development)")
    else:
        print(f"✅ PREFECT_API_KEY: {api_key[:8]}... (set)")

    print("\nTo set environment variables:")
    print("  export PREFECT_API_URL=https://your-server.com/api")
    print("  export PREFECT_API_KEY=pnu_your_key_here")


async def main():
    """Main test function."""
    check_environment()

    print("\nPress Enter to continue with connection test...")
    input()

    success = await test_connection()

    if not success:
        exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test cancelled by user")
        exit(0)
