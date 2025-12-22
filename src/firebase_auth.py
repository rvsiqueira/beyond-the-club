"""Firebase authentication module."""

import time
import httpx
from dataclasses import dataclass
from typing import Optional
import logging

from .config import FirebaseConfig

logger = logging.getLogger(__name__)


@dataclass
class FirebaseTokens:
    """Container for Firebase tokens."""
    id_token: str
    refresh_token: str
    expires_at: float  # Unix timestamp


class FirebaseAuth:
    """Handle Firebase authentication flow."""

    IDENTITY_TOOLKIT_URL = "https://www.googleapis.com/identitytoolkit/v3/relyingparty"
    REMOTE_CONFIG_URL = "https://firebaseremoteconfig.googleapis.com/v1/projects"

    def __init__(self, config: FirebaseConfig, on_tokens_updated: Optional[callable] = None):
        self.config = config
        self._tokens: Optional[FirebaseTokens] = None
        self._client = httpx.Client(timeout=30.0)
        self._on_tokens_updated = on_tokens_updated

    def _get_common_headers(self) -> dict:
        """Get common headers for Firebase requests."""
        return {
            "accept-encoding": "gzip",
            "accept-language": "pt-BR, en-US",
            "connection": "Keep-Alive",
            "content-type": "application/json",
            "user-agent": "Dalvik/2.1.0 (Linux; U; Android 15; motorola razr 50 ultra Build/V2UXS35.47-37-3-6)",
            "x-android-cert": self.config.android_cert,
            "x-android-package": self.config.android_package,
            "x-client-version": "Android/Fallback/X23002001/FirebaseCore-Android",
            "x-firebase-gmpid": self.config.app_id,
        }

    def verify_password(self, email: str, password: str) -> FirebaseTokens:
        """Authenticate with email and password."""
        url = f"{self.IDENTITY_TOOLKIT_URL}/verifyPassword?key={self.config.api_key}"

        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
            "clientType": "CLIENT_TYPE_ANDROID"
        }

        response = self._client.post(url, json=payload, headers=self._get_common_headers())
        response.raise_for_status()

        data = response.json()
        expires_in = int(data.get("expiresIn", 3600))

        self._tokens = FirebaseTokens(
            id_token=data["idToken"],
            refresh_token=data["refreshToken"],
            expires_at=time.time() + expires_in - 60  # 60s buffer
        )

        logger.info("Firebase password authentication successful")
        return self._tokens

    def verify_custom_token(self, custom_token: str) -> FirebaseTokens:
        """Verify a custom token (from SMS verification)."""
        url = f"{self.IDENTITY_TOOLKIT_URL}/verifyCustomToken?key={self.config.api_key}"

        payload = {
            "token": custom_token,
            "returnSecureToken": True
        }

        response = self._client.post(url, json=payload, headers=self._get_common_headers())
        response.raise_for_status()

        data = response.json()
        expires_in = int(data.get("expiresIn", 3600))

        self._tokens = FirebaseTokens(
            id_token=data["idToken"],
            refresh_token=data["refreshToken"],
            expires_at=time.time() + expires_in - 60
        )

        logger.info("Firebase custom token verification successful")
        return self._tokens

    def get_account_info(self, id_token: str) -> dict:
        """Get account information for the authenticated user."""
        url = f"{self.IDENTITY_TOOLKIT_URL}/getAccountInfo?key={self.config.api_key}"

        payload = {"idToken": id_token}

        response = self._client.post(url, json=payload, headers=self._get_common_headers())
        response.raise_for_status()

        return response.json()

    def refresh_token(self) -> FirebaseTokens:
        """Refresh the ID token using the refresh token."""
        if not self._tokens:
            raise ValueError("No tokens available to refresh")

        url = f"https://securetoken.googleapis.com/v1/token?key={self.config.api_key}"

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self._tokens.refresh_token
        }

        headers = self._get_common_headers()
        headers["content-type"] = "application/x-www-form-urlencoded"

        response = self._client.post(url, data=payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        expires_in = int(data.get("expires_in", 3600))

        self._tokens = FirebaseTokens(
            id_token=data["id_token"],
            refresh_token=data["refresh_token"],
            expires_at=time.time() + expires_in - 60
        )

        logger.info("Firebase token refreshed successfully")

        # Notify callback to save updated tokens
        if self._on_tokens_updated:
            self._on_tokens_updated(self._tokens)

        return self._tokens

    def get_valid_token(self) -> str:
        """Get a valid ID token, refreshing if necessary."""
        if not self._tokens:
            raise ValueError("Not authenticated")

        if time.time() >= self._tokens.expires_at:
            self.refresh_token()

        return self._tokens.id_token

    @property
    def is_authenticated(self) -> bool:
        """Check if we have valid tokens."""
        return self._tokens is not None

    def close(self):
        """Close the HTTP client."""
        self._client.close()
