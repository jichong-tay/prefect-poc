# Authentication Guide for Private Prefect Server

## Overview

This guide covers authentication for **self-hosted/private Prefect servers**. Your code supports both **development mode** (local, no authentication) and **production mode** (private server with API key authentication).

## Development Mode (Local Setup)

```bash
# Local Docker Prefect server - no authentication needed
export PREFECT_API_URL=http://localhost:4200/api

python flows/prefect_flow.py
```

✅ **Works without API key** - Local server has no authentication

## Production Mode (Private Prefect Server)

### Step 1: Get Your API Key

**From Your Private Prefect Server:**
1. Log into your Prefect Server UI
2. Go to Settings → API Keys
3. Click "Create API Key"
4. Give it a name (e.g., "ETL Pipeline")
5. Copy the generated key

### Step 2: Configure Environment Variables

**Option A: Using .env file (recommended)**

```bash
# Create .env file from example
cp .env.example .env

# Edit .env file
nano .env
```

Add your credentials:
```bash
PREFECT_API_URL=https://your-prefect-server.com/api
PREFECT_API_KEY=pnu_1234567890abcdefghijklmnopqrstuvwxyz
```

**Option B: Export directly in terminal**

```bash
export PREFECT_API_URL=https://your-prefect-server.com/api
export PREFECT_API_KEY=pnu_1234567890abcdefghijklmnopqrstuvwxyz
```

### Step 3: Run Your Flow

The code automatically picks up the API key from environment:

```bash
# Load .env file (if using option A)
source .env

# Run the flow - API key is used automatically
python flows/prefect_flow.py
```

### Step 4: Set Up Concurrency Limits

```bash
# Setup script also uses the API key automatically
python scripts/setup_concurrency_limit.py
```

## How Authentication Works

### Flow Execution

```python
# In flows/prefect_flow.py
if __name__ == "__main__":
    # The .serve() method automatically uses PREFECT_API_KEY
    # from environment variables for authentication
    main_etl.serve(name="etl-job")
```

**Behind the scenes:**
1. Prefect reads `PREFECT_API_KEY` from environment
2. Adds `Authorization: Bearer <api_key>` header to all API calls
3. Your private Prefect server validates the token
4. Flow runs with proper authentication

### API Client (Setup Scripts)

```python
# In scripts/setup_concurrency_limit.py
async def create_concurrency_limit(limit_name: str, max_concurrent: int, api_key: str = None):
    httpx_settings = {}
    if api_key:
        httpx_settings["headers"] = {"Authorization": f"Bearer {api_key}"}
    
    async with get_client(httpx_settings=httpx_settings) as client:
        # Client now authenticated
        await client.create_concurrency_limit(...)
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ YOUR FLOW (flows/prefect_flow.py)                          │
│                                                             │
│ Environment:                                                │
│   PREFECT_API_URL=https://prefect.company.com/api          │
│   PREFECT_API_KEY=pnu_abc123...                            │
└─────────────────────────────────────────────────────────────┘
                    │
                    │ HTTP Request with Authorization header:
                    │ Authorization: Bearer pnu_abc123...
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ PRIVATE PREFECT SERVER (SELF-HOSTED)                       │
│                                                             │
│ 1. Validates API key                                        │
│ 2. Checks permissions                                       │
│ 3. Accepts flow run if authorized                           │
│ 4. Applies concurrency limits                               │
└─────────────────────────────────────────────────────────────┘
```

## Security Best Practices

### ✅ DO:

1. **Use Environment Variables**
   ```bash
   export PREFECT_API_KEY=your_key
   # NOT: hardcoded in code!
   ```

2. **Use .env Files for Local Development**
   ```bash
   # .env (not committed to git)
   PREFECT_API_KEY=pnu_dev_key_123
   ```

3. **Use Secrets Management in Production**
   - AWS Secrets Manager
   - Azure Key Vault
   - HashiCorp Vault
   - Kubernetes Secrets

4. **Rotate Keys Regularly**
   - Create new API keys every 90 days
   - Revoke old keys after rotation

