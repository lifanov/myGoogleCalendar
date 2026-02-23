import pyotp

# Global Variables
EMPLOYEE_ID = "00000000"
# Replace these numbers with your TMID you use at the time clock

PASSWORD = "myPassword"
# Replace password with your password when you sign into Workday or Target Pay and Benefits.

STORE_NUMBER = "1375"
# Replace this with  your 4 digit store number is.
# Note if your store number is less than 4 digits, like store number 192, make sure you have a leading 0, so in this case it would be 0192

API_KEY = "eb2551e4accc14f38cc42d32fbc2b2ea"
# You can change this but the default one should work

PUSHOVER_APP_API_KEY = ""
PUSHOVER_USER_API_KEY = ""
# These two lines are if you want to get notifications on your phone about any posted shifts AND if you want to get notified that a shift was added to your Google calendar.
# If you don't want to get these notifications, just leave these two strings empty

run_posted_shifts = True
# If this is set to true, then it will read the available shifts in your store and notify you via Pushover. You need to setup the pushover APP and USER API key in the above block though.

headless = True
# Headless means that you wont see see Chrome open to obtain the Bearer.

# MFA Configuration
# Ensure you have your TOTP secret. It should look like "REALLYLONGTOKEN".
# Put it inside the quotes below.
totp = pyotp.TOTP("")

def get_mfa_code():
    """
    Returns the current MFA code using the TOTP secret.
    """
    return totp.now()

def get_auth_headers(bearer):
    """
    Returns headers for authentication with WFM API.
    """
    return {
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }

def get_posted_shifts_headers(bearer):
    """
    Returns headers for fetching posted shifts.
    Typically similar to auth headers.
    """
    return get_auth_headers(bearer)

def get_schedule_headers():
    """
    Returns headers for fetching store info (RedSky API).
    Often these don't require the Bearer token but might need the API Key.
    """
    return {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }
