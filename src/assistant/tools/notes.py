import subprocess

from .. import config as cfg_module
from .registry import register

_CREATE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_note",
        "description": (
            "Create a new note in Apple Notes with the given title and body text. "
            "Use this when the user asks you to take a note, jot something down, "
            "or save information for later."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "The note title"},
                "body": {"type": "string", "description": "The note content/body"},
            },
            "required": ["title", "body"],
        },
    },
}

_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_notes",
        "description": (
            "Search through existing Apple Notes by keyword. Returns matching note titles and content snippets."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword or phrase"},
            },
            "required": ["query"],
        },
    },
}


def _escape_applescript(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _create_note(title: str, body: str) -> str:
    cfg = cfg_module.load()
    folder = cfg.get("notes", {}).get("folder", "Personal")

    safe_title = _escape_applescript(title)
    safe_body = _escape_applescript(body)
    safe_folder = _escape_applescript(folder)

    script = f'''
tell application "Notes"
    if not (exists folder "{safe_folder}") then
        make new folder with properties {{name:"{safe_folder}"}}
    end if
    tell folder "{safe_folder}"
        make new note with properties {{name:"{safe_title}", body:"{safe_body}"}}
    end tell
end tell
'''
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        return f"Failed to create note: {result.stderr.strip()}"
    return f'Note "{title}" created in Apple Notes (folder: {folder}).'


def _search_notes(query: str) -> str:
    safe_query = _escape_applescript(query.lower())

    script = f'''
set matchingNotes to {{}}
tell application "Notes"
    repeat with aNote in every note
        set noteBody to body of aNote
        set noteTitle to name of aNote
        if noteTitle contains "{safe_query}" or noteBody contains "{safe_query}" then
            set end of matchingNotes to "Title: " & noteTitle & "\\nSnippet: " & (text 1 thru (minimum value of {{200, (length of noteBody)}}) of noteBody)
        end if
    end repeat
end tell
return matchingNotes
'''
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        return f"Failed to search notes: {result.stderr.strip()}"

    output = result.stdout.strip()
    if not output or output == "{}":
        return f"No notes found matching '{query}'."
    return output


register(_CREATE_SCHEMA, _create_note)
register(_SEARCH_SCHEMA, _search_notes)
