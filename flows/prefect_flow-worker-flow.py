import time
import os
from prefect import task, flow, get_run_logger
from prefect.deployments import run_deployment
from prefect.client.orchestration import get_client
from prefect.client.schemas.filters import FlowRunFilter
from prefect.client.schemas.objects import StateType
import asyncio


@flow(name="main-etl-job", log_prints=True)
async def main_etl():
    """
    Main orchestrator flow that coordinates the ETL process.
    Calls sub_etl to handle the distributed execution.
    """
    logger = get_run_logger()
    logger.info("Starting ETL flow...")

    # Call sub_etl to handle distributed execution
    result = await sub_etl()

    logger.info("ETL flow completed.")
    return result


@flow(name="sub-etl-job", log_prints=True)
async def sub_etl():
    """
    Sub-orchestrator that submits subflows to work pool for distributed execution.
    Each subflow will be picked up by workers and run concurrently based on work pool capacity.
    """
    logger = get_run_logger()
    logger.info("Starting sub-ETL orchestration...")

    # Submit all 20 ETL subflows to the work pool for distributed execution
    logger.info("Submitting 20 ETL subflows to work pool...")
    flow_run_ids = []

    for table in range(20):
        # Use run_deployment to trigger deployed subflow
        # This creates a flow run that gets queued in the work pool
        flow_run = await run_deployment(
            name="process-table-etl/process-table-etl-deployment",
            parameters={"table": table},
            timeout=0,  # Don't wait, return immediately
        )
        flow_run_ids.append(flow_run.id)
        logger.info(f"Submitted ETL subflow for table {table} (run_id: {flow_run.id})")

    # Wait for all ETL subflows to complete
    logger.info(f"Waiting for all {len(flow_run_ids)} ETL subflows to complete...")
    await wait_for_flow_runs(flow_run_ids)
    logger.info(f"All {len(flow_run_ids)} ETL subflows completed successfully")

    # Now run cleanup as separate subflows
    logger.info("Starting cleanup subflows...")

    cleanup1_run = await run_deployment(
        name="cleanup-flow-1/cleanup-flow-1-deployment",
        timeout=0,
    )
    cleanup2_run = await run_deployment(
        name="cleanup-flow-2/cleanup-flow-2-deployment",
        timeout=0,
    )

    # Wait for cleanup to finish
    await wait_for_flow_runs([cleanup1_run.id, cleanup2_run.id])
    logger.info("Cleanup completed")

    logger.info("Sub-ETL orchestration completed.")
    return {"completed_tables": len(flow_run_ids)}


async def wait_for_flow_runs(flow_run_ids: list):
    """
    Wait for all flow runs to complete.
    Polls the Prefect API to check flow run states.
    """
    logger = get_run_logger()

    async with get_client() as client:
        pending_ids = set(flow_run_ids)

        while pending_ids:
            # Check status of pending flow runs
            for run_id in list(pending_ids):
                flow_run = await client.read_flow_run(run_id)

                if flow_run.state.is_final():
                    if flow_run.state.is_completed():
                        logger.info(f"Flow run {run_id} completed successfully")
                    elif flow_run.state.is_failed():
                        logger.error(
                            f"Flow run {run_id} failed: {flow_run.state.message}"
                        )
                    elif flow_run.state.is_crashed():
                        logger.error(
                            f"Flow run {run_id} crashed: {flow_run.state.message}"
                        )
                    elif flow_run.state.is_cancelled():
                        logger.warning(f"Flow run {run_id} was cancelled")

                    pending_ids.remove(run_id)

            if pending_ids:
                # Still have pending runs, wait before checking again
                await asyncio.sleep(2)

        logger.info("All flow runs completed")


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
            # Deploy flows to work pool
            print("\n🚀 Deploying flows to work pool...")

            # Deploy all flows that will be executed by workers
            from prefect.deployments import Deployment
            from prefect.server.schemas.schedules import IntervalSchedule
            from datetime import timedelta

            # Deploy main orchestrator
            deployment_main = Deployment.build_from_flow(
                flow=main_etl,
                name="main-etl-deployment",
                work_pool_name=work_pool,
                description="Main ETL orchestrator that calls sub_etl",
            )
            deployment_main.apply()
            print(f"✅ Deployed: main-etl-job")

            # Deploy sub-ETL orchestrator
            deployment_sub = Deployment.build_from_flow(
                flow=sub_etl,
                name="sub-etl-deployment",
                work_pool_name=work_pool,
                description="Sub-ETL orchestrator that submits subflows to work pool",
            )
            deployment_sub.apply()
            print(f"✅ Deployed: sub-etl-job")

            # Deploy table ETL subflow
            deployment_table = Deployment.build_from_flow(
                flow=process_table_etl,
                name="process-table-etl-deployment",
                work_pool_name=work_pool,
                description="ETL subflow for processing individual tables",
            )
            deployment_table.apply()
            print(f"✅ Deployed: process-table-etl")

            # Deploy cleanup flows
            deployment_cleanup1 = Deployment.build_from_flow(
                flow=cleanup_flow1,
                name="cleanup-flow-1-deployment",
                work_pool_name=work_pool,
                description="Cleanup subflow 1",
            )
            deployment_cleanup1.apply()
            print(f"✅ Deployed: cleanup-flow-1")

            deployment_cleanup2 = Deployment.build_from_flow(
                flow=cleanup_flow2,
                name="cleanup-flow-2-deployment",
                work_pool_name=work_pool,
                description="Cleanup subflow 2",
            )
            deployment_cleanup2.apply()
            print(f"✅ Deployed: cleanup-flow-2")

            print(f"\n🎉 All deployments created successfully!")
            print(f"\n💡 Next: Start workers with:")
            print(f"   prefect worker start --pool {work_pool}")

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
