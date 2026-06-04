"""Authentication dependency for FastAPI routes.

Two modes, selected by ``AUTH_MODE``:

- ``disabled`` (default): no token required; every request runs as a fixed dev
  user. Keeps local development and the test suite frictionless.
- ``firebase``: requires an ``Authorization: Bearer <id-token>`` header. The
  token is a Firebase ID token, verified against Google's public keys using the
  project id — no service-account credential needed on the backend.
"""

from dataclasses import dataclass

import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient

from app.config import get_settings

# Google's JWK set for Firebase Secure Token service.
_FIREBASE_JWKS_URL = (
    "https://www.googleapis.com/service_accounts/v1/jwk/"
    "securetoken@system.gserviceaccount.com"
)

DEV_USER_ID = "dev-user"

_jwk_client: PyJWKClient | None = None


@dataclass
class AuthUser:
    uid: str
    email: str | None = None


def _jwks() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        _jwk_client = PyJWKClient(_FIREBASE_JWKS_URL)
    return _jwk_client


async def get_current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    settings = get_settings()

    if settings.auth_mode == "disabled":
        return AuthUser(uid=DEV_USER_ID, email="dev@local")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    project_id = settings.firebase_project_id
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="FIREBASE_PROJECT_ID is not configured",
        )

    token = authorization.split(" ", 1)[1]
    try:
        signing_key = _jwks().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=project_id,
            issuer=f"https://securetoken.google.com/{project_id}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    uid = claims.get("user_id") or claims.get("sub")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing a subject",
        )
    return AuthUser(uid=uid, email=claims.get("email"))
