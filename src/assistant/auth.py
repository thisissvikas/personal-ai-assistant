import os
import stat
from pathlib import Path

import msal

_TOKEN_CACHE_PATH = Path.home() / ".config" / "pai" / "token_cache.json"
_SCOPES = [
    "Calendars.ReadWrite",
    "Chat.ReadWrite",
    "ChannelMessage.Send",
    "Team.ReadBasic.All",
    "User.Read",
    "User.ReadBasic.All",
    "MailboxSettings.Read",
]


def _load_cache() -> msal.SerializableTokenCache:
    """Load the MSAL token cache from disk, or return an empty cache if none exists."""
    token_cache = msal.SerializableTokenCache()
    if _TOKEN_CACHE_PATH.exists():
        token_cache.deserialize(_TOKEN_CACHE_PATH.read_text())
    return token_cache


def _save_cache(token_cache: msal.SerializableTokenCache) -> None:
    """Persist the token cache to disk only when it has changed."""
    if token_cache.has_state_changed:
        _TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _TOKEN_CACHE_PATH.write_text(token_cache.serialize())
        os.chmod(_TOKEN_CACHE_PATH, stat.S_IRUSR | stat.S_IWUSR)


def get_token(client_id: str, tenant_id: str) -> str:
    """Return a valid Microsoft Graph access token.

    Attempts a silent token acquisition from the cache first. Falls back to
    the OAuth 2.0 device code flow when no cached token is available, which
    prints a URL and code for the user to authenticate in a browser. The
    token is cached to disk so subsequent calls are silent.
    """
    token_cache = _load_cache()
    app = msal.PublicClientApplication(
        client_id=client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        token_cache=token_cache,
    )

    cached_accounts = app.get_accounts()
    auth_result = None
    if cached_accounts:
        auth_result = app.acquire_token_silent(_SCOPES, account=cached_accounts[0])

    if not auth_result:
        device_flow = app.initiate_device_flow(scopes=_SCOPES)
        if "user_code" not in device_flow:
            raise RuntimeError(
                f"Failed to create device flow: {device_flow.get('error_description')}"
            )
        print(f"\n{device_flow['message']}\n")
        auth_result = app.acquire_token_by_device_flow(device_flow)

    _save_cache(token_cache)

    if "access_token" not in auth_result:
        raise RuntimeError(
            f"Authentication failed: "
            f"{auth_result.get('error_description', auth_result.get('error', 'unknown'))}"
        )

    return auth_result["access_token"]


def get_graph_token() -> str:
    """Return a Graph access token using client_id/tenant_id from config.

    Convenience wrapper so calendar.py and teams.py don't duplicate the
    config-loading logic. Delegates to ``get_token()`` for the actual auth.
    """
    from . import config as cfg_module

    cfg = cfg_module.load()
    microsoft_cfg = cfg.get("microsoft", {})
    return get_token(microsoft_cfg["client_id"], microsoft_cfg["tenant_id"])
