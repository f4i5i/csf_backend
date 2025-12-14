"""Email validation utilities."""

# Common disposable/temporary email domains to block
# This list can be extended as needed
DISPOSABLE_EMAIL_DOMAINS = {
    # Popular temp mail services
    "tempmail.com",
    "temp-mail.org",
    "10minutemail.com",
    "guerrillamail.com",
    "mailinator.com",
    "maildrop.cc",
    "throwaway.email",
    "getnada.com",
    "trashmail.com",
    "yopmail.com",
    "fakeinbox.com",
    "sharklasers.com",
    "grr.la",
    "guerrillamailblock.com",
    "pokemail.net",
    "spam4.me",
    "tempinbox.com",
    "temp-mail.io",
    "mohmal.com",
    "emailondeck.com",
    "dispostable.com",
    "mintemail.com",
    "mytemp.email",
    "emailfake.com",
    "mailnesia.com",
    "tempail.com",
    "burnermail.io",
    "throwawaymail.com",
    "fakemailgenerator.com",
    "mailcatch.com",
    "mailsac.com",
    "temp-mail.de",
    "fakemail.net",
    "inboxkitten.com",
    "temp-inbox.com",
    "momentemail.com",
    "nowmymail.com",
    "temp-mails.com",
    "anonbox.net",
    "emailsensei.com",
    "incognitomail.com",
    "mailhazard.com",
    "mywrld.top",
    "tempmailo.com",
    "throwbin.com",
    "ghostemail.com",
    "tempmail.ninja",
    "mailtemp.info",
}


def is_disposable_email(email: str) -> bool:
    """
    Check if an email address uses a disposable/temporary email service.

    Args:
        email: Email address to validate

    Returns:
        True if the email domain is disposable, False otherwise
    """
    try:
        # Extract domain from email
        _, domain = email.rsplit("@", 1)
        domain = domain.lower()
        return domain in DISPOSABLE_EMAIL_DOMAINS
    except (ValueError, AttributeError):
        # Invalid email format, let other validators handle it
        return False
