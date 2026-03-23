import io, os, json
import base64
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


def _load_google_token_info():
    raw = os.environ.get("GOOGLE_TOKEN_JSON")
    if raw:
        return json.loads(raw)

    raw_b64 = os.environ.get("GOOGLE_TOKEN_JSON_B64")
    if raw_b64:
        decoded = base64.b64decode(raw_b64).decode("utf-8")
        return json.loads(decoded)

    return None


def _drive_service():
    token_info = _load_google_token_info()
    if token_info:
        creds = Credentials.from_authorized_user_info(token_info)
    elif os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json')
    else:
        raise RuntimeError('No Google credentials: token.json not found and GOOGLE_TOKEN_JSON/GOOGLE_TOKEN_JSON_B64 not set.')

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build('drive', 'v3', credentials=creds)


def list_files_in_folder(folder_name: str) -> str:
    """List files in a Google Drive folder shared with you."""
    try:
        svc = _drive_service()
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        folders = svc.files().list(q=query, fields='files(id,name)').execute().get('files', [])
        if not folders:
            return f'No folder named "{folder_name}" found in your Drive.'
        folder_id = folders[0]['id']
        files = svc.files().list(
            q=f"'{folder_id}' in parents",
            fields='files(id,name,mimeType)'
        ).execute().get('files', [])
        return '\n'.join(f"{f['name']} (id: {f['id']})" for f in files)
    except Exception as e:
        return f'Drive error: {e}'


def read_text_file(file_id: str) -> str:
    """Read the text content of a Google Drive file by its ID."""
    try:
        svc = _drive_service()
        meta = svc.files().get(fileId=file_id, fields='name,mimeType').execute()
        mime = meta['mimeType']

        # For Google Docs, export as plain text
        if 'google-apps.document' in mime:
            content = svc.files().export(
                fileId=file_id, mimeType='text/plain'
            ).execute()
            return content.decode('utf-8')[:4000]

        # For PDFs and other files, download bytes
        buf = io.BytesIO()
        dl  = MediaIoBaseDownload(buf, svc.files().get_media(fileId=file_id))
        done = False
        while not done:
            _, done = dl.next_chunk()
        # Return raw bytes as hex — agent will handle PDF parsing
        return f'File downloaded: {len(buf.getvalue())} bytes. Name: {meta["name"]}'
    except Exception as e:
        return f'Drive read error: {e}'

