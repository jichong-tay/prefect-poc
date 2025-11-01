# Multi-Phase ETL Pattern with Parallel Execution

## Overview

The refactored `prefect_flow-worker-flow-v2.py` now implements a sophisticated multi-phase ETL orchestration pattern that supports:

1. **Parallel execution** of independent flows
2. **Sequential coordination** with dependency management
3. **Distributed processing** via work pools
4. **Clean separation** of concerns

## Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        main-etl-job                             │
│                    (Main Orchestrator)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │
              ┌───────────────┴───────────────┐
              │         PHASE 1               │
              │    (Parallel Execution)       │
              └───────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
            ┌───────▼───────┐   ┌──────▼──────┐
            │  pre-etl-job  │   │ sub-etl-job │
            │               │   │             │
            │ - Validate    │   │ - Process   │
            │ - Setup       │   │   20 tables │
            │ - Prepare     │   │ - Cleanup   │
            └───────┬───────┘   └──────┬──────┘
                    │                  │
                    │                  │
                    │         ┌────────▼────────┐
                    │         │ 20x process-    │
                    │         │ table-etl       │
                    │         │ (Distributed)   │
                    │         └────────┬────────┘
                    │                  │
                    │         ┌────────▼────────┐
                    │         │ cleanup-flow-1  │
                    │         │ cleanup-flow-2  │
                    │         └────────┬────────┘
                    │                  │
                    └─────────┬────────┘
                              │
              ┌───────────────▼───────────────┐
              │         PHASE 2               │
              │    (Sequential Execution)     │
              └───────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  final-etl-job     │
                    │                    │
                    │ - Aggregate        │
                    │ - Report           │
                    │ - Validate         │
                    └────────────────────┘
```

## Flow Execution Sequence

### Phase 1: Parallel Pre-processing and Main Processing

**Executed simultaneously:**

1. **pre-etl-job** (10 seconds)
   - Validates data sources
   - Sets up connections
   - Prepares workspace
   - Returns validation status

2. **sub-etl-job** (10+ minutes depending on workers)
   - Triggers 20 parallel `process-table-etl` subflows
   - Each processes one table (30 seconds each)
   - Runs `cleanup-flow-1` and `cleanup-flow-2` after tables complete
   - Returns count of completed tables

**Synchronization Point:** Main orchestrator waits for BOTH to complete before proceeding.

### Phase 2: Sequential Finalization

**Executed after Phase 1:**

3. **final-etl-job** (15 seconds)
   - Aggregates results from all previous flows
   - Generates reports
   - Validates final outputs
   - Returns completion status

## Code Implementation

### Main Orchestrator (main_etl)

```python
@flow(name="main-etl-job", log_prints=True)
async def main_etl():
    """
    Main orchestrator flow that coordinates the ETL process.
    Executes pre_etl and sub_etl in parallel, then runs final_etl.
    """
    logger = get_run_logger()
    logger.info("Starting ETL flow...")

    # Phase 1: Run pre_etl and sub_etl in parallel
    logger.info("Phase 1: Starting pre_etl and sub_etl in parallel...")
    
    pre_etl_run_id = await trigger_subflow("pre-etl-job/pre-etl-deployment")
    sub_etl_run_id = await trigger_subflow("sub-etl-job/sub-etl-deployment")
    
    # Wait for both to complete
    await wait_for_flow_runs([pre_etl_run_id, sub_etl_run_id])
    logger.info("Phase 1 completed: pre_etl and sub_etl finished")

    # Phase 2: Run final_etl after both complete
    logger.info("Phase 2: Starting final_etl...")
    final_etl_run_id = await trigger_subflow("final-etl-job/final-etl-deployment")
    
    await wait_for_flow_runs([final_etl_run_id])
    logger.info("Phase 2 completed: final_etl finished")

    logger.info("ETL flow completed successfully.")
    return {
        "pre_etl_run_id": pre_etl_run_id,
        "sub_etl_run_id": sub_etl_run_id,
        "final_etl_run_id": final_etl_run_id,
        "status": "completed"
    }
```

### New Flows Added

#### Pre-ETL Flow

```python
@flow(name="pre-etl-job", log_prints=True)
def pre_etl():
    """
    Pre-ETL flow that runs before main processing.
    Performs setup, validation, or preparatory tasks.
    """
    logger = get_run_logger()
    logger.info("Starting pre-ETL processing...")
    
    result = pre_etl_task()
    
    logger.info("Pre-ETL processing completed.")
    return result

