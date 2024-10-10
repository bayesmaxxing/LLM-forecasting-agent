import numpy as np 
import psycopg as pg 
import os 
from google.oauth2.credentials import Credentials 
from googleapiclient.discovery import build
from google.auth.transport.requests import Request 
from google_auth_oauthlib.flow import InstalledAppFlow
from email.mime.text import MIMEText
from googleapiclient.errors import HttpError
import base64
from dotenv import load_dotenv

def get_forecasts():
    """
    Get the forecasts related to a particular category.
    :param category: the category of forecasts to fetch.
    """
    load_dotenv()

    db_pass = os.getenv("DB_PASSWORD")
    host = os.getenv("HOST")

    with pg.connect(f'dbname=postgres user=postgres host={host} port=5432 password={db_pass}') as conn:
        with conn.cursor() as cur:
            cur.execute("""
                        SELECT question, category, created  
                        FROM forecast_v2
                        WHERE resolved IS NULL
                        """)

            forecasts = cur.fetchall()
            return [
                {
                    "question": row[0],
                    "category": row[1],
                    "created_at": row[2]
                }
                for row in forecasts
            ]

def download_gmail_emails(num_emails=10, tag="news"):
    """
    Download a specified number of emails from Gmail as text. 
    :param num_emails: the number of emails to download (default is 10)
    :param tag: the tag the downloaded emails should have
    :return: A list of dictionaries containing email metadata and text content
    """
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.modify','https://www.googleapis.com/auth/gmail.send']

    creds = None
    
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)

    query = f'label:{tag}' if tag else ''

    results = service.users().messages().list(userId='me', maxResults=num_emails, q=query).execute()
    messages = results.get('messages', [])

    email_data = []
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
        
        # Extract email content
        payload = msg['payload']
        headers = payload.get("headers")
        parts = payload.get("parts")
        
        subject = next(header['value'] for header in headers if header['name'] == 'Subject')
        sender = next(header['value'] for header in headers if header['name'] == 'From')
        
        if parts:
            body = parts[0]['body']
            data = body.get('data')
        else:
            data = payload['body'].get('data')
        
        if data:
            text = base64.urlsafe_b64decode(data).decode()
        else:
            text = ""
        
        email_data.append({
            'id': msg['id'],
            'subject': subject,
            'sender': sender,
            'text': text
        })

    return email_data 

def send_email(subject, body):
    """
    Send an email to yourself.
    :param subject: The subject of the email
    :param body: The body content of the email
    """
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']

    creds = None
    
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)

    message = MIMEText(body)
    message['to'] = 'bayesmaxxing@gmail.com'  # Replace with your email address
    message['subject'] = subject

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    try:
        sent_message = service.users().messages().send(userId="me", body={'raw': raw_message}).execute()
        print(f'Message Id: {sent_message["id"]}')
        return sent_message
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None


