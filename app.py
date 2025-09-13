import os
import json
import time
import requests
import smtplib
from email.mime.text import MIMEText
from apscheduler.schedulers.blocking import BlockingScheduler
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

logger.info("Mid-Am Score Monitor starting...")

EMAIL = os.getenv('GMAIL_EMAIL')
PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
VERIZON_PHONES = os.getenv('VERIZON_PHONE', '')
API_URL = 'https://ace-api.usga.org/scoring/v1/scoring.json?championship=usmidam&championship-year=2025'
LAST_SCORE_FILE = 'last_score.json'

# Parse phone numbers
verizon_numbers = [num.strip() for num in VERIZON_PHONES.split(',') if num.strip()]

logger.info(f"Environment variables loaded - EMAIL: {EMAIL}, VERIZON: {verizon_numbers}, PASSWORD set: {bool(PASSWORD)}")

def send_notifications(subject, body):
    if not verizon_numbers:
        logger.warning("No Verizon phone numbers configured")
        return

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL, PASSWORD)
            for phone in verizon_numbers:
                # Create a fresh message for each recipient
                msg = MIMEText(body)
                msg['Subject'] = subject
                msg['From'] = EMAIL
                msg['To'] = f'{phone}@vtext.com'
                server.sendmail(EMAIL, f'{phone}@vtext.com', msg.as_string())
                logger.info(f"Email sent to Verizon {phone}@vtext.com")
        logger.info(f"Emails sent successfully to {len(verizon_numbers)} Verizon recipients")
    except Exception as e:
        logger.error(f"Failed to send Verizon emails: {e}")

def get_score():
    logger.info("Starting score fetching from API...")
    try:
        logger.debug(f"Fetching API: {API_URL}")
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
        logger.info("API response received, parsing JSON...")
        data = response.json()
        standings = data.get('strokeplay', {}).get('standings', [])
        logger.info(f"Found {len(standings)} players in standings")
        for player_data in standings:
            player = player_data.get('player', {})
            if player.get('firstName') == 'Ronald' and player.get('lastName') == 'Kelton':
                logger.info("Found Ronald Kelton in standings, extracting data...")
                position = player_data.get('position', {}).get('displayValue', 'N/A')
                to_par = player_data.get('toPar', {}).get('displayValue', 'N/A')
                holes_through = player_data.get('holesThrough', {}).get('displayValue', 'N/A')
                logger.info(f"Successfully fetched position: {position}, score: {to_par}, holes: {holes_through}")
                return {'position': position, 'score': to_par, 'holes': holes_through}
        logger.warning("Ronald Kelton not found in standings")
        return None
    except Exception as e:
        logger.error(f"Error fetching score: {e}")
        return None

def check_and_notify():
    logger.info("Starting score check and notify...")
    current = get_score()
    if not current:
        logger.error("Could not retrieve current score")
        return

    try:
        with open(LAST_SCORE_FILE, 'r') as f:
            last = json.load(f)
        logger.info(f"Loaded last score: {last}")
    except FileNotFoundError:
        last = {}
        logger.info("No previous score file found, starting fresh")

    logger.info(f"Current score: {current}, Last score: {last}")
    if current != last:
        body = f"Ronald Kelton's current position: {current['position']}\nScore: {current['score']}\nHoles completed: {current['holes']}"
        logger.info("Score changed, sending notifications...")
        send_notifications("Mid-Am Score Update", body)
        with open(LAST_SCORE_FILE, 'w') as f:
            json.dump(current, f)
        logger.info(f"Score updated and saved: {current}")
    else:
        logger.info("No score change detected")

if __name__ == "__main__":
    # Check environment variables
    if not EMAIL or not PASSWORD:
        logger.error("Missing required environment variables. Please set GMAIL_EMAIL and GMAIL_APP_PASSWORD")
        exit(1)
    if not verizon_numbers:
        logger.error("No phone numbers configured. Please set VERIZON_PHONE")
        exit(1)

    scheduler = BlockingScheduler()
    scheduler.add_job(check_and_notify, 'interval', minutes=10)
    logger.info("Starting Mid-Am Score Monitor...")
    # Run once at start
    check_and_notify()
    scheduler.start()
