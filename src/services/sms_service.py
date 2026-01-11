"""
SMS Service using Twilio.

Sends SMS notifications for booking confirmations.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SMSService:
    """Service for sending SMS notifications via Twilio."""

    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_PHONE_NUMBER")
        self._client = None

        if self.account_sid and self.auth_token:
            try:
                from twilio.rest import Client
                self._client = Client(self.account_sid, self.auth_token)
                logger.info("Twilio SMS service initialized")
            except ImportError:
                logger.warning("Twilio library not installed, SMS disabled")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio: {e}")

    def is_configured(self) -> bool:
        """Check if Twilio is properly configured."""
        return self._client is not None and self.from_number is not None

    def format_brazilian_phone(self, phone: str) -> str:
        """
        Format Brazilian phone number to E.164 format.

        Input examples:
            - "11981491849"
            - "(11) 98149-1849"
            - "+5511981491849"
            - "5511981491849"

        Output: "+5511981491849"
        """
        # Remove everything except digits
        digits = ''.join(filter(str.isdigit, phone))

        # If doesn't start with 55, add country code
        if not digits.startswith('55'):
            digits = '55' + digits

        return '+' + digits

    def send_booking_notification(
        self,
        to_phone: str,
        member_name: str,
        date: str,
        time: str,
        level: str,
        wave_side: Optional[str],
        voucher: str,
        access_code: str
    ) -> dict:
        """
        Send booking confirmation SMS.

        Args:
            to_phone: Destination phone number (Brazilian format)
            member_name: Name of the member
            date: Session date (YYYY-MM-DD)
            time: Session time (HH:MM)
            level: Session level
            wave_side: Wave side (optional)
            voucher: Booking voucher code
            access_code: Access code for the session

        Returns:
            Dict with success status and message SID or error
        """
        if not self.is_configured():
            logger.warning("Twilio not configured, skipping SMS notification")
            return {"success": False, "error": "Twilio not configured"}

        to_formatted = self.format_brazilian_phone(to_phone)

        # Format wave side for display
        wave_display = ""
        if wave_side:
            wave_display = "Esquerda" if "esquerdo" in wave_side.lower() else "Direita"

        # Build message body
        message_lines = [
            "Beyond The Club - Sessao Agendada!",
            "",
            f"Membro: {member_name}",
            f"Data: {date} as {time}",
            f"Nivel: {level.replace('_', ' ')}",
        ]

        if wave_display:
            message_lines.append(f"Lado: {wave_display}")

        message_lines.extend([
            f"Voucher: {voucher}",
            f"Codigo: {access_code}",
        ])

        message_body = "\n".join(message_lines)

        try:
            message = self._client.messages.create(
                body=message_body,
                from_=self.from_number,
                to=to_formatted
            )
            logger.info(f"SMS sent successfully to {to_formatted}: {message.sid}")
            return {"success": True, "sid": message.sid}
        except Exception as e:
            logger.error(f"SMS send failed to {to_formatted}: {e}")
            return {"success": False, "error": str(e)}

    def send_test_sms(self, to_phone: str, message: str = "Teste Beyond The Club SMS") -> dict:
        """Send a test SMS message."""
        if not self.is_configured():
            return {"success": False, "error": "Twilio not configured"}

        to_formatted = self.format_brazilian_phone(to_phone)

        try:
            msg = self._client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_formatted
            )
            logger.info(f"Test SMS sent to {to_formatted}: {msg.sid}")
            return {"success": True, "sid": msg.sid}
        except Exception as e:
            logger.error(f"Test SMS failed: {e}")
            return {"success": False, "error": str(e)}
