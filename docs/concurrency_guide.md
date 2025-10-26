# Server-Side Concurrency Control with Prefect

## Overview

Instead of manually batching tasks in your code, Prefect can control concurrency at the **server level** using **concurrency limits** and **task tags**.

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│ YOUR CODE (prefect_flow.py)                                 │
│                                                             │
│ @task(tags=["database"])                                    │
│ def sql_query(table):                                       │
│     # Execute query                                         │
│                                                             │
│ @flow                                                       │
│ def sub_etl():                                              │
│     # Submit ALL 20 at once                                 │
│     futures = [sql_query.submit(i) for i in range(20)]      │
│     results = [f.result() for f in futures]                 │
└─────────────────────────────────────────────────────────────┘
                    │
                    │ All 20 submitted
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ PREFECT SERVER (with concurrency limit)                     │
│                                                             │
│ Concurrency Limit: "database" = 3                           │
│                                                             │
│ Task Queue:                                                 │
│   ✅ Running: table 0, table 1, table 2                     │
│   ⏳ Waiting: table 3, table 4, ..., table 19               │
│                                                             │
│ When table 0 finishes → table 3 starts automatically        │
└─────────────────────────────────────────────────────────────┘
```

## Setup Steps

### Step 1: Tag Your Tasks

Your tasks need a tag that matches the concurrency limit:

```python
@task(
    name="sql-query-task",
    tags=["database"],  # ← This tag!
    retries=2
)
def sql_query(table):
    # Your query logic
    pass
```

✅ **Already done in your `prefect_flow.py`!**

### Step 2: Create Concurrency Limit on Server

Run the setup script:

```bash
cd /Users/jichong/projects/playground/BOS/prefect-poc
export PREFECT_API_URL=http://localhost:4200/api
python setup_concurrency_limit.py
```

This creates a server-side rule: **max 3 tasks with tag "database" at once**

**OR** do it manually via CLI:

```bash
export PREFECT_API_URL=http://localhost:4200/api
prefect concurrency-limit create database 3
```

**OR** via the Prefect UI:
- Go to http://localhost:4200
- Settings → Concurrency Limits
- Click "+ Create"
- Tag: `database`
- Limit: `3`

### Step 3: Run Your Flow

```bash
python streamlit/prefect_flow.py
```

Watch in the UI at http://localhost:4200 - you'll see exactly 3 queries running at a time!

## Code Changes Made

### Before (Your Original - Had Issues):
```python
@flow
def sub_etl():
    for table in range(20):
        sql_query.submit(table)  # No future handling
    cleanup1.submit()            # Runs immediately!
    cleanup2.submit()            # Doesn't wait!
```

**Problems:**
- ❌ Doesn't wait for queries to finish
- ❌ Cleanup runs while queries still running
- ❌ No result collection

### After (Fixed):
```python
@flow
def sub_etl():
    # Submit all 20 queries
    query_futures = [sql_query.submit(i) for i in range(20)]
    
    # Wait for ALL to complete (server limits to 3 concurrent)
    query_results = [f.result() for f in query_futures]
    
    # NOW run cleanup (only after queries done)
    cleanup1.submit().result()
    cleanup2.submit().result()
    
    return query_results
```

**Improvements:**
- ✅ Proper future handling
- ✅ Cleanup waits for queries
- ✅ Collects all results
- ✅ Server controls concurrency (not your code!)

## Execution Timeline

```
Time: 0s
├── Submit all 20 queries to server
├── Server starts 3 tasks (limit = 3)
│   ├── Query 0 ⏳
│   ├── Query 1 ⏳
│   └── Query 2 ⏳
└── Queries 3-19 queued ⏸️

Time: 30s
├── Query 0 completes ✅
├── Server starts Query 3 ⏳
│   ├── Query 1 ⏳
│   ├── Query 2 ⏳
│   └── Query 3 ⏳
└── Queries 4-19 queued ⏸️

Time: 60s
├── Query 1 completes ✅
├── Server starts Query 4 ⏳
... (continues)

Time: 200s
└── All 20 queries complete ✅

Time: 200s
├── cleanup1 starts ⏳
└── cleanup2 starts ⏳

Time: 205s
└── All done! ✅
```

## Advantages of Server-Side Concurrency

### ✅ Pros:
1. **Clean Code** - No batching logic in your flow
2. **Centralized Control** - Change limit without changing code
3. **Team-Wide** - All deployments respect the same limit
4. **Dynamic** - Adjust limit in real-time via UI
5. **Cross-Flow** - Limits work across multiple flows

### 🤔 Considerations:
1. **Requires Server** - Won't work in local-only mode without server
2. **Setup Step** - Need to create limit before running
3. **Tag Management** - Must remember to tag tasks correctly

## Adjusting the Limit

Want to run 5 queries at a time instead of 3? Just update the limit:

```bash
# Via CLI
prefect concurrency-limit delete database
prefect concurrency-limit create database 5

# OR via UI
# Settings → Concurrency Limits → Edit "database" → Change to 5
```

**No code changes needed!** 🎉

## Monitoring

Watch your flow in the Prefect UI:
- http://localhost:4200
- Click on your flow run
- You'll see the task graph
- Tasks will show "Pending" (waiting for concurrency slot)
- Exactly 3 will show "Running" at any time

## Troubleshooting

### Queries all run at once (no limiting)?

**Check:**
1. Did you create the concurrency limit? `prefect concurrency-limit list`
2. Is the tag correct? Must be `tags=["database"]` in your task
3. Is the server running? Check http://localhost:4200

### Queries don't start at all?

**Check:**
1. Is a worker running? `prefect worker start --pool <pool-name>`
2. For `.serve()`: The serve process should be running
3. Check logs in the Prefect UI for errors

## Best Practices

1. **Tag Consistently** - Use the same tag for similar resources
   - `tags=["database"]` for DB queries
   - `tags=["api"]` for API calls
   - `tags=["heavy-compute"]` for CPU-intensive tasks

2. **Set Appropriate Limits** - Based on your resources
   - Database: Check `max_connections` setting
   - APIs: Check rate limits
   - CPU: Number of cores

3. **Monitor and Adjust** - Start conservative, increase if stable
   - Start with 3
   - Monitor success rate
   - Increase to 5, then 10, etc.

4. **Use Multiple Tags** - For fine-grained control
   ```python
   @task(tags=["database", "postgres", "read-only"])
   def query_postgres():
       pass
   ```

## Additional Examples

### Example 1: Different Limits for Different Resources

```python
@task(tags=["database"])  # Limit: 3
def db_query():
    pass

@task(tags=["api"])  # Limit: 10
def api_call():
    pass

# Setup:
# prefect concurrency-limit create database 3
# prefect concurrency-limit create api 10
```

### Example 2: Shared Limit Across Flows

```python
# Flow 1
@task(tags=["database"])
def flow1_query():
    pass

# Flow 2
@task(tags=["database"])
def flow2_query():
    pass

# Both flows share the same "database" limit of 3!
# If Flow 1 uses 2 slots, Flow 2 can only use 1
```

## Summary

✅ **Your code is now fixed with:**
- Proper future handling (`.result()` calls)
- Cleanup waits for queries
- Server-side concurrency control via tags
- Error handling with retries

🚀 **To use it:**
1. Run: `python setup_concurrency_limit.py`
2. Run: `python streamlit/prefect_flow.py`
3. Watch: http://localhost:4200

The server will automatically ensure only 3 queries run at a time! 🎉
