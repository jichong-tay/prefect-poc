# Documentation Index

Welcome to the Prefect POC documentation!

## Quick Start

New to the project? Start here:
1. Read the [main README](../README.md) for setup instructions
2. Follow [Authentication Guide](authentication_guide.md) to configure credentials
3. Learn about [Concurrency Control](concurrency_guide.md) for parallel execution

## Documentation Files

### 📚 Guides

- **[Authentication Guide](authentication_guide.md)**
  - Complete guide for dev/prod authentication
  - API key setup and management
  - Security best practices
  - Deployment examples (Docker, Kubernetes, AWS)
  - Troubleshooting authentication issues

- **[Concurrency Guide](concurrency_guide.md)**
  - Server-side concurrency control explained
  - How to use task tags for limiting parallel execution
  - Setup and configuration steps
  - Monitoring and adjusting limits
  - Best practices for database connections

### ⚡ Quick Reference

- **[Auth Quick Reference](auth_quick_reference.md)**
  - Command cheat sheet
  - Environment variable setup
  - Common troubleshooting solutions
  - Deployment snippets

## Common Tasks

### Development Setup
```bash
# Start Prefect server
docker run -d -p 4200:4200 --name prefect-server \
  prefecthq/prefect:2.13.7-python3.10 \
  prefect server start --host 0.0.0.0

# Configure concurrency
export PREFECT_API_URL=http://localhost:4200/api
python scripts/setup_concurrency_limit.py

# Run a flow
python flows/prefect_flow.py
```

### Production Setup
```bash
# Set credentials
export PREFECT_API_URL=https://your-server.com/api
export PREFECT_API_KEY=pnu_your_key_here

# Test connection
python scripts/test_prefect_auth.py

# Deploy flows
python flows/prefect_flow.py
```

## Project Structure

```
prefect-poc/
├── docs/                       ← You are here
│   ├── README.md              ← This file
│   ├── authentication_guide.md
│   ├── concurrency_guide.md
│   └── auth_quick_reference.md
│
├── flows/                      ← Prefect flow definitions
│   └── prefect_flow.py        ← Production ETL flow
│
├── scripts/                    ← Utility scripts
│   ├── setup_concurrency_limit.py
│   └── test_prefect_auth.py
│
└── streamlit/                  ← UI and notebooks
    ├── main.py
    └── playground.ipynb
```

## Key Concepts

### Server-Side Concurrency Control

Instead of manually batching tasks in your code, Prefect's server can control how many tasks run simultaneously:

```python
@task(tags=["database"])  # Tag for concurrency control
def sql_query(table):
    # Your query logic
    pass

# Submit all tasks - server limits concurrent execution
futures = [sql_query.submit(i) for i in range(20)]
results = [f.result() for f in futures]
```

Server configuration ensures only 3 tasks with "database" tag run at once.

### Authentication Modes

**Development (no auth):**
```bash
export PREFECT_API_URL=http://localhost:4200/api
```

**Production (with API key):**
```bash
export PREFECT_API_URL=https://prefect.company.com/api
export PREFECT_API_KEY=pnu_abc123...
```

Code automatically detects and uses the API key.

## Additional Resources

- [Prefect Official Docs](https://docs.prefect.io)
- [Prefect Cloud](https://app.prefect.cloud)
- [Main Project README](../README.md)

## Getting Help

1. Check the relevant guide for your topic
2. Run diagnostic scripts:
   - `python scripts/test_prefect_auth.py` - test connection
   - `prefect config view` - check configuration
3. Review logs in Prefect UI at http://localhost:4200

## Contributing to Docs

When updating documentation:
1. Keep examples realistic and tested
2. Include both dev and prod scenarios
3. Add troubleshooting sections
4. Update this index if adding new docs
