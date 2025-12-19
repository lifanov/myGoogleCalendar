import datetime
import functions
import get_bearer
import config_file
import configparser
from loguru import logger

logger.add("script.log", rotation="500 MB")  # Automatically rotate too big file
# GOOGLE CALENDAR INIT


def start_get_schedule():
    logger.info("Starting start_get_schedule function.")
    logger.info("Reading Configuration file. ")
    config = configparser.ConfigParser()
    logger.info("Setting up store info object")
    store_info = functions.Store()
    config.read("config.cfg")
    headers = config_file.get_auth_headers(config["DEFAULT"]["Bearer"])
    logger.info("Testing previously used token.")
    # test the token.
    if functions.test_token(headers).status_code == 401:
        # 401 means that response was invalid
        logger.warning("Token invalid. Generating new token...")
        # get new token
        new_token = get_bearer.get_token()
        logger.success("New Token obtained. Testing new token...")
        # set new header and test new token
        headers = config_file.get_auth_headers(new_token)
        if functions.test_token(headers).status_code == 400:
            # This may seem weird at first, but we're just checking if it authenticated properly, not the actual API
            logger.success("New Token valid! Updating configuration file...")
            config["DEFAULT"]["Bearer"] = new_token
            # Update the new config file.
            with open("config.cfg", "w") as configfile:
                config.write(configfile)
        else:
            logger.error(
                f"ERROR! New Token Invalid! error {functions.test_token(headers).status_code}"
            )
            logger.error("New Token invalid! Exiting...")
            exit(-1)
    else:
        logger.success("Existing Token valid!")
    # Now everything is verified and is working properly, we can start to work

    logger.info("Setting up DateTime Objects")
    start_week_obj = datetime.datetime.now()
    start_week_obj -= datetime.timedelta(start_week_obj.weekday() + 1)
    end_week_obj = start_week_obj + datetime.timedelta(6)
    # These date time objects allow us to easily move between calendar dates

    for i in range(4):
        # 4 to check 4 weeks of data
        if i > 0:
            start_week_obj += datetime.timedelta(7)
            end_week_obj += datetime.timedelta(7)

        logger.info(f"Fetching schedule for {start_week_obj.date()} to {end_week_obj.date()}")
        call = functions.call_wfm(headers, start_week_obj.date(), end_week_obj.date())
        # call and check the results
        if call.status_code != 200:
            logger.error(f"WFM Schedule API error for date range {start_week_obj.date()} to {end_week_obj.date()}")
            logger.error(f"Status code: {call.status_code}")
            logger.error(f"Response text: {call.text}")
            try:
                logger.error(f"Response JSON: {call.json()}")
            except:
                pass
            exit(-2)
        call_json = call.json()

        for j in range(7):
            # check once for every day
            display_segments = call_json["schedules"][j]["total_display_segments"]
            # check to see how many shifts are scheduled on that date
            if display_segments == 0:
                # this means no schedule on this date.
                logger.info(
                    f'No shifts found for {call_json["schedules"][j]["schedule_date"]}'
                )
                continue
            shift_location = call_json["schedules"][j]["display_segments"][0][
                "location"
            ]
            if store_info.store_id != shift_location:
                logger.warning(
                    f"Current location {store_info.store_id} incorrect. "
                    f"Retrieving store location for {shift_location}"
                )
                store_info = functions.get_store_info(shift_location)
            job_counter = call_json["schedules"][j]["display_segments"][0]["total_jobs"]
            shift_start = call_json["schedules"][j]["display_segments"][0][
                "segment_start"
            ]
            shift_end = call_json["schedules"][j]["display_segments"][0]["segment_end"]
            # fix them to make sure they're in T Format
            shift_start = (
                f"{shift_start[:10]}T{shift_start[-8:]}{store_info.timezone_offset}"
            )
            shift_end = f"{shift_end[:10]}T{shift_end[-8:]}{store_info.timezone_offset}"
            # A bit ugly, but it grabs all the bits we want

            # Grab the location of the shift location

            logger.info("Shift Found! Checking if multiple Shifts...")
            job_title = call_json["schedules"][j]["display_segments"][0]["job_name"]
            # Grab the first job title
            if job_counter > 1:
                # if there is multiple shifts, you can adjust that.
                logger.info("Multiple shifts found. Grabbing all of them")
                for k in range(1, job_counter):
                    temp = call_json["schedules"][j]["display_segments"][0]["jobs"][k][
                        "job_path"
                    ]
                    job_title = f'{job_title} and {temp.split("/")[-1]}'
            logger.success(f"Shifts found! {job_title}")
            # Format the job title

            full_date = call_json["schedules"][j]["schedule_date"]
            year = full_date[:4]
            month = full_date[5:7]
            day = full_date[8:10]

            search_range_start = (
                f"{year}-{month}-{day}T00:00:00{store_info.timezone_offset}"
            )
            search_range_end = (
                f"{year}-{month}-{day}T23:59:00{store_info.timezone_offset}"
            )
            events_result = (
                functions.service.events()
                .list(
                    calendarId="primary",
                    timeMin=search_range_start,
                    timeMax=search_range_end,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])
            make_event = True
            for event in events:
                if (
                    event["summary"] == "Target"
                    and event["start"]["dateTime"] == shift_start
                    and event["end"]["dateTime"] == shift_end
                    and event["description"]
                    == f"You are being requested to work a shift of {job_title}"
                ):
                    logger.info("Existing shift found in GCal. Ignoring....")
                    make_event = False
                    break
                elif event["summary"] == "Target" and (
                    event["start"]["dateTime"] != shift_start
                    or event["end"]["dateTime"] != shift_end
                    or event["description"]
                    != f"You are being requested to work a shift of {job_title}"
                ):
                    # This checks to see if something already exists in the calendar. If the label is
                    # matching but the times are wrong then they update.
                    logger.warning(
                        "Existing item found but with differences... Updating..."
                    )
                    functions.notify_user(
                        f"Shift Modification on {full_date} for {job_title}"
                    )
                    event["description"] = (
                        f"You are being requested to work a shift of {job_title}"
                    )
                    event["start"]["dateTime"] = shift_start
                    event["end"]["dateTime"] = shift_end
                    functions.service.events().update(
                        calendarId="primary", eventId=event["id"], body=event
                    ).execute()
                    make_event = False
                    break
            if make_event:
                functions.create_event(
                    store_info.address, job_title, shift_start, shift_end
                )
                functions.notify_user(
                    f"New shift posted on {full_date} for {job_title}"
                )
    logger.success("Script Complete, Exiting Gracefully...")
    exit(0)
