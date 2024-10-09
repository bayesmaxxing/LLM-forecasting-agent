import anthropic
import requests
import json
from datetime import datetime 
from './tools.py' import download_gmail_emails, get_forecasts, send_email

get_news = {
    "name": "get_news",
    "description": "Get news related to a forecast",
    "input_schema": {
        "type": "object", 
        "properties": {
            
        }
    }
}
client = anthropic.Client(api_key = '')

def main():
    # First get the news of the day and insert into prompt
    news =  download_gmail_emails(10, "news")

    file = open("prompt.txt","r")
    prompt = file.read()

    response = client.messages.create(
        model = "claude-3-5-sonnet-20240620",
        max_tokens=2048,
        tools=[
            {
                "name": "send_email",
                "description": "Sends an email with a subject and a body. Use this when sending summaries.",
                "input_schema": {
                    "type": "object", 
                    "properties": {
                        "subject": "The subject of the email. e.g something like Forecast Minutes or similar. Also add today's date in the subject",
                        "body": "The body of the email. This is where summaries and the main text goes.""
                    }
                }, 
            }
        ], 
        messages = [{"role": "user", "content": prompt}]
    )
