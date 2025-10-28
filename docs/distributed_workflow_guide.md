# Distributed ETL Flow with Work Pools

This guide explains how to run the ETL flow in a distributed manner using Prefect work pools and workers.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Prefect Server                         │
│                                                              │
│  ┌────────────────┐         ┌─────────────────────────┐    │
│  │  Work Pool     │         │   Flow Runs Queue       │    │
│  │  (default-pool)│◄────────┤   - process-table-etl   │    │
│  └────────────────┘         │   - cleanup-flow-1       │    │
│         ▲                   │   - cleanup-flow-2       │    │
│         │                   └─────────────────────────┘    │
└─────────┼───────────────────────────────────────────────────┘
          │
          │ Poll for work
          │
    ┌─────┴─────────────────────────────────┐
    │                                        │
┌───▼────┐  ┌──────────┐  ┌──────────┐  ┌──▼──────┐
│Worker 1│  │Worker 2  │  │Worker 3  │  │Worker N │
│        │  │          │  │          │  │         │
│Running │  │Running   │  │Running   │  │Waiting  │
│Table 1 │  │Table 2   │  │Table 3   │  │for work │
└────────┘  └──────────┘  └──────────┘  └─────────┘
```

## How It Works

### 1. Main Orchestrator Flow
- `main_etl()` - Async orchestrator that coordinates the ETL process
- Uses `run_deployment()` to trigger 20 subflows (one per table)
- Each subflow is queued as a separate flow run in the work pool
- Waits for all table processing to complete using `wait_for_flow_runs()`
- Then triggers cleanup subflows via `run_deployment()`

### 2. Subflows (Executed by Workers)
- `process_table_etl(table)` - Processes a single table
- `cleanup_flow1()` - First cleanup operation
- `cleanup_flow2()` - Second cleanup operation

### 3. Workers
- Poll the work pool for queued flow runs
- Execute subflows concurrently (based on number of workers)
- Multiple workers = higher concurrency
- Each worker can run one flow at a time

## Key Benefits

1. **True Distribution**: Subflows run on separate workers (can be different machines)
2. **Scalability**: Add more workers to increase concurrency
3. **Resilience**: Workers can restart without losing queued work
4. **Flexibility**: Workers can run anywhere (local, VMs, containers, K8s)
5. **Work Pool Concurrency**: Server-side control of concurrent executions

## Setup & Usage

### Step 1: Start Prefect Server

```bash
# Docker
make prefect-server

# Or native
prefect server start
```

### Step 2: Configure Server

```bash
# Setup work pools and concurrency limits
python scripts/setup_prefect_server.py

# Or with native server auto-start
export PREFECT_START_SERVER=native
python scripts/setup_prefect_server.py
```

### Step 3: Deploy Flows to Work Pool

```bash
# Deploy all flows (main + subflows) to work pool
python flows/prefect_flow-worker-flow.py deploy
```

Expected output:
```
🚀 Deploying flows to work pool...
✅ Deployed: main-etl-job
✅ Deployed: process-table-etl
✅ Deployed: cleanup-flow-1
✅ Deployed: cleanup-flow-2

🎉 All deployments created successfully!
```

### Step 4: Start Workers

**Option A: Single Worker**
```bash
prefect worker start --pool default-pool
```

**Option B: Multiple Workers (using helper script)**
```bash
# Start 3 workers
python scripts/start_workers.py --workers 3

# Use custom work pool
python scripts/start_workers.py --pool my-pool --workers 5
```

Expected output:
```
============================================================
PREFECT WORKER MANAGER
============================================================
🔗 Prefect Server: http://localhost:4200/api
🏊 Work Pool: default-pool
👷 Workers: 3
============================================================

🚀 Starting worker: worker-1
✅ Worker worker-1 started (PID: 12345)
🚀 Starting worker: worker-2
✅ Worker worker-2 started (PID: 12346)
🚀 Starting worker: worker-3
✅ Worker worker-3 started (PID: 12347)

============================================================
✅ All 3 worker(s) started successfully!
============================================================

💡 Workers are now polling for flow runs...
   Press Ctrl+C to stop all workers
```

### Step 5: Run the Orchestrator Flow

**Option A: Run via Python**
```bash
python flows/prefect_flow-worker-flow.py run
```

**Option B: Run via Prefect CLI**
```bash
prefect deployment run "main-etl-job/main-etl-deployment"
```

**Option C: Run via UI**
1. Visit http://localhost:4200
2. Go to Deployments
3. Find "main-etl-job/main-etl-deployment"
4. Click "Run"

## Execution Flow

When you run the main orchestrator:

```
1. main_etl() starts (async orchestrator)
2. Uses run_deployment() to trigger 20 process_table_etl subflows
   ├─ Table 0 → Queued
   ├─ Table 1 → Queued
   ├─ Table 2 → Queued
   └─ ... (17 more)
   
3. Workers pick up subflows (3 concurrent if 3 workers):
   ├─ Worker 1: Table 0 (running) ████████░░░░░░░░
   ├─ Worker 2: Table 1 (running) ████████░░░░░░░░
   └─ Worker 3: Table 2 (running) ████████░░░░░░░░
   
4. As workers complete, they pick up next queued subflows:
   ├─ Worker 1: Table 0 (done) → Table 3 (running)
   ├─ Worker 2: Table 1 (done) → Table 4 (running)
   └─ Worker 3: Table 2 (done) → Table 5 (running)
   
