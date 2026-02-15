import json
import logging
import os
import smtplib
from email.mime.text import MIMEText

import requests
from apscheduler.schedulers.blocking import BlockingScheduler


API_URL = (
    "https://tv-admin.varsity.com/api/experiences/web/event-hub/14478875/results"
    "?version=1.33.2&tz=America/New_York&search=maine%20stars"
    "&isEventHubLayoutEnabled=true&isEventHubBracketsEnabled=false"
    "&isNextGenEventHub=false&site_id=20"
)
TEAM_FILTER = "maine stars"
LAST_SCORE_FILE = "last_score.json"

EMAIL = os.getenv("GMAIL_EMAIL")
PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")
ALERT_RECIPIENTS = [email.strip() for email in ALERT_EMAIL_TO.split(",") if email.strip()]


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def extract_team_scores(node):
    """Recursively search the payload for rows that contain both
    `program-team` and `performance-score` cells.
    """
    matches = []

    if isinstance(node, list):
        row = {}
        is_row_like = False

        for item in node:
            if isinstance(item, dict) and "key" in item and "data" in item:
                is_row_like = True
                key = item.get("key")
                data = item.get("data", {})

                if key == "program-team":
                    name = data.get("text") or ""
                    sub_name = data.get("subText") or ""
                    full_name = f"{name} {sub_name}".strip()
                    row[key] = full_name
                else:
                    row[key] = data.get("text")

        if is_row_like and ("program-team" in row and "performance-score" in row):
            matches.append(
                {
                    "team_name": row.get("program-team"),
                    "performance_score": row.get("performance-score"),
                }
            )

        for item in node:
            matches.extend(extract_team_scores(item))

    elif isinstance(node, dict):
        for value in node.values():
            matches.extend(extract_team_scores(value))

    return matches


def get_maine_stars_scores():
    logger.info("Fetching Varsity Event Hub results...")
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    payload = response.json()

    extracted = extract_team_scores(payload)
    filtered = [
        team
        for team in extracted
        if isinstance(team.get("team_name"), str)
        and TEAM_FILTER in team["team_name"].lower()
    ]

    # Remove duplicates while preserving order.
    seen = set()
    unique = []
    for team in filtered:
        team_tuple = (team.get("team_name"), team.get("performance_score"))
        if team_tuple not in seen:
            seen.add(team_tuple)
            unique.append(team)

    return sorted(unique, key=lambda t: (t.get("team_name") or "", t.get("performance_score") or ""))


def format_team_scores(teams):
    return "\n".join(f"{team['team_name']} - {team['performance_score']}" for team in teams)


def send_email_alert(subject, body):
    if not EMAIL or not PASSWORD:
        raise ValueError("Missing GMAIL_EMAIL or GMAIL_APP_PASSWORD environment variables.")
    if not ALERT_RECIPIENTS:
        raise ValueError("Missing ALERT_EMAIL_TO environment variable.")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL, PASSWORD)
        for recipient in ALERT_RECIPIENTS:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = EMAIL
            msg["To"] = recipient
            server.sendmail(EMAIL, recipient, msg.as_string())


def load_last_scores():
    try:
        with open(LAST_SCORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except FileNotFoundError:
        return []


def save_scores(scores):
    with open(LAST_SCORE_FILE, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2)


def check_for_changes_and_notify():
    logger.info("Running score check...")
    current_scores = get_maine_stars_scores()
    previous_scores = load_last_scores()

    if not previous_scores:
        logger.info("No baseline file found. Saving current scores without sending an alert.")
        save_scores(current_scores)
        return

    if current_scores != previous_scores:
        body = "Maine Stars scores changed:\n\n" + format_team_scores(current_scores)
        send_email_alert("Maine Stars Score Update", body)
        save_scores(current_scores)
        logger.info("Change detected. Email alert sent and new scores saved.")
    else:
        logger.info("No changes detected.")


if __name__ == "__main__":
    try:
        if not EMAIL or not PASSWORD:
            raise ValueError("Please set GMAIL_EMAIL and GMAIL_APP_PASSWORD.")
        if not ALERT_RECIPIENTS:
            raise ValueError("Please set ALERT_EMAIL_TO.")

        scheduler = BlockingScheduler()
        scheduler.add_job(check_for_changes_and_notify, "interval", minutes=1)

        logger.info("Starting Maine Stars monitor (checks every 1 minute)...")
        check_for_changes_and_notify()
        scheduler.start()
    except Exception as exc:
        logger.error(f"Application failed: {exc}")
        raise
