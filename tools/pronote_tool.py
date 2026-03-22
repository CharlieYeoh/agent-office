import pronotepy
import os
import json
from datetime import date, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CREDENTIALS_FILE = Path("pronote_token.json")


def _get_client():
    """Connect to Pronote and return a client object."""
    url      = os.environ["PRONOTE_URL"]
    username = os.environ["PRONOTE_USERNAME"]
    password = os.environ["PRONOTE_PASSWORD"]

    if CREDENTIALS_FILE.exists():
        try:
            creds = json.loads(CREDENTIALS_FILE.read_text())
            client = pronotepy.Client.token_login(**creds)
            if client.logged_in:
                CREDENTIALS_FILE.write_text(json.dumps(client.export_credentials()))
                return client
        except Exception:
            pass

    # Fall back to username/password login
    client = pronotepy.Client(url, username=username, password=password)
    if client.logged_in:
        CREDENTIALS_FILE.write_text(json.dumps(client.export_credentials()))
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
