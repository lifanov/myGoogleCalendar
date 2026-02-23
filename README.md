# myGoogleCalendar (v2)

A Python program to automatically sync your Target myTime shifts to Google Calendar.

This tool authenticates with Target's systems, retrieves your schedule, and adds or updates events in your Google Calendar. It supports Multi-Factor Authentication (MFA) and can verify previously added shifts to ensure accuracy.

## Prerequisites

*   **Google Cloud Developer Account**: Required to access the Google Calendar API.
*   **Python 3.x**: Ensure you have Python installed.
*   **Google Chrome**: Required for the automation script to log in.

## Setup Instructions

### 1. Clone the Repository

Clone this project to your local machine.
All the working files for the latest version are in the `v2` folder.

### 2. Google Calendar API Setup

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project.
3.  Enable the **Google Calendar API**.
4.  Configure the **OAuth Consent Screen**:
    *   Set usage to "External" (or "Internal" if you have a Google Workspace organization).
    *   Fill in required details.
    *   **Important**: Switch the publishing status from "Testing" to **"Production"** to prevent the token from expiring every 7 days.
5.  Create **OAuth 2.0 Client IDs**:
    *   Go to **Credentials** > **Create Credentials** > **OAuth client ID**.
    *   Select "Desktop app".
    *   Download the JSON file.
6.  Rename the downloaded file to `credentials.json` and place it inside the `v2` folder.

### 3. Configuration

1.  Navigate to the `v2` folder.
2.  Locate `config_template.py` and rename it to `config_file.py`.
3.  Open `config_file.py` in a text editor and update the following variables:

    *   `EMPLOYEE_ID`: Your Target Team Member ID (e.g., `"12345678"`).
    *   `PASSWORD`: Your password for Workday / Target Pay and Benefits.
    *   `STORE_NUMBER`: Your 4-digit store number (e.g., `"1375"`).
    *   `PUSHOVER_APP_API_KEY` & `PUSHOVER_USER_API_KEY`: (Optional) Fill these if you want push notifications via Pushover.
    *   `run_posted_shifts`: Set to `True` to scan for available shifts.
    *   `headless`: Set to `True` to run the browser in the background (hidden).

#### Multi-Factor Authentication (MFA) Setup

**This is a critical step.** You need to extract the TOTP secret from your authenticator setup.

1.  Log in to [mylogin.prod.target.com](https://mylogin.prod.target.com) (must be on Target Internal Network, e.g., at the store).
2.  Go to the Authenticator App setup section.
3.  **Before** scanning the QR code, capture the URL or secret key. It usually looks like `otpauth://totp/...?secret=REALLYLONGTOKEN...`.
4.  Copy the `REALLYLONGTOKEN` part.
5.  In `config_file.py`, paste it into the `totp` setup:
    ```python
    totp = pyotp.TOTP("REALLYLONGTOKEN")
    ```

### 4. Installation

Open a terminal or command prompt, navigate to the `v2` folder, and install the required dependencies:

```bash
cd v2
pip install -r requirements.txt
```

### 5. Running the Script

Run the main script:

```bash
python top.py
```

## First Run

*   **Google Authentication**: On the first run, a browser window will open asking you to log in to your Google account and allow access to your calendar. This will generate a `token.json` file for future runs.
    *   If you see a "Google hasn't verified this app" warning, click "Advanced" and then "Go to [Project Name] (unsafe)". This is normal for personal projects.
*   **Target Login**: The script will launch a browser (visible or headless depending on your config) to log in to myTime and retrieve your schedule.

## Troubleshooting

*   **SQLAlchemy Errors**: If you encounter issues related to SQLAlchemy, try reinstalling it: `pip install SQLAlchemy`.
*   **ChromeDriver**: Ensure you have Google Chrome installed. The script uses `undetected-chromedriver` which handles driver installation.

## Disclaimer

This code is open source and provided as-is. Please review the code if you have security concerns.
