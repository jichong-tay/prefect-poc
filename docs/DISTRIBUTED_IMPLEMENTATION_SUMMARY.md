# Distributed ETL Implementation Summary

## What Changed

Refactored the ETL flow from task-based concurrency to distributed subflow execution using Prefect work pools and workers.

## Architecture Comparison

### Before: Task Concurrency (Single Flow Run)
```python
@flow
def etl():
    futures = [sql_query.submit(table) for table in range(20)]
    # All tasks run in same flow run
    # Limited by task concurrency (max 3)
```

**Limitations:**
- All tasks in single flow run process
- Cannot distribute across machines
- Concurrency limited to task runner capacity
- Scalability constrained by single process

### After: Distributed Subflows (Multiple Flow Runs)
```python
@flow
async def main_etl():
    # Each subflow is separate flow run triggered via run_deployment
    flow_run_ids = []
    for table in range(20):
        flow_run = await run_deployment(
            name="process-table-etl/process-table-etl-deployment",
            parameters={"table": table},
            timeout=0,
        )
        flow_run_ids.append(flow_run.id)
    
    # Wait for all to complete
    await wait_for_flow_runs(flow_run_ids)

@flow  # Subflow - runs on worker
def process_table_etl(table: int):
    return sql_query(table)
```

**Benefits:**
- 20 independent flow runs
- Distributed across multiple workers
- Horizontal scaling (add more workers)
- Can run on different machines
- Better fault isolation

## New Files

### 1. `flows/prefect_flow-worker-flow.py`
Main ETL implementation with distributed subflows.

**Key Functions:**
- `main_etl()` - Orchestrator flow that submits work
- `process_table_etl(table)` - Subflow for each table
- `cleanup_flow1()` - Cleanup subflow 1
- `cleanup_flow2()` - Cleanup subflow 2

**Commands:**
```bash
# Deploy to work pool
python flows/prefect_flow-worker-flow.py deploy

# Run orchestrator
python flows/prefect_flow-worker-flow.py run
```

### 2. `scripts/start_workers.py`
Helper script to manage multiple Prefect workers.

**Features:**
- Start N workers concurrently
- Monitor and auto-restart failed workers
- Graceful shutdown on Ctrl+C
- Customizable work pool

**Usage:**
```bash
# Start 3 workers
python scripts/start_workers.py --workers 3

# Custom pool
python scripts/start_workers.py --pool my-pool --workers 5
```

### 3. `docs/distributed_workflow_guide.md`
Comprehensive guide for distributed workflows.

**Covers:**
- Architecture overview
- Setup instructions
- Scaling strategies
- Monitoring and troubleshooting
- Production considerations
- Task vs subflow comparison

### 4. `docs/QUICKSTART_DISTRIBUTED.md`
5-minute quick start guide.

**Steps:**
1. Start Prefect server
2. Configure server
3. Deploy flows
4. Start workers
5. Run flow

### 5. Updated `makefile`
Added commands for distributed workflows.

**New Commands:**
```bash
make deploy-flows       # Deploy flows to work pool
make start-workers      # Start 3 workers (default)
make start-workers N=5  # Start 5 workers
make run-distributed    # Run distributed ETL
```

## Usage Pattern

### Complete Workflow

```bash
# One-time setup
make prefect-server    # Start Prefect server
make prefect-setup     # Configure server & work pools
make deploy-flows      # Deploy flows to work pool

# Run workflow
make start-workers     # Terminal 1: Start workers
make run-distributed   # Terminal 2: Run orchestrator

# Or run from UI
# Visit http://localhost:4200 → Deployments → Run
```

### Deployment Details

When you run `make deploy-flows`, it creates 4 deployments:

1. **main-etl-job/main-etl-deployment**
   - The orchestrator flow
   - Run this to start the entire process

