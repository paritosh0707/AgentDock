# How to Start Server with Environment Variable

## The Problem

The server is currently running **WITHOUT** the `MY_AGENT_KEY` environment variable set.

From the logs at startup:
```
{"timestamp": "2025-12-17T05:15:15.509710Z", "level": "WARNING", "service": "dockrion_runtime.auth.api_key", "message": "API key environment variable MY_AGENT_KEY not set"}
{"timestamp": "2025-12-17T05:15:15.509731Z", "level": "WARNING", "service": "dockrion_runtime.auth.api_key", "message": "No API keys loaded. Auth will fail for all requests. Set MY_AGENT_KEY or keys with prefix None"}
```

This means:
- ❌ No API key loaded in memory
- ❌ All authenticated requests will fail
- ❌ Even with correct `X-API-Key` header, comparison fails

## The Solution

### Step 1: Stop the Current Server

In the terminal where the server is running, press:
```
Ctrl + C
```

### Step 2: Set the Environment Variable and Restart

**Option A: Set for current session**
```bash
export MY_AGENT_KEY="test-api-key-12345"
dockrion run
```

**Option B: Set inline (one command)**
```bash
MY_AGENT_KEY="test-api-key-12345" dockrion run
```

**Option C: Set in shell profile (permanent)**
```bash
# Add to ~/.zshrc or ~/.bashrc
echo 'export MY_AGENT_KEY="test-api-key-12345"' >> ~/.zshrc
source ~/.zshrc
dockrion run
```

### Step 3: Verify Environment Variable is Loaded

After restarting, you should see in the logs:
```
✅ Loaded API key from MY_AGENT_KEY
```

Instead of:
```
⚠️ API key environment variable MY_AGENT_KEY not set
⚠️ No API keys loaded
```

## Testing After Restart

### With curl:
```bash
curl -X POST http://0.0.0.0:8080/invoke \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-api-key-12345" \
  -d '{
    "invoice_id": "INV-001",
    "vendor_name": "Acme Corp",
    "total_amount": 1250.00,
    "line_items": []
  }'
```

### In Swagger UI:
1. Go to http://0.0.0.0:8080/docs
2. Click "Authorize"
3. Enter: `test-api-key-12345`
4. Try the `/invoke` endpoint

## Important Notes

1. **Environment variables must be set BEFORE starting the server**
2. The API key is loaded into memory at startup
3. Changing the environment variable after the server starts won't work
4. You must restart the server for changes to take effect

## Why This Happens

The `ApiKeyAuthHandler` loads keys during initialization:

```python
class ApiKeyAuthHandler(BaseAuthHandler):
    def __init__(self, config: AuthConfig):
        super().__init__(config)
        self._keys: Dict[str, ApiKeyMetadata] = {}
        self._load_keys()  # ← Loads keys from environment at startup
```

If `MY_AGENT_KEY` is not set when `_load_keys()` runs, the `_keys` dict remains empty, and all authentication will fail.

## Alternative: Use Environment File

Create a `.env` file in your project:

```bash
# .env
MY_AGENT_KEY=test-api-key-12345
```

Then load it before starting:
```bash
export $(cat .env | xargs)
dockrion run
```

Or use a tool like `dotenv`:
```bash
pip install python-dotenv
dotenv run dockrion run
```

---

**Remember:** The server must be restarted with the environment variable set!

