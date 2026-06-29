import httpx
from langchain_core.tools import StructuredTool

from .. import auth
from .registry import register

_GRAPH = "https://graph.microsoft.com/v1.0"


def _find_teams_user(name: str) -> str:
    """Search Microsoft 365 users by display name or email prefix.

    Returns up to 5 matches with display name, email, and user ID. Useful
    when the caller only has a person's name and needs their ID for a DM.
    """
    safe_name = name.replace("'", "")  # guard against OData literal injection
    access_token = auth.get_graph_token()
    response = httpx.get(
        f"{_GRAPH}/users",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "$filter": f"startsWith(displayName, '{safe_name}') or startsWith(mail, '{safe_name}')",
            "$select": "id,displayName,mail",
            "$top": 5,
        },
    )
    response.raise_for_status()
    users = response.json().get("value", [])

    if not users:
        return f"No users found matching '{name}'."

    return "\n".join(
        f"• {user_entry['displayName']} — {user_entry.get('mail', 'no email')} (id: {user_entry['id']})"
        for user_entry in users
    )


def _send_teams_dm(user: str, message: str) -> str:
    """Send a 1:1 Teams DM to the given user email or Microsoft user ID.

    Creates the oneOnOne chat if it doesn't already exist (Graph handles
    deduplication automatically), then posts the message.
    """
    access_token = auth.get_graph_token()
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    chat_response = httpx.post(
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
    chat_response.raise_for_status()
    chat_id = chat_response.json()["id"]

    message_response = httpx.post(
        f"{_GRAPH}/chats/{chat_id}/messages",
        headers=headers,
        json={"body": {"content": message}},
    )
    message_response.raise_for_status()

    return f"Message sent to {user} on Teams."


def _send_channel_message(team_name: str, channel_name: str, message: str) -> str:
    """Post a message to a Teams channel, resolving team and channel by display name.

    Returns a helpful error listing available teams or channels when the
    requested name is not found.
    """
    access_token = auth.get_graph_token()
    headers = {"Authorization": f"Bearer {access_token}"}

    teams_response = httpx.get(
        f"{_GRAPH}/me/joinedTeams",
        headers=headers,
        params={"$select": "id,displayName"},
    )
    teams_response.raise_for_status()
    joined_teams = teams_response.json().get("value", [])

    matched_team = next(
        (team for team in joined_teams if team["displayName"].lower() == team_name.lower()),
        None,
    )
    if not matched_team:
        available_teams = ", ".join(team["displayName"] for team in joined_teams)
        return f"Team '{team_name}' not found. Your teams: {available_teams}"

    channels_response = httpx.get(
        f"{_GRAPH}/teams/{matched_team['id']}/channels",
        headers=headers,
        params={"$select": "id,displayName"},
    )
    channels_response.raise_for_status()
    team_channels = channels_response.json().get("value", [])

    matched_channel = next(
        (ch for ch in team_channels if ch["displayName"].lower() == channel_name.lower()),
        None,
    )
    if not matched_channel:
        available_channels = ", ".join(ch["displayName"] for ch in team_channels)
        return f"Channel '{channel_name}' not found in {team_name}. Channels: {available_channels}"

    post_response = httpx.post(
        f"{_GRAPH}/teams/{matched_team['id']}/channels/{matched_channel['id']}/messages",
        headers={**headers, "Content-Type": "application/json"},
        json={"body": {"content": message}},
    )
    post_response.raise_for_status()

    return f"Message posted to #{channel_name} in {team_name}."


register(
    StructuredTool.from_function(
        func=_find_teams_user,
        name="find_teams_user",
        description=(
            "Look up a Microsoft 365 user by name or partial name. Returns their display name "
            "and user ID needed for sending DMs. Call this before send_teams_dm when you only "
            "have a name, not an email."
        ),
    )
)

register(
    StructuredTool.from_function(
        func=_send_teams_dm,
        name="send_teams_dm",
        description=(
            "Send a direct message to a person on Microsoft Teams. "
            "Use the user's email address or user ID. "
            "If you only have their name, call find_teams_user first."
        ),
    )
)

register(
    StructuredTool.from_function(
        func=_send_channel_message,
        name="send_channel_message",
        description=(
            "Post a message to a Microsoft Teams channel. Specify the team name and channel name."
        ),
    )
)
