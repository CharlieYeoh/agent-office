import pronotepy
import os
import json
import base64
from datetime import date, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CREDENTIALS_FILE = Path("pronote_token.json")


def _load_json_from_env(var_name: str, b64_var_name: str | None = None):
    raw = os.environ.get(var_name)
    if raw:
        return json.loads(raw)

    if b64_var_name:
        raw_b64 = os.environ.get(b64_var_name)
        if raw_b64:
            decoded = base64.b64decode(raw_b64).decode("utf-8")
            return json.loads(decoded)

    return None


def _get_client():
    """Connect to Pronote and return a client object."""
    url = os.environ["PRONOTE_URL"]
    username = os.environ.get("PRONOTE_USERNAME", "")
    password = os.environ.get("PRONOTE_PASSWORD", "")

    env_token = _load_json_from_env("PRONOTE_TOKEN_JSON", "PRONOTE_TOKEN_JSON_B64")
    if env_token:
        try:
            client = pronotepy.Client.token_login(**env_token)
            if client.logged_in:
                return client
        except Exception:
            pass

    if CREDENTIALS_FILE.exists():
        try:
            creds = json.loads(CREDENTIALS_FILE.read_text())
            client = pronotepy.Client.token_login(**creds)
            if client.logged_in:
                try:
                    CREDENTIALS_FILE.write_text(json.dumps(client.export_credentials()))
                except Exception:
                    pass
                return client
        except Exception:
            pass

    if not username or not password:
        raise RuntimeError(
            "Pronote credentials missing. Set PRONOTE_USERNAME and PRONOTE_PASSWORD, "
            "or provide PRONOTE_TOKEN_JSON."
        )

    # Fall back to username/password login
    client = pronotepy.Client(url, username=username, password=password)
    if client.logged_in:
        try:
            CREDENTIALS_FILE.write_text(json.dumps(client.export_credentials()))
        except Exception:
            pass
        return client
    raise RuntimeError("Could not log in to Pronote")


def get_homework(days_ahead: int = 14) -> str:
    """
    Fetch homework due in the next N days.
    Returns a formatted string listing each task with subject, description,
    due date, and any attachment filenames.
    """
    try:
        client = _get_client()
        today = date.today()
        until = today + timedelta(days=days_ahead)
        homework_list = client.homework(today, until)

        if not homework_list:
            return "No homework found for the next " + str(days_ahead) + " days."

        result = []
        for hw in homework_list:
            raw_attachments = getattr(hw, 'attachments', None) or getattr(hw, 'files', None) or []
            attachments = ", ".join(a.name for a in raw_attachments) if raw_attachments else "none"

            result.append(
                f"Subject: {hw.subject.name}\n"
                f"Due: {hw.date}\n"
                f"Description: {hw.description}\n"
                f"Attachments: {attachments}\n"
                f"Done: {hw.done}"
            )
        return "\n\n".join(result)
    except Exception as e:
        return f"Pronote error: {e}"


def get_homework_for_subject(subject_name: str, days_ahead: int = 14) -> str:
    """Get homework for a specific subject (e.g. 'Mathématiques', 'Physique')."""
    try:
        client = _get_client()
        today = date.today()
        until = today + timedelta(days=days_ahead)
        all_hw = client.homework(today, until)
        filtered = [
            hw for hw in all_hw
            if subject_name.lower() in hw.subject.name.lower()
        ]
        if not filtered:
            return f"No homework found for subject: {subject_name}"
        result = []
        for hw in filtered:
            raw_attachments = getattr(hw, 'attachments', None) or getattr(hw, 'files', None) or []
            attachments = ", ".join(a.name for a in raw_attachments) if raw_attachments else "none"
            result.append(
                f"Due: {hw.date}\n"
                f"Description: {hw.description}\n"
                f"Attachments: {attachments}"
            )
        return "\n\n".join(result)
    except Exception as e:
        return f"Pronote error: {e}"
