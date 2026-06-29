from datetime import UTC, datetime, timedelta

import httpx

from .. import auth
from .. import config as cfg_module
from .registry import register

_GRAPH = "https://graph.microsoft.com/v1.0"

_GET_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_today_schedule",
        "description": (
            "Fetch the user's calendar events for today (or a specified date range). "
            "Use this when asked about the schedule, agenda, meetings, or free slots."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date to fetch events for (YYYY-MM-DD). Defaults to today.",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to look ahead (default 1).",
                    "default": 1,
                },
            },
        },
    },
}

_CREATE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_meeting",
        "description": (
            "Create a calendar event / meeting in Outlook. Adds attendees and sends invites. "
            "Use this when the user asks to schedule a call, book a meeting, or set up a catch-up."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Meeting title/subject"},
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee email addresses or display names",
                },
                "start": {
                    "type": "string",
                    "description": "Start time in ISO 8601 format or natural language (e.g. '2024-07-15T14:00:00')",
                },
                "end": {
                    "type": "string",
                    "description": "End time in ISO 8601 format. If omitted, defaults to 30 minutes after start.",
                },
                "body": {
                    "type": "string",
                    "description": "Optional meeting description/agenda",
                },
                "location": {
                    "type": "string",
                    "description": "Optional meeting location or Teams link request",
                },
                "is_online": {
                    "type": "boolean",
                    "description": "Whether to add a Teams meeting link (default true)",
                    "default": True,
                },
            },
            "required": ["subject", "start"],
        },
    },
}


def _token() -> str:
    cfg = cfg_module.load()
    ms = cfg.get("microsoft", {})
    return auth.get_token(ms["client_id"], ms["tenant_id"])


def _local_tz() -> str:
    cfg = cfg_module.load()
    return cfg.get("timezone", datetime.now(UTC).astimezone().tzname() or "UTC")


def _get_today_schedule(date: str | None = None, days: int = 1) -> str:
    token = _token()
    tz_name = _local_tz()

    if date:
        start_dt = datetime.fromisoformat(date)
    else:
        start_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    end_dt = start_dt + timedelta(days=days)
    start_str = start_dt.isoformat()
    end_str = end_dt.isoformat()

    resp = httpx.get(
        f"{_GRAPH}/me/calendarView",
        headers={"Authorization": f"Bearer {token}", "Prefer": f'outlook.timezone="{tz_name}"'},
        params={
            "startDateTime": start_str,
            "endDateTime": end_str,
            "$orderby": "start/dateTime",
            "$select": "subject,start,end,location,organizer,attendees,bodyPreview,isOnlineMeeting",
            "$top": 50,
        },
    )
    resp.raise_for_status()
    events = resp.json().get("value", [])

    if not events:
        label = date if date else "today"
        return f"No events found for {label}."

    lines = []
    for e in events:
        s = e["start"]["dateTime"][:16].replace("T", " ")
        en = e["end"]["dateTime"][:16].replace("T", " ")
        subject = e.get("subject", "(No subject)")
        loc = e.get("location", {}).get("displayName", "")
        online = " [Teams]" if e.get("isOnlineMeeting") else ""
        attendee_names = [a["emailAddress"]["name"] for a in e.get("attendees", [])[:5]]
        att_str = ", ".join(attendee_names) if attendee_names else ""
        lines.append(f"• **{subject}**{online}  {s}-{en[-5:]}")
        if loc:
            lines.append(f"  Location: {loc}")
        if att_str:
            lines.append(f"  With: {att_str}")

    return "\n".join(lines)


def _create_meeting(
    subject: str,
    start: str,
    attendees: list[str] | None = None,
    end: str | None = None,
    body: str | None = None,
    location: str | None = None,
    is_online: bool = True,
) -> str:
    token = _token()
    tz_name = _local_tz()

    start_dt = (
        datetime.fromisoformat(start)
        if "T" in start
        else datetime.fromisoformat(start + "T09:00:00")
    )
    end_dt = datetime.fromisoformat(end) if end else start_dt + timedelta(minutes=30)

    attendee_list = []
    for a in attendees or []:
        attendee_list.append(
            {
                "emailAddress": {"address": a if "@" in a else f"{a}@placeholder.com", "name": a},
                "type": "required",
            }
        )

    payload: dict = {
        "subject": subject,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": tz_name},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": tz_name},
        "attendees": attendee_list,
        "isOnlineMeeting": is_online,
    }
    if body:
        payload["body"] = {"contentType": "HTML", "content": body}
    if location:
        payload["location"] = {"displayName": location}

    resp = httpx.post(
        f"{_GRAPH}/me/events",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
    )
    resp.raise_for_status()
    event = resp.json()
    web_link = event.get("webLink", "")

    duration_mins = int((end_dt - start_dt).total_seconds() / 60)
    att_names = ", ".join(a if "@" not in a else a.split("@")[0] for a in (attendees or []))
    result = (
        f'Meeting "{subject}" created for {start_dt.strftime("%A %d %b, %H:%M")} '
        f"({duration_mins} min)"
    )
    if att_names:
        result += f"\nAttendees: {att_names}"
    if web_link:
        result += f"\nOutlook link: {web_link}"
    return result


register(_GET_SCHEMA, _get_today_schedule)
register(_CREATE_SCHEMA, _create_meeting)
