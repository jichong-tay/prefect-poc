import time
import os
from prefect import task, flow, get_run_logger


@flow(name="main-etl-job", log_prints=True)
def main_etl():
    logger = get_run_logger()
    logger.info("Starting ETL flow...")
    sub_etl()
    logger.info("ETL flow completed.")


@flow(name="sub-etl-job", log_prints=True)
def sub_etl():
    logger = get_run_logger()
    
    # Submit all 20 queries at once - Prefect server will control concurrency
    logger.info("Submitting all 20 queries...")
    query_futures = []
    for table in range(20):
        future = sql_query.submit(table)
        query_futures.append(future)
    
    # Wait for ALL queries to complete before cleanup
    logger.info("Waiting for all queries to complete...")
    query_results = [future.result() for future in query_futures]
    logger.info(f"All {len(query_results)} queries completed successfully")
    
    # Now run cleanup tasks
    logger.info("Starting cleanup...")
    cleanup1_future = cleanup1.submit()
    cleanup2_future = cleanup2.submit()
    
    # Wait for cleanup to finish
    cleanup1_future.result()
    cleanup2_future.result()
    logger.info("Cleanup completed")
    
    return query_results


@task(
    name="sql-query-task",
    log_prints=True,
    tags=["database"],
    retries=2,
    retry_delay_seconds=10
)
def sql_query(table):
    logger = get_run_logger()
    logger.info(f"Running ETL job for table {table}...")
    time.sleep(30)
    logger.info(f"ETL job completed for table {table}")
    return {"table": table, "status": "success"}


@task(name="cleanup-task-1", log_prints=True)
def cleanup1():
    logger = get_run_logger()
    logger.info("Cleaning up resources...")
    time.sleep(5)
    logger.info("Cleanup done.")
    return {"status": "cleanup1_complete"}


@task(name="cleanup-task-2", log_prints=True)
def cleanup2():
    logger = get_run_logger()
    logger.info("Finalizing cleanup...")
    time.sleep(5)
    logger.info("Cleanup finalized.")
    return {"status": "cleanup2_complete"}


if __name__ == "__main__":
    # Check for authentication configuration
    prefect_api_url = os.getenv("PREFECT_API_URL", "http://localhost:4200/api")
    prefect_api_key = os.getenv("PREFECT_API_KEY")
    
    print("=" * 70)
    print("PREFECT ETL FLOW")
    print("=" * 70)
    print(f"🔗 Prefect Server: {prefect_api_url}")
    
    if prefect_api_key:
        print(f"🔐 Using API Key: {prefect_api_key[:8]}...")
        # Note: When using .serve(), Prefect automatically picks up PREFECT_API_KEY
        # from environment variables for authentication
    else:
        print("⚠️  No API key (development mode)")
    
    print("=" * 70)
    print("\nStarting flow server...")
    print("Press Ctrl+C to stop\n")
    
    # The .serve() method will automatically use PREFECT_API_KEY if set
    main_etl().serve(name="etl-job")
