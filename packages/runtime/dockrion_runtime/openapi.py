"""
OpenAPI Security Configuration

Handles OpenAPI security scheme generation and customization based on auth configuration.
"""

from typing import Any, Dict

from dockrion_schema import DockSpec
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from .config import RuntimeConfig


def build_security_schemes(config: RuntimeConfig, spec: DockSpec) -> Dict[str, Any]:
    """
    Build OpenAPI security schemes based on auth configuration.

    Args:
        config: Runtime configuration
        spec: DockSpec with auth settings

    Returns:
        Dictionary of security schemes for OpenAPI
    """
    if not config.auth_enabled:
        return {}

    if config.auth_mode == "api_key":
        # Get the header name from auth config
        header_name = "X-API-Key"
        if spec.auth and hasattr(spec.auth, "api_keys") and spec.auth.api_keys:
            header_name = (
                spec.auth.api_keys.get("header", "X-API-Key")
                if isinstance(spec.auth.api_keys, dict)
                else "X-API-Key"
            )

        return {
            "APIKeyHeader": {
                "type": "apiKey",
                "in": "header",
                "name": header_name,
                "description": f"API Key authentication. Pass your API key in the `{header_name}` header.",
            },
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "description": "API Key authentication. Pass your API key as a Bearer token in the `Authorization` header.",
            },
        }

    elif config.auth_mode == "jwt":
        return {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT authentication. Pass your JWT token in the `Authorization` header.",
            }
        }

    return {}


# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = frozenset(["/health", "/ready", "/schema", "/info", "/metrics"])


def configure_openapi_security(app: FastAPI, security_schemes: Dict[str, Any]) -> None:
    """
    Configure OpenAPI security for a FastAPI application.

    Adds security schemes and applies them to protected endpoints.

    Args:
        app: FastAPI application instance
        security_schemes: Dictionary of security schemes
    """
    if not security_schemes:
        return

    def custom_openapi() -> Dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        # Add security schemes
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}
        openapi_schema["components"]["securitySchemes"] = security_schemes

        # Apply security to all protected endpoints
        for path, path_item in openapi_schema.get("paths", {}).items():
            for method, operation in path_item.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    # Skip public endpoints
                    if path in PUBLIC_ENDPOINTS:
                        continue
                    # Add security requirement to protected endpoints
                    if "APIKeyHeader" in security_schemes:
                        operation["security"] = [{"APIKeyHeader": []}, {"BearerAuth": []}]
                    else:
                        operation["security"] = [{"BearerAuth": []}]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
