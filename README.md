# Maine Stars Score Monitor

A Python app that polls Varsity Event Hub results, tracks Maine Stars team performance scores, and emails updates every 10 minutes.

## Features

- Queries Varsity Event Hub results API
- Extracts full team name (`program-team` text + `subText`) and `performance-score`
- Filters only Maine Stars teams
- Checks every 10 minutes
- Sends an email update every run

## Environment Variables

Set these before running:

- `GMAIL_EMAIL` - sending Gmail address
- `GMAIL_APP_PASSWORD` - Gmail app password (requires 2FA)
- `ALERT_EMAIL_TO` - recipient email (comma-separated for multiple recipients)

## Local Run

```bash
export GMAIL_EMAIL="yourgmail@gmail.com"
export GMAIL_APP_PASSWORD="your_16_char_app_password"
export ALERT_EMAIL_TO="you@example.com"
python3 app.py
```

## Behavior

1. On startup, the app fetches current Maine Stars scores and sends an email update immediately.
2. Every 10 minutes, it fetches the latest scores and sends another email update.
3. If no matching Maine Stars scores are found, the email includes that status.