5. Continue until all 20 tables processed

6. Orchestrator triggers cleanup subflows via run_deployment():
   ├─ cleanup_flow1 → Worker 1
   └─ cleanup_flow2 → Worker 2
   
7. Wait for cleanup to complete (wait_for_flow_runs)

8. main_etl() finishes
```

## Concurrency Control

### Work Pool Level
Control how many subflows can run concurrently across all workers:

```bash
# Set work pool concurrency limit
prefect work-pool set-concurrency-limit default-pool 5
```

### Global Concurrency Limits (via Tags)
Control tasks with specific tags (already configured via setup script):

```python
@task(tags=["database"])  # Limited by concurrency limit on "database" tag
def sql_query(table):
    ...
```

Server configuration:
- Tag: `database`
- Limit: 3 concurrent tasks with this tag across all flows

## Monitoring

### View Active Workers
```bash
prefect worker ls
```

### View Work Pool Status
```bash
prefect work-pool inspect default-pool
```

### View Flow Runs
```bash
# All flow runs
prefect flow-run ls

# Specific flow
prefect flow-run ls --flow-name process-table-etl
```

### UI Dashboard
Visit http://localhost:4200 to see:
- Flow runs in real-time
- Worker status
- Work queue depth
- Execution timeline

## Scaling Strategies

### Horizontal Scaling (More Workers)
```bash
# Start more workers on same machine
python scripts/start_workers.py --workers 10

# Or start workers on different machines
# Machine 1:
prefect worker start --pool default-pool --name worker-machine1

# Machine 2:
prefect worker start --pool default-pool --name worker-machine2
```

### Work Pool Concurrency
```bash
# Increase work pool capacity
prefect work-pool set-concurrency-limit default-pool 20
```

### Task Concurrency (Database Tag)
```bash
# Increase database task concurrency
# Edit and run: python scripts/setup_concurrency_limit.py
export PREFECT_CONCURRENCY_LIMIT=10
python scripts/setup_prefect_server.py
```

## Production Considerations

### 1. Worker Configuration
For production (Anaconda Enterprise Workbench):

```bash
# Set persistent environment variables
export PREFECT_API_URL=https://your-server.com/api
export PREFECT_API_KEY=pnu_your_key
export PREFECT_WORK_POOL=production-pool

# Start workers with process manager (systemd, supervisord, etc.)
prefect worker start --pool production-pool
```

### 2. Worker Pools by Purpose
Create separate work pools for different workload types:

```bash
# ETL work pool
prefect work-pool create etl-pool --type process

# Cleanup work pool
prefect work-pool create cleanup-pool --type process

# Deploy accordingly
# In flow code, specify work_pool_name in Deployment.build_from_flow()
```

### 3. Resource Limits
Set resource limits per worker:

```python
# In deployment
deployment = Deployment.build_from_flow(
    flow=process_table_etl,
    work_pool_name="etl-pool",
    infrastructure_overrides={
        "cpu": 2,
        "memory": 4096,  # MB
    }
)
```

### 4. Error Handling
Tasks already have retry logic:

```python
@task(
    retries=2,
    retry_delay_seconds=10
)
def sql_query(table):
    ...
```

Add flow-level retries if needed:

```python
@flow(retries=1, retry_delay_seconds=60)
def process_table_etl(table: int):
    ...
```

## Troubleshooting

### Workers Not Picking Up Work
1. Check worker is running: `prefect worker ls`
2. Check work pool name matches deployment
3. Check server connection: `echo $PREFECT_API_URL`

### Flow Runs Stuck in Scheduled
1. Ensure workers are started
2. Check work pool has capacity
3. Check concurrency limits not exceeded

### Authentication Errors
```bash
# Set API key
export PREFECT_API_KEY=pnu_your_key

# Verify connection
python scripts/test_prefect_auth.py
```

## Comparison: Tasks vs Subflows

### Previous Approach (Task Concurrency)
```python
# Limited to single flow run
for table in range(20):
    future = sql_query.submit(table)  # Task
# Max concurrency: 3 (via database tag)
```

**Limitations:**
- All tasks run in single flow run
- Can't distribute across machines
- Limited by task runner capacity

### New Approach (Subflow Distribution via run_deployment)
```python
# Distributed across workers (Prefect 2.13.7)
@flow
async def main_etl():
    flow_run_ids = []
    for table in range(20):
        flow_run = await run_deployment(
            name="process-table-etl/process-table-etl-deployment",
            parameters={"table": table},
            timeout=0,
        )
        flow_run_ids.append(flow_run.id)
    
    await wait_for_flow_runs(flow_run_ids)
# Max concurrency: number of workers
```

**Benefits:**
- Each subflow is independent flow run
- Can run on different machines
- Horizontal scaling with more workers
- Better isolation and fault tolerance

## Files Reference

- `flows/prefect_flow-worker-flow.py` - Main ETL flow and subflows
- `scripts/start_workers.py` - Helper to start multiple workers
- `scripts/setup_prefect_server.py` - Server configuration
- `scripts/setup_concurrency_limit.py` - Task concurrency limits

## Next Steps

1. **Test locally**: Follow steps above with 3 workers
2. **Monitor execution**: Watch UI dashboard during run
3. **Adjust concurrency**: Tune worker count and limits
4. **Deploy to production**: Use process manager for workers
5. **Scale horizontally**: Add workers on additional machines
