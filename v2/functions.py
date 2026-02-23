import os
import requests
import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import engine, SeenShift

# Google Imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from loguru import logger

import config_file

logger.info("Changing cwd to file path")
os.chdir(os.path.dirname(__file__))

logger.info("Initializing Google Calendar... Please Wait.")

creds = None
SCOPES = ["https://www.googleapis.com/auth/calendar"]

if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
        token.write(creds.to_json())
service = build("calendar", "v3", credentials=creds)


class Store:
    def __init__(self):
        self.address = ""
        self.timezone_offset = "00:00:00"
        self.store_id = "0000"


def notify_user(message):
    if config_file.PUSHOVER_APP_API_KEY == "" or config_file.PUSHOVER_USER_API_KEY == "":
        logger.info("Config file for pushover is empty, ignoring")
        return
    logger.info("Notifying User via Pushover...")
    r = requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": config_file.PUSHOVER_APP_API_KEY,
            "user": config_file.PUSHOVER_USER_API_KEY,
            "message": message,
        },
    )
    # try to notify the user, if it fails then log
    try:
        r.raise_for_status()
        logger.success("User Notified")
    except:
        logger.error(f"Notifying FAILED {r.text}")


def create_event(location, job_title, s_time, e_time):
    # function to create events via Google Calendar
    event = {
        "summary": "Target",
        "location": location,
        "description": f"You are being requested to work a shift of {job_title}",
        "colorId": 11,
        "start": {
            "dateTime": s_time,
        },
        "end": {
            "dateTime": e_time,
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 45},
            ],
        },
    }
    # this sends the event to google, and You will know it is successful by seeing "Event Created:" in the console.
    event = service.events().insert(calendarId="primary", body=event).execute()
    logger.success("Event created: %s" % (event.get("htmlLink")))


def get_current_timezone_offset():
    """
    Returns the current system timezone offset in ISO 8601 format (e.g., +05:30, -05:00).
    """
    local_now = datetime.datetime.now().astimezone()
    offset = local_now.strftime("%z")  # Returns +HHMM or -HHMM
    return f"{offset[:-2]}:{offset[-2:]}"


def get_store_info(store_id):
    # Get store address and TimeZone offset
    r = requests.get(
        "https://redsky.target.com/redsky_aggregations/v1/web/store_location_v1"
        f"?store_id={store_id}"
        f"&key={config_file.API_KEY}",
        headers=config_file.get_schedule_headers(),
    )
    s = Store()
    # Initialize store object

    store_json = r.json()["data"]["store"]["mailing_address"]
    # create object to reduce lines of code.
    s.address = (
        f"{store_json['address_line1']} {store_json['city']}, "
        f"{store_json['region']}, {store_json['postal_code']}"
    )
    s.timezone_offset = get_current_timezone_offset()
    s.store_id = store_id
    return s


def call_wfm(
    hdr,
    start_date,
    end_date,
):
    # Function to call and retrieve schedule.
    # Start Date and end date format should be YYYY-MM-DD
    url = (
        f"https://api.target.com/wfm_schedules/v1/weekly_schedules?"
        f"team_member_number=00{config_file.EMPLOYEE_ID}"
        f"&start_date={start_date}"
        f"&end_date={end_date}"
        f"&location_id="  # Needs this flag for some reason.
        f"&key={config_file.API_KEY}"
    )
    logger.info(f"Calling WFM API: {url}")
    r = requests.get(url, headers=hdr)
    logger.info(f"WFM API response status: {r.status_code}")
    return r


def call_available_shifts(
    hdr,
    start_date,
    end_date,
):
    url = (
        f"https://api.target.com/wfm_available_shifts/v1/available_shifts?"
        f"worker_id={config_file.EMPLOYEE_ID}"
        f"&start_date={start_date}"
        f"&end_date={end_date}"
        f"&location_ids={config_file.STORE_NUMBER}"  # Needs this flag for some reason.
        f"&key={config_file.API_KEY}"
    )
    logger.info(f"Calling Available Shifts API: {url}")
    r = requests.get(url, headers=hdr)
    logger.info(f"Available Shifts API response status: {r.status_code}")
    return r


def seen_or_record(shift):
    with Session(engine) as session:
        logger.info(f"Checking if shift {shift['available_shift_id']} exists")
        result = session.scalar(
            select(SeenShift).filter(SeenShift.id == shift["available_shift_id"])
        )

        if result:
            logger.info("Shift found, exiting function")
            return
        logger.info("Shift not found, adding to database")
        new_shift = SeenShift(id=shift["available_shift_id"])
        session.add(new_shift)
        session.commit()

        dt_start = datetime.datetime.fromisoformat(shift["shift_start"])
        dt_end = datetime.datetime.fromisoformat(shift["shift_end"])

        notify_user(
            f"A new {shift['shift_hours']} hour shift has been posted for {dt_start.date()} "
            f"from {dt_start.strftime('%I:%M %p')} "
            f"to {dt_end.strftime('%I:%M %p')} for "
            f"{shift['org_structure']['job']}"
        )
