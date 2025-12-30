"""
Dockrion Runtime Welcome Page

Provides a beautiful branded landing page at the root endpoint.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ..config import RuntimeConfig


def create_welcome_router(config: RuntimeConfig) -> APIRouter:
    """
    Create the welcome page router.
    
    Args:
        config: Runtime configuration
        
    Returns:
        APIRouter with welcome endpoint
    """
    router = APIRouter(tags=["Welcome"])
    
    @router.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def welcome_page() -> str:
        """
        Serve the Dockrion welcome/landing page.
        
        Returns a beautiful branded HTML page with:
        - Dockrion logo and branding
        - Agent information
        - Quick links to all endpoints
        - Status indicator
        """
        return _generate_welcome_html(config)
    
    return router


def _generate_welcome_html(config: RuntimeConfig) -> str:
    """Generate the welcome page HTML with Dockrion branding."""
    
    # Use the actual Dockrion logo image from static files
    logo_html = '''<img src="/static/dockrion-logo.png" alt="Dockrion Logo" class="logo-img">'''
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.agent_name} | Dockrion</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(145deg, #f8f9fa 0%, #e9ecef 50%, #f8f9fa 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: #1e3a5f;
            padding: 2rem;
        }}
        
        .container {{
            text-align: center;
            max-width: 700px;
            width: 100%;
        }}
        
        .logo-container {{
            margin-bottom: 1.5rem;
        }}
        
        .logo-img {{
            max-width: 320px;
            width: 100%;
            height: auto;
            margin-bottom: 0.5rem;
        }}
        
        .brand-name {{
            font-size: 2.8rem;
            font-weight: 700;
            color: #1e3a5f;
            letter-spacing: 0.15em;
            margin-bottom: 0.25rem;
        }}
        
        .tagline {{
            font-size: 1rem;
            font-weight: 600;
            letter-spacing: 0.2em;
            color: #c65d3b;
        }}
        
        .divider {{
            width: 80px;
            height: 3px;
            background: linear-gradient(90deg, #1e3a5f, #c65d3b);
            margin: 2rem auto;
            border-radius: 2px;
        }}
        
        .agent-card {{
            background: white;
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 4px 24px rgba(30, 58, 95, 0.08);
            border: 1px solid rgba(30, 58, 95, 0.08);
            margin-bottom: 1.5rem;
        }}
        
        .agent-name {{
            font-size: 1.75rem;
            font-weight: 600;
            color: #1e3a5f;
            margin-bottom: 0.5rem;
        }}
        
        .agent-description {{
            color: #5a6c7d;
            font-size: 1rem;
            margin-bottom: 1.25rem;
        }}
        
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.25);
            padding: 0.5rem 1.25rem;
            border-radius: 50px;
            color: #059669;
            font-size: 0.875rem;
            font-weight: 500;
        }}
        
        .status-dot {{
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            animation: pulse 2s ease-in-out infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.6; transform: scale(0.9); }}
        }}
        
        .endpoints-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 0.875rem;
            margin-top: 1.5rem;
        }}
        
        .endpoint-card {{
            background: white;
            border: 1px solid rgba(30, 58, 95, 0.1);
            border-radius: 12px;
            padding: 1.25rem 1rem;
            text-decoration: none;
            transition: all 0.2s ease;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .endpoint-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 8px 24px rgba(30, 58, 95, 0.12);
            border-color: #1e3a5f;
        }}
        
        .endpoint-icon {{
            font-size: 1.5rem;
        }}
        
        .endpoint-name {{
            font-weight: 600;
            color: #1e3a5f;
            font-size: 0.9rem;
        }}
        
        .endpoint-path {{
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
            font-size: 0.75rem;
            color: #8896a4;
        }}
        
        .meta-info {{
            margin-top: 2rem;
            display: flex;
            justify-content: center;
            gap: 2rem;
            flex-wrap: wrap;
        }}
        
        .meta-item {{
            font-size: 0.8rem;
            color: #8896a4;
        }}
        
        .meta-item strong {{
            color: #5a6c7d;
        }}
        
        .footer {{
            margin-top: 2.5rem;
            font-size: 0.75rem;
            color: #a0aab4;
        }}
        
        .footer a {{
            color: #1e3a5f;
            text-decoration: none;
            font-weight: 500;
        }}
        
        .footer a:hover {{
            text-decoration: underline;
        }}
        
        /* Dark mode support */
        @media (prefers-color-scheme: dark) {{
            body {{
                background: linear-gradient(145deg, #0f1419 0%, #1a2332 50%, #0f1419 100%);
                color: #e1e8ed;
            }}
            
            .brand-name {{
                color: #e1e8ed;
            }}
            
            .agent-card {{
                background: #1a2332;
                border-color: rgba(255, 255, 255, 0.08);
            }}
            
            .agent-name {{
                color: #e1e8ed;
            }}
            
            .agent-description {{
                color: #8899a6;
            }}
            
            .endpoint-card {{
                background: #1a2332;
                border-color: rgba(255, 255, 255, 0.1);
            }}
            
            .endpoint-card:hover {{
                border-color: #4a9eff;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
            }}
            
            .endpoint-name {{
                color: #e1e8ed;
            }}
            
            .footer {{
                color: #5a6c7d;
            }}
            
            .footer a {{
                color: #4a9eff;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Logo and Branding -->
        <div class="logo-container">
            {logo_html}
        </div>
        
        <div class="divider"></div>
        
        <!-- Agent Information Card -->
        <div class="agent-card">
            <h2 class="agent-name">{config.agent_name}</h2>
            <p class="agent-description">{config.agent_description}</p>
            <div class="status-badge">
                <span class="status-dot"></span>
                Agent Running
            </div>
            
            <!-- Endpoint Quick Links -->
            <div class="endpoints-grid">
                <a href="/docs" class="endpoint-card">
                    <span class="endpoint-icon">📚</span>
                    <span class="endpoint-name">API Docs</span>
                    <span class="endpoint-path">/docs</span>
                </a>
                <a href="/redoc" class="endpoint-card">
                    <span class="endpoint-icon">📖</span>
                    <span class="endpoint-name">ReDoc</span>
                    <span class="endpoint-path">/redoc</span>
                </a>
            </div>
        </div>
        
        <!-- Metadata -->
        <div class="meta-info">
            <span class="meta-item"><strong>Version:</strong> {config.version}</span>
            <span class="meta-item"><strong>Framework:</strong> {config.agent_framework}</span>
            <span class="meta-item"><strong>Mode:</strong> {"Handler" if config.use_handler_mode else "Agent"}</span>
            <span class="meta-item"><strong>Auth:</strong> {"Enabled" if config.auth_enabled else "None"}</span>
        </div>
        
        <!-- Footer -->
        <footer class="footer">
            Powered by <a href="https://github.com/dockrion/dockrion" target="_blank">Dockrion</a>
        </footer>
    </div>
</body>
</html>'''

