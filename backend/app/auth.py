"""
OAuth2 authentication via MSAL.

Azure app (client_id: f759339d-4358-445b-9276-f7f5c8513016) must have:
  - API permission: Office 365 Exchange Online > EWS.AccessAsUser.All (Delegated)
  - Authentication > "Allow public client flows" = Yes
  - Redirect URI: http://localhost:8400 (type: Mobile and desktop applications)
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import msal
from fastapi import HTTPException

CLIENT_ID = "f759339d-4358-445b-9276-f7f5c8513016"
TENANT_ID = "2e5f16a8-8000-492c-a0fb-73e46d3aaf77"
REDIRECT_URI = "http://localhost:8400"
SCOPES = ["https://outlook.office.com/EWS.AccessAsUser.All"]
ALLOWED_DOMAIN = "fortisstructural.com"

TOKEN_CACHE_FILE = Path.home() / ".fortis_email_tool" / "token_cache.json"

_token_cache: Optional[msal.SerializableTokenCache] = None
_msal_app: Optional[msal.PublicClientApplication] = None


def _get_token_cache() -> msal.SerializableTokenCache:
    global _token_cache
    if _token_cache is None:
        _token_cache = msal.SerializableTokenCache()
        if TOKEN_CACHE_FILE.exists():
            _token_cache.deserialize(TOKEN_CACHE_FILE.read_text())
    return _token_cache


def _save_token_cache() -> None:
    if _token_cache and _token_cache.has_state_changed:
        TOKEN_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_CACHE_FILE.write_text(_token_cache.serialize())


def _get_msal_app() -> msal.PublicClientApplication:
    global _msal_app
    if _msal_app is None:
        _msal_app = msal.PublicClientApplication(
            client_id=CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{TENANT_ID}",
            token_cache=_get_token_cache(),
        )
    return _msal_app


def get_cached_token() -> Optional[dict]:
    """Return a valid token from cache (silent refresh), or None if not authenticated."""
    app = _get_msal_app()
    accounts = app.get_accounts()
    if not accounts:
        return None
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    if result and "access_token" in result:
        _save_token_cache()
        return result
    return None


def _do_interactive_login() -> dict:
    """Blocking - opens browser for user login. Run in thread executor."""
    app = _get_msal_app()
    result = app.acquire_token_interactive(scopes=SCOPES, port=8400)
    _save_token_cache()
    return result


async def interactive_login() -> dict:
    """Trigger interactive browser login. Returns token result dict."""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _do_interactive_login)
    if "error" in result:
        raise HTTPException(
            400,
            f"Authentication failed: {result.get('error_description', result['error'])}",
        )
    return result


def get_user_email(token_result: dict) -> str:
    """Extract the user's email/UPN from token claims."""
    claims = token_result.get("id_token_claims") or {}
    email = (
        claims.get("preferred_username")
        or claims.get("upn")
        or claims.get("email")
        or ""
    )
    return email.lower().strip()


def verify_domain(email: str) -> bool:
    return email.endswith(f"@{ALLOWED_DOMAIN}")


def require_auth() -> tuple[str, str]:
    """
    Returns (user_email, access_token) or raises HTTPException.
    Call this at the start of any protected route handler.
    """
    token = get_cached_token()
    if not token:
        raise HTTPException(401, "Not authenticated. Please login first.")
    email = get_user_email(token)
    if not verify_domain(email):
        raise HTTPException(403, f"Account {email!r} is not authorized (must be @{ALLOWED_DOMAIN})")
    return email, token["access_token"]


def clear_auth() -> None:
    """Remove cached token and reset MSAL app state."""
    global _token_cache, _msal_app
    if TOKEN_CACHE_FILE.exists():
        TOKEN_CACHE_FILE.unlink()
    _token_cache = None
    _msal_app = None
