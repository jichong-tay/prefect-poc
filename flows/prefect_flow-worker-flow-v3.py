import time
import os
from typing import List, Dict, Any
from dataclasses import dataclass
from prefect import task, flow, get_run_logger
from prefect.deployments import run_deployment, Deployment
from prefect.client.orchestration import get_client
from prefect.client.schemas.filters import FlowRunFilter
from prefect.client.schemas.objects import StateType
import asyncio


# ============================================================================
# Configuration
# ============================================================================


@dataclass
class DeploymentConfig:
    """Configuration for a flow deployment."""

    flow_func: Any
    deployment_name: str
    description: str

    @property
    def deployment_path(self) -> str:
        """Get the full deployment path for run_deployment."""
        flow_name = self.flow_func.__name__.replace("_", "-")
        return f"{flow_name}/{self.deployment_name}"


# Define all deployments in one place
DEPLOYMENT_CONFIGS = [
    DeploymentConfig(
        flow_func=None,  # Will be set below after flow definitions
        deployment_name="main-etl-deployment",
        description="Main ETL orchestrator that coordinates pre_etl, sub_etl, and final_etl",
    ),
    DeploymentConfig(
        flow_func=None,
        deployment_name="pre-etl-deployment",
        description="Pre-ETL flow that runs before main processing",
    ),
    DeploymentConfig(
        flow_func=None,
        deployment_name="sub-etl-deployment",
        description="Sub-ETL orchestrator that submits subflows to work pool",
    ),
    DeploymentConfig(
        flow_func=None,
        deployment_name="final-etl-deployment",
        description="Final ETL flow that runs after all processing completes",
    ),
    DeploymentConfig(
        flow_func=None,
        deployment_name="process-table-etl-deployment",
        description="ETL subflow for processing individual tables",
    ),
    DeploymentConfig(
        flow_func=None,
        deployment_name="cleanup-flow-1-deployment",
        description="Cleanup subflow 1",
    ),
    DeploymentConfig(
        flow_func=None,
        deployment_name="cleanup-flow-2-deployment",
        description="Cleanup subflow 2",
    ),
]


# ============================================================================
# Utility Functions
# ============================================================================


class FlowSubmission:
    """
    Submit Prefect flow deployments asynchronously and wait for their completion.
    Designed for use with Prefect 2.13.x worker pools.
    """

    def __init__(self, deployment_path: str):
        self.deployment_path = deployment_path
        self.run_ids: List[str] = []
        self.results: Dict[str, str] = {}

    async def submit(self, **parameters) -> str:
        """
        Submit a flow run asynchronously via the specified deployment.
        Returns the flow_run_id for tracking.
        """
        flow_run = await run_deployment(
            name=self.deployment_path,
            parameters=parameters,
            timeout=0,
            schedule=True,  # ensure run is queued immediately for workers
        )
        self.run_ids.append(flow_run.id)
        return flow_run.id

    async def wait(
        self, poll_interval: int = 5, show_summary: bool = True
    ) -> Dict[str, str]:
        """
        Wait for all submitted runs to complete.
        Returns a dict of {flow_run_id: final_state_name}.
        """
        if not self.run_ids:
            return {}

        logger = get_run_logger()
        async with get_client() as client:
            pending = set(self.run_ids)
            logger.info(f"Waiting for {len(pending)} flow runs to complete...")

            while pending:
                completed = []
                for run_id in list(pending):
                    flow_run = await client.read_flow_run(run_id)
                    if flow_run.state.is_final():
                        self.results[run_id] = flow_run.state.name
                        status_icon = "✅" if flow_run.state.is_completed() else "❌"
                        logger.info(
                            f"{status_icon} [{self.deployment_path}] "
                            f"Run {run_id[:8]} finished with state: {flow_run.state.name}"
                        )
                        completed.append(run_id)

                for c in completed:
                    pending.remove(c)

                if pending:
                    await asyncio.sleep(poll_interval)

        if show_summary:
            total = len(self.results)
            success = sum(v == "Completed" for v in self.results.values())
            failed = total - success
            logger.info(f"Summary → {success}/{total} succeeded, {failed} failed")

        return self.results


def flow_submitter(deployment_path: str) -> FlowSubmission:
    """
    Factory helper for ergonomic usage.

    Example:
        etl = flow_submitter("etl-parent/etl-child-deployment")

        # Submit multiple flows asynchronously
        await asyncio.gather(
            etl.submit(table="customer"),
            etl.submit(table="orders"),
            etl.submit(table="sales"),
        )

        # Wait for all runs to complete
        await etl.wait()
    """
    return FlowSubmission(deployment_path)


# ============================================================================
# Flow Definitions
# ============================================================================


