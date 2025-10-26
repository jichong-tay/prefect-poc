#!/usr/bin/env python3
"""
Prefect server configuration script.

This script configures a Prefect server environment:
1. Connects to running Prefect server (or starts one if configured)
2. Creates work pools
3. Sets up concurrency limits
4. Verifies the configuration

Server Management:
- By default, connects to existing server (must be running)
- Set PREFECT_START_SERVER=native to auto-start a native server
- Docker servers must be started manually (make prefect-server)

Usage:
    # Configure existing local server
    export PREFECT_API_URL=http://localhost:4200/api
    python scripts/setup_prefect_server.py

    # Auto-start native server and configure
    export PREFECT_API_URL=http://localhost:4200/api
    export PREFECT_START_SERVER=native
    python scripts/setup_prefect_server.py

    # Configure remote server with auth
    export PREFECT_API_URL=https://your-prefect-server.com/api
    export PREFECT_API_KEY=pnu_your_key
    python scripts/setup_prefect_server.py

    # Override settings via environment variables
    export PREFECT_CONCURRENCY_TAG=database
    export PREFECT_CONCURRENCY_LIMIT=5
    export PREFECT_WORK_POOL=my-pool
    python scripts/setup_prefect_server.py
"""

import asyncio
import os
import subprocess
import sys
import time

import httpx
from prefect.client.orchestration import get_client
from prefect.settings import (
    PREFECT_API_URL,
    PREFECT_API_KEY,
)


