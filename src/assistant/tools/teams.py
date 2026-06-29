import httpx

from .. import auth
from .. import config as cfg_module
from .registry import register

_GRAPH = "https://graph.microsoft.com/v1.0"

_FIND_USER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "find_teams_user",
        "description": (
            "Look up a Microsoft 365 user by name or partial name. Returns their display name "
            "and user ID needed for sending DMs. Call this before send_teams_dm when you only "
            "have a name, not an email."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Full or partial display name to search for",
                },
            },
            "required": ["name"],
        },
    },
}

_SEND_DM_SCHEMA = {
    "type": "function",
    "function": {
        "name": "send_teams_dm",
        "description": (
            "Send a direct message to a person on Microsoft Teams. "
            "Use the user's email address or user ID. "
            "If you only have their name, call find_teams_user first."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user": {
                    "type": "string",
                    "description": "Recipient's email address or Microsoft user ID",
                },
                "message": {"type": "string", "description": "Message text to send"},
            },
            "required": ["user", "message"],
        },
    },
}

_SEND_CHANNEL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "send_channel_message",
        "description": (
            "Post a message to a Microsoft Teams channel. Specify the team name and channel name."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "team_name": {"type": "string", "description": "The display name of the team"},
                "channel_name": {
                    "type": "string",
                    "description": "The channel name (e.g. 'General')",
                },
                "message": {"type": "string", "description": "Message text to post"},
            },
            "required": ["team_name", "channel_name", "message"],
        },
    },
}


def _token() -> str:
    cfg = cfg_module.load()
    ms = cfg.get("microsoft", {})
    return auth.get_token(ms["client_id"], ms["tenant_id"])


def _find_teams_user(name: str) -> str:
    token = _token()
    resp = httpx.get(
        f"{_GRAPH}/users",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "$filter": f"startsWith(displayName, '{name}') or startsWith(mail, '{name}')",
            "$select": "id,displayName,mail",
            "$top": 5,
        },
    )
    resp.raise_for_status()
    users = resp.json().get("value", [])

    if not users:
        return f"No users found matching '{name}'."

    lines = []
    for u in users:
        lines.append(f"• {u['displayName']} — {u.get('mail', 'no email')} (id: {u['id']})")
    return "\n".join(lines)


def _send_teams_dm(user: str, message: str) -> str:
    token = _token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Create or get existing 1:1 chat
    chat_resp = httpx.post(
        f"{_GRAPH}/me/chats",
        headers=headers,
        json={
            "chatType": "oneOnOne",
            "members": [
                {
                    "@odata.type": "#microsoft.graph.aadUserConversationMember",
                    "roles": ["owner"],
                    "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{user}')",
                },
                {
                    "@odata.type": "#microsoft.graph.aadUserConversationMember",
                    "roles": ["owner"],
                    "user@odata.bind": "https://graph.microsoft.com/v1.0/me",
                },
            ],
        },
    )
    chat_resp.raise_for_status()
    chat_id = chat_resp.json()["id"]

    # Send message
    msg_resp = httpx.post(
        f"{_GRAPH}/chats/{chat_id}/messages",
        headers=headers,
        json={"body": {"content": message}},
    )
    msg_resp.raise_for_status()

    return f"Message sent to {user} on Teams."


def _send_channel_message(team_name: str, channel_name: str, message: str) -> str:
    token = _token()
    headers = {"Authorization": f"Bearer {token}"}

    # Resolve team
    teams_resp = httpx.get(
        f"{_GRAPH}/me/joinedTeams",
        headers=headers,
        params={"$select": "id,displayName"},
    )
    teams_resp.raise_for_status()
    teams = teams_resp.json().get("value", [])

    team = next(
        (t for t in teams if t["displayName"].lower() == team_name.lower()),
        None,
    )
    if not team:
        team_names = ", ".join(t["displayName"] for t in teams)
        return f"Team '{team_name}' not found. Your teams: {team_names}"

    # Resolve channel
    chan_resp = httpx.get(
        f"{_GRAPH}/teams/{team['id']}/channels",
        headers=headers,
        params={"$select": "id,displayName"},
    )
    chan_resp.raise_for_status()
    channels = chan_resp.json().get("value", [])

    channel = next(
        (c for c in channels if c["displayName"].lower() == channel_name.lower()),
        None,
    )
    if not channel:
        chan_names = ", ".join(c["displayName"] for c in channels)
        return f"Channel '{channel_name}' not found in {team_name}. Channels: {chan_names}"

    # Post message
    post_resp = httpx.post(
        f"{_GRAPH}/teams/{team['id']}/channels/{channel['id']}/messages",
        headers={**headers, "Content-Type": "application/json"},
        json={"body": {"content": message}},
    )
    post_resp.raise_for_status()

    return f"Message posted to #{channel_name} in {team_name}."


register(_FIND_USER_SCHEMA, _find_teams_user)
register(_SEND_DM_SCHEMA, _send_teams_dm)
register(_SEND_CHANNEL_SCHEMA, _send_channel_message)
