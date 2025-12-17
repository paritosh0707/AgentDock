# OpenAPI Authentication Configuration Fix

## Problem
The Swagger UI was not showing the "Authorize" button because the FastAPI app didn't have OpenAPI security schemes configured.

## Solution
Added automatic OpenAPI security scheme configuration based on the auth mode in the Dockfile.

## What Was Changed

### File: `/packages/runtime/dockrion_runtime/app.py`

#### 1. Added Security Imports
```python
from fastapi.security import APIKeyHeader, HTTPBearer
from fastapi.openapi.models import SecuritySchemeType
```

#### 2. Added OpenAPI Security Scheme Generation
After the lifespan manager, before creating the FastAPI app:

```python
# Build OpenAPI security schemes based on auth configuration
openapi_security_schemes = {}
if config.auth_enabled and config.auth_mode == "api_key":
    # Get the header name from auth config
    header_name = "X-API-Key"
    if spec.auth and hasattr(spec.auth, 'api_keys') and spec.auth.api_keys:
        header_name = spec.auth.api_keys.get('header', 'X-API-Key') if isinstance(spec.auth.api_keys, dict) else "X-API-Key"
    
    openapi_security_schemes = {
        "APIKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": header_name,
            "description": f"API Key authentication. Pass your API key in the `{header_name}` header."
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "description": "API Key authentication. Pass your API key as a Bearer token in the `Authorization` header."
        }
    }
elif config.auth_enabled and config.auth_mode == "jwt":
    openapi_security_schemes = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT authentication. Pass your JWT token in the `Authorization` header."
        }
    }
```

#### 3. Added Custom OpenAPI Schema Function
This function:
- Adds security schemes to the OpenAPI spec
- Automatically marks protected endpoints (skips `/health`, `/ready`, `/schema`, `/info`)
- Supports both `X-API-Key` header and `Authorization: Bearer` token

```python
if openapi_security_schemes:
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        from fastapi.openapi.utils import get_openapi
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        
        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = openapi_security_schemes
        
        # Apply security to all protected endpoints
        for path, path_item in openapi_schema["paths"].items():
            for method, operation in path_item.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    # Skip health and schema endpoints (they're public)
                    if path in ["/health", "/ready", "/schema", "/info"]:
                        continue
                    # Add security requirement to protected endpoints
                    if "APIKeyHeader" in openapi_security_schemes:
                        operation["security"] = [
                            {"APIKeyHeader": []},
                            {"BearerAuth": []}
                        ]
                    else:
                        operation["security"] = [{"BearerAuth": []}]
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
```

## How to Test

### Step 1: Rebuild the Runtime
```bash
cd /Users/prakharagarwal/Dockrion/examples/invoice_copilot
rm -rf .dockrion_runtime
MY_AGENT_KEY="test-api-key-12345" dockrion run
```

### Step 2: Open Swagger UI
Navigate to: **http://0.0.0.0:8080/docs**

### Step 3: Look for the "Authorize" Button
You should now see:
- ✅ A green padlock icon 🔓 in the top-right corner
- ✅ When you click it, you'll see two auth options:
  - **APIKeyHeader (apiKey)** - for `X-API-Key` header
  - **BearerAuth (http, Bearer)** - for `Authorization: Bearer` header

### Step 4: Authorize
1. Click the "Authorize" button
2. Enter your API key: `test-api-key-12345`
3. You can enter it in either field (they both work)
4. Click "Authorize"
5. Click "Close"

### Step 5: Test the Endpoint
1. Scroll to the `/invoke` endpoint
2. Click "Try it out"
3. You should see the padlock icon next to the endpoint is now locked 🔒
4. Fill in the request body
5. Click "Execute"
6. You should get a successful response!

## What You'll See in Swagger UI

### Before (Without Auth Config):
- ❌ No "Authorize" button
- ❌ Error message when trying to call `/invoke`
- ❌ Confusing error: "API key authentication not configured"

### After (With Auth Config):
- ✅ "Authorize" button in top-right
- ✅ Two authentication methods available
- ✅ Padlock icons on protected endpoints
- ✅ Successful API calls after authorization

## OpenAPI Schema Generated

The generated OpenAPI schema will include:

```json
{
  "components": {
    "securitySchemes": {
      "APIKeyHeader": {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "API Key authentication. Pass your API key in the `X-API-Key` header."
      },
      "BearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "description": "API Key authentication. Pass your API key as a Bearer token in the `Authorization` header."
      }
    }
  },
  "paths": {
    "/invoke": {
      "post": {
        "security": [
          {"APIKeyHeader": []},
          {"BearerAuth": []}
        ],
        ...
      }
    }
  }
}
```

## Benefits

1. **Better UX**: Clear "Authorize" button in Swagger UI
2. **Flexibility**: Support for both header formats (`X-API-Key` and `Authorization: Bearer`)
3. **Auto-Configuration**: Automatically adapts to auth mode in Dockfile
4. **Public Endpoints**: Health and info endpoints remain public
5. **Standards Compliant**: Follows OpenAPI 3.0 security scheme spec

## Notes

- The security schemes are dynamically generated based on the Dockfile's `auth.mode`
- If `auth.mode: none`, no security schemes are added
- If `auth.mode: api_key`, both header and bearer auth are supported
- If `auth.mode: jwt`, only bearer auth is supported
- Public endpoints (`/health`, `/ready`, `/schema`, `/info`) are always accessible

---

**Status:** ✅ Fixed
**Date:** December 17, 2025

