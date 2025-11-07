"""Authentication routes for Microsoft SSO."""

from typing import Optional
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from app.services.auth_service import AuthService
from app.utils.logger import setup_logger
from app.config import settings
import secrets

logger = setup_logger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

# Initialize auth service
_auth_service: AuthService = None


def get_auth_service() -> AuthService:
    """Get or create auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None) -> HTMLResponse:
    """Display login page or redirect to Microsoft login.
    
    Args:
        error: Optional error message to display
        
    Returns:
        HTML login page or redirect to Microsoft
    """
    # If already authenticated, redirect to home
    if request.session.get("authenticated"):
        return RedirectResponse(url="/", status_code=302)
    
    error_message = ""
    if error == "auth_failed":
        error_message = "Authentication failed. Please try again."
    elif error == "domain_not_allowed":
        error_message = f"Access restricted to @{settings.sso_allowed_domain} email addresses only."
    elif error == "invalid_state":
        error_message = "Invalid session. Please try again."
    elif error == "no_code":
        error_message = "No authorization code received. Please try again."
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Login - Sindbad.Tech SharePoint Doc Indexer</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: #f5f5f5;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .login-container {{
                background: #ffffff;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
                padding: 40px;
                max-width: 450px;
                width: 100%;
                border: 1px solid #e0e0e0;
            }}
            .login-header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .login-header h1 {{
                color: #333333;
                font-size: 28px;
                margin-bottom: 10px;
            }}
            .login-header p {{
                color: #666666;
                font-size: 14px;
            }}
            .error-message {{
                background: #3a2525;
                border: 1px solid #5a3535;
                color: #ff6b6b;
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 20px;
                font-size: 14px;
            }}
            .login-button {{
                width: 100%;
                background: rgba(9, 115, 230, 1);
                color: #ffffff;
                border: 1px solid rgba(9, 115, 230, 1);
                padding: 14px 24px;
                font-size: 16px;
                font-weight: 600;
                border-radius: 6px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
                transition: all 0.2s;
                text-decoration: none;
            }}
            .login-button:hover {{
                background: rgba(8, 100, 200, 1);
                border-color: rgba(8, 100, 200, 1);
            }}
            .login-button:active {{
                background: rgba(7, 85, 170, 1);
            }}
            .info-box {{
                background: #f9f9f9;
                border-left: 4px solid #00ffff;
                padding: 15px;
                margin-top: 20px;
                border-radius: 4px;
                border: 1px solid #e0e0e0;
            }}
            .info-box p {{
                color: #666666;
                font-size: 13px;
                line-height: 1.6;
            }}
            .info-box strong {{
                color: #333333;
            }}
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="login-header">
                    <h1>📁 Sindbad.Tech SharePoint Doc Indexer</h1>
                <p>Sign in with your Microsoft account</p>
            </div>
            
            {f'<div class="error-message">{error_message}</div>' if error_message else ''}
            
            <a href="/auth/start" class="login-button">
                <svg width="20" height="20" viewBox="0 0 23 23" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M11.5 0C5.15 0 0 5.15 0 11.5C0 17.85 5.15 23 11.5 23C17.85 23 23 17.85 23 11.5C23 5.15 17.85 0 11.5 0Z" fill="#F25022"/>
                    <path d="M11.5 0C5.15 0 0 5.15 0 11.5C0 13.45 0.5 15.25 1.35 16.8L7.5 10.65V0H11.5Z" fill="#7FBA00"/>
                    <path d="M23 11.5C23 5.15 17.85 0 11.5 0V11.5H23Z" fill="#00A4EF"/>
                    <path d="M11.5 23C17.85 23 23 17.85 23 11.5H11.5V23Z" fill="#FFB900"/>
                </svg>
                Sign in with Microsoft
            </a>
            
            <div class="info-box">
                <p><strong>Access Restricted:</strong> This application is only available to @{settings.sso_allowed_domain} employees.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/start")
async def start_login(request: Request) -> RedirectResponse:
    """Initiate Microsoft SSO login.
    
    Returns:
        Redirect to Microsoft login page
    """
    auth_service = get_auth_service()
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    request.session["auth_state"] = state
    
    # Log for debugging
    logger.info(f"Generated state: {state[:10]}... (stored in session)")
    
    # Get login URL
    login_url = auth_service.get_login_url(state=state)
    
    logger.info("Redirecting to Microsoft login")
    # Create response to ensure session cookie is set
    response = RedirectResponse(url=login_url, status_code=302)
    return response


@router.get("/callback")
async def callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None) -> RedirectResponse:
    """Handle Microsoft SSO callback.
    
    Args:
        code: Authorization code from Microsoft
        state: State parameter for CSRF protection
        error: Error from Microsoft if authentication failed
        
    Returns:
        Redirect to home page or login page
    """
    auth_service = get_auth_service()
    
    # Check for errors
    if error:
        logger.error(f"Authentication error: {error}")
        return RedirectResponse(url="/auth/login?error=auth_failed", status_code=302)
    
    # Verify state
    session_state = request.session.get("auth_state")
    logger.info(f"Callback received state: {state[:10] if state else 'None'}...")
    logger.info(f"Session state: {session_state[:10] if session_state else 'None'}...")
    
    if not state:
        logger.error("No state parameter received from Microsoft")
        return RedirectResponse(url="/auth/login?error=invalid_state", status_code=302)
    
    if not session_state:
        logger.error("No state found in session - session may have expired or cookie not set")
        return RedirectResponse(url="/auth/login?error=invalid_state", status_code=302)
    
    if state != session_state:
        logger.error(f"State mismatch - received: {state[:10]}..., expected: {session_state[:10]}...")
        return RedirectResponse(url="/auth/login?error=invalid_state", status_code=302)
    
    # Clear state from session
    request.session.pop("auth_state", None)
    
    if not code:
        logger.error("No authorization code received")
        return RedirectResponse(url="/auth/login?error=no_code", status_code=302)
    
    try:
        # Exchange code for token
        token_result = await auth_service.acquire_token_by_code(code)
        
        # Get user info
        access_token = token_result.get("access_token")
        if not access_token:
            raise Exception("No access token in response")
        
        user_info = await auth_service.get_user_info(access_token)
        user_email = user_info.get("mail") or user_info.get("userPrincipalName", "")
        
        # Validate domain
        if not auth_service.validate_user_domain(user_email):
            logger.warning(f"Access denied for user: {user_email} (not from {settings.sso_allowed_domain})")
            return RedirectResponse(url="/auth/login?error=domain_not_allowed", status_code=302)
        
        # Store user info in session
        request.session["user"] = {
            "email": user_email,
            "name": user_info.get("displayName", ""),
            "id": user_info.get("id", ""),
        }
        request.session["authenticated"] = True
        
        logger.info(f"User authenticated: {user_email}")
        
        # Redirect to home
        return RedirectResponse(url="/", status_code=302)
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}", exc_info=True)
        return RedirectResponse(url="/auth/login?error=auth_failed", status_code=302)


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    """Logout user and clear session.
    
    Returns:
        Redirect to login page
    """
    user_email = request.session.get("user", {}).get("email", "Unknown")
    request.session.clear()
    logger.info(f"User logged out: {user_email}")
    
    # Redirect to login page
    return RedirectResponse(url="/auth/login", status_code=302)