5. **Use Service Accounts**
   - Create a dedicated service account for flows
   - Don't use personal API keys in production

### ❌ DON'T:

1. **Never Hardcode API Keys**
   ```python
   # ❌ NEVER DO THIS!
   api_key = "pnu_1234567890"
   ```

2. **Never Commit Keys to Git**
   ```bash
   # Add to .gitignore
   echo ".env" >> .gitignore
   ```

3. **Never Share Keys**
   - Each developer gets their own key
   - Each environment gets its own key

4. **Never Log Keys**
   ```python
   # ❌ Don't print API keys
   print(f"Using key: {api_key}")  # DANGEROUS!
   ```

## Example: Production Deployment

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.10

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Don't hardcode credentials!
# Pass via environment at runtime

CMD ["python", "flows/prefect_flow.py"]
```

```bash
# Run container with credentials
docker run \
  -e PREFECT_API_URL=https://prefect.company.com/api \
  -e PREFECT_API_KEY=$PREFECT_API_KEY \
  your-image:latest
```

## Troubleshooting

### Error: "Unauthorized" or 401

**Problem:** API key is invalid or missing

**Solution:**
```bash
# Check if API key is set
echo $PREFECT_API_KEY

# Verify it's not empty
if [ -z "$PREFECT_API_KEY" ]; then
    echo "API key is not set!"
fi

# Test with Prefect CLI
prefect config view
```

### Error: "Forbidden" or 403

**Problem:** API key is valid but lacks permissions

**Solution:**
- Check API key permissions in your Prefect Server UI
- Ensure key has "Write" access for flows
- Contact your Prefect server admin

### Error: Connection Refused

**Problem:** Wrong API URL or server is down

**Solution:**
```bash
# Test connection
curl -H "Authorization: Bearer $PREFECT_API_KEY" \
     $PREFECT_API_URL/health

# Check URL is correct
echo $PREFECT_API_URL
```

### API Key Not Being Used

**Problem:** Code runs but doesn't authenticate

**Solution:**
```python
# Verify environment variable is loaded
import os
print(f"API URL: {os.getenv('PREFECT_API_URL')}")
print(f"API Key set: {bool(os.getenv('PREFECT_API_KEY'))}")
```

## Testing Authentication

### Quick Test Script

```python
#!/usr/bin/env python3
"""Test Prefect server authentication"""

import asyncio
import os
from prefect.client.orchestration import get_client

async def test_auth():
    api_url = os.getenv("PREFECT_API_URL")
    api_key = os.getenv("PREFECT_API_KEY")
    
    print(f"Testing connection to: {api_url}")
    print(f"Using API key: {'Yes' if api_key else 'No'}")
    
    httpx_settings = {}
    if api_key:
        httpx_settings["headers"] = {"Authorization": f"Bearer {api_key}"}
    
    try:
        async with get_client(httpx_settings=httpx_settings) as client:
            # Try to read flows
            flows = await client.read_flows(limit=1)
            print("✅ Authentication successful!")
            print(f"   Found {len(flows)} flows")
            return True
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_auth())
```

Save as `scripts/test_prefect_auth.py` and run:
```bash
python scripts/test_prefect_auth.py
```

## Summary

### Development Setup (Local - No Auth):
```bash
export PREFECT_API_URL=http://localhost:4200/api
python flows/prefect_flow.py
```

### Production Setup (Private Server - With Auth):
```bash
export PREFECT_API_URL=https://your-private-server.com/api
export PREFECT_API_KEY=pnu_your_key_here
python flows/prefect_flow.py
```

### Key Points:
- ✅ This guide is for **self-hosted/private Prefect servers only**
- ✅ API key passed via `PREFECT_API_KEY` environment variable
- ✅ `.serve()` automatically uses the key for authentication
- ✅ Setup scripts also use the key automatically
- ✅ Never hardcode credentials in code
- ✅ Use secrets management in production
- ✅ Keep .env files out of git

Your private Prefect server setup is now production-ready with proper authentication! 🚀
