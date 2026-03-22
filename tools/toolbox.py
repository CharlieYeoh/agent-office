import os
import io
import json
import requests
from datetime import datetime, date, timedelta
from pathlib import Path
from dotenv import load_dotenv

from tools.github_tool import (
    list_repo_files, read_repo_file,
    write_repo_file, delete_repo_file, get_repo_info
)

load_dotenv()


# ══════════════════════════════════════════════════════════════════════════
# BASIC TOOLS
# ══════════════════════════════════════════════════════════════════════════

def web_search(query: str) -> str:
    """Search the web using DuckDuckGo. No API key needed."""
    try:
        url    = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_html": 1}
        r      = requests.get(url, params=params, timeout=8)
        data   = r.json()
        if data.get("AbstractText"):
            return data["AbstractText"][:800]
        topics  = data.get("RelatedTopics", [])[:5]
        results = [t["Text"] for t in topics if isinstance(t, dict) and "Text" in t]
        return "\n".join(results) if results else "No results found."
    except Exception as e:
        return f"Search error: {e}"


def read_file(filepath: str) -> str:
    """Read a text file and return its contents (max 4000 chars)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()[:4000]
    except FileNotFoundError:
        return f"Error: file '{filepath}' not found"
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(filepath: str, content: str) -> str:
    """Write content to a file, creating it if it does not exist."""
    try:
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Wrote {len(content)} characters to {filepath}"
    except Exception as e:
        return f"Error writing file: {e}"


def get_datetime(**kwargs) -> str:
    """Return the current date and time."""
    return datetime.now().strftime("%A, %d %B %Y at %H:%M")


def calculator(expression: str) -> str:
    """Safely evaluate a math expression."""
    try:
        allowed = set("0123456789+-*/()., ")
        if not all(c in allowed for c in expression):
            return "Error: unsafe expression"
        return str(eval(expression))  # noqa: S307
    except Exception as e:
        return f"Error: {e}"


# ══════════════════════════════════════════════════════════════════════════
# PRONOTE TOOLS
# ══════════════════════════════════════════════════════════════════════════

PRONOTE_TOKEN_FILE = Path("pronote_token.json")


def _pronote_client():
    """Connect to Pronote and return a logged-in client."""
    try:
        import pronotepy
    except ImportError:
        raise RuntimeError("pronotepy not installed. Run: pip install pronotepy")

    url      = os.environ.get("PRONOTE_URL", "")
    username = os.environ.get("PRONOTE_USERNAME", "")
    password = os.environ.get("PRONOTE_PASSWORD", "")

    if not url:
        raise RuntimeError("PRONOTE_URL not set in .env")

    # Try token login first (faster, avoids re-authenticating every call)
    if PRONOTE_TOKEN_FILE.exists():
        try:
            creds  = json.loads(PRONOTE_TOKEN_FILE.read_text())
            client = pronotepy.Client.token_login(**creds)
            if client.logged_in:
                PRONOTE_TOKEN_FILE.write_text(
                    json.dumps(client.export_credentials())
                )
                return client
        except Exception:
            pass

    client = pronotepy.Client(url, username=username, password=password)
    if client.logged_in:
        PRONOTE_TOKEN_FILE.write_text(json.dumps(client.export_credentials()))
        return client
    raise RuntimeError("Could not log in to Pronote — check URL, username, password in .env")


def _safe_attachments(hw) -> list:
    """Get attachments regardless of pronotepy version."""
    for attr in ("attachments", "files", "resources"):
        val = getattr(hw, attr, None)
        if val:
            return val
    return []


def get_homework(days_ahead: int = 14) -> str:
    """Fetch all homework due in the next N days from Pronote."""
    try:
        client = _pronote_client()
        today  = date.today()
        until  = today + timedelta(days=int(days_ahead))
        items  = client.homework(today, until)
        if not items:
            return f"No homework found for the next {days_ahead} days."
        result = []
        for hw in items:
            atts = ", ".join(
                getattr(a, "name", str(a)) for a in _safe_attachments(hw)
            ) or "none"
            result.append(
                f"Subject: {hw.subject.name}\n"
                f"Due: {hw.date}\n"
                f"Description: {hw.description}\n"
                f"Attachments: {atts}\n"
                f"Done: {hw.done}"
            )
        return "\n\n".join(result)
    except Exception as e:
        return f"Pronote error: {e}"


def get_homework_for_subject(subject_name: str, days_ahead: int = 14) -> str:
    """Fetch homework for a specific subject from Pronote."""
    try:
        client   = _pronote_client()
        today    = date.today()
        until    = today + timedelta(days=int(days_ahead))
        all_hw   = client.homework(today, until)
        filtered = [
            hw for hw in all_hw
            if subject_name.lower() in hw.subject.name.lower()
        ]
        if not filtered:
            return f"No homework found for '{subject_name}' in the next {days_ahead} days."
        result = []
        for hw in filtered:
            atts = ", ".join(
                getattr(a, "name", str(a)) for a in _safe_attachments(hw)
            ) or "none"
            result.append(
                f"Due: {hw.date}\n"
                f"Description: {hw.description}\n"
                f"Attachments: {atts}\n"
                f"Done: {hw.done}"
            )
        return "\n\n".join(result)
    except Exception as e:
        return f"Pronote error: {e}"


# ══════════════════════════════════════════════════════════════════════════
# GMAIL TOOLS
# ══════════════════════════════════════════════════════════════════════════

def _gmail_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import json as _json

    token_json = os.environ.get("GOOGLE_TOKEN_JSON")
    if token_json:
        info = _json.loads(token_json)
        creds = Credentials.from_authorized_user_info(info)
    elif os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json")
    else:
        raise RuntimeError(
            "No Google credentials found. "
            "Set GOOGLE_TOKEN_JSON in Render environment variables."
        )

    # Auto-refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build("gmail", "v1", credentials=creds)


def read_emails(max_results: int = 10) -> str:
    """Read the latest N emails from Gmail inbox."""
    try:
        svc      = _gmail_service()
        # Get the label ID for 'school'
        labels = svc.users().labels().list(userId="me").execute().get("labels", [])
        school_label = next((l["id"] for l in labels if l["name"].lower() == "school"), None)
        if not school_label:
            return "No label named 'school' found in your Gmail. Create it in Gmail settings first."
        messages = svc.users().messages().list(
            userId="me", labelIds=[school_label], maxResults=int(max_results)
        ).execute().get("messages", [])

        if not messages:
            return "Inbox is empty."

        results = []
        for msg in messages:
            detail  = svc.users().messages().get(
                userId="me", id=msg["id"], format="full"
            ).execute()
            headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
            results.append(
                f"ID: {msg['id']}\n"
                f"From: {headers.get('From', 'unknown')}\n"
                f"Subject: {headers.get('Subject', '(no subject)')}\n"
                f"Date: {headers.get('Date', '')}\n"
                f"Preview: {detail.get('snippet', '')}"
            )
        return "\n\n".join(results)
    except Exception as e:
        return f"Gmail error: {e}"


def draft_reply(message_id: str, reply_text: str) -> str:
    """Save a draft reply to a specific email. Does NOT send it."""
    try:
        import base64
        svc      = _gmail_service()
        original = svc.users().messages().get(
            userId="me", id=message_id, format="metadata"
        ).execute()
        headers   = {h["name"]: h["value"] for h in original["payload"]["headers"]}
        to        = headers.get("From", "")
        subject   = "Re: " + headers.get("Subject", "")
        thread_id = original.get("threadId", "")

        raw_msg = f"To: {to}\nSubject: {subject}\n\n{reply_text}"
        encoded = base64.urlsafe_b64encode(raw_msg.encode()).decode()
        svc.users().drafts().create(
            userId="me",
            body={"message": {"raw": encoded, "threadId": thread_id}}
        ).execute()
        return f"Draft saved. To: {to} | Subject: {subject}"
    except Exception as e:
        return f"Gmail draft error: {e}"


# ══════════════════════════════════════════════════════════════════════════
# GOOGLE DRIVE TOOLS
# ══════════════════════════════════════════════════════════════════════════

def _drive_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    token_json = os.environ.get("GOOGLE_TOKEN_JSON")
    if token_json:
        import json as _json
        creds = Credentials.from_authorized_user_info(_json.loads(token_json))
    else:
        creds = Credentials.from_authorized_user_file("token.json")
    return build("drive", "v3", credentials=creds)


def list_files_in_folder(folder_name: str) -> str:
    """List files in a Google Drive folder shared with you."""
    try:
        svc     = _drive_service()
        query   = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        folders = svc.files().list(
            q=query, fields="files(id,name)"
        ).execute().get("files", [])

        if not folders:
            return f"No folder named '{folder_name}' found in your Drive."

        folder_id = folders[0]["id"]
        files     = svc.files().list(
            q=f"'{folder_id}' in parents",
            fields="files(id,name,mimeType)"
        ).execute().get("files", [])

        if not files:
            return f"Folder '{folder_name}' is empty."

        return "\n".join(f"{f['name']}  (id: {f['id']})" for f in files)
    except Exception as e:
        return f"Drive error: {e}"


def read_text_file_drive(file_id: str) -> str:
    """Read the text content of a Google Drive file by its ID."""
    try:
        from googleapiclient.http import MediaIoBaseDownload
        svc  = _drive_service()
        meta = svc.files().get(fileId=file_id, fields="name,mimeType").execute()
        mime = meta["mimeType"]

        if "google-apps.document" in mime:
            content = svc.files().export(
                fileId=file_id, mimeType="text/plain"
            ).execute()
            return content.decode("utf-8")[:4000]

        buf  = io.BytesIO()
        dl   = MediaIoBaseDownload(buf, svc.files().get_media(fileId=file_id))
        done = False
        while not done:
            _, done = dl.next_chunk()
        return f"File downloaded: {len(buf.getvalue())} bytes | Name: {meta['name']}"
    except Exception as e:
        return f"Drive read error: {e}"


# ══════════════════════════════════════════════════════════════════════════
# TOOL REGISTRY — single source of truth for all agents
# ══════════════════════════════════════════════════════════════════════════

TOOL_REGISTRY = {

    # ── Basic ──────────────────────────────────────────────────────────────
    "web_search": (web_search, {
        "name": "web_search",
        "description": "Search the web for current information on any topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"]
        }
    }),
    "read_file": (read_file, {
        "name": "read_file",
        "description": "Read the contents of a local text file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path to the file"}
            },
            "required": ["filepath"]
        }
    }),
    "write_file": (write_file, {
        "name": "write_file",
        "description": "Write text content to a local file, creating it if needed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path to the file"},
                "content":  {"type": "string", "description": "Content to write"}
            },
            "required": ["filepath", "content"]
        }
    }),
    "get_datetime": (get_datetime, {
        "name": "get_datetime",
        "description": "Get the current date and time.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    }),
    "calculator": (calculator, {
        "name": "calculator",
        "description": "Evaluate a safe arithmetic expression.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Arithmetic expression e.g. '(12 * 3) / 4'"}
            },
            "required": ["expression"]
        }
    }),

    # ── Pronote ────────────────────────────────────────────────────────────
    "get_homework": (get_homework, {
        "name": "get_homework",
        "description": "Fetch all homework from Pronote due in the next N days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days_ahead": {"type": "integer", "description": "Days ahead to look (default 14)"}
            },
            "required": []
        }
    }),
    "get_homework_for_subject": (get_homework_for_subject, {
        "name": "get_homework_for_subject",
        "description": "Fetch homework from Pronote for a specific subject.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject_name": {"type": "string", "description": "Subject name as it appears in Pronote"},
                "days_ahead":   {"type": "integer", "description": "Days ahead to look (default 14)"}
            },
            "required": ["subject_name"]
        }
    }),

    # ── Gmail ──────────────────────────────────────────────────────────────
    "read_emails": (read_emails, {
        "name": "read_emails",
        "description": "Read the latest N emails from your Gmail inbox.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "Number of emails to fetch (default 10)"}
            },
            "required": []
        }
    }),
    "draft_reply": (draft_reply, {
        "name": "draft_reply",
        "description": "Save a draft reply to a specific email in Gmail. Does NOT send it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "The Gmail message ID to reply to"},
                "reply_text": {"type": "string", "description": "The full text of the reply"}
            },
            "required": ["message_id", "reply_text"]
        }
    }),


    # ── GitHub ──────────────────────────────────────────────────────────────
    "list_repo_files": (list_repo_files, {
    "name": "list_repo_files",
    "description": "List files and folders in the website GitHub repository.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Folder path to list (empty string for root)"}
        },
        "required": []
    }
    }),
    "read_repo_file": (read_repo_file, {
        "name": "read_repo_file",
        "description": "Read the contents of a file from the website GitHub repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path to the file e.g. 'index.html' or 'css/style.css'"}
            },
            "required": ["filepath"]
        }
    }),
    "write_repo_file": (write_repo_file, {
        "name": "write_repo_file",
        "description": "Write or update a file in the website GitHub repository. Creates a real commit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath":       {"type": "string", "description": "Path to the file"},
                "content":        {"type": "string", "description": "Full file content to write"},
                "commit_message": {"type": "string", "description": "Git commit message"}
            },
            "required": ["filepath", "content"]
        }
    }),
    "delete_repo_file": (delete_repo_file, {
        "name": "delete_repo_file",
        "description": "Delete a file from the website GitHub repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath":       {"type": "string", "description": "Path to the file to delete"},
                "commit_message": {"type": "string", "description": "Git commit message"}
            },
            "required": ["filepath"]
        }
    }),
    "get_repo_info": (get_repo_info, {
        "name": "get_repo_info",
        "description": "Get basic information about the website GitHub repository.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }),

    # ── Google Drive ───────────────────────────────────────────────────────
    "list_files_in_folder": (list_files_in_folder, {
        "name": "list_files_in_folder",
        "description": "List files in a Google Drive folder shared with you.",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_name": {"type": "string", "description": "Name of the Google Drive folder"}
            },
            "required": ["folder_name"]
        }
    }),
    "read_text_file_drive": (read_text_file_drive, {
        "name": "read_text_file_drive",
        "description": "Read the text content of a Google Drive file by its file ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "Google Drive file ID"}
            },
            "required": ["file_id"]
        }
    }),
}


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Run a tool by name and return its output as a string."""
    if tool_name not in TOOL_REGISTRY:
        return f"Error: unknown tool '{tool_name}'"
    fn, _ = TOOL_REGISTRY[tool_name]
    try:
        return str(fn(**tool_input))
    except Exception as e:
        return f"Error running {tool_name}: {e}"