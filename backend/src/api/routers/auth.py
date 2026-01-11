import logging
from datetime import datetime, timezone, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.auth.transport import requests
from google.oauth2 import id_token
from jwt import InvalidTokenError

from config import config
from src.api.schemas import GoogleAuthResponse, GoogleAuthRequest, UserInfoResponse

"""
1. Google token verification: https://google-auth.readthedocs.io/en/master/reference/google.oauth2.id_token.html
2. JWT handling: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/#handle-jwt-tokens 
"""

logger = logging.getLogger(__name__)

router = APIRouter()

# Security scheme for bearer token
security = HTTPBearer()

# JWT Configuration (loaded from environment)
JWT_SECRET_KEY = config.jwt_secret_key
JWT_ALGORITHM = config.jwt_algorithm
JWT_EXPIRATION_HOURS = config.jwt_expiration_hours
GOOGLE_CLIENT_ID = config.google_client_id

# ============================================================================
# Helper Functions
# ============================================================================

def verify_google_token(token: str) -> dict:
    """
    Verify Google OAuth ID token and return user info.

    Args:
        token: Google ID token from frontend

    Returns:
        dict with user info: { 'email': '...', 'name': '...', 'picture': '...' }

    Raises:
        HTTPException: If token is invalid
    """
    try:
        # Verify token with Google
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )

        # Verify issuer
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Invalid issuer')

        # Extract user info
        return {
            'email': idinfo['email'],
            'name': idinfo.get('name', ''),
            'picture': idinfo.get('picture', ''),
            'email_verified': idinfo.get('email_verified', False)
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}"
        )


def create_access_token(email: str, name: str) -> str:
    """
    Create JWT access token for authenticated user.

    Args:
        email: User's email address
        name: User's display name

    Returns:
        JWT token string
    """
    # Token expiration time (timezone-aware)
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=JWT_EXPIRATION_HOURS)

    # Token payload
    to_encode = {
        'sub': email,  # Subject (user identifier)
        'name': name,
        'exp': expire,
        'iat': now  # Issued at
    }

    # Create JWT
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Dependency to validate JWT and get current user.

    Usage in FastAPI endpoints:
        @app.get("/protected")
        def protected_route(user: dict = Depends(get_current_user)):
            return {"email": user["email"]}

    Args:
        credentials: HTTP Authorization header (Bearer token)

    Returns:
        dict with user info: { 'email': '...', 'name': '...' }

    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials

    try:
        # Decode JWT
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub")
        name: str = payload.get("name", "")

        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        return {"email": email, "name": name}

    except InvalidTokenError as e:
        # Show Error class name only to avoid potential token fragments
        logger.debug(f"JWT validation failed: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}"
        )

# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/google", response_model=GoogleAuthResponse)
def google_auth(request: GoogleAuthRequest):
    """
    Authenticate user with Google OAuth ID token.

    Frontend flow:
    1. User clicks "Sign in with Google"
    2. Frontend receives Google ID token
    3. Frontend sends token to this endpoint
    4. Backend validates token with Google
    5. Backend returns JWT for subsequent requests

    Args:
        request: GoogleAuthRequest with id_token

    Returns:
        GoogleAuthResponse with JWT access token
    """
    # Verify Google token and get user info
    user_info = verify_google_token(request.id_token)

    # Create JWT access token
    access_token = create_access_token(
        email=user_info['email'],
        name=user_info['name']
    )

    logger.info(f"User Authenticated: {user_info['email']}")
    logger.debug(f"Token created for {user_info['email'][:3]}")

    return GoogleAuthResponse(
        access_token=access_token,
        email=user_info['email'],
        name=user_info['name'],
        picture=user_info['picture']
    )

@router.get("/me", response_model=UserInfoResponse)
def get_user_info(user: dict = Depends(get_current_user)):
    """
    Get current authenticated user info.

    Requires: Authorization header with Bearer token

    Returns:
        UserInfoResponse with user email and name
    """
    return UserInfoResponse(
        email=user['email'],
        name=user['name']
    )