@task(name="pre-etl-task", log_prints=True, tags=["pre-processing"])
def pre_etl_task():
    """Pre-ETL task for setup and validation."""
    logger = get_run_logger()
    logger.info("Executing pre-ETL task...")
    logger.info("- Validating data sources")
    logger.info("- Setting up connections")
    logger.info("- Preparing workspace")
    time.sleep(10)  # Simulate pre-processing work
    logger.info("Pre-ETL task completed.")
    return {"status": "pre_etl_complete", "sources_validated": True}
```

#### Final ETL Flow

```python
@flow(name="final-etl-job", log_prints=True)
def final_etl():
    """
    Final ETL flow that runs after all processing completes.
    Performs finalization tasks like aggregation, reporting, or validation.
    """
    logger = get_run_logger()
    logger.info("Starting final ETL processing...")
    
    result = final_etl_task()
    
    logger.info("Final ETL processing completed.")
    return result

@task(name="final-etl-task", log_prints=True, tags=["post-processing"])
def final_etl_task():
    """Final ETL task for aggregation and reporting."""
    logger = get_run_logger()
    logger.info("Executing final ETL task...")
    logger.info("- Aggregating results")
    logger.info("- Generating reports")
    logger.info("- Validating outputs")
    time.sleep(15)  # Simulate final processing work
    logger.info("Final ETL task completed.")
    return {"status": "final_etl_complete", "reports_generated": True}
```

## Deployment Configuration

All flows are configured in the centralized `DEPLOYMENT_CONFIGS` list:

```python
DEPLOYMENT_CONFIGS = [
    DeploymentConfig(
        flow_func=main_etl,
        deployment_name="main-etl-deployment",
        description="Main ETL orchestrator that coordinates pre_etl, sub_etl, and final_etl",
    ),
    DeploymentConfig(
        flow_func=pre_etl,
        deployment_name="pre-etl-deployment",
        description="Pre-ETL flow that runs before main processing",
    ),
    DeploymentConfig(
        flow_func=sub_etl,
        deployment_name="sub-etl-deployment",
        description="Sub-ETL orchestrator that submits subflows to work pool",
    ),
    DeploymentConfig(
        flow_func=final_etl,
        deployment_name="final-etl-deployment",
        description="Final ETL flow that runs after all processing completes",
    ),
    # ... other flows
]
```

## Usage

### 1. Deploy All Flows

```bash
python flows/prefect_flow-worker-flow-v2.py deploy
```

This deploys all 7 flows:
- ✅ main-etl-job
- ✅ pre-etl-job
- ✅ sub-etl-job
- ✅ final-etl-job
- ✅ process-table-etl
- ✅ cleanup-flow-1
- ✅ cleanup-flow-2

### 2. Start Workers

```bash
# Start 3 workers (default)
prefect worker start --pool default-pool

# Or use the make command
make start-workers

# Or start more workers for faster processing
make start-workers N=5
```

### 3. Run the Orchestrator

```bash
# Option 1: Run from CLI
python flows/prefect_flow-worker-flow-v2.py run

# Option 2: Trigger from Prefect UI
# Visit http://localhost:4200
# Navigate to Deployments → main-etl-job → Run