@flow(name="main-etl-job", log_prints=True)
async def main_etl():
    """
    Main orchestrator flow that coordinates the ETL process.
    Executes pre_etl and sub_etl in parallel, then runs final_etl after both complete.

    Uses flow_submitter() for clean, task-like .submit() and .wait() syntax.
    """
    logger = get_run_logger()
    logger.info("Starting ETL flow...")

    # Phase 1: Run pre_etl and sub_etl in parallel (task-like syntax!)
    logger.info("Phase 1: Starting pre_etl and sub_etl in parallel...")

    pre_etl = flow_submitter("pre-etl-job/pre-etl-deployment")
    sub_etl = flow_submitter("sub-etl-job/sub-etl-deployment")

    # Submit both (like task.submit())
    await pre_etl.submit()
    await sub_etl.submit()

    # Wait for both to complete (like future.result())
    await pre_etl.wait()
    await sub_etl.wait()
    logger.info("Phase 1 completed: pre_etl and sub_etl finished")

    # Phase 2: Run final_etl after both complete
    logger.info("Phase 2: Starting final_etl...")
    final_etl = flow_submitter("final-etl-job/final-etl-deployment")
    await final_etl.submit()
    await final_etl.wait()
    logger.info("Phase 2 completed: final_etl finished")

    logger.info("ETL flow completed successfully.")
    return {
        "pre_etl_run_ids": pre_etl.run_ids,
        "sub_etl_run_ids": sub_etl.run_ids,
        "final_etl_run_ids": final_etl.run_ids,
        "status": "completed",
    }


@flow(name="pre-etl-job", log_prints=True)
def pre_etl():
    """
    Pre-ETL flow that runs before main processing.
    Performs setup, validation, or preparatory tasks.
    """
    logger = get_run_logger()
    logger.info("Starting pre-ETL processing...")

    # Simulate pre-ETL work (e.g., data validation, setup)
    result = pre_etl_task()

    logger.info("Pre-ETL processing completed.")
    return result


@flow(name="sub-etl-job", log_prints=True)
async def sub_etl():
    """
    Sub-orchestrator that submits subflows to work pool for distributed execution.
    Each subflow will be picked up by workers and run concurrently based on work pool capacity.

    Uses flow_submitter() for clean, task-like syntax.
    """
    logger = get_run_logger()
    logger.info("Starting sub-ETL orchestration...")

    # Submit all 20 ETL subflows to the work pool (task-like syntax!)
    logger.info("Submitting 20 ETL subflows...")
    table_etl = flow_submitter("process-table-etl/process-table-etl-deployment")

    for table in range(20):
        await table_etl.submit(table=table)

    # Wait for all tables to complete
    logger.info(f"Waiting for all {len(table_etl.run_ids)} ETL subflows to complete...")
    await table_etl.wait()
    logger.info(f"All {len(table_etl.run_ids)} ETL subflows completed successfully")

    # Now run cleanup as separate subflows
    logger.info("Starting cleanup subflows...")
    cleanup1 = flow_submitter("cleanup-flow-1/cleanup-flow-1-deployment")
    cleanup2 = flow_submitter("cleanup-flow-2/cleanup-flow-2-deployment")

    await cleanup1.submit()
    await cleanup2.submit()
    await cleanup1.wait()
    await cleanup2.wait()

    logger.info("Cleanup completed")
    logger.info("Sub-ETL orchestration completed.")
    return {"completed_tables": len(table_etl.run_ids)}


@flow(name="final-etl-job", log_prints=True)
def final_etl():
    """
    Final ETL flow that runs after all processing completes.
    Performs finalization tasks like aggregation, reporting, or validation.
    """
    logger = get_run_logger()
    logger.info("Starting final ETL processing...")

    # Simulate final ETL work (e.g., aggregation, reporting)
    result = final_etl_task()

    logger.info("Final ETL processing completed.")
    return result


@flow(name="process-table-etl", log_prints=True)
def process_table_etl(table: int):
    """
    Subflow that processes a single table.
    This will be executed by workers from the work pool.
    """
    logger = get_run_logger()
    logger.info(f"Processing table {table} ETL...")

    # Call the actual ETL task
    result = sql_query(table)

    logger.info(f"Table {table} ETL completed")
    return result


@task(
    name="sql-query-task",
    log_prints=True,
    tags=["database"],
    retries=2,
    retry_delay_seconds=10,
)
def sql_query(table):
    logger = get_run_logger()
    logger.info(f"Running SQL query for table {table}...")
    time.sleep(30)
    logger.info(f"SQL query completed for table {table}")
    return {"table": table, "status": "success"}


@task(name="pre-etl-task", log_prints=True, tags=["pre-processing"])
def pre_etl_task():
    """
    Pre-ETL task for setup and validation.
    """
    logger = get_run_logger()
    logger.info("Executing pre-ETL task...")
    logger.info("- Validating data sources")
    logger.info("- Setting up connections")
    logger.info("- Preparing workspace")
    time.sleep(10)  # Simulate pre-processing work
    logger.info("Pre-ETL task completed.")
    return {"status": "pre_etl_complete", "sources_validated": True}


