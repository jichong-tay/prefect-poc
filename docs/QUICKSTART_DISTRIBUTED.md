# Quick Start: Distributed ETL Flow

Get the distributed ETL flow running in 5 minutes!

## Prerequisites

- Docker installed (for Prefect server)
- Python 3.10+ with dependencies installed (`make setup`)

## Step-by-Step

### 1. Start Prefect Server (1 min)

```bash
# Start Docker-based Prefect server
make prefect-server

# Wait for server to be ready (check http://localhost:4200)
```

### 2. Configure Server (30 sec)

```bash
# Setup work pools and concurrency limits
make prefect-setup
```

Expected output:
```
✅ Setup Complete!
   Work Pool: default-pool
   Concurrency Tag: database
   Max Concurrent: 3
```

### 3. Deploy Flows (30 sec)

```bash
# Deploy all flows to work pool
make deploy-flows
```

Expected output:
```
✅ Deployed: main-etl-job
✅ Deployed: process-table-etl
✅ Deployed: cleanup-flow-1
✅ Deployed: cleanup-flow-2
```

### 4. Start Workers (30 sec)

```bash
# Terminal 1: Start 3 workers
make start-workers

# Or specify custom number
make start-workers N=5
```

Expected output:
```
✅ All 3 worker(s) started successfully!
💡 Workers are now polling for flow runs...
```

### 5. Run the Flow (2 min)

```bash
# Terminal 2: Run distributed ETL flow
make run-distributed
```

**Or run from UI:**
1. Visit http://localhost:4200
2. Go to "Deployments"
3. Click on "main-etl-job/main-etl-deployment"
4. Click "Quick Run"

### 6. Watch Execution

Visit http://localhost:4200 to see:
- 20 table processing subflows running across workers
- Cleanup flows executing after all tables complete
- Real-time execution timeline

## What's Happening?

```
main_etl() async orchestrator
    ↓
Triggers 20 subflows via run_deployment()
    ↓
┌─────────────┬─────────────┬─────────────┐
│  Worker 1   │  Worker 2   │  Worker 3   │
│             │             │             │
│ Table 0     │ Table 1     │ Table 2     │
│ (30s)       │ (30s)       │ (30s)       │
└─────────────┴─────────────┴─────────────┘
    ↓ Complete      ↓             ↓
┌─────────────┬─────────────┬─────────────┐
│ Table 3     │ Table 4     │ Table 5     │
│ (30s)       │ (30s)       │ (30s)       │
└─────────────┴─────────────┴─────────────┘
    
... continues until all 20 tables done ...

    ↓
Trigger cleanup subflows via run_deployment()
    ↓
┌─────────────┬─────────────┐
│ Cleanup 1   │ Cleanup 2   │
│ (5s)        │ (5s)        │
└─────────────┴─────────────┘
    ↓
Done! ✅
```

**Timeline:**
- 3 workers processing 20 tables = ~200 seconds (7 batches × 30s each)
- Plus cleanup = ~205 seconds total
- Compare to sequential: 20 × 30s = 600 seconds (10 minutes!)

## Scaling Up

### More Workers = Faster Execution

```bash
# 5 workers instead of 3
make start-workers N=5
```

Timeline with 5 workers:
- 5 workers × 4 batches × 30s = ~120 seconds (2 minutes!)

### Adjust Concurrency

The "database" tag limits concurrent database operations:

```bash
# Increase from 3 to 10
export PREFECT_CONCURRENCY_LIMIT=10
make prefect-setup
```

## Common Commands

```bash
# View all deployments
prefect deployment ls

# View active workers
prefect worker ls

# View flow runs
prefect flow-run ls

# Check work pool status
prefect work-pool inspect default-pool

# Stop workers (in worker terminal)
Ctrl+C
```

## Troubleshooting

### Issue: Workers not picking up work

**Solution:**
```bash
# Check workers are running
prefect worker ls

# Ensure work pool matches deployment
prefect work-pool ls
```

### Issue: Flow runs stuck in "Scheduled"

**Solution:**
- Make sure workers are started (`make start-workers`)
- Check server is running (http://localhost:4200)

### Issue: Authentication errors

**Solution:**
```bash
# Set API URL
export PREFECT_API_URL=http://localhost:4200/api

# For production with auth
export PREFECT_API_KEY=pnu_your_key
```

## Next Steps

1. **Monitor in UI**: Watch real-time execution at http://localhost:4200
2. **Adjust concurrency**: Try different worker counts
3. **Read full guide**: See `docs/distributed_workflow_guide.md`
4. **Production deploy**: Configure for Anaconda Enterprise Workbench

## All Commands Summary

```bash
# Complete setup (run once)
make prefect-server    # Start server
make prefect-setup     # Configure server
make deploy-flows      # Deploy flows

# Run workflow (every time)
make start-workers     # Terminal 1
make run-distributed   # Terminal 2

# Or run from UI (http://localhost:4200)
```

That's it! Your distributed ETL flow is running. 🎉
