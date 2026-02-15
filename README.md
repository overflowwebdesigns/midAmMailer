# Maine Stars Score Monitor

A Python app that polls Varsity Event Hub results, tracks Maine Stars team performance scores, and emails updates when scores change.

## Features

- Queries Varsity Event Hub results API
- Extracts full team name (`program-team` text + `subText`) and `performance-score`
- Filters only Maine Stars teams
- Checks every 1 minute
- Sends email only when values change
- Persists last snapshot in `last_score.json`

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

1. First run creates baseline `last_score.json` and does not send an alert.
2. Every minute, current scores are compared to baseline.
3. If any team/score changes, an email is sent and baseline is updated.
