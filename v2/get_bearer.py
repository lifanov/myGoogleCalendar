import json
import time
import config_file
from loguru import logger
import undetected_chromedriver as uc
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

def get_token():
    logger.info("Setting up Chrome Options")
    options = uc.ChromeOptions()
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    options.add_experimental_option("perfLoggingPrefs", {"enableNetwork": True})

    # Headless setup
    if config_file.headless:
        options.add_argument("--headless=new")

    options.add_argument("--incognito")
    options.add_argument("--enable-automation")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    browser = None
    try:
        # service=Service() is handled by uc internally usually, but let's stick to default
        browser = uc.Chrome(use_subprocess=True, options=options)
        logger.success("ChromeDriver Setup! Starting")

        logger.info("Launching myTime")
        browser.get("http://mytime.target.com")

        # Wait for login page
        wait = WebDriverWait(browser, 20)
        try:
            username_field = wait.until(ec.presence_of_element_located((By.ID, "loginID")))
        except TimeoutException:
            logger.error("Timed out waiting for Login Page to load")
            raise Exception("Timed out waiting for Login Page")

        logger.info("Entering credentials...")
        username_field.click()
        username_field.send_keys(config_file.EMPLOYEE_ID)
        username_field.send_keys(Keys.TAB)

        password_field = browser.find_element(By.ID, "password")
        password_field.send_keys(config_file.PASSWORD)

        login_button = browser.find_element(By.ID, "submit-button")
        login_button.click()

        # Handle MFA
        # The flow might vary. Sometimes it goes straight to OTP, sometimes asks for method.
        # We try to click "Authenticator App" if present.
        try:
            mfa_button = wait.until(ec.element_to_be_clickable((By.XPATH, '//*[contains(text(), "Authenticator")]')))
            mfa_button.click()
        except TimeoutException:
            logger.info("MFA selection button not found or timed out, assuming direct OTP entry or different flow...")

        try:
            otp_field = wait.until(ec.presence_of_element_located((By.ID, "totp-code")))
            logger.success("MFA Page Loaded. Entering code...")
            otp_code = config_file.get_mfa_code()
            otp_field.send_keys(otp_code)

            submit_btn = browser.find_element(By.ID, "submit-button")
            submit_btn.click()
        except TimeoutException:
            logger.error("Timed out waiting for OTP input field")
            raise Exception("Timed out waiting for OTP input field")

        logger.info("Waiting for login to complete and token to appear...")
        # Poll logs for token
        start_time = time.time()
        while time.time() - start_time < 45: # Wait up to 45 seconds
            logs = browser.get_log("performance")
            token = extract_token_from_logs(logs)
            if token:
                logger.success("Bearer obtained! Closing...")
                return token
            time.sleep(1)

        logger.error("Failed to extract Bearer token from logs after 45 seconds")
        raise Exception("Could not find Bearer token in browser logs")

    except Exception as e:
        logger.error(f"Error in get_token: {e}")
        raise
    finally:
        if browser:
            try:
                browser.quit()
            except:
                pass

def extract_token_from_logs(logs):
    for entry in logs:
        try:
            message = json.loads(entry["message"])["message"]
            if "params" in message:
                # Check request headers
                if "request" in message["params"]:
                    headers = message["params"]["request"].get("headers", {})
                    if "Authorization" in headers and "Bearer " in headers["Authorization"]:
                        return headers["Authorization"]

                # Check response headers
                if "response" in message["params"]:
                    headers = message["params"]["response"].get("headers", {})
                    if "Authorization" in headers and "Bearer " in headers["Authorization"]:
                        return headers["Authorization"]
        except (KeyError, ValueError, TypeError):
            continue
    return None
