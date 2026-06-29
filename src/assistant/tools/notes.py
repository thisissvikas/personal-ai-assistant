import subprocess

from langchain_core.tools import StructuredTool

from .. import config as cfg_module
from .registry import register


def _escape_applescript(text: str) -> str:
    """Escape characters that would break an AppleScript double-quoted string literal.

    Newlines cannot appear inside a single-line -e argument, so they are
    replaced with a space rather than propagated.
    """
    return (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r\n", " ")
        .replace("\n", " ")
        .replace("\r", " ")
    )


def _create_note(title: str, body: str) -> str:
    """Create a note in Apple Notes via AppleScript.

    Creates the target folder if it doesn't already exist. The folder name
    comes from ``PAI_NOTES_FOLDER`` in config (default: ``Personal``).
    """
    cfg = cfg_module.load()
    folder_name = cfg.get("notes", {}).get("folder", "Personal")

    safe_title = _escape_applescript(title)
    safe_body = _escape_applescript(body)
    safe_folder = _escape_applescript(folder_name)

    applescript = f'''
tell application "Notes"
    if not (exists folder "{safe_folder}") then
        make new folder with properties {{name:"{safe_folder}"}}
    end if
    tell folder "{safe_folder}"
        make new note with properties {{name:"{safe_title}", body:"{safe_body}"}}
    end tell
end tell
'''
    process_result = subprocess.run(
        ["osascript", "-e", applescript], capture_output=True, text=True
    )
    if process_result.returncode != 0:
        return f"Failed to create note: {process_result.stderr.strip()}"
    return f'Note "{title}" created in Apple Notes (folder: {folder_name}).'


def _search_notes(query: str) -> str:
    """Search all Apple Notes for the given keyword via AppleScript.

    Returns matching note titles plus a 200-character content snippet for each.
    """
    safe_query = _escape_applescript(query.lower())

    applescript = f'''
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
    process_result = subprocess.run(
        ["osascript", "-e", applescript], capture_output=True, text=True
    )
    if process_result.returncode != 0:
        return f"Failed to search notes: {process_result.stderr.strip()}"

    output = process_result.stdout.strip()
    if not output or output == "{}":
        return f"No notes found matching '{query}'."
    return output


register(
    StructuredTool.from_function(
        func=_create_note,
        name="create_note",
        description=(
            "Create a new note in Apple Notes with the given title and body text. "
            "Use this when the user asks you to take a note, jot something down, "
            "or save information for later."
        ),
    )
)

register(
    StructuredTool.from_function(
        func=_search_notes,
        name="search_notes",
        description=(
            "Search through existing Apple Notes by keyword. "
            "Returns matching note titles and content snippets."
        ),
    )
)
