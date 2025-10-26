# Native Server Spawn Logic - Addition Summary

## Overview
Added native Prefect server spawning capability back to `setup_prefect_server.py`. The script can now optionally start a Prefect server process if one is not already running.

## What Was Added

### 1. Import
- Added `subprocess` module for process spawning

### 2. New Methods

#### `start_native_server() -> subprocess.Popen`
Starts a Prefect server as a background native process.

**Features:**
- Spawns `prefect server start --host 0.0.0.0` in background
- Captures stdout/stderr for debugging
- Checks if process starts successfully
- Returns process handle (or None on failure)
- Provides clear error messages

**Output:**
```
🚀 Starting Prefect server...
   This will run in the background
✅ Server process started (PID: 12345)
   Note: Server will continue running in background
   To stop: kill 12345
```

#### `wait_for_server_ready(max_wait: int = 30) -> bool`
Waits for the server to become ready after starting.

**Features:**
- Polls `/health` endpoint with 2s timeout
- Default max wait: 30 seconds
- Shows progress dots while waiting
- Returns True when server responds with 200 OK

**Output:**
```
⏳ Waiting for server to be ready...
.....✅ Server is ready (took 5.2s)
```

### 3. Updated Logic

#### `setup()` Method
Enhanced to optionally start server before configuration:

**Flow:**
1. Check if server is already running
2. If not connected AND `start_server_native` is True:
   - Start native server process
   - Wait for server to be ready
   - Continue with configuration
3. If not connected AND `start_server_native` is False:
   - Show error message
   - Suggest manual start or setting `PREFECT_START_SERVER=native`
   - Exit

**New Messages:**
```
1️⃣  Checking Prefect server...
❌ Cannot connect to server

   Starting native Prefect server...
🚀 Starting Prefect server...
✅ Server process started (PID: 12345)
⏳ Waiting for server to be ready...
✅ Server is ready (took 5.2s)
```

#### Configuration Detection
The script determines whether to start a native server based on:

```python
# From environment variable PREFECT_START_SERVER
start_server_mode = os.getenv("PREFECT_START_SERVER", "auto").lower()

self.start_server_native = start_server_mode in [
    "native",
    "yes", 
    "true",
] or os.getenv("PREFECT_START_SERVER_NATIVE", "").lower() in [
    "yes",
    "true",
    "1",
]
```

**Modes:**
- `auto` (default): Only configure, don't start server
- `native`, `yes`, `true`: Start native server if not running
- `docker`: Reserved for future (currently treated as auto)

### 4. Updated Documentation

#### Docstring
Updated script docstring to show native server option:

```python
"""
Server Management:
- By default, connects to existing server (must be running)
- Set PREFECT_START_SERVER=native to auto-start a native server
- Docker servers must be started manually (make prefect-server)
"""
```

#### Usage Examples
```bash
# Auto-start native server and configure
export PREFECT_API_URL=http://localhost:4200/api
export PREFECT_START_SERVER=native
python scripts/setup_prefect_server.py
```

#### Main Function
Added display of `PREFECT_START_SERVER` configuration:

```
📋 Configuration (from environment):
   PREFECT_API_URL: http://localhost:4200/api
   PREFECT_API_KEY: Not set
   PREFECT_START_SERVER: native
   PREFECT_CONCURRENCY_TAG: database (default)
   PREFECT_CONCURRENCY_LIMIT: 3 (default)
   PREFECT_WORK_POOL: default-pool (default)
```

### 5. Enhanced Output

#### Success with Native Server
```
✅ Setup Complete!
============================================================

📋 Configuration Summary:
   API URL: http://localhost:4200/api
   Work Pool: default-pool
   Concurrency Tag: database
   Max Concurrent: 3

💡 Next Steps:
   1. Run a flow: python flows/prefect_flow.py
   2. View UI: http://localhost:4200

⚠️  Server running in background (PID: 12345)
   To stop: kill 12345
```

## Usage Patterns

### Pattern 1: Manual Server Start (Default)
```bash
# Terminal 1: Start server manually
prefect server start

# Terminal 2: Configure
python scripts/setup_prefect_server.py
```

### Pattern 2: Auto-start Native Server (New!)
```bash
# Single command - starts server and configures
export PREFECT_START_SERVER=native
python scripts/setup_prefect_server.py

# Server runs in background (note PID to kill later)
```

### Pattern 3: Docker (Manual)
```bash
# Terminal 1: Start Docker server
make prefect-server

# Terminal 2: Configure  
python scripts/setup_prefect_server.py
```

## Environment Variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `PREFECT_START_SERVER` | `auto`, `native`, `yes`, `true` | `auto` | Whether to start server if not running |
| `PREFECT_START_SERVER_NATIVE` | `yes`, `true`, `1` | - | Alternative flag to enable native start |

## Benefits

1. **Convenience**: Single command to start + configure
2. **Development**: Faster iteration (no manual server management)
3. **CI/CD**: Can be fully automated in pipelines
4. **Flexibility**: Still supports manual start (default behavior)
5. **Background Process**: Server continues running after script completes

## Important Notes

1. **Background Process**: Native server runs as background process
   - Script provides PID for stopping: `kill <PID>`
   - Server continues running after script exits
   - Not daemonized - will stop if terminal closes

2. **Docker Not Auto-Started**: Docker servers must still be started manually
   - Reason: Docker management is complex and error-prone
   - Use `make prefect-server` for Docker

3. **Production Use**: For production (Anaconda workbench):
   - Set `PREFECT_START_SERVER=native` in environment
   - Or start server separately and use default behavior

4. **Process Management**: Consider using a process manager for production:
   - systemd (Linux)
   - launchd (macOS)
   - supervisord (cross-platform)

## Migration Notes

- Existing usage (default behavior) unchanged - fully backward compatible
- New opt-in feature via `PREFECT_START_SERVER=native`
- No breaking changes to existing scripts or workflows