# Option 3: Use make command
make run-distributed
```

## Execution Timeline Example

With 3 workers processing the distributed subflows:

```
Time    Phase          Flow                Status
00:00   Phase 1 Start  pre-etl-job        ⚙️  Running
00:00   Phase 1 Start  sub-etl-job        ⚙️  Running
00:00   Phase 1        ├─ table-0-etl     ⚙️  Running
00:00   Phase 1        ├─ table-1-etl     ⚙️  Running
00:00   Phase 1        └─ table-2-etl     ⚙️  Running
00:10   Phase 1        pre-etl-job        ✅ Complete (10s)
00:30   Phase 1        ├─ table-0-etl     ✅ Complete (30s)
00:30   Phase 1        └─ table-3-etl     ⚙️  Running
...
05:00   Phase 1        ├─ table-19-etl    ✅ Complete
05:00   Phase 1        ├─ cleanup-1       ⚙️  Running
05:00   Phase 1        └─ cleanup-2       ⚙️  Running
05:05   Phase 1 Done   sub-etl-job        ✅ Complete (~5m)
05:05   Phase 2 Start  final-etl-job      ⚙️  Running
05:20   Phase 2 Done   final-etl-job      ✅ Complete (15s)
05:20   Complete       main-etl-job       ✅ Complete (~5.3m total)
```

## Key Benefits

### 1. Parallelism Where Possible
- `pre-etl-job` and `sub-etl-job` run simultaneously
- Saves time if pre-processing can happen independently
- Optimal resource utilization

### 2. Guaranteed Ordering Where Needed
- `final-etl-job` only runs after both Phase 1 flows complete
- Ensures data consistency and correctness
- Clear dependency chain

### 3. Easy to Extend

**Add a new parallel flow in Phase 1:**

```python
# In main_etl, Phase 1 section:
pre_etl_run_id = await trigger_subflow("pre-etl-job/pre-etl-deployment")
sub_etl_run_id = await trigger_subflow("sub-etl-job/sub-etl-deployment")
new_flow_run_id = await trigger_subflow("new-flow-job/new-flow-deployment")  # New!

# Wait for all three
await wait_for_flow_runs([pre_etl_run_id, sub_etl_run_id, new_flow_run_id])
```

**Add a new sequential phase:**

```python
# After Phase 2:
# Phase 3: Run post-final cleanup
logger.info("Phase 3: Starting post-final cleanup...")
cleanup_run_id = await trigger_subflow("post-final-cleanup/deployment")
await wait_for_flow_runs([cleanup_run_id])
logger.info("Phase 3 completed")
```

### 4. Distributed Execution
- All flows run as separate deployments
- Workers pick them up from work pool
- Horizontal scaling capability
- Independent flow runs with full observability

### 5. Clean Abstractions
- `trigger_subflow()` hides complexity
- `wait_for_flow_runs()` handles polling
- Easy to read orchestration logic
- Simple to test and debug

## Monitoring

### In Prefect UI

1. **Main Flow Run** shows overall progress
2. **Flow Run Graph** visualizes the execution tree
3. **Individual Flow Runs** for each subflow
4. **Logs** for each phase and flow
5. **Timeline** shows parallel vs sequential execution

### Key Metrics to Monitor

- **Phase 1 Duration**: Max of `pre_etl` and `sub_etl` durations
- **Phase 2 Duration**: `final_etl` duration
- **Total Duration**: Phase 1 + Phase 2
- **Table Processing**: Average time per table
- **Worker Utilization**: How many workers are active

## Error Handling

If any flow fails:

1. **Phase 1 Failure**: 
   - `wait_for_flow_runs()` logs the error
   - Main orchestrator will still wait for other flows
   - Phase 2 won't start if Phase 1 fails

2. **Phase 2 Failure**:
   - Logged in main orchestrator
   - Phase 1 results are already complete
   - Can be re-run independently

## Comparison to Sequential Pattern

### Old Pattern (Sequential)
```python
await sub_etl()  # Wait 5+ minutes
# Then do final work
```
Total: 5+ minutes (sequential)

### New Pattern (Parallel + Sequential)
```python
# Phase 1: Parallel
pre_etl (10s) || sub_etl (5m)  # Max = 5m
# Phase 2: Sequential
final_etl (15s)
```
Total: ~5.25 minutes (parallel where possible)

**Time saved**: pre_etl duration (since it runs in parallel)

## Real-World Use Cases

This pattern is ideal for:

1. **Data Validation + Processing**: Validate schema while processing data
2. **Multi-Source ETL**: Pull from multiple sources in parallel
3. **Setup + Processing**: Initialize resources while starting main work
4. **Aggregation After Completion**: Roll up results after all processing done
5. **Reporting Pipelines**: Process + validate in parallel, then generate reports

## Conclusion

The multi-phase ETL pattern provides:
- ✅ Maximum parallelism where safe
- ✅ Guaranteed ordering where needed
- ✅ Clean, maintainable code
- ✅ Easy to extend and modify
- ✅ Full observability in Prefect UI
- ✅ Production-ready error handling

This is the recommended pattern for complex ETL workflows with mixed parallel and sequential dependencies.
