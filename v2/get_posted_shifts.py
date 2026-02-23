import datetime
import functions
import config_file
from loguru import logger
from token_manager import TokenManager

def get_posted_shifts():
    logger.info("Starting get_posted_shifts function.")
    # logger.info("Reading Configuration file. ")
    # config = configparser.ConfigParser()
    logger.info("Setting up store info object")
    store_info = functions.Store()

    # Get Token
    tm = TokenManager()
    try:
        bearer_token = tm.get_valid_token()
    except Exception as e:
        logger.error(f"Failed to obtain valid token: {e}")
        exit(-1)

    posted_shift_headers = config_file.get_posted_shifts_headers(bearer_token)
    logger.success("Token valid!")

    # Now everything is verified and is working properly, we can start to work+

    logger.info("Starting API calls for available shifts.")

    start_week_obj = datetime.datetime.now()
    start_week_obj -= datetime.timedelta(start_week_obj.weekday() + 1)
    end_week_obj = start_week_obj + datetime.timedelta(6)
    # These date time objects allow us to easily move between calendar dates

    for i in range(4):
        # 4 to check 4 weeks of data
        if i > 0:
            start_week_obj += datetime.timedelta(7)
            end_week_obj += datetime.timedelta(7)
        logger.info(f"Fetching available shifts for {start_week_obj.date()} to {end_week_obj.date()}")
        call = functions.call_available_shifts(
            posted_shift_headers, start_week_obj.date(), end_week_obj.date()
        )
        # call and check the results
        if call.status_code != 200:
            logger.error(f"Available Shifts API error for date range {start_week_obj.date()} to {end_week_obj.date()}")
            logger.error(f"Status code: {call.status_code}")
            logger.error(f"Response text: {call.text}")
            try:
                logger.error(f"Response JSON: {call.json()}")
            except:
                pass
            exit(-2)
        call_json = call.json()

        if not len(call_json["available_shifts"]):
            logger.info("No available shifts found.")
            continue
        logger.success(f"Shifts found!")

        for shift in call_json["available_shifts"]:
            functions.seen_or_record(shift)
