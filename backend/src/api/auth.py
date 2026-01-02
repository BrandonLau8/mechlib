from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from jwt.exceptions import InvalidTokenError

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.auth.transport import requests
from google.oauth2 import id_token

from config import config

"""
1. Google token verification: https://google-auth.readthedocs.io/en/master/reference/google.oauth2.id_token.html
2. JWT handling: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/#handle-jwt-tokens 
"""

# Security scheme for bearer token
security = HTTPBearer()

# JWT Configuration (loaded from environment)
JWT_SECRET_KEY = config.jwt_secret_key
JWT_ALGORITHM = config.jwt_algorithm
JWT_EXPIRATION_HOURS = config.jwt_expiration_hours
GOOGLE_CLIENT_ID = config.google_client_id


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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}"
        )