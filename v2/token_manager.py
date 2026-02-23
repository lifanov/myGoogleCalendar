import json
import os
import requests
from loguru import logger
import config_file
import get_bearer

TOKEN_FILE = "bearer_token.json"

class TokenManager:
    def __init__(self):
        self.token_file = TOKEN_FILE

    def get_valid_token(self):
        """
        Retrieves a valid Bearer token.
        Checks the existing token and refreshes if necessary.
        """
        token = self._load_token()
        if token:
            logger.info("Checking if existing token is valid...")
            if self.is_token_valid(token):
                logger.success("Existing token is valid.")
                return token

        logger.warning("Token invalid or missing. Fetching new token...")
        return self.refresh_token()

    def _load_token(self):
        if not os.path.exists(self.token_file):
            return None
        try:
            with open(self.token_file, "r") as f:
                data = json.load(f)
                return data.get("bearer_token")
        except Exception as e:
            logger.error(f"Failed to load token: {e}")
            return None

    def save_token(self, token):
        try:
            with open(self.token_file, "w") as f:
                json.dump({"bearer_token": token}, f)
            logger.success("Token saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save token: {e}")

    def refresh_token(self):
        logger.info("Attempting to refresh token...")
        new_token = get_bearer.get_token()
        if new_token:
            logger.info("New token obtained. Verifying...")
            if self.is_token_valid(new_token):
                self.save_token(new_token)
                return new_token
            else:
                logger.error("Newly fetched token is invalid!")
                raise Exception("Newly fetched token is invalid")
        else:
            raise Exception("Failed to fetch new token")

    def is_token_valid(self, token):
        headers = config_file.get_auth_headers(token)
        # using the same test logic as before
        try:
            # We use a known past date range to check if the token is accepted.
            # We are not concerned with the data returned, just the status code.
            response = requests.get(
                f"https://api.target.com/wfm_schedules/v1/weekly_schedules?"
                f"team_member_number=00{config_file.EMPLOYEE_ID}"
                "&start_date=2020-06-23"
                "&end_date=2020-06-29"
                "&location_id="
                f"&key={config_file.API_KEY}",
                headers=headers,
                timeout=15
            )
            # The original code considered 400 as success (valid token, bad request).
            # 200 is obviously success.
            # 401/403 are failures.
            if response.status_code == 200:
                return True
            if response.status_code == 400:
                # Assuming 400 means auth worked but params were wrong (which is expected here due to missing location_id)
                # If auth failed, it would be 401 or 403.
                return True

            logger.debug(f"Token validation failed with status: {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error checking token validity: {e}")
            return False
