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
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.agent_name} | Dockrion</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0a0e14;
            --bg-secondary: #0d1117;
            --bg-card: rgba(22, 27, 34, 0.8);
            --bg-card-hover: rgba(33, 38, 45, 0.9);
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --text-muted: #6e7681;
            --accent-primary: #58a6ff;
            --accent-secondary: #f78166;
            --accent-green: #3fb950;
            --border-primary: rgba(240, 246, 252, 0.1);
            --border-hover: rgba(88, 166, 255, 0.4);
            --glow-primary: rgba(88, 166, 255, 0.15);
            --glow-secondary: rgba(247, 129, 102, 0.1);
        }}
        
        [data-theme="light"] {{
            --bg-primary: #f6f8fa;
            --bg-secondary: #ffffff;
            --bg-card: rgba(255, 255, 255, 0.9);
            --bg-card-hover: rgba(255, 255, 255, 1);
            --text-primary: #1f2328;
            --text-secondary: #656d76;
            --text-muted: #8b949e;
            --accent-primary: #0969da;
            --accent-secondary: #cf222e;
            --accent-green: #1a7f37;
            --border-primary: rgba(31, 35, 40, 0.15);
            --border-hover: rgba(9, 105, 218, 0.5);
            --glow-primary: rgba(9, 105, 218, 0.1);
            --glow-secondary: rgba(207, 34, 46, 0.05);
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Sora', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: var(--text-primary);
            padding: 2rem;
            position: relative;
            overflow-x: hidden;
        }}
        
        /* Animated gradient mesh background */
        .bg-mesh {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            opacity: 0.6;
            background: 
                radial-gradient(ellipse at 20% 20%, var(--glow-primary) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 80%, var(--glow-secondary) 0%, transparent 50%),
                radial-gradient(ellipse at 50% 50%, rgba(88, 166, 255, 0.05) 0%, transparent 70%);
            animation: meshFloat 20s ease-in-out infinite;
        }}
        
        @keyframes meshFloat {{
            0%, 100% {{ transform: translate(0, 0) scale(1); }}
            33% {{ transform: translate(-2%, 2%) scale(1.02); }}
            66% {{ transform: translate(2%, -1%) scale(0.98); }}
        }}
        
        /* Floating geometric shapes */
        .geo-shape {{
            position: fixed;
            border: 1px solid var(--border-primary);
            border-radius: 50%;
            opacity: 0.3;
            z-index: -1;
        }}
        
        .geo-1 {{
            width: 300px;
            height: 300px;
            top: 10%;
            left: -5%;
            animation: float1 25s ease-in-out infinite;
        }}
        
        .geo-2 {{
            width: 200px;
            height: 200px;
            bottom: 15%;
            right: -3%;
            animation: float2 20s ease-in-out infinite;
        }}
        
        .geo-3 {{
            width: 150px;
            height: 150px;
            top: 60%;
            left: 5%;
            border-radius: 30%;
            animation: float3 18s ease-in-out infinite;
        }}
        
        @keyframes float1 {{
            0%, 100% {{ transform: translate(0, 0) rotate(0deg); }}
            50% {{ transform: translate(30px, 20px) rotate(180deg); }}
        }}
        
        @keyframes float2 {{
            0%, 100% {{ transform: translate(0, 0) rotate(0deg); }}
            50% {{ transform: translate(-20px, 30px) rotate(-180deg); }}
        }}
        
        @keyframes float3 {{
            0%, 100% {{ transform: translate(0, 0) rotate(0deg); }}
            50% {{ transform: translate(15px, -25px) rotate(90deg); }}
        }}
        
        /* Theme toggle */
        .theme-toggle {{
            position: fixed;
            top: 1.5rem;
            right: 1.5rem;
            background: var(--bg-card);
            border: 1px solid var(--border-primary);
            border-radius: 50px;
            padding: 0.5rem;
            cursor: pointer;
            transition: all 0.3s ease;
            backdrop-filter: blur(12px);
            display: flex;
            align-items: center;
            gap: 0.5rem;
            z-index: 100;
        }}
        
        .theme-toggle:hover {{
            border-color: var(--border-hover);
            transform: scale(1.05);
        }}
        
        .theme-toggle svg {{
            width: 20px;
            height: 20px;
            fill: var(--text-secondary);
            transition: all 0.3s ease;
        }}
        
        .theme-toggle:hover svg {{
            fill: var(--accent-primary);
        }}
        
        .sun-icon {{ display: none; }}
        .moon-icon {{ display: block; }}
        
        [data-theme="light"] .sun-icon {{ display: block; }}
        [data-theme="light"] .moon-icon {{ display: none; }}
        
        .container {{
            text-align: center;
            max-width: 600px;
            width: 100%;
            animation: fadeInUp 0.8s ease-out;
        }}
        
        @keyframes fadeInUp {{
            from {{
                opacity: 0;
                transform: translateY(30px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .logo-container {{
            margin-bottom: 2rem;
            animation: fadeInUp 0.8s ease-out 0.1s both;
        }}
        
        .logo-img {{
            max-width: 280px;
            width: 100%;
            height: auto;
            filter: drop-shadow(0 4px 20px var(--glow-primary));
            transition: filter 0.3s ease;
        }}
        
        .logo-img:hover {{
            filter: drop-shadow(0 8px 30px var(--glow-primary));
        }}
        
        /* Agent info section */
        .agent-section {{
            animation: fadeInUp 0.8s ease-out 0.2s both;
        }}
        
        .agent-name {{
            font-size: 2.2rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 0.75rem;
            letter-spacing: -0.02em;
        }}
        
        .agent-description {{
            color: var(--text-secondary);
            font-size: 1.1rem;
            line-height: 1.6;
            margin-bottom: 1.5rem;
            max-width: 500px;
            margin-left: auto;
            margin-right: auto;
        }}
        
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.6rem;
            background: rgba(63, 185, 80, 0.1);
            border: 1px solid rgba(63, 185, 80, 0.3);
            padding: 0.6rem 1.4rem;
            border-radius: 50px;
            color: var(--accent-green);
            font-size: 0.875rem;
            font-weight: 500;
            margin-bottom: 2.5rem;
        }}
        
        .status-dot {{
            width: 8px;
            height: 8px;
            background: var(--accent-green);
            border-radius: 50%;
            animation: pulse 2s ease-in-out infinite;
            box-shadow: 0 0 10px var(--accent-green);
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.6; transform: scale(0.85); }}
        }}
        
        /* Documentation buttons - Hero style */
        .docs-section {{
            display: flex;
            flex-direction: column;
            gap: 1rem;
            animation: fadeInUp 0.8s ease-out 0.3s both;
        }}
        
        .doc-card {{
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-primary);
            border-radius: 16px;
            padding: 1.5rem 2rem;
            text-decoration: none;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex;
            align-items: center;
            gap: 1.25rem;
            position: relative;
            overflow: hidden;
        }}
        
        .doc-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, var(--glow-primary) 0%, transparent 50%);
            opacity: 0;
            transition: opacity 0.3s ease;
        }}
        
        .doc-card:hover {{
            transform: translateY(-4px);
            border-color: var(--border-hover);
            box-shadow: 
                0 20px 40px rgba(0, 0, 0, 0.3),
                0 0 40px var(--glow-primary);
        }}
        
        .doc-card:hover::before {{
            opacity: 1;
        }}
        
        .doc-icon {{
            width: 52px;
            height: 52px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            flex-shrink: 0;
            position: relative;
            z-index: 1;
        }}
        
        .doc-card.swagger .doc-icon {{
            background: linear-gradient(135deg, #85ea2d 0%, #173647 100%);
        }}
        
        .doc-card.redoc .doc-icon {{
            background: linear-gradient(135deg, #e84d31 0%, #8b0000 100%);
        }}
        
        .doc-content {{
            flex: 1;
            text-align: left;
            position: relative;
            z-index: 1;
        }}
        
        .doc-title {{
            font-weight: 600;
            color: var(--text-primary);
            font-size: 1.1rem;
            margin-bottom: 0.3rem;
        }}
        
        .doc-subtitle {{
            color: var(--text-secondary);
            font-size: 0.875rem;
        }}
        
        .doc-path {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: var(--text-muted);
            background: rgba(88, 166, 255, 0.1);
            padding: 0.3rem 0.6rem;
            border-radius: 6px;
            position: relative;
            z-index: 1;
        }}
        
        .doc-arrow {{
            color: var(--text-muted);
            font-size: 1.25rem;
            transition: all 0.3s ease;
            position: relative;
            z-index: 1;
        }}
        
        .doc-card:hover .doc-arrow {{
            color: var(--accent-primary);
            transform: translateX(4px);
        }}
        
        /* Meta info - pill badges */
        .meta-section {{
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin-top: 2.5rem;
            animation: fadeInUp 0.8s ease-out 0.4s both;
        }}
        
        .meta-pill {{
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-primary);
            padding: 0.5rem 1rem;
            border-radius: 50px;
            font-size: 0.75rem;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .meta-pill .label {{
            color: var(--text-muted);
        }}
        
        .meta-pill .value {{
            color: var(--text-primary);
            font-weight: 500;
            font-family: 'JetBrains Mono', monospace;
        }}
        
        /* Footer */
        .footer {{
            margin-top: 3rem;
            font-size: 0.8rem;
            color: var(--text-muted);
            animation: fadeInUp 0.8s ease-out 0.5s both;
        }}
        
        .footer a {{
            color: var(--accent-primary);
            text-decoration: none;
            font-weight: 500;
            transition: all 0.2s ease;
        }}
        
        .footer a:hover {{
            text-decoration: underline;
            text-underline-offset: 3px;
        }}
        
        /* Responsive */
        @media (max-width: 640px) {{
            .agent-name {{
                font-size: 1.75rem;
            }}
            
            .doc-card {{
                padding: 1.25rem 1.5rem;
            }}
            
            .meta-section {{
                gap: 0.5rem;
            }}
            
            .meta-pill {{
                font-size: 0.7rem;
                padding: 0.4rem 0.8rem;
            }}
        }}
    </style>
</head>
<body>
    <!-- Background elements -->
    <div class="bg-mesh"></div>
    <div class="geo-shape geo-1"></div>
    <div class="geo-shape geo-2"></div>
    <div class="geo-shape geo-3"></div>
    
    <!-- Theme toggle -->
    <button class="theme-toggle" onclick="toggleTheme()" aria-label="Toggle theme">
        <svg class="sun-icon" viewBox="0 0 24 24"><path d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zM2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 .45-1 1s.45 1 1 1zm18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1zM11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1-1-1s-1 .45-1 1zm0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1s-1 .45-1 1zM5.99 4.58c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41L5.99 4.58zm12.37 12.37c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0 .39-.39.39-1.03 0-1.41l-1.06-1.06zm1.06-10.96c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06zM7.05 18.36c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06z"/></svg>
        <svg class="moon-icon" viewBox="0 0 24 24"><path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-.46-.04-.92-.1-1.36-.98 1.37-2.58 2.26-4.4 2.26-2.98 0-5.4-2.42-5.4-5.4 0-1.81.89-3.42 2.26-4.4-.44-.06-.9-.1-1.36-.1z"/></svg>
    </button>
    
    <div class="container">
        <!-- Logo -->
        <div class="logo-container">
            {logo_html}
        </div>
        
        <!-- Agent Info -->
        <div class="agent-section">
            <h1 class="agent-name">{config.agent_name}</h1>
            <p class="agent-description">{config.agent_description}</p>
            <div class="status-badge">
                <span class="status-dot"></span>
                Running
            </div>
        </div>
        
        <!-- Documentation Links -->
        <div class="docs-section">
            <a href="/docs" class="doc-card swagger">
                <div class="doc-icon">⚡</div>
                <div class="doc-content">
                    <div class="doc-title">Swagger UI</div>
                    <div class="doc-subtitle">Interactive API explorer</div>
                </div>
                <span class="doc-path">/docs</span>
                <span class="doc-arrow">→</span>
            </a>
            <a href="/redoc" class="doc-card redoc">
                <div class="doc-icon">📖</div>
                <div class="doc-content">
                    <div class="doc-title">ReDoc</div>
                    <div class="doc-subtitle">Clean API reference</div>
                </div>
                <span class="doc-path">/redoc</span>
                <span class="doc-arrow">→</span>
            </a>
        </div>
        
        <!-- Metadata Pills -->
        <div class="meta-section">
            <div class="meta-pill">
                <span class="label">v</span>
                <span class="value">{config.version}</span>
            </div>
            <div class="meta-pill">
                <span class="label">framework</span>
                <span class="value">{config.agent_framework}</span>
            </div>
            <div class="meta-pill">
                <span class="label">mode</span>
                <span class="value">{"handler" if config.use_handler_mode else "agent"}</span>
            </div>
            <div class="meta-pill">
                <span class="label">auth</span>
                <span class="value">{"on" if config.auth_enabled else "off"}</span>
            </div>
        </div>
        
        <!-- Footer -->
        <footer class="footer">
            Powered by <a href="https://github.com/dockrion/dockrion" target="_blank">Dockrion</a>
        </footer>
    </div>
    
    <script>
        function toggleTheme() {{
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('dockrion-theme', newTheme);
        }}
        
        // Load saved theme preference
        (function() {{
            const savedTheme = localStorage.getItem('dockrion-theme');
            if (savedTheme) {{
                document.documentElement.setAttribute('data-theme', savedTheme);
            }}
        }})();
    </script>
</body>
</html>'''

