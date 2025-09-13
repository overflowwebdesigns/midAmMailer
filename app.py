import os
import json
import time
import requests
import smtplib
from email.mime.text import MIMEText
from apscheduler.schedulers.blocking import BlockingScheduler

print("Mid-Am Score Monitor starting...")

EMAIL = os.getenv('GMAIL_EMAIL')
PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
VERIZON_PHONES = os.getenv('VERIZON_PHONE', '')
API_URL = 'https://ace-api.usga.org/scoring/v1/scoring.json?championship=usmidam&championship-year=2025'
LAST_SCORE_FILE = 'last_score.json'

# Parse phone numbers
verizon_numbers = [num.strip() for num in VERIZON_PHONES.split(',') if num.strip()]
all_recipients = [f'{num}@vtext.com' for num in verizon_numbers]

print(f"Environment variables loaded - EMAIL: {EMAIL}, VERIZON: {verizon_numbers}, PASSWORD set: {bool(PASSWORD)}")
print(f"Total recipients: {len(all_recipients)}")

def send_email(subject, body):
    if not all_recipients:
        print("No phone numbers configured")
        return

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL, PASSWORD)
            for recipient in all_recipients:
                # Create a fresh message for each recipient
                msg = MIMEText(body)
                msg['Subject'] = subject
                msg['From'] = EMAIL
                msg['To'] = recipient
                server.sendmail(EMAIL, recipient, msg.as_string())
                print(f"Email sent to {recipient}")
        print(f"Emails sent successfully to {len(all_recipients)} recipients")
    except Exception as e:
        print(f"Failed to send email: {e}")

def get_score():
    print("Starting score fetching from API...")
    try:
        print(f"Fetching API: {API_URL}")
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
        print("API response received, parsing JSON...")
        data = response.json()
        standings = data.get('strokeplay', {}).get('standings', [])
        print(f"Found {len(standings)} players in standings")
        for player_data in standings:
            player = player_data.get('player', {})
            if player.get('firstName') == 'Ronald' and player.get('lastName') == 'Kelton':
                print("Found Ronald Kelton in standings, extracting data...")
                position = player_data.get('position', {}).get('displayValue', 'N/A')
                to_par = player_data.get('toPar', {}).get('displayValue', 'N/A')
                holes_through = player_data.get('holesThrough', {}).get('displayValue', 'N/A')
                print(f"Successfully fetched position: {position}, score: {to_par}, holes: {holes_through}")
                return {'position': position, 'score': to_par, 'holes': holes_through}
        print("Ronald Kelton not found in standings")
        return None
    except Exception as e:
        print(f"Error fetching score: {e}")
        return None

def check_and_notify():
    print("Starting score check and notify...")
    current = get_score()
    if not current:
        print("Could not retrieve current score")
        return

    try:
        with open(LAST_SCORE_FILE, 'r') as f:
            last = json.load(f)
        print(f"Loaded last score: {last}")
    except FileNotFoundError:
        last = {}
        print("No previous score file found, starting fresh")

    print(f"Current score: {current}, Last score: {last}")
    if current != last:
        body = f"Ronald Kelton's current position: {current['position']}\nScore: {current['score']}\nHoles completed: {current['holes']}"
        print("Score changed, sending email...")
        send_email("Mid-Am Score Update", body)
        with open(LAST_SCORE_FILE, 'w') as f:
            json.dump(current, f)
        print(f"Score updated and saved: {current}")
    else:
        print("No score change detected")

if __name__ == "__main__":
    # Check environment variables
    if not EMAIL or not PASSWORD:
        print("Missing required environment variables. Please set GMAIL_EMAIL and GMAIL_APP_PASSWORD")
        exit(1)
    if not all_recipients:
        print("No phone numbers configured. Please set VERIZON_PHONE")
        exit(1)

    scheduler = BlockingScheduler()
    scheduler.add_job(check_and_notify, 'interval', minutes=10)
    print("Starting Mid-Am Score Monitor...")
    # Run once at start
    check_and_notify()
    scheduler.start()
