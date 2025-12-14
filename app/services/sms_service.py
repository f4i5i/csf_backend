"""SMS service for sending text messages to students/parents."""

from typing import List, Optional

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from core.config import config
from core.logging import get_logger

logger = get_logger(__name__)


class SMSService:
    """Service for sending SMS messages via Twilio."""

    def __init__(self):
        """Initialize Twilio client."""
        self.account_sid = config.TWILIO_ACCOUNT_SID
        self.auth_token = config.TWILIO_AUTH_TOKEN
        self.from_number = config.TWILIO_PHONE_NUMBER

        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
            self.enabled = True
            logger.info("SMS service initialized with Twilio")
        else:
            self.client = None
            self.enabled = False
            logger.warning(
                "SMS service disabled - Twilio credentials not configured"
            )

    def send_sms(
        self, to_number: str, message: str, max_length: int = 160
    ) -> dict:
        """
        Send an SMS message to a single phone number.

        Args:
            to_number: Phone number in E.164 format (e.g., +12125551234)
            message: Message content
            max_length: Maximum message length (default: 160 chars for single SMS)

        Returns:
            dict with status and message_sid or error

        Raises:
            ValueError: If SMS service is not enabled
        """
        if not self.enabled:
            raise ValueError(
                "SMS service is not enabled. Configure Twilio credentials in environment variables."
            )

        # Validate phone number format
        if not to_number.startswith("+"):
            to_number = f"+1{to_number}"  # Assume US if no country code

        # Truncate message if too long
        if len(message) > max_length:
            message = message[:max_length - 3] + "..."
            logger.warning(
                f"Message truncated to {max_length} characters for SMS"
            )

        try:
            sms = self.client.messages.create(
                body=message, from_=self.from_number, to=to_number
            )

            logger.info(f"SMS sent successfully to {to_number}: {sms.sid}")
            return {
                "status": "sent",
                "message_sid": sms.sid,
                "to": to_number,
            }

        except TwilioRestException as e:
            logger.error(f"Failed to send SMS to {to_number}: {e.msg}")
            return {
                "status": "failed",
                "error": e.msg,
                "error_code": e.code,
                "to": to_number,
            }

    def send_bulk_sms(
        self, phone_numbers: List[str], message: str
    ) -> dict:
        """
        Send the same SMS message to multiple phone numbers.

        Args:
            phone_numbers: List of phone numbers in E.164 format
            message: Message content

        Returns:
            dict with sent_count, failed_count, and details
        """
        if not self.enabled:
            raise ValueError(
                "SMS service is not enabled. Configure Twilio credentials."
            )

        results = {
            "sent_count": 0,
            "failed_count": 0,
            "total": len(phone_numbers),
            "details": [],
        }

        for phone_number in phone_numbers:
            result = self.send_sms(phone_number, message)
            results["details"].append(result)

            if result["status"] == "sent":
                results["sent_count"] += 1
            else:
                results["failed_count"] += 1

        logger.info(
            f"Bulk SMS completed: {results['sent_count']}/{results['total']} sent successfully"
        )
        return results

    def send_class_announcement(
        self,
        class_name: str,
        coach_name: str,
        phone_numbers: List[str],
        message: str,
    ) -> dict:
        """
        Send a class announcement to all students in a class.

        Args:
            class_name: Name of the class
            coach_name: Coach sending the message
            phone_numbers: List of parent phone numbers
            message: Announcement message

        Returns:
            dict with results
        """
        # Format message with header
        formatted_message = (
            f"CSF - {class_name}\n"
            f"Coach {coach_name}: {message}"
        )

        logger.info(
            f"Sending class announcement from {coach_name} to {len(phone_numbers)} parents"
        )
        return self.send_bulk_sms(phone_numbers, formatted_message)

    def send_check_in_reminder(
        self, parent_phone: str, child_name: str, class_name: str
    ) -> dict:
        """
        Send a check-in reminder to a parent.

        Args:
            parent_phone: Parent's phone number
            child_name: Child's name
            class_name: Class name

        Returns:
            dict with status
        """
        message = (
            f"CSF Reminder: {child_name} is not checked in for {class_name}. "
            f"Please check in when you arrive."
        )

        return self.send_sms(parent_phone, message)

    def send_attendance_alert(
        self, parent_phone: str, child_name: str, class_name: str, date: str
    ) -> dict:
        """
        Send an attendance alert to a parent.

        Args:
            parent_phone: Parent's phone number
            child_name: Child's name
            class_name: Class name
            date: Date of absence

        Returns:
            dict with status
        """
        message = (
            f"CSF Alert: {child_name} was marked absent from {class_name} on {date}. "
            f"If this is incorrect, please contact your coach."
        )

        return self.send_sms(parent_phone, message)

    def send_badge_earned_notification(
        self, parent_phone: str, child_name: str, badge_name: str
    ) -> dict:
        """
        Send a badge earned notification to a parent.

        Args:
            parent_phone: Parent's phone number
            child_name: Child's name
            badge_name: Badge earned

        Returns:
            dict with status
        """
        message = (
            f"Congratulations! {child_name} earned the '{badge_name}' badge! "
            f"View all achievements in your CSF app."
        )

        return self.send_sms(parent_phone, message)

    def send_event_reminder(
        self,
        phone_numbers: List[str],
        event_name: str,
        event_date: str,
        event_time: str,
    ) -> dict:
        """
        Send an event reminder to multiple parents.

        Args:
            phone_numbers: List of parent phone numbers
            event_name: Event name
            event_date: Event date
            event_time: Event time

        Returns:
            dict with results
        """
        message = (
            f"CSF Reminder: {event_name} is on {event_date} at {event_time}. "
            f"Don't forget to arrive 30 minutes early!"
        )

        logger.info(
            f"Sending event reminder for '{event_name}' to {len(phone_numbers)} parents"
        )
        return self.send_bulk_sms(phone_numbers, message)


# Singleton instance
_sms_service: Optional[SMSService] = None


def get_sms_service() -> SMSService:
    """Get singleton SMS service instance."""
    global _sms_service
    if _sms_service is None:
        _sms_service = SMSService()
    return _sms_service
