# Flows Directory

Prefect flow definitions demonstrating production patterns.

## Available Flows

### 🚀 prefect_flow.py (Production ETL Flow)

**Purpose:** Production-ready ETL flow with parallel task execution and server-side concurrency control.

**Features:**
- ✅ Parallel execution of 20 SQL queries
- ✅ Server-side concurrency limiting (max 3 concurrent)
- ✅ Proper future handling and result collection
- ✅ Cleanup tasks that wait for queries to complete
- ✅ Error handling with automatic retries
- ✅ Authentication support (dev + prod)

**Usage:**
```bash
# Development
export PREFECT_API_URL=http://localhost:4200/api
python flows/prefect_flow.py

# Production
export PREFECT_API_URL=https://your-server.com/api
export PREFECT_API_KEY=pnu_your_key
python flows/prefect_flow.py
```

**Architecture:**
```
main_etl()
└── sub_etl()
    ├── sql_query(0) ⎤
    ├── sql_query(1) ⎥ ← Max 3 concurrent (server-controlled)
    ├── sql_query(2) ⎦
    ├── ... (17 more)
    ├── cleanup1() ← Waits for all queries
    └── cleanup2() ← Runs after cleanup1
```

**Key Patterns:**
```python
# Submit all tasks
futures = [sql_query.submit(i) for i in range(20)]

# Wait for completion (server limits to 3 concurrent)
results = [f.result() for f in futures]

# Cleanup after all tasks done
cleanup1.submit().result()
```

## Flow Patterns

### Pattern 1: Sequential Execution
```python
@flow
def sequential_flow():
    result1 = task1()
    result2 = task2(result1)
    result3 = task3(result2)
    return result3
```

**Use when:** Tasks depend on each other

### Pattern 2: Parallel Execution (Uncontrolled)
```python
@flow
def parallel_flow():
    futures = [task.submit(i) for i in range(10)]
    results = [f.result() for f in futures]
    return results
```

**Use when:** Tasks are independent and system can handle load

### Pattern 3: Parallel with Server-Side Concurrency (Recommended)
```python
@task(tags=["database"])  # Server controls concurrency by tag
def query_task(i):
    # Query logic
    pass

@flow
def controlled_flow():
    # Submit all - server limits concurrent execution
    futures = [query_task.submit(i) for i in range(20)]
    results = [f.result() for f in futures]
    return results
```

**Use when:** Need to limit concurrent execution (e.g., database connections)

### Pattern 4: Batched Parallel (Manual Control)
```python
@flow
def batched_flow():
    batch_size = 3
    all_results = []
    
    for i in range(0, 20, batch_size):
        batch = range(i, min(i + batch_size, 20))
        futures = [task.submit(j) for j in batch]
        batch_results = [f.result() for f in futures]
        all_results.extend(batch_results)
    
    return all_results
```

**Use when:** Need explicit batch control (checkpoints, progress tracking)

## Running Flows

### Local Execution (Development)
```bash
# Run flow directly
python flows/prefect_flow.py

# Monitor at http://localhost:4200
```

### Deployed Execution (Production)
```bash
# 1. Deploy flow
prefect deploy flows/prefect_flow.py:main_etl \
  --name prod-etl \
  --pool prod-pool

# 2. Start worker
prefect worker start --pool prod-pool

# 3. Trigger via API or schedule
prefect deployment run main-etl-job/prod-etl
```

## Best Practices

### ✅ DO:

1. **Use task tags for concurrency control**
   ```python
   @task(tags=["database", "read-only"])
   def query(): pass
   ```

2. **Handle futures properly**
   ```python
   futures = [task.submit(i) for i in range(10)]
   results = [f.result() for f in futures]  # Wait for all
   ```

3. **Add error handling**
   ```python
   @task(retries=2, retry_delay_seconds=10)
   def query(): pass
   ```

4. **Return values from tasks**
   ```python
   @task
   def process():
       return {"status": "success", "count": 100}
   ```

5. **Use get_run_logger()**
   ```python
   logger = get_run_logger()
   logger.info("Processing...")
   ```

### ❌ DON'T:

1. **Don't forget .result()**
   ```python
   # ❌ Wrong - doesn't wait
   task.submit(i)
   
   # ✅ Correct - waits for completion
   task.submit(i).result()
   ```

2. **Don't call .result() in loop if you want parallelism**
   ```python
   # ❌ Wrong - runs sequentially
   for i in range(10):
       result = task.submit(i).result()
   
   # ✅ Correct - runs in parallel
   futures = [task.submit(i) for i in range(10)]
   results = [f.result() for f in futures]
   ```

3. **Don't hardcode credentials**
   ```python
   # ❌ Wrong
   db_url = "postgres://user:pass@host/db"
   
   # ✅ Correct
   db_url = os.getenv("DATABASE_URL")
   ```

## Testing Flows

```bash
# Test locally first
python flows/your_flow.py

# Check logs in UI
open http://localhost:4200

# Test with authentication
export PREFECT_API_KEY=test_key
python flows/your_flow.py
```

## Creating New Flows

### Template:
```python
import time
import os
from prefect import task, flow, get_run_logger


@task(
    name="my-task",
    tags=["category"],
    retries=2,
    retry_delay_seconds=10
)
def my_task(param):
    """Task description."""
    logger = get_run_logger()
    logger.info(f"Processing {param}...")
    
    # Your logic here
    result = param * 2
    
    logger.info(f"Completed: {result}")
    return {"param": param, "result": result}


@flow(name="my-flow", log_prints=True)
def my_flow():
    """Flow description."""
    logger = get_run_logger()
    logger.info("Starting flow...")
    
    # Submit tasks
    futures = [my_task.submit(i) for i in range(10)]
    
    # Wait for completion
    results = [f.result() for f in futures]
    
    logger.info(f"Completed {len(results)} tasks")
    return results


if __name__ == "__main__":
    # Support both dev and prod
    prefect_api_url = os.getenv("PREFECT_API_URL", "http://localhost:4200/api")
    prefect_api_key = os.getenv("PREFECT_API_KEY")
    
    print(f"Prefect Server: {prefect_api_url}")
    if prefect_api_key:
        print(f"Using API Key: {prefect_api_key[:8]}...")
    
    # Run flow
    my_flow()
```

## Troubleshooting

### Flow doesn't run
```bash
# Check server connection
curl http://localhost:4200/api/health

# Verify environment
echo $PREFECT_API_URL
```

### Tasks run sequentially (not parallel)
```bash
# Check if you're calling .result() in the submission loop
# Should be:
futures = [task.submit(i) for i in range(10)]
results = [f.result() for f in futures]
```

### Concurrency limit not working
```bash
# Verify concurrency limit exists
prefect concurrency-limit list

# Check task has correct tag
grep "tags=" flows/your_flow.py

# Create limit if missing
python scripts/setup_concurrency_limit.py
```

## See Also

- [Concurrency Guide](../docs/concurrency_guide.md) - How to control parallel execution
- [Authentication Guide](../docs/authentication_guide.md) - Dev/prod auth setup
- [Prefect Docs](https://docs.prefect.io) - Official documentation
