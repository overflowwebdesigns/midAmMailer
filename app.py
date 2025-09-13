import os
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import smtplib
from email.mime.text import MIMEText
from apscheduler.schedulers.blocking import BlockingScheduler

print("Mid-Am Score Monitor starting...")

EMAIL = os.getenv('GMAIL_EMAIL')
PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
PHONE = os.getenv('VERIZON_PHONE')
URL = 'https://championships.usga.org/usmidamateur/2025/scoring.html'
LAST_SCORE_FILE = 'last_score.json'

print(f"Environment variables loaded - EMAIL: {EMAIL}, PHONE: {PHONE}, PASSWORD set: {bool(PASSWORD)}")

def send_email(subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL
    msg['To'] = f'{PHONE}@vtext.com'
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL, PASSWORD)
            server.sendmail(EMAIL, f'{PHONE}@vtext.com', msg.as_string())
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")

def get_score():
    print("Starting score scraping...")
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.binary_location = '/usr/bin/chromium'
    try:
        print("Initializing Chrome driver...")
        service = Service(executable_path='/usr/lib/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=options)
        print(f"Loading URL: {URL}")
        driver.get(URL)
        print("Waiting for Ronald Kelton to appear on page...")
        # Wait for the page to load and find Ronald Kelton
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Ronald Kelton')]"))
        )
        print("Found Ronald Kelton on page, extracting data...")
        # Find the table row containing Ronald Kelton
        row = driver.find_element(By.XPATH, "//tr[td[contains(text(), 'Ronald Kelton')]]")
        tds = row.find_elements(By.TAG_NAME, 'td')
        print(f"Found {len(tds)} columns in row")
        # Assuming columns: position, name, score, thru (holes)
        # Adjust indices based on actual table structure
        score = tds[2].text.strip() if len(tds) > 2 else 'N/A'
        holes = tds[3].text.strip() if len(tds) > 3 else 'N/A'
        driver.quit()
        print(f"Successfully scraped score: {score}, holes: {holes}")
        return {'score': score, 'holes': holes}
    except Exception as e:
        print(f"Error scraping score: {e}")
        if 'driver' in locals():
            driver.quit()
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
        body = f"Ronald Kelton's current score: {current['score']}\nHoles completed: {current['holes']}"
        print("Score changed, sending email...")
        send_email("Mid-Am Score Update", body)
        with open(LAST_SCORE_FILE, 'w') as f:
            json.dump(current, f)
        print(f"Score updated and saved: {current}")
    else:
        print("No score change detected")

if __name__ == "__main__":
    # Check environment variables
    if not all([EMAIL, PASSWORD, PHONE]):
        print("Missing environment variables. Please set GMAIL_EMAIL, GMAIL_APP_PASSWORD, and VERIZON_PHONE")
        exit(1)

    scheduler = BlockingScheduler()
    scheduler.add_job(check_and_notify, 'interval', hours=1)
    print("Starting Mid-Am Score Monitor...")
    # Run once at start
    check_and_notify()
    scheduler.start()
