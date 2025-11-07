"""Authentication service for Microsoft SSO."""

import secrets
from typing import Optional, Dict, Any
from urllib.parse import urlencode
from msal import ConfidentialClientApplication, PublicClientApplication
from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class AuthService:
    """Service for handling Microsoft SSO authentication."""

    def __init__(self):
        """Initialize the authentication service."""
        self.authority = f"https://login.microsoftonline.com/{settings.azure_tenant_id}"
        self.client_id = settings.azure_client_id
        self.client_secret = settings.azure_client_secret
        self.redirect_uri = settings.sso_redirect_uri or "http://localhost:8000/auth/callback"
        self.allowed_domain = settings.sso_allowed_domain.lower()
        
        # Scopes for user authentication
        # Note: MSAL automatically adds 'openid', 'profile', and 'offline_access'
        # We only need to specify the actual permission scopes
        self.scopes = [
            "User.Read",
        ]
        
        # Create MSAL app for user authentication
        self._msal_app = ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=self.authority,
        )

    def get_login_url(self, state: Optional[str] = None) -> str:
        """Generate Microsoft login URL.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Microsoft login URL
        """
        if not state:
            state = secrets.token_urlsafe(32)
        
        # MSAL will automatically add 'openid', 'profile', 'offline_access'
        # We need to include them in the authorization URL for proper OAuth flow
        scopes_for_url = self.scopes + ["openid", "profile"]
        
        auth_url = (
            f"{self.authority}/oauth2/v2.0/authorize?"
            f"client_id={self.client_id}&"
            f"response_type=code&"
            f"redirect_uri={self.redirect_uri}&"
            f"response_mode=query&"
            f"scope={' '.join(scopes_for_url)}&"
            f"state={state}"
        )
        
        return auth_url

    async def acquire_token_by_code(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token.
        
        Args:
            code: Authorization code from Microsoft
            
        Returns:
            Token response with user info
        """
        try:
            result = self._msal_app.acquire_token_by_authorization_code(
                code=code,
                scopes=self.scopes,
                redirect_uri=self.redirect_uri,
            )
            
            if "error" in result:
                error = result.get("error_description", result.get("error", "Unknown error"))
                raise Exception(f"Token acquisition failed: {error}")
            
            return result
        except Exception as e:
            logger.error(f"Failed to acquire token: {e}", exc_info=True)
            raise

    def validate_user_domain(self, email: Optional[str]) -> bool:
        """Validate that user email is from allowed domain.
        
        Args:
            email: User email address
            
        Returns:
            True if email is from allowed domain, False otherwise
        """
        if not email:
            return False
        
        email_lower = email.lower()
        allowed_domain = f"@{self.allowed_domain}"
        
        return email_lower.endswith(allowed_domain)

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Microsoft Graph API.
        
        Args:
            access_token: Access token for Microsoft Graph
            
        Returns:
            User information dictionary
        """
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

