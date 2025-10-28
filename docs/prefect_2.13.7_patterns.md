# Key Differences in Prefect 2.13.7

## Flow Submission

### ❌ WRONG (Not supported in 2.13.7)
```python
@flow
def main_flow():
    # Cannot use .submit() on flows!
    future = my_subflow.submit(param)  # ❌ AttributeError
    result = future.result()
```

### ✅ CORRECT (Use run_deployment)
```python
@flow
async def main_flow():
    # Use run_deployment to trigger deployed subflows
    flow_run = await run_deployment(
        name="my-subflow/deployment-name",
        parameters={"param": value},
        timeout=0,  # Return immediately, don't wait
    )
    
    # Wait for completion separately
    await wait_for_flow_runs([flow_run.id])
```

## Task vs Flow Execution

### Tasks (Can use .submit())
```python
@task
def my_task(x):
    return x * 2

@flow
def my_flow():
    # Tasks support .submit()
    future = my_task.submit(5)  # ✅ Works
    result = future.result()
```

### Flows (Cannot use .submit())
```python
@flow
def my_subflow(x):
    return x * 2

@flow
def my_main_flow():
    # Option 1: Direct call (runs in same process)
    result = my_subflow(5)  # ✅ Works but not distributed
    
    # Option 2: Call deployed flow via run_deployment (distributed)
    flow_run = await run_deployment(  # ✅ Distributed execution
        name="my-subflow/deployment",
        parameters={"x": 5},
        timeout=0
    )
```

## When to Use Each Approach

### Direct Subflow Call
```python
@flow
def main_flow():
    # Runs in same process, same flow run
    result = subflow()  # Simple, fast, but not distributed
```

**Use when:**
- Simple workflow
- Don't need distribution
- All on same machine
- Quick execution

### Deployed Subflow (run_deployment)
```python
@flow
async def main_flow():
    # Runs as separate flow run on workers
    flow_run = await run_deployment(
        name="subflow/deployment",
        timeout=0
    )
    await wait_for_flow_runs([flow_run.id])
```

**Use when:**
- Need distributed execution
- Multiple workers
- Horizontal scaling
- Independent flow runs
- **Production workloads**

## Complete Example

### File: flows/distributed_example.py

```python
import asyncio
from prefect import task, flow, get_run_logger
from prefect.deployments import run_deployment
from prefect.client.orchestration import get_client


@flow(name="process-item")
def process_item(item_id: int):
    """Subflow that processes one item."""
    logger = get_run_logger()
    logger.info(f"Processing item {item_id}")
    
    # Do work
    result = heavy_task(item_id)
    
    logger.info(f"Item {item_id} complete")
    return result


@task
def heavy_task(item_id: int):
    """Actual work as a task."""
    import time
    time.sleep(10)
    return {"item": item_id, "status": "done"}


@flow(name="orchestrator")
async def orchestrator():
    """Main orchestrator that distributes work."""
    logger = get_run_logger()
    
    # Submit all items as separate flow runs
    flow_run_ids = []
    for i in range(10):
        flow_run = await run_deployment(
            name="process-item/process-item-deployment",
            parameters={"item_id": i},
            timeout=0,
        )
        flow_run_ids.append(flow_run.id)
        logger.info(f"Submitted item {i}")
    
    # Wait for all to complete
    await wait_for_flow_runs(flow_run_ids)
    logger.info("All items processed!")


async def wait_for_flow_runs(flow_run_ids: list):
    """Wait for flow runs to complete."""
    async with get_client() as client:
        pending = set(flow_run_ids)
        
        while pending:
            for run_id in list(pending):
                flow_run = await client.read_flow_run(run_id)
                if flow_run.state.is_final():
                    pending.remove(run_id)
            
            if pending:
                await asyncio.sleep(2)


if __name__ == "__main__":
    import sys
    from prefect.deployments import Deployment
    
    if sys.argv[1] == "deploy":
        # Deploy subflow
        Deployment.build_from_flow(
            flow=process_item,
            name="process-item-deployment",
            work_pool_name="default-pool",
        ).apply()
        
        # Deploy orchestrator
        Deployment.build_from_flow(
            flow=orchestrator,
            name="orchestrator-deployment",
            work_pool_name="default-pool",
        ).apply()
        
    elif sys.argv[1] == "run":
        asyncio.run(orchestrator())
```

## Deployment & Execution

```bash
# 1. Deploy
python flows/distributed_example.py deploy

# 2. Start workers
prefect worker start --pool default-pool

# 3. Run orchestrator
python flows/distributed_example.py run

# Or trigger from UI/CLI
prefect deployment run "orchestrator/orchestrator-deployment"
```

## Important Notes

1. **Main flow must be async** when using `run_deployment()`
2. **Subflows must be deployed** before they can be triggered
3. **Workers must be running** to execute the subflows
4. **Use timeout=0** to submit without waiting
5. **Poll flow run status** to wait for completion

## Comparison

| Feature | Task .submit() | Flow run_deployment() |
|---------|---------------|----------------------|
| Syntax | `task.submit()` | `await run_deployment()` |
| Distribution | Task runner | Work pool + workers |
| Async required | No | Yes (for orchestrator) |
| Deployment needed | No | Yes |
| Workers needed | No | Yes |
| Isolation | Same flow run | Separate flow runs |
| Scaling | Limited | Horizontal |

## Migration Path

### Old approach (tasks only)
```python
@flow
def etl():
    futures = [process.submit(i) for i in range(20)]
    results = [f.result() for f in futures]
```

### New approach (distributed subflows)
```python
@flow
async def etl():
    run_ids = []
    for i in range(20):
        run = await run_deployment(
            name="process/deployment",
            parameters={"i": i},
            timeout=0
        )
        run_ids.append(run.id)
    
    await wait_for_flow_runs(run_ids)
```

## See Also

- Main implementation: `flows/prefect_flow-worker-flow.py`
- Quick start: `docs/QUICKSTART_DISTRIBUTED.md`
- Full guide: `docs/distributed_workflow_guide.md`
