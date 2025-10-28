#!/usr/bin/env python3
"""
Start Prefect workers for distributed flow execution.

This script helps start multiple Prefect workers that poll the work pool
for flow runs to execute. Workers can run concurrently to process multiple
subflows in parallel.

Usage:
    # Start a single worker
    python scripts/start_workers.py

    # Start multiple workers (e.g., 3 workers)
    python scripts/start_workers.py --workers 3

    # Use specific work pool
    python scripts/start_workers.py --pool my-pool --workers 3
"""

import os
import sys
import subprocess
import signal
import time
from prefect.settings import PREFECT_API_URL, PREFECT_API_KEY


def start_worker(pool_name: str, worker_id: int = 1):
    """Start a single Prefect worker process."""
    worker_name = f"worker-{worker_id}"

    print(f"🚀 Starting worker: {worker_name}")
    print(f"   Pool: {pool_name}")

    cmd = ["prefect", "worker", "start", "--pool", pool_name, "--name", worker_name]

    # Start worker process
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
    )

    print(f"✅ Worker {worker_name} started (PID: {process.pid})")
    return process


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Start Prefect workers for distributed flow execution"
    )
    parser.add_argument(
        "--workers", type=int, default=1, help="Number of workers to start (default: 1)"
    )
    parser.add_argument(
        "--pool",
        type=str,
        default=os.getenv("PREFECT_WORK_POOL", "default-pool"),
        help="Work pool name (default: from PREFECT_WORK_POOL env or 'default-pool')",
    )

    args = parser.parse_args()

    # Show configuration
    api_url = PREFECT_API_URL.value()
    api_key = PREFECT_API_KEY.value()

    print("=" * 70)
    print("PREFECT WORKER MANAGER")
    print("=" * 70)
    print(f"🔗 Prefect Server: {api_url}")
    print(f"🏊 Work Pool: {args.pool}")
    print(f"👷 Workers: {args.workers}")

    if api_key:
        print(f"🔐 Using API Key: {api_key[:8]}...")
    else:
        print("⚠️  No API key (development mode)")

    print("=" * 70)
    print()

    # Start workers
    processes = []

    try:
        for i in range(1, args.workers + 1):
            process = start_worker(args.pool, i)
            processes.append(process)
            time.sleep(1)  # Stagger startup

        print()
        print("=" * 70)
        print(f"✅ All {args.workers} worker(s) started successfully!")
        print("=" * 70)
        print()
        print("💡 Workers are now polling for flow runs...")
        print("   Press Ctrl+C to stop all workers")
        print()

        # Monitor workers
        while True:
            time.sleep(5)

            # Check if any workers died
            for i, process in enumerate(processes, 1):
                if process.poll() is not None:
                    print(
                        f"⚠️  Worker {i} (PID: {process.pid}) exited with code {process.returncode}"
                    )
                    # Optionally restart
                    print(f"   Restarting worker {i}...")
                    new_process = start_worker(args.pool, i)
                    processes[i - 1] = new_process

    except KeyboardInterrupt:
        print("\n\n⚠️  Shutting down workers...")
        for i, process in enumerate(processes, 1):
            print(f"   Stopping worker {i} (PID: {process.pid})...")
            process.terminate()

        # Wait for graceful shutdown
        time.sleep(2)

        # Force kill if needed
        for process in processes:
            if process.poll() is None:
                process.kill()

        print("✅ All workers stopped")
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        # Stop all workers
        for process in processes:
            if process.poll() is None:
                process.terminate()
        sys.exit(1)


if __name__ == "__main__":
    main()
