# Prefect Server Setup - Updated Usage Guide

## Overview

The `setup_prefect_server.py` script now supports **three modes**:

1. **Local Dev (Docker)**: Uses Docker to run Prefect server
2. **Production (Start Native)**: Starts Prefect server natively (no Docker) on Anaconda workbench
3. **Production (Connect)**: Connects to existing running Prefect server

## Configuration via Environment Variables

The script uses **Prefect's native settings** (no argparse), configured via environment variables:

### Core Settings

```bash
# Prefect API URL
export PREFECT_API_URL=http://localhost:4200/api

# API Key (production only)
export PREFECT_API_KEY=pnu_your_api_key_here

# Server start mode (NEW!)
export PREFECT_START_SERVER=auto      # auto-detect (default)
# OR
export PREFECT_START_SERVER=docker    # Force Docker
# OR
export PREFECT_START_SERVER=native    # Start server natively (no Docker)
# OR
export PREFECT_START_SERVER=no        # Connect to existing server only
```

### Optional Settings

```bash
# Concurrency configuration
export PREFECT_CONCURRENCY_TAG=database     # Default: "database"
export PREFECT_CONCURRENCY_LIMIT=5          # Default: 3

# Work pool configuration
export PREFECT_WORK_POOL=my-pool           # Default: "default-pool"

# Docker settings (local dev only)
export PREFECT_SERVER_PORT=4200            # Default: 4200
```

## Usage Examples

### 1. Local Development (Docker)

```bash
# Simple - uses defaults
make prefect-setup

# Or directly
python scripts/setup_prefect_server.py

# With custom concurrency
export PREFECT_CONCURRENCY_LIMIT=10
python scripts/setup_prefect_server.py
```

**What happens:**
1. ✅ Checks Docker availability
2. ✅ Starts/creates Prefect server container
3. ✅ Waits for server to be ready
4. ✅ Creates work pool
5. ✅ Sets up concurrency limits

### 2. Production (Start Native Server on Anaconda Workbench)

```bash
# Set to start server natively
export PREFECT_API_URL=http://localhost:4200/api
export PREFECT_START_SERVER=native

# Run setup (starts server WITHOUT Docker + configures)
python scripts/setup_prefect_server.py
```

**What happens:**
1. ✅ Starts Prefect server natively in background
2. ✅ Waits for server to be ready
3. ✅ Creates work pool
4. ✅ Sets up concurrency limits

**Note:** The server runs in background. To stop it, you'll need to kill the process.

### 3. Production (Connect to Existing Server)

```bash
# Set production server URL
export PREFECT_API_URL=https://your-prefect-server.com/api
export PREFECT_API_KEY=pnu_your_production_key
export PREFECT_START_SERVER=no

# Run setup (connects to existing server + configures)
python scripts/setup_prefect_server.py
```

**What happens:**
1. ✅ Connects to existing Prefect server
2. ✅ Verifies connection
3. ✅ Creates work pool
4. ✅ Sets up concurrency limits

## Mode Detection

The script automatically detects which mode to use based on `PREFECT_START_SERVER`:

| PREFECT_START_SERVER | Mode |
|---------------------|------|
| `auto` (default) | Detects based on API URL (localhost = Docker) |
| `docker` | Force Docker mode |
| `native` | Start Prefect server natively (no Docker) |
| `no` | Connect to existing server only |

## Example Workflows

### First Time Local Setup

```bash
# 1. Install dependencies
make setup

# 2. Run automated setup (starts Docker + configures)
make prefect-setup

# 3. Verify
curl http://localhost:4200/api/health

# 4. Run a flow
make run-flow
```

### Production Setup on Anaconda Workbench (Start Server)

```bash
# 1. Set environment to start server natively
export PREFECT_API_URL=http://localhost:4200/api
export PREFECT_START_SERVER=native

# 2. Run setup (starts server + configures)
python scripts/setup_prefect_server.py

# Server is now running in background
# Note: You'll see the PID - save it to stop later

# 3. Run flows
python flows/prefect_flow.py
```

### Production Setup on Existing Server

```bash
# 1. Set environment (add to ~/.bashrc or workbench config)
export PREFECT_API_URL=https://prefect.company.com/api
export PREFECT_API_KEY=pnu_abc123xyz
export PREFECT_START_SERVER=no

# 2. Run configuration script (connects to existing server)
python scripts/setup_prefect_server.py

# 3. Run flows
python flows/prefect_flow.py
```

### Custom Configuration

```bash
# Different concurrency settings
export PREFECT_CONCURRENCY_TAG=api-calls
export PREFECT_CONCURRENCY_LIMIT=5
export PREFECT_WORK_POOL=production-pool

# Run setup with custom config
python scripts/setup_prefect_server.py
```

## Comparison: Before vs After

### Before (argparse)

```bash
# Had to pass arguments manually
python scripts/setup_prefect_server.py --port 4200 --concurrency 5 --concurrency-tag database
```

### After (Prefect settings)

```bash
# Use Prefect's native environment variables
export PREFECT_CONCURRENCY_LIMIT=5
python scripts/setup_prefect_server.py
```

## Benefits

1. **✅ Consistent with Prefect**: Uses Prefect's built-in settings system
2. **✅ Environment-aware**: Automatically detects dev vs production
3. **✅ No Docker in production**: Works with Anaconda workbench
4. **✅ Flexible**: Configure via env vars, .env file, or shell profile
5. **✅ Idempotent**: Safe to run multiple times

## Troubleshooting

### Script detects wrong mode

```bash
# Explicitly check your API URL
echo $PREFECT_API_URL

# Should be:
# - localhost or 127.0.0.1 for local dev
# - your-server.com for production
```

### Production mode but no API key

```bash
# Script will warn and ask for confirmation
# Set the key:
export PREFECT_API_KEY=pnu_your_key
```

### Docker not needed in production

```bash
# Correct! Script automatically skips Docker steps
# when PREFECT_API_URL points to remote server
```

## See Also

- [Authentication Guide](../docs/authentication_guide.md)
- [Scripts README](README.md)
- [Concurrency Guide](../docs/concurrency_guide.md)
