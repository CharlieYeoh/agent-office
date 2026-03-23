import os, base64, json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


def _load_google_token_info():
    raw = os.environ.get("GOOGLE_TOKEN_JSON")
    if raw:
        return json.loads(raw)

    raw_b64 = os.environ.get("GOOGLE_TOKEN_JSON_B64")
    if raw_b64:
        decoded = base64.b64decode(raw_b64).decode("utf-8")
        return json.loads(decoded)

    return None


def _gmail_service():
    token_info = _load_google_token_info()
    if token_info:
        creds = Credentials.from_authorized_user_info(token_info)
    elif os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json')
    else:
        raise RuntimeError('No Google credentials: token.json not found and GOOGLE_TOKEN_JSON/GOOGLE_TOKEN_JSON_B64 not set.')

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build('gmail', 'v1', credentials=creds)


def read_emails(max_results: int = 10) -> str:
    """Read the latest N emails from your inbox."""
    try:
        svc = _gmail_service()
        messages = svc.users().messages().list(
            userId='me', labelIds=['INBOX'], maxResults=max_results
        ).execute().get('messages', [])

        results = []
        for msg in messages:
            detail = svc.users().messages().get(
                userId='me', id=msg['id'], format='full'
            ).execute()
            headers = {h['name']: h['value'] for h in detail['payload']['headers']}
            subject = headers.get('Subject', '(no subject)')
            sender  = headers.get('From', 'unknown')
            snippet = detail.get('snippet', '')
            results.append(f"From: {sender}\nSubject: {subject}\nPreview: {snippet}\nID: {msg['id']}")
        return '\n\n'.join(results) if results else 'Inbox is empty.'
    except Exception as e:
        return f'Gmail error: {e}'


def draft_reply(message_id: str, reply_text: str) -> str:
    """Save a draft reply to a specific email (does not send)."""
    try:
        svc = _gmail_service()
        original = svc.users().messages().get(
            userId='me', id=message_id, format='metadata'
        ).execute()
        headers = {h['name']: h['value'] for h in original['payload']['headers']}
        to      = headers.get('From', '')
        subject = 'Re: ' + headers.get('Subject', '')
        thread_id = original.get('threadId', '')

        raw_msg = f'To: {to}\nSubject: {subject}\n\n{reply_text}'
        encoded = base64.urlsafe_b64encode(raw_msg.encode()).decode()
        draft_body = {'message': {'raw': encoded, 'threadId': thread_id}}

        svc.users().drafts().create(userId='me', body=draft_body).execute()
        return f'Draft saved. To: {to}, Subject: {subject}'
    except Exception as e:
        return f'Gmail draft error: {e}'


