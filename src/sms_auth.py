"""SMS authentication module for Beyond The Club."""

import httpx
import logging
from typing import Optional

from .firebase_auth import FirebaseAuth, FirebaseTokens

logger = logging.getLogger(__name__)


class SMSAuth:
    """Handle SMS-based authentication flow."""

    def __init__(self, firebase_auth: FirebaseAuth, api_base_url: str):
        self.firebase_auth = firebase_auth
        self.api_base_url = api_base_url
        self._client = httpx.Client(timeout=30.0)
        self._user_tokens: Optional[FirebaseTokens] = None

    def _get_api_headers(self, bearer_token: str) -> dict:
        """Get headers for API requests."""
        return {
            "accept": "application/json",
            "accept-encoding": "gzip",
            "authorization": f"Bearer {bearer_token}",
            "connection": "Keep-Alive",
            "content-type": "application/json",
            "host": "api.beyondtheclub.tech",
            "user-agent": "okhttp/4.12.0",
        }

    def send_sms_code(self, phone_number: str, admin_token: str) -> bool:
        """Send SMS verification code to phone number."""
        url = f"{self.api_base_url}/send-sms"

        payload = {"phone": phone_number}
        headers = self._get_api_headers(admin_token)

        logger.debug(f"Sending SMS request to {url} with phone: {phone_number}")
        response = self._client.post(url, json=payload, headers=headers)

        if not response.is_success:
            logger.error(f"SMS request failed: {response.status_code} - {response.text}")
            # Check for rate limiting in response body
            try:
                data = response.json()
                if data.get("statusCode") == 429:
                    raise Exception("Limite de SMS atingido. Aguarde alguns minutos antes de tentar novamente.")
            except Exception as e:
                if "Limite de SMS" in str(e):
                    raise e

        response.raise_for_status()

        logger.info(f"SMS code sent to {phone_number}")
        return True

    def verify_sms_code(self, phone_number: str, code: str, admin_token: str) -> str:
        """Verify SMS code and get custom token."""
        url = f"{self.api_base_url}/verify-sms"

        payload = {
            "phone": phone_number,
            "code": code
        }
        headers = self._get_api_headers(admin_token)

        response = self._client.post(url, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        logger.debug(f"verify-sms response: {data}")

        # Response is wrapped in { "value": { "token": "..." } }
        value = data.get("value", data)
        custom_token = value.get("token")

        if not custom_token:
            logger.error(f"verify-sms full response: {data}")
            raise ValueError(f"No custom token in SMS verification response")

        logger.info("SMS verification successful")
        return custom_token

    def complete_auth_flow(self, phone_number: str, sms_code: str, admin_token: str) -> FirebaseTokens:
        """Complete the full SMS authentication flow."""
        # Verify SMS and get custom token
        custom_token = self.verify_sms_code(phone_number, sms_code, admin_token)

        # Exchange custom token for Firebase tokens
        self._user_tokens = self.firebase_auth.verify_custom_token(custom_token)

        return self._user_tokens

    def get_user_token(self) -> str:
        """Get the authenticated user's token."""
        if not self._user_tokens:
            raise ValueError("User not authenticated via SMS")

        return self.firebase_auth.get_valid_token()

    @property
    def is_user_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self._user_tokens is not None

    def close(self):
        """Close the HTTP client."""
        self._client.close()
