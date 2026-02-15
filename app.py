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

    return sorted(filtered, key=lambda t: (t.get("team_name") or "", t.get("performance_score") or ""))


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


def send_score_update():
    logger.info("Running scheduled score update...")
    current_scores = get_maine_stars_scores()

    if current_scores:
        body = "Maine Stars score update:\n\n" + format_team_scores(current_scores)
    else:
        body = "Maine Stars score update:\n\nNo matching Maine Stars scores were found in the latest fetch."

    send_email_alert("Maine Stars Score Update", body)
    logger.info("Scheduled score update email sent.")


if __name__ == "__main__":
    try:
        if not EMAIL or not PASSWORD:
            raise ValueError("Please set GMAIL_EMAIL and GMAIL_APP_PASSWORD.")
        if not ALERT_RECIPIENTS:
            raise ValueError("Please set ALERT_EMAIL_TO.")

        scheduler = BlockingScheduler()
        scheduler.add_job(send_score_update, "interval", minutes=10)

        logger.info("Starting Maine Stars monitor (sends updates every 10 minutes)...")
        send_score_update()
        scheduler.start()
    except Exception as exc:
        logger.error(f"Application failed: {exc}")
        raise
