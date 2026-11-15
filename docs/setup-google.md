# Google Calendar OAuth Setup Guide for Cyber Agent

This guide walks you through setting up read-only Google Calendar integration for Cyber Agent.
Following the security constitution, the AI agent **never** accesses your plain text credentials or client secrets.

---

## Step 1: Create OAuth 2.0 Credentials in Google Cloud Console

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project (e.g., `cyber-agent-personal`).
3. Enable the **Google Calendar API**:
   - Go to **APIs & Services** > **Library**.
   - Search for `Google Calendar API` and click **Enable**.
4. Configure OAuth Consent Screen:
   - Go to **APIs & Services** > **OAuth consent screen**.
   - Select **External**, fill the required app name (`Cyber Agent`) and your email.
   - Under Scopes, add `https://www.googleapis.com/auth/calendar.readonly`.
   - Add your Gmail as a **Test User**.
5. Create OAuth Client ID:
   - Go to **APIs & Services** > **Credentials**.
   - Click **Create Credentials** > **OAuth Client ID**.
   - Application type: **Desktop app**. Name: `Cyber Agent Desktop`.
   - Download the JSON client configuration.

---

## Step 2: Store Credentials Securely on Your Laptop

Save the downloaded JSON file to:
`~/.config/cyber-agent/calendar_credentials.json`

Set strict permissions:
```bash
chmod 600 ~/.config/cyber-agent/calendar_credentials.json
```

---

## Step 3: Authorize on Your Laptop (Human Step)

Run the local authentication helper:
```bash
uv run python -c "
from cyber_agent.integrations.google_calendar import authenticate_google_calendar
authenticate_google_calendar()
"
```
A browser window will open asking you to sign in with your Google account.
Once granted, the token will be stored in `data/calendar_token.json` (protected by `.gitignore` and permissions `0600`).

---

## Security Invariants
- **Read-Only by Default:** The agent only requests read-only permissions (`calendar.readonly`).
- **Calendar Writing Disabled by Default:** Writing events requires setting `CYBER_CALENDAR_WRITE=true` in `.env` and confirming every write action.
- **Untrusted Event Descriptions:** Event descriptions from external invitees are treated as untrusted data and mark the session tainted.
