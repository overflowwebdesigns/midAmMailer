# Mid-Am Score Monitor

A Python application that monitors Ronald Kelton's score in the 2025 U.S. Mid-Amateur Championship and sends text message updates via Verizon.

## Features

- Scrapes the USGA scoring page for Ronald Kelton's current score and holes completed
- Sends SMS notifications to Verizon phone numbers when score changes
- Runs continuously with hourly checks
- Containerized for easy deployment on CapRover

## Prerequisites

- CapRover instance
- Gmail account with 2FA enabled
- Verizon phone number for SMS delivery

## Setup

### 1. Gmail App Password

1. Go to your Google Account settings
2. Navigate to Security → 2-Step Verification → App passwords
3. Generate a new app password for "Mail"
4. Note the 16-character password

### 2. Environment Variables

Set the following environment variables in your CapRover app:

- `GMAIL_EMAIL`: Your Gmail address (e.g., yourname@gmail.com)
- `GMAIL_APP_PASSWORD`: The 16-character app password
- `VERIZON_PHONE`: 10-digit Verizon phone number (e.g., 1234567890)

## Deployment to CapRover

1. Clone or upload this repository to your CapRover instance
2. Create a new app in CapRover
3. Set the environment variables in the app settings
4. Deploy the app using the provided Dockerfile
5. The app will start monitoring immediately and check for updates every hour

## Local Testing

To test locally:

```bash
export GMAIL_EMAIL="yourgmail@gmail.com"
export GMAIL_APP_PASSWORD="yourapppassword"
export VERIZON_PHONE="1234567890"
python app.py
```

Note: Local testing requires Chrome/Chromium installed on your system.

## How It Works

1. The app uses Selenium to load the USGA scoring page in headless Chrome
2. Waits for the leaderboard to load and locates Ronald Kelton's row
3. Extracts the current score and holes completed
4. Compares to the previously stored score
5. If changed, sends an email to `phonenumber@vtext.com` (Verizon's SMS gateway)
6. Updates the stored score for future comparisons

## File Structure

- `app.py`: Main application logic
- `requirements.txt`: Python dependencies
- `Dockerfile`: Container configuration
- `last_score.json`: Stores the last known score (created automatically)

## Notes

- The app assumes a specific table structure on the USGA page. If the page layout changes, the XPath selectors may need adjustment.
- SMS delivery depends on Verizon's email-to-SMS gateway.
- The app runs continuously and checks for updates every hour.