2. **process-table-etl/process-table-etl-deployment**
   - Subflow for processing individual tables
   - Called by orchestrator (don't run directly)

3. **cleanup-flow-1/cleanup-flow-1-deployment**
   - Cleanup subflow 1
   - Called by orchestrator after tables complete

4. **cleanup-flow-2/cleanup-flow-2-deployment**
   - Cleanup subflow 2
   - Called by orchestrator after tables complete

## Execution Flow

```
1. User runs main_etl() orchestrator (async)
   ↓
2. Orchestrator uses run_deployment() to trigger 20 subflows
   → Each becomes separate flow run in work queue
   ↓
3. Workers poll work queue and pick up subflows
   → Worker 1: Table 0
   → Worker 2: Table 1
   → Worker 3: Table 2
   ↓
4. As workers finish, they pick up next queued subflows
   → Worker 1: Table 0 done → Table 3
   → Worker 2: Table 1 done → Table 4
   → Worker 3: Table 2 done → Table 5
   ↓
5. Continue until all 20 tables processed
   ↓
6. Orchestrator triggers cleanup subflows via run_deployment()
   → Worker 1: cleanup_flow1
   → Worker 2: cleanup_flow2
   ↓
7. Wait for cleanup to complete (via wait_for_flow_runs)
   ↓
8. Orchestrator completes ✅
```

## Performance Comparison

### Sequential Execution
- 20 tables × 30 seconds = 600 seconds (10 minutes)
- Plus cleanup = 610 seconds total

### Task Concurrency (Previous)
- Max 3 concurrent via database tag
- 7 batches × 30 seconds = 210 seconds
- Plus cleanup = 215 seconds total

### Distributed Subflows (New)

**With 3 workers:**
- 7 batches × 30 seconds = 210 seconds
- Plus cleanup = 215 seconds total
- Same as task concurrency BUT can scale horizontally

**With 5 workers:**
- 4 batches × 30 seconds = 120 seconds
- Plus cleanup = 125 seconds total
- **~2 minutes vs 10 minutes!**

**With 10 workers:**
- 2 batches × 30 seconds = 60 seconds
- Plus cleanup = 65 seconds total
- **~1 minute vs 10 minutes!**

## Scaling Strategies

### 1. Horizontal Scaling (Add Workers)
```bash
# More workers = more concurrency
make start-workers N=10
```

### 2. Distributed Workers (Different Machines)
```bash
# Machine 1
prefect worker start --pool default-pool --name worker-m1

# Machine 2
prefect worker start --pool default-pool --name worker-m2

# Machine N
prefect worker start --pool default-pool --name worker-mN
```

### 3. Work Pool Concurrency
```bash
# Limit total concurrent subflows
prefect work-pool set-concurrency-limit default-pool 10
```

### 4. Task-Level Concurrency (Still Applies)
```bash
# Limit concurrent database operations
export PREFECT_CONCURRENCY_LIMIT=5
make prefect-setup
```

## Key Differences from Previous Implementation

| Aspect | Task Concurrency | Distributed Subflows |
|--------|-----------------|---------------------|
| **Execution Unit** | Task | Flow (subflow) |
| **Concurrency Control** | Task tags | Work pool + workers |
| **Distribution** | Single process | Multiple workers |
| **Scaling** | Vertical only | Horizontal |
| **Isolation** | Tasks in same flow | Independent flow runs |
| **Deployment** | `.serve()` | `Deployment.build_from_flow()` |
| **Triggering** | `task.submit()` | `await run_deployment()` |
| **Orchestrator** | Sync flow | Async flow |
| **Workers** | Not required | Required |
| **Best For** | Simple workflows | Complex/distributed workflows |

## Production Considerations

### 1. Anaconda Enterprise Workbench
```bash
# Set environment variables
export PREFECT_API_URL=https://your-server.com/api
export PREFECT_API_KEY=pnu_your_key
export PREFECT_WORK_POOL=production-pool

# Deploy flows
python flows/prefect_flow-worker-flow.py deploy

# Start workers (use process manager like systemd)
prefect worker start --pool production-pool
```

### 2. Worker Management
Use process manager for reliable worker operation:
- **Linux**: systemd
- **macOS**: launchd  
- **Cross-platform**: supervisord

### 3. Multiple Work Pools
Separate workloads by creating dedicated pools:
```bash
# ETL work pool (heavy compute)
prefect work-pool create etl-pool

# Cleanup work pool (light tasks)
prefect work-pool create cleanup-pool
```

### 4. Resource Limits
Configure per-worker resources:
```python
deployment = Deployment.build_from_flow(
    flow=process_table_etl,
    work_pool_name="etl-pool",
    infrastructure_overrides={
        "cpu": 2,
        "memory": 4096,
    }
)
```

## Monitoring

### CLI Commands
```bash
# View workers
prefect worker ls

# View work pool
prefect work-pool inspect default-pool

# View flow runs
prefect flow-run ls

# View specific flow
prefect flow-run ls --flow-name process-table-etl
```

### UI Dashboard
Visit http://localhost:4200:
- Real-time flow run status
- Worker activity
- Work queue depth
- Execution timeline
- Logs and errors

## Migration Notes

### Existing Code
- Previous task-based flow still works: `flows/prefect_flow.py`
- Use `make run-flow` for old approach
- Use `make run-distributed` for new approach

### When to Use Each

**Task Concurrency (`prefect_flow.py`):**
- Simple workflows
- Single machine execution
- Limited scale requirements
- Quick development/testing

**Distributed Subflows (`prefect_flow-worker-flow.py`):**
- Complex workflows
- Multi-machine execution
- Horizontal scaling needed
- Production workloads
- High concurrency requirements

## Troubleshooting

### Workers not picking up work
```bash
# Check workers running
prefect worker ls

# Verify work pool
prefect work-pool ls

# Check deployments
prefect deployment ls
```

### Flow runs stuck in Scheduled
- Ensure workers are started
- Check work pool name matches
- Verify server connection

### Authentication errors
```bash
export PREFECT_API_URL=http://localhost:4200/api
export PREFECT_API_KEY=pnu_your_key  # If needed
```

## References

- **Quick Start**: `docs/QUICKSTART_DISTRIBUTED.md`
- **Full Guide**: `docs/distributed_workflow_guide.md`
- **Main Flow**: `flows/prefect_flow-worker-flow.py`
- **Worker Script**: `scripts/start_workers.py`

## Summary

✅ **Converted from**: Task concurrency (single flow run)  
✅ **Converted to**: Distributed subflows (multiple flow runs)  
✅ **Benefits**: Horizontal scaling, better isolation, production-ready  
✅ **Usage**: Deploy → Start workers → Run orchestrator  
✅ **Performance**: 10min → 2min (with 5 workers) or 1min (with 10 workers)
