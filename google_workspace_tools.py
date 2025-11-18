import os.path
import base64
from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Define the scopes (permissions) you need
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_FILE = "token.json"
CRED_FILE = "credentials.json" # This MUST be in your root directory

def get_gmail_service():
    """
    Handles the complex OAuth flow for the Gmail API.
    Returns an authenticated service object.
    
    The first time this is run, it will open a browser for you to log in
    and grant permission. It will save your credentials in 'token.json'.
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CRED_FILE):
                raise FileNotFoundError(
                    f"'{CRED_FILE}' not found. "
                    "Please download it from Google Cloud Console and place it in the root."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CRED_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    
    service = build("gmail", "v1", credentials=creds)
    return service

def send_gmail(to_email: str, subject: str, body: str) -> dict:
    """
    Creates and sends an email message.
    """
    try:
        service = get_gmail_service()
        
        message = EmailMessage()
        message.set_content(body)
        message["To"] = to_email
        message["From"] = "me" # "me" is a special value for the authenticated user
        message["Subject"] = subject
        
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        create_message = {"raw": encoded_message}
        
        send_message = (
            service.users()
            .messages()
            .send(userId="me", body=create_message)
            .execute()
        )
        
        print(f"Message Id: {send_message['id']}")
        return {"success": True, "message_id": send_message['id']}
    
    except HttpError as err:
        print(f"An error occurred: {err}")
        return {"success": False, "error": str(err)}
    except Exception as e:
        print(f"An error occurred: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    # Test function
    print("Attempting to authenticate with Gmail...")
    # The first time you run `python google_workspace_tools.py`,
    # it will open your browser for authentication.
    service = get_gmail_service()
    print("Authentication successful. 'token.json' is created.")