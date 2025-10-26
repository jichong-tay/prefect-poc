

## Project Context

This is a proof-of-concept project demonstrating Prefect orchestration with Streamlit monitoring UI.

**Key Features:**
- Prefect 2.13.7 workflows with parallel task execution
- Server-side concurrency control using tags
- Production-ready authentication support
- Streamlit UI for flow monitoring

### Tech Stack
- Python 3.10+
- Prefect 2.13.7
- Streamlit 1.45.1+
- Docker (for Prefect server)



## Project Structure

```
prefect-poc/
├── 📁 flows/                      # Prefect flow definitions
│   └── prefect_flow.py        # Production ETL flow with concurrency control
│
├── streamlit/                  # Streamlit monitoring UI
│   ├── main.py                # Main Streamlit app
│   ├── rest_api_app.py        # REST API integration
│   └── playground.ipynb       # Learning notebook
│
├── scripts/                    # Utility scripts
│   ├── setup_concurrency_limit.py  # Configure server-side concurrency
│   └── test_prefect_auth.py       # Test authentication
│
├── docs/                       # Documentation
│   ├── auth_quick_reference.md     # Quick auth reference
│   ├── authentication_guide.md     # Detailed auth guide
│   └── concurrency_guide.md        # Concurrency control guide
│
├── .env.example               # Environment variable template
├── .gitignore                 # Git ignore rules
├── pyproject.toml            # Python dependencies
└── README.md                 # This file
```

## Quick Start

### 1. Setup Environment

```bash
# Install dependencies
uv sync

# Copy environment template
cp .env.example .env
```

### 2. Start Prefect Server (Development)

```bash
docker run -d -p 4200:4200 --name prefect-server \
  prefecthq/prefect:2.13.7-python3.10 \
  prefect server start --host 0.0.0.0
```

Access UI: http://localhost:4200

### 3. Configure Concurrency Limits

```bash
export PREFECT_API_URL=http://localhost:4200/api
python scripts/setup_concurrency_limit.py
```

### 4. Run a Flow

```bash
# Production ETL flow with concurrency control
python flows/prefect_flow.py
```

## Setup Instructions

### Development Mode (No Authentication)

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Start Prefect server:**
   ```bash
   docker run -d -p 4200:4200 --name prefect-server \
     prefecthq/prefect:2.13.7-python3.10 \
     prefect server start --host 0.0.0.0
   ```

3. **Configure environment:**
   ```bash
   export PREFECT_API_URL=http://localhost:4200/api
   ```

4. **Setup concurrency limits:**
   ```bash
   python scripts/setup_concurrency_limit.py
   ```

5. **Run flows:**
   ```bash
   python flows/prefect_flow.py
   ```

### Production Mode (With Authentication)

1. **Set environment variables:**
   ```bash
   export PREFECT_API_URL=https://your-prefect-server.com/api
   export PREFECT_API_KEY=pnu_your_api_key_here
   ```

2. **Test authentication:**
   ```bash
   python scripts/test_prefect_auth.py
   ```

3. **Configure and run:**
   ```bash
   python scripts/setup_concurrency_limit.py
   python flows/prefect_flow.py
   ```

## Key Features

### Parallel Task Execution

The `prefect_flow.py` demonstrates running multiple SQL queries with controlled concurrency:

- Submits all 20 queries at once
- Server limits execution to 3 concurrent tasks
- Uses task tags for concurrency control
- Proper future handling and cleanup sequencing

### Server-Side Concurrency Control

Instead of batching in code, uses Prefect's built-in concurrency limits:

```python
@task(tags=["database"])  # Tag for concurrency control
def sql_query(table):
    # Query logic
    pass
```

Server configuration ensures max 3 tasks with `database` tag run simultaneously.

### Authentication Support

Works in both development (no auth) and production (with API keys):

- Automatic API key detection from environment
- Standard OAuth Bearer token format
- Secure credential management
- No hardcoded secrets

## Documentation

- **[Authentication Guide](docs/authentication_guide.md)** - Complete auth documentation
- **[Concurrency Guide](docs/concurrency_guide.md)** - Server-side concurrency control
- **[Quick Reference](docs/auth_quick_reference.md)** - Command cheat sheet

## Common Commands

```bash
# Start Prefect server
docker start prefect-server

# Stop Prefect server
docker stop prefect-server

# View server logs
docker logs prefect-server

# Test authentication
python scripts/test_prefect_auth.py

# Setup concurrency limits
python scripts/setup_concurrency_limit.py

# Run ETL flow
python flows/prefect_flow.py

# Run Streamlit UI
streamlit run streamlit/main.py
```

## Development Workflow

1. **Local Testing:**
   - Start Docker Prefect server
   - Run flows directly: `python flows/prefect_flow.py`
   - Monitor at http://localhost:4200

2. **Deployment:**
   - Set production API URL and key
   - Deploy: `prefect deploy flows/prefect_flow.py:main_etl`
   - Start workers to execute flows

## Troubleshooting

### Connection Issues
```bash
# Check if server is running
curl http://localhost:4200/api/health

# Verify environment
echo $PREFECT_API_URL
echo $PREFECT_API_KEY
```

### Authentication Errors
```bash
# Test auth
python scripts/test_prefect_auth.py

# Check API key validity
prefect config view
```

### Concurrency Not Working
```bash
# List concurrency limits
prefect concurrency-limit list

# Verify task tags
grep "tags=" flows/prefect_flow.py
```

## Contributing

When adding new flows:
1. Place in `flows/` directory
2. Use proper task tags for concurrency control
3. Include error handling and retries
4. Update documentation

## License

MIT License