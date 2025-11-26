"""Mailchimp service for marketing automation and audience management."""

import logging
from typing import Any, Dict, Optional

import mailchimp_marketing as MailchimpMarketing
from mailchimp_marketing.api_client import ApiClientError

from core.config import config

logger = logging.getLogger(__name__)


class MailchimpService:
    """Service for Mailchimp marketing automation."""

    def __init__(self):
        """Initialize Mailchimp client."""
        self.client = None
        self.audience_id = config.MAILCHIMP_AUDIENCE_ID

        if config.MAILCHIMP_API_KEY and config.MAILCHIMP_SERVER_PREFIX:
            try:
                self.client = MailchimpMarketing.Client()
                self.client.set_config({
                    "api_key": config.MAILCHIMP_API_KEY,
                    "server": config.MAILCHIMP_SERVER_PREFIX,
                })
                logger.info("Mailchimp client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Mailchimp client: {str(e)}")
        else:
            logger.warning("Mailchimp not configured - skipping initialization")

    def add_or_update_contact(
        self,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        tags: Optional[list[str]] = None,
        merge_fields: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add or update a contact in the Mailchimp audience.

        Args:
            email: Contact email address
            first_name: First name
            last_name: Last name
            tags: List of tags to apply
            merge_fields: Additional merge fields (e.g., {"PHONE": "123-456-7890"})

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client or not self.audience_id:
            logger.warning(f"Mailchimp not configured. Would add contact: {email}")
            return False

        try:
            # Prepare member data
            member_data = {
                "email_address": email,
                "status_if_new": "subscribed",  # Auto-subscribe new contacts
                "merge_fields": merge_fields or {},
            }

            # Add name fields if provided
            if first_name:
                member_data["merge_fields"]["FNAME"] = first_name
            if last_name:
                member_data["merge_fields"]["LNAME"] = last_name

            # Add or update member
            response = self.client.lists.set_list_member(
                self.audience_id,
                email.lower(),
                member_data,
            )

            # Add tags if provided
            if tags and response.get("id"):
                self.add_tags(email, tags)

            logger.info(f"Successfully added/updated contact in Mailchimp: {email}")
            return True

        except ApiClientError as e:
            logger.error(f"Mailchimp API error for {email}: {e.text}")
            return False
        except Exception as e:
            logger.error(f"Failed to add/update Mailchimp contact {email}: {str(e)}")
            return False

    def add_tags(self, email: str, tags: list[str]) -> bool:
        """Add tags to a contact.

        Args:
            email: Contact email address
            tags: List of tags to add

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client or not self.audience_id:
            logger.warning(f"Mailchimp not configured. Would add tags to: {email}")
            return False

        try:
            tag_data = {
                "tags": [{"name": tag, "status": "active"} for tag in tags]
            }

            self.client.lists.update_list_member_tags(
                self.audience_id,
                email.lower(),
                tag_data,
            )

            logger.info(f"Added tags to {email}: {', '.join(tags)}")
            return True

        except ApiClientError as e:
            logger.error(f"Mailchimp API error adding tags to {email}: {e.text}")
            return False
        except Exception as e:
            logger.error(f"Failed to add tags to {email}: {str(e)}")
            return False

    def remove_tags(self, email: str, tags: list[str]) -> bool:
        """Remove tags from a contact.

        Args:
            email: Contact email address
            tags: List of tags to remove

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client or not self.audience_id:
            logger.warning(f"Mailchimp not configured. Would remove tags from: {email}")
            return False

        try:
            tag_data = {
                "tags": [{"name": tag, "status": "inactive"} for tag in tags]
            }

            self.client.lists.update_list_member_tags(
                self.audience_id,
                email.lower(),
                tag_data,
            )

            logger.info(f"Removed tags from {email}: {', '.join(tags)}")
            return True

        except ApiClientError as e:
            logger.error(f"Mailchimp API error removing tags from {email}: {e.text}")
            return False
        except Exception as e:
            logger.error(f"Failed to remove tags from {email}: {str(e)}")
            return False

    def unsubscribe_contact(self, email: str) -> bool:
        """Unsubscribe a contact from the audience.

        Args:
            email: Contact email address

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client or not self.audience_id:
            logger.warning(f"Mailchimp not configured. Would unsubscribe: {email}")
            return False

        try:
            self.client.lists.update_list_member(
                self.audience_id,
                email.lower(),
                {"status": "unsubscribed"},
            )

            logger.info(f"Unsubscribed contact from Mailchimp: {email}")
            return True

        except ApiClientError as e:
            logger.error(f"Mailchimp API error unsubscribing {email}: {e.text}")
            return False
        except Exception as e:
            logger.error(f"Failed to unsubscribe {email}: {str(e)}")
            return False

    def add_enrollment_contact(
        self,
        email: str,
        first_name: str,
        last_name: str,
        child_name: str,
        class_name: str,
        program_name: str,
    ) -> bool:
        """Add a contact who enrolled their child in a class.

        Args:
            email: Parent email
            first_name: Parent first name
            last_name: Parent last name
            child_name: Child's name
            class_name: Enrolled class name
            program_name: Program name

        Returns:
            bool: True if successful
        """
        tags = [
            "Enrolled",
            f"Program: {program_name}",
            f"Class: {class_name}",
        ]

        merge_fields = {
            "CHILD": child_name,
            "CLASS": class_name,
            "PROGRAM": program_name,
        }

        return self.add_or_update_contact(
            email=email,
            first_name=first_name,
            last_name=last_name,
            tags=tags,
            merge_fields=merge_fields,
        )

    def add_payment_contact(
        self,
        email: str,
        first_name: str,
        last_name: str,
        payment_type: str,
        amount: str,
    ) -> bool:
        """Add tags for a contact who made a payment.

        Args:
            email: Contact email
            first_name: First name
            last_name: Last name
            payment_type: Payment type (one-time, subscription, installment)
            amount: Payment amount

        Returns:
            bool: True if successful
        """
        tags = [
            "Paid Customer",
            f"Payment: {payment_type}",
        ]

        merge_fields = {
            "LAST_PAYMENT": amount,
            "PAYMENT_TYPE": payment_type,
        }

        return self.add_or_update_contact(
            email=email,
            first_name=first_name,
            last_name=last_name,
            tags=tags,
            merge_fields=merge_fields,
        )


# Singleton instance
mailchimp_service = MailchimpService()
