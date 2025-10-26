# Quick Reference: Prefect Authentication

## Development Mode (Local - No Auth)

```bash
export PREFECT_API_URL=http://localhost:4200/api
```

## Production Mode (Private Server - With Auth)

```bash
export PREFECT_API_URL=https://your-prefect-server.com/api
export PREFECT_API_KEY=pnu_your_api_key_here
```

## Commands

### Test Connection
```bash
python scripts/test_prefect_auth.py
```

### Setup Concurrency Limits
```bash
python scripts/setup_concurrency_limit.py
```

### Run Flow
```bash
python flows/prefect_flow.py
```

## File Checklist

- [x] `flows/prefect_flow.py` - Auto-detects and uses `PREFECT_API_KEY`
- [x] `scripts/setup_concurrency_limit.py` - Supports authentication
- [x] `scripts/test_prefect_auth.py` - Verify authentication works
- [x] `.env.example` - Template for credentials
- [x] `.gitignore` - Prevents committing `.env` files

## Security Checklist

- [ ] Never hardcode API keys in code
- [ ] Never commit `.env` files to git
- [ ] Use environment variables for credentials
- [ ] Rotate API keys regularly (every 90 days)
- [ ] Use service accounts, not personal keys
- [ ] Keep API keys in secrets manager (production)

## Troubleshooting

| Error | Solution |
|-------|----------|
| 401 Unauthorized | API key invalid/expired - generate new key |
| 403 Forbidden | API key lacks permissions - check permissions |
| Connection refused | Check PREFECT_API_URL, verify server is running |
| Empty response | API key not being sent - check environment variable |

## Getting API Key (Self-Hosted)

1. Login to your Prefect UI
2. Settings → API Keys → Create API Key

## Production Deployment Examples

### Docker
```bash
docker run \
  -e PREFECT_API_URL=https://prefect.company.com/api \
  -e PREFECT_API_KEY=$PREFECT_API_KEY \
  your-image:latest
```

## Need Help?

- See `docs/authentication_guide.md` for detailed documentation
- Run `python scripts/test_prefect_auth.py` to diagnose issues
- Check Prefect docs: https://docs.prefect.io