class PrefectServerSetup:
    """Handles complete Prefect server setup and configuration."""

    def __init__(
        self,
        use_docker: bool = None,
        port: int = None,
        container_name: str = "prefect-server",
        concurrency_tag: str = None,
        concurrency_limit: int = None,
        work_pool_name: str = None,
    ):
        # Get API URL from Prefect settings (supports env var)
        self.api_url = PREFECT_API_URL.value()
        self.api_key = PREFECT_API_KEY.value()

        # Determine if we're using Docker based on API URL and env var
        start_server_mode = os.getenv("PREFECT_START_SERVER", "auto").lower()

        if use_docker is None:
            if start_server_mode == "docker":
                self.use_docker = True
            elif start_server_mode == "native":
                self.use_docker = False
            else:
                # Auto-detect: if API URL is localhost, check for Docker
                self.use_docker = (
                    "localhost" in self.api_url or "127.0.0.1" in self.api_url
                )
        else:
            self.use_docker = use_docker

        # Server start method for production (native or none)
        self.start_server_native = start_server_mode in [
            "native",
            "yes",
            "true",
        ] or os.getenv("PREFECT_START_SERVER_NATIVE", "").lower() in [
            "yes",
            "true",
            "1",
        ]

        # Docker settings (only used in local dev)
        self.port = port or int(os.getenv("PREFECT_SERVER_PORT", "4200"))
        self.container_name = container_name

        # Configuration settings (can be overridden by env vars)
        self.concurrency_tag = concurrency_tag or os.getenv(
            "PREFECT_CONCURRENCY_TAG", "database"
        )
        self.concurrency_limit = concurrency_limit or int(
            os.getenv("PREFECT_CONCURRENCY_LIMIT", "3")
        )
        self.work_pool_name = work_pool_name or os.getenv(
            "PREFECT_WORK_POOL", "default-pool"
        )

    async def check_server_connection(self) -> bool:
        """Check if we can connect to the Prefect server."""
        print(f"🔍 Checking connection to Prefect server...")
        print(f"   API URL: {self.api_url}")

        try:
            response = httpx.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ Connected to Prefect server")
                return True
            else:
                print(f"❌ Server responded with status {response.status_code}")
                return False
        except httpx.ConnectError:
            print(f"❌ Cannot connect to server")
            print(f"   Please ensure Prefect server is running:")
            print(f"   - Docker: make prefect-server")
            print(f"   - Native: prefect server start")
            return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False

    def start_native_server(self) -> subprocess.Popen:
        """Start Prefect server as a native process."""
        print(f"🚀 Starting Prefect server...")
        print(f"   This will run in the background")

        try:
            # Start server in background
            process = subprocess.Popen(
                ["prefect", "server", "start", "--host", "0.0.0.0"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Give it a moment to start
            time.sleep(2)

            # Check if process is still running
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print(f"❌ Server failed to start:")
                if stderr:
                    print(f"   {stderr}")
                return None

            print(f"✅ Server process started (PID: {process.pid})")
            print(f"   Note: Server will continue running in background")
            print(f"   To stop: kill {process.pid}")

            return process

        except FileNotFoundError:
            print(f"❌ 'prefect' command not found")
            print(f"   Make sure Prefect is installed: pip install prefect")
            return None
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return None

    def wait_for_server_ready(self, max_wait: int = 30) -> bool:
        """Wait for server to be ready to accept requests."""
        print(f"⏳ Waiting for server to be ready...")

        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                response = httpx.get(f"{self.api_url}/health", timeout=2)
                if response.status_code == 200:
                    elapsed = time.time() - start_time
                    print(f"✅ Server is ready (took {elapsed:.1f}s)")
                    return True
            except:
                pass

            time.sleep(1)
            print(".", end="", flush=True)

        print(f"\n❌ Server did not become ready within {max_wait}s")
        return False

    async def create_work_pool(self) -> bool:
        """Create a work pool for running flows."""
        print(f"\n📋 Setting up work pool '{self.work_pool_name}'...")

        try:
            async with get_client() as client:
                # Check if work pool already exists
                try:
                    existing_pools = await client.read_work_pools()
                    pool_names = [pool.name for pool in existing_pools]

                    if self.work_pool_name in pool_names:
                        print(f"✅ Work pool '{self.work_pool_name}' already exists")
                        return True
                except Exception:
                    pass

                # Create work pool
                await client.create_work_pool(
                    name=self.work_pool_name,
                    type="process",  # Process work pool for local execution
                )
                print(f"✅ Created work pool: '{self.work_pool_name}'")
                return True

        except Exception as e:
            print(f"⚠️  Could not create work pool: {e}")
            print(f"   You may need to create it manually via the UI")
            return False

    async def setup_concurrency_limit(self) -> bool:
        """Set up server-side concurrency limits."""
        print(f"\n🔧 Setting up concurrency limit...")

        try:
            async with get_client() as client:
                # Check if limit already exists
                try:
                    limits = await client.read_concurrency_limits()
                    existing_tags = [limit.tag for limit in limits]

                    if self.concurrency_tag in existing_tags:
                        print(
                            f"✅ Concurrency limit for '{self.concurrency_tag}' already exists"
                        )
                        return True
                except Exception:
                    pass

                # Create concurrency limit
                await client.create_concurrency_limit(
                    tag=self.concurrency_tag, concurrency_limit=self.concurrency_limit
                )
                print(f"✅ Created concurrency limit:")
                print(f"   Tag: '{self.concurrency_tag}'")
                print(f"   Max concurrent: {self.concurrency_limit}")
                print(
                    f"   Tasks with tag '{self.concurrency_tag}' will be limited to {self.concurrency_limit} concurrent runs"
                )
                return True

        except Exception as e:
            print(f"❌ Error setting up concurrency limit: {e}")
            return False

    async def verify_setup(self) -> bool:
        """Verify that everything is configured correctly."""
        print(f"\n🔍 Verifying setup...")

        all_good = True

        try:
            async with get_client() as client:
                # Check flows endpoint
                try:
                    flows = await client.read_flows(limit=1)
                    print(f"✅ Can connect to Prefect API")
                except Exception as e:
                    print(f"❌ Cannot connect to Prefect API: {e}")
                    all_good = False

                # Check work pools
                try:
                    pools = await client.read_work_pools()
                    pool_names = [pool.name for pool in pools]
                    if self.work_pool_name in pool_names:
                        print(f"✅ Work pool '{self.work_pool_name}' exists")
                    else:
                        print(f"⚠️  Work pool '{self.work_pool_name}' not found")
                        all_good = False
                except Exception as e:
                    print(f"⚠️  Could not verify work pools: {e}")

                # Check concurrency limits
                try:
                    limits = await client.read_concurrency_limits()
                    limit_tags = [limit.tag for limit in limits]
                    if self.concurrency_tag in limit_tags:
                        print(
                            f"✅ Concurrency limit for '{self.concurrency_tag}' exists"
                        )
                    else:
                        print(
                            f"❌ Concurrency limit for '{self.concurrency_tag}' not found"
                        )
                        all_good = False
                except Exception as e:
                    print(f"❌ Could not verify concurrency limits: {e}")
                    all_good = False

        except Exception as e:
            print(f"❌ Error during verification: {e}")
            all_good = False

        return all_good

    async def setup(self) -> bool:
        """Run the complete setup process."""
        print("=" * 60)
        print("🚀 Prefect Server Configuration")
        print("=" * 60)
        print(f"\n📍 API URL: {self.api_url}")
        if self.api_key:
            print(f"🔐 Authentication: Enabled")
        else:
            print(f"🔓 Authentication: Disabled")

        # Step 1: Check connection or start server
        print(f"\n1️⃣  Checking Prefect server...")
        server_process = None

        if not await self.check_server_connection():
            # If connection fails and we're configured to start native server
            if self.start_server_native:
                print(f"\n   Starting native Prefect server...")
                server_process = self.start_native_server()
                if not server_process:
                    print(f"❌ Failed to start server")
                    return False

                # Wait for server to be ready
                if not self.wait_for_server_ready():
                    print(f"❌ Server did not start successfully")
                    if server_process:
                        server_process.terminate()
                    return False
            else:
                print(f"\n❌ Cannot connect to server")
                print(f"   Please start the server first:")
                print(f"   - Docker: make prefect-server")
                print(f"   - Native: prefect server start")
                print(f"   Or set PREFECT_START_SERVER=native to auto-start")
                return False

        # Step 2: Create work pool
        print(f"\n2️⃣  Setting up work pool...")
        await self.create_work_pool()

        # Step 3: Setup concurrency limits
        print(f"\n3️⃣  Configuring concurrency limits...")
        await self.setup_concurrency_limit()

        # Step 4: Verify everything
        print(f"\n4️⃣  Verification...")
        verification_passed = await self.verify_setup()

        # Summary
        print("\n" + "=" * 60)
        if verification_passed:
            print("✅ Setup Complete!")
            print("=" * 60)
            print(f"\n📋 Configuration Summary:")
            print(f"   API URL: {self.api_url}")
            print(f"   Work Pool: {self.work_pool_name}")
            print(f"   Concurrency Tag: {self.concurrency_tag}")
            print(f"   Max Concurrent: {self.concurrency_limit}")
            print(f"\n💡 Next Steps:")
            print(f"   1. Run a flow: python flows/prefect_flow.py")
            print(f"   2. View UI: {self.api_url.replace('/api', '')}")
            if server_process:
                print(f"\n⚠️  Server running in background (PID: {server_process.pid})")
                print(f"   To stop: kill {server_process.pid}")
            return True
        else:
            print("⚠️  Setup completed with warnings")
            print("=" * 60)
            print(f"\n   Check the messages above for details")
            print(f"   You may need to configure some items manually")
            if server_process:
                print(f"\n⚠️  Server running in background (PID: {server_process.pid})")
                print(f"   To stop: kill {server_process.pid}")
            return False


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("Prefect Server Configuration")
    print("=" * 60)

    # Show current configuration
    api_url = PREFECT_API_URL.value()
    api_key = PREFECT_API_KEY.value()

    print("\n📋 Configuration (from environment):")
    print(f"   PREFECT_API_URL: {api_url}")
    print(f"   PREFECT_API_KEY: {'Set' if api_key else 'Not set'}")
    print(
        f"   PREFECT_START_SERVER: {os.getenv('PREFECT_START_SERVER', 'auto (default)')}"
    )
    print(
        f"   PREFECT_CONCURRENCY_TAG: {os.getenv('PREFECT_CONCURRENCY_TAG', 'database (default)')}"
    )
    print(
        f"   PREFECT_CONCURRENCY_LIMIT: {os.getenv('PREFECT_CONCURRENCY_LIMIT', '3 (default)')}"
    )
    print(
        f"   PREFECT_WORK_POOL: {os.getenv('PREFECT_WORK_POOL', 'default-pool (default)')}"
    )

    # Check for production API key
    is_local = "localhost" in api_url or "127.0.0.1" in api_url
    if not is_local and not api_key:
        print("\n⚠️  WARNING: Production URL detected but PREFECT_API_KEY is not set!")
        print("   Set it with: export PREFECT_API_KEY=pnu_your_key")
        response = input("\n   Continue anyway? (y/n): ")
        if response.lower() != "y":
            print("   Aborted.")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("")

    # Create setup instance and run
    setup = PrefectServerSetup()

    try:
        success = asyncio.run(setup.setup())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
