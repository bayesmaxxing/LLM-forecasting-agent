import anthropic
import os
from dotenv import load_dotenv
import requests
import json
from datetime import datetime 
from tools import download_gmail_emails, get_forecasts, send_email

def main():
    # First get the news of the day and insert into prompt``
    load_dotenv()

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("Anthropic api key environment variable is not set")
    client = anthropic.Client(api_key = api_key)

    try:
        news =  download_gmail_emails(10, "news")
        forecasts = get_forecasts()

        file = open("prompt.txt","r")
        prompt = file.read()

        prompt += "\n\nForecasts:\n"
        for forecast in forecasts:
            prompt += f"- {forecast}\n"

        print(prompt)

        response = client.messages.create(
            model = "claude-3-5-sonnet-20240620",
            max_tokens=3084,
            tools=[
                {
                    "name": "send_email",
                    "description": "Sends an email with a subject and a body. Use this when sending summaries.",
                    "input_schema": {
                        "type": "object", 
                        "properties": {
                            "subject": {
                                    "type": "string",
                                    "description": "The subject of the email, choose this to be something short and informative about the body"
                                },
                            "body": {
                                    "type": "string",
                                    "description": "The body of the email. This is where summaries and the main text goes."
                                }
                        }
                    }, 
                }
            ], 
            messages = [{"role": "user", "content": prompt}]
        )

        if response.content[0].type == 'tool_call' and response.content[0].tool_call_function == 'send_email': 
            email_data = json.loads(response.content[0].tool_call.function.arguments)
            subject = email_data['subject']
            body = email_data['body']
        else:
            subject = "Forecasts summary"
            body = response.content[0].text

        send_email(subject, body)

    except Exception as e:
        print(f"An error occured: {e}")

if __name__ == "__main__":
    main()
