import zoneinfo
from datetime import datetime, timedelta

import httpx
from langchain_core.tools import StructuredTool
from tzlocal import get_localzone_name

from .. import auth
from .. import config as cfg_module
from .registry import register

_GRAPH = "https://graph.microsoft.com/v1.0"


def _local_timezone() -> str:
    """Return the IANA timezone name for the current user.

    Checks ``PAI_TIMEZONE`` in config first; falls back to the OS-reported
    local timezone via ``tzlocal``. Returns ``"UTC"`` as a last resort.
    """
    cfg = cfg_module.load()
    configured = cfg.get("timezone", "")
    if configured:
        return configured
    return get_localzone_name() or "UTC"


def _get_today_schedule(date: str | None = None, days: int = 1) -> str:
    """Fetch calendar events from Microsoft Graph for the given date window.

    Defaults to today when ``date`` is omitted. Results are ordered by start
    time and formatted as a bullet list with subject, time, location, and
    attendees.
    """
    access_token = auth.get_graph_token()
    timezone_name = _local_timezone()
    tz = zoneinfo.ZoneInfo(timezone_name)

    if date:
        start_dt = datetime.fromisoformat(date)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=tz)
    else:
        start_dt = datetime.now(tz=tz).replace(hour=0, minute=0, second=0, microsecond=0)

    end_dt = start_dt + timedelta(days=days)

    response = httpx.get(
        f"{_GRAPH}/me/calendarView",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Prefer": f'outlook.timezone="{timezone_name}"',
        },
        params={
            "startDateTime": start_dt.isoformat(),
            "endDateTime": end_dt.isoformat(),
            "$orderby": "start/dateTime",
            "$select": "subject,start,end,location,organizer,attendees,bodyPreview,isOnlineMeeting",
            "$top": 50,
        },
    )
    response.raise_for_status()
    events = response.json().get("value", [])

    if not events:
        label = date if date else "today"
        return f"No events found for {label}."

    lines = []
    for event in events:
        start_time = event["start"]["dateTime"][:16].replace("T", " ")
        end_time = event["end"]["dateTime"][:16].replace("T", " ")
        subject = event.get("subject", "(No subject)")
        location_name = event.get("location", {}).get("displayName", "")
        online_badge = " [Teams]" if event.get("isOnlineMeeting") else ""
        attendee_names = [a["emailAddress"]["name"] for a in event.get("attendees", [])[:5]]
        attendees_display = ", ".join(attendee_names) if attendee_names else ""

        lines.append(f"• **{subject}**{online_badge}  {start_time}-{end_time[-5:]}")
        if location_name:
            lines.append(f"  Location: {location_name}")
        if attendees_display:
            lines.append(f"  With: {attendees_display}")

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
    """Create an Outlook calendar event via Microsoft Graph.

    Accepts ISO 8601 datetimes for ``start``/``end``. When ``end`` is omitted
    the meeting defaults to 30 minutes. Attendees without an ``@`` are
    treated as display names and get a placeholder email — a warning is
    included in the return value so the user knows invites were not delivered.
    """
    access_token = auth.get_graph_token()
    timezone_name = _local_timezone()
    tz = zoneinfo.ZoneInfo(timezone_name)

    start_dt = (
        datetime.fromisoformat(start)
        if "T" in start
        else datetime.fromisoformat(start + "T09:00:00")
    )
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=tz)

    end_dt = datetime.fromisoformat(end) if end else start_dt + timedelta(minutes=30)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=tz)

    attendee_list = []
    placeholder_names = []
    for attendee_email in attendees or []:
        if "@" in attendee_email:
            email_address = attendee_email
        else:
            email_address = f"{attendee_email}@placeholder.com"
            placeholder_names.append(attendee_email)
        attendee_list.append(
            {
                "emailAddress": {"address": email_address, "name": attendee_email},
                "type": "required",
            }
        )

    payload: dict = {
        "subject": subject,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": timezone_name},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": timezone_name},
        "attendees": attendee_list,
        "isOnlineMeeting": is_online,
    }
    if body:
        payload["body"] = {"contentType": "HTML", "content": body}
    if location:
        payload["location"] = {"displayName": location}

    response = httpx.post(
        f"{_GRAPH}/me/events",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json=payload,
    )
    response.raise_for_status()
    created_event = response.json()
    web_link = created_event.get("webLink", "")

    duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
    attendee_names_display = ", ".join(
        addr if "@" not in addr else addr.split("@")[0] for addr in (attendees or [])
    )
    summary = (
        f'Meeting "{subject}" created for {start_dt.strftime("%A %d %b, %H:%M")} '
        f"({duration_minutes} min)"
    )
    if attendee_names_display:
        summary += f"\nAttendees: {attendee_names_display}"
    if web_link:
        summary += f"\nOutlook link: {web_link}"
    if placeholder_names:
        summary += (
            f"\nWarning: no email address for {', '.join(placeholder_names)} "
            "— invite not delivered to them"
        )
    return summary


register(
    StructuredTool.from_function(
        func=_get_today_schedule,
        name="get_today_schedule",
        description=(
            "Fetch the user's calendar events for today (or a specified date range). "
            "Use this when asked about the schedule, agenda, meetings, or free slots."
        ),
    )
)

register(
    StructuredTool.from_function(
        func=_create_meeting,
        name="create_meeting",
        description=(
            "Create a calendar event / meeting in Outlook. Adds attendees and sends invites. "
            "Use this when the user asks to schedule a call, book a meeting, or set up a catch-up."
        ),
    )
)