@task(name="final-etl-task", log_prints=True, tags=["post-processing"])
def final_etl_task():
    """
    Final ETL task for aggregation and reporting.
    """
    logger = get_run_logger()
    logger.info("Executing final ETL task...")
    logger.info("- Aggregating results")
    logger.info("- Generating reports")
    logger.info("- Validating outputs")
    time.sleep(15)  # Simulate final processing work
    logger.info("Final ETL task completed.")
    return {"status": "final_etl_complete", "reports_generated": True}


@flow(name="cleanup-flow-1", log_prints=True)
def cleanup_flow1():
    """
    Cleanup subflow - will be executed by workers from work pool.
    """
    logger = get_run_logger()
    logger.info("Cleaning up resources...")
    result = cleanup_task1()
    logger.info("Cleanup flow 1 done.")
    return result


@flow(name="cleanup-flow-2", log_prints=True)
def cleanup_flow2():
    """
    Cleanup subflow - will be executed by workers from work pool.
    """
    logger = get_run_logger()
    logger.info("Finalizing cleanup...")
    result = cleanup_task2()
    logger.info("Cleanup flow 2 finalized.")
    return result


@task(name="cleanup-task-1", log_prints=True)
def cleanup_task1():
    logger = get_run_logger()
    logger.info("Executing cleanup task 1...")
    time.sleep(5)
    logger.info("Cleanup task 1 done.")
    return {"status": "cleanup1_complete"}


@task(name="cleanup-task-2", log_prints=True)
def cleanup_task2():
    logger = get_run_logger()
    logger.info("Executing cleanup task 2...")
    time.sleep(5)
    logger.info("Cleanup task 2 finalized.")
    return {"status": "cleanup2_complete"}


# ============================================================================
# Deployment Management
# ============================================================================

# Link flow functions to deployment configs
DEPLOYMENT_CONFIGS[0].flow_func = main_etl
DEPLOYMENT_CONFIGS[1].flow_func = pre_etl
DEPLOYMENT_CONFIGS[2].flow_func = sub_etl
DEPLOYMENT_CONFIGS[3].flow_func = final_etl
DEPLOYMENT_CONFIGS[4].flow_func = process_table_etl
DEPLOYMENT_CONFIGS[5].flow_func = cleanup_flow1
DEPLOYMENT_CONFIGS[6].flow_func = cleanup_flow2


def deploy_all_flows(work_pool: str) -> None:
    """
    Deploy all flows to the work pool.

    Args:
        work_pool: Name of the work pool to deploy to
    """
    print("\n🚀 Deploying flows to work pool...")

    for config in DEPLOYMENT_CONFIGS:
        deployment = Deployment.build_from_flow(
            flow=config.flow_func,
            name=config.deployment_name,
            work_pool_name=work_pool,
            description=config.description,
        )
        deployment.apply()

        flow_name = config.flow_func.name
        print(f"✅ Deployed: {flow_name}")

    print(f"\n🎉 All {len(DEPLOYMENT_CONFIGS)} deployments created successfully!")
    print(f"\n💡 Next: Start workers with:")
    print(f"   prefect worker start --pool {work_pool}")


# ============================================================================
# CLI Interface
# ============================================================================

if __name__ == "__main__":
    # Check for authentication configuration
    prefect_api_url = os.getenv("PREFECT_API_URL", "http://localhost:4200/api")
    prefect_api_key = os.getenv("PREFECT_API_KEY")
    work_pool = os.getenv("PREFECT_WORK_POOL", "default-pool")

    print("=" * 70)
    print("PREFECT DISTRIBUTED ETL FLOW (Work Pool)")
    print("=" * 70)
    print(f"🔗 Prefect Server: {prefect_api_url}")
    print(f"🏊 Work Pool: {work_pool}")

    if prefect_api_key:
        print(f"🔐 Using API Key: {prefect_api_key[:8]}...")
    else:
        print("⚠️  No API key (development mode)")

    print("=" * 70)
    print("\n📋 DEPLOYMENT INSTRUCTIONS:")
    print("-" * 70)
    print("This flow uses work pools for distributed execution.")
    print("Follow these steps:")
    print()
    print("1. Deploy all flows to work pool:")
    print("   python flows/prefect_flow-worker-flow.py deploy")
    print()
    print("2. Start workers to process flows:")
    print(f"   prefect worker start --pool {work_pool}")
    print()
    print("3. Run the main orchestrator flow:")
    print("   python flows/prefect_flow-worker-flow.py run")
    print()
    print("Or use the deployment from UI:")
    print(f"   - Visit: {prefect_api_url.replace('/api', '')}")
    print("   - Navigate to Deployments")
    print("   - Find 'main-etl-job' and click 'Run'")
    print("=" * 70)

    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "deploy":
            deploy_all_flows(work_pool)

        elif command == "run":
            # Run the main flow directly (for testing)
            print("\n▶️  Running main ETL flow...")
            print("⚠️  Make sure workers are running!")
            asyncio.run(main_etl())

        else:
            print(f"\n❌ Unknown command: {command}")
            print("   Use: deploy, run")
    else:
        print("\n⚠️  No command specified. Use: deploy, run")
