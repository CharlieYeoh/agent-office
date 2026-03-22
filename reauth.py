from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/drive.readonly'
]

flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0, access_type='offline', prompt='consent')

with open('token.json', 'w') as f:
    f.write(creds.to_json())

print('Done. token.json created with refresh token.')