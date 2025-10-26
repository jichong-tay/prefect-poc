# Scripts Directory

Utility scripts for Prefect setup, testing, and administration.

## Quick Start - Complete Setup

**Recommended: Use the automated setup script**

```bash
# Install dependencies
make setup

# Run complete automated setup
make prefect-setup
```

This will automatically:
- ✅ Start Prefect server (Docker)
- ✅ Create work pools
- ✅ Configure concurrency limits
- ✅ Verify everything works

## Available Scripts

### 🚀 setup_prefect_server.py (NEW - Recommended)

**Purpose:** Complete automated Prefect server setup - one command does everything!

**Usage:**
```bash
# Use make command (easiest)
make prefect-setup

# Or run directly
python scripts/setup_prefect_server.py

# With custom settings
python scripts/setup_prefect_server.py --port 4200 --concurrency 5
```

**Options:**
- `--port` - Prefect server port (default: 4200)
- `--concurrency` - Max concurrent tasks (default: 3)
- `--concurrency-tag` - Tag for concurrency limit (default: "database")
- `--work-pool` - Work pool name (default: "default-pool")

**What it does:**
1. Checks Docker availability
2. Starts Prefect server container (creates new or starts existing)
3. Waits for server to be ready
4. Creates work pool for flow execution
5. Sets up concurrency limits for tagged tasks
6. Verifies all configurations

**Perfect for:**
- First-time setup
- Clean development environment
- CI/CD pipelines
- Getting started quickly

### 🔧 setup_concurrency_limit.py

**Purpose:** Configure server-side concurrency limits on your Prefect server.

**Usage:**
```bash
# Development (no auth)
export PREFECT_API_URL=http://localhost:4200/api
python scripts/setup_concurrency_limit.py

# Production (with auth)
export PREFECT_API_URL=https://your-server.com/api
export PREFECT_API_KEY=pnu_your_key
python scripts/setup_concurrency_limit.py
```

**What it does:**
- Creates a concurrency limit named "database" with max 3 concurrent tasks
- Lists existing concurrency limits
- Validates connection to Prefect server
- Supports both authenticated and non-authenticated modes

**Customization:**
Edit the script to change the limit settings:
```python
await create_concurrency_limit(
    limit_name="database",    # Change tag name
    max_concurrent=3,         # Change limit
    api_key=prefect_api_key
)
```

### 🧪 test_prefect_auth.py

**Purpose:** Test and validate Prefect server connection and authentication.

**Usage:**
```bash
# Test local connection (no auth)
export PREFECT_API_URL=http://localhost:4200/api
python scripts/test_prefect_auth.py

# Test production connection (with auth)
export PREFECT_API_URL=https://your-server.com/api
export PREFECT_API_KEY=pnu_your_key
python scripts/test_prefect_auth.py
```

**What it tests:**
1. ✅ Connection to Prefect server
2. ✅ Authentication (if API key provided)
3. ✅ Read flows permission
4. ✅ Read work pools permission
5. ✅ Read concurrency limits permission

**Output:**
- Shows connection details
- Lists available flows, work pools, and concurrency limits
- Provides troubleshooting tips if connection fails

## Quick Commands

```bash
# Test connection first
python scripts/test_prefect_auth.py

# Then setup concurrency limits
python scripts/setup_concurrency_limit.py

# Verify limits were created
prefect concurrency-limit list
```

## Environment Variables

Both scripts use these environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PREFECT_API_URL` | Yes | `http://localhost:4200/api` | Prefect server API endpoint |
| `PREFECT_API_KEY` | Production only | - | API key for authentication |

## Troubleshooting

### Script fails with "Connection refused"
```bash
# Check if Prefect server is running
curl http://localhost:4200/api/health

# Start server if needed
docker start prefect-server
```

### Script fails with "Unauthorized"
```bash
# Verify API key is set
echo $PREFECT_API_KEY

# Test key validity
python scripts/test_prefect_auth.py
```

### Concurrency limit already exists
```bash
# Delete existing limit
prefect concurrency-limit delete database

# Run setup again
python scripts/setup_concurrency_limit.py
```

## Development

### Adding New Scripts

When adding new utility scripts:

1. **Follow naming convention:** `verb_noun.py` (e.g., `setup_worker.py`)
2. **Include docstring:** Explain purpose and usage
3. **Support both modes:** Dev (no auth) and prod (with auth)
4. **Add error handling:** Clear error messages
5. **Update this README:** Document the new script

### Script Template

```python
#!/usr/bin/env python3
"""
Brief description of what the script does.

Usage:
    python scripts/your_script.py
"""

import asyncio
import os
from prefect.client.orchestration import get_client


async def main():
    """Main function."""
    api_url = os.getenv("PREFECT_API_URL", "http://localhost:4200/api")
    api_key = os.getenv("PREFECT_API_KEY")
    
    print(f"Connecting to: {api_url}")
    
    # Setup auth if needed
    httpx_settings = {}
    if api_key:
        httpx_settings["headers"] = {"Authorization": f"Bearer {api_key}"}
    
    async with get_client(httpx_settings=httpx_settings) as client:
        # Your logic here
        pass


if __name__ == "__main__":
    asyncio.run(main())
```

## See Also

- [Authentication Guide](../docs/authentication_guide.md) - Detailed auth documentation
- [Concurrency Guide](../docs/concurrency_guide.md) - How concurrency limits work
- [Quick Reference](../docs/auth_quick_reference.md) - Command cheat sheet
