import os
import re
import time
import socket
import platform
import getpass
import smtplib
import secrets
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from dotenv import load_dotenv
import psutil  # For fetching MAC address

# Load environment variables from a .env file
load_dotenv()

# OTP settings
OTP_LENGTH = 6
OTP_VALIDITY_SECONDS = 60  # in seconds
_otp_store = {}  # Maps email -> {"otp": str, "expires_at": datetime}

# Email sender credentials
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

# Security alert settings (legacy)
MAX_ATTEMPTS = 5


def is_valid_email(email: str) -> bool:
    """Validate the email address format using a regular expression."""
    regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.match(regex, email) is not None


def _send_email(subject: str, html_body: str, to_email: str, logo_data=None, icon_data=None):
    """Low-level helper to send an HTML email with inline images."""
    if not is_valid_email(EMAIL_USER) or not is_valid_email(to_email):
        raise ValueError("Invalid email address.")

    msg = MIMEMultipart('related')
    msg['From'] = EMAIL_USER
    msg['To'] = to_email
    msg['Subject'] = subject

    alt = MIMEMultipart('alternative')
    msg.attach(alt)
    alt.attach(MIMEText(html_body, 'html'))

    # Inline images
    if logo_data:
        logo = MIMEImage(logo_data)
        logo.add_header('Content-ID', '<logo_image>')
        logo.add_header('Content-Disposition', 'inline', filename='logo.jpg')
        msg.attach(logo)
    if icon_data:
        icon = MIMEImage(icon_data)
        icon.add_header('Content-ID', '<icon_image>')
        icon.add_header('Content-Disposition', 'inline', filename='icon.png')
        msg.attach(icon)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)


def generate_otp(length: int = OTP_LENGTH) -> str:
    """Generate a numeric OTP of given length."""
    return ''.join(str(secrets.randbelow(10)) for _ in range(length))


def send_otp_email(to_email: str) -> None:
    """Generate an OTP, store it, and email it to the user."""
    otp = generate_otp()
    expires = datetime.datetime.utcnow() + datetime.timedelta(seconds=OTP_VALIDITY_SECONDS)
    _otp_store[to_email] = {'otp': otp, 'expires_at': expires}

    # Load HTML template
    with open('security/admin_recovery_otp.html', 'r') as f:
        html = f.read()

    # Replace placeholders
    html = html.replace('{{OTP_CODE}}', otp)
    html = html.replace('{{EXPIRY_MINUTES}}', str(OTP_VALIDITY_SECONDS // 60))
    html = html.replace('{{CURRENT_YEAR}}', str(datetime.datetime.utcnow().year))

    # Read logo into memory
    with open('ui/Secure Chat App3.png', 'rb') as img:
        logo_bytes = img.read()

    _send_email(
        subject="SecureChat™ Admin Key Recovery OTP",
        html_body=html,
        to_email=to_email,
        logo_data=logo_bytes   # this attaches the logo inline
    )


def verify_otp(to_email: str, otp_input: str) -> bool:
    """Check if the provided OTP matches and is within the valid time window."""
    record = _otp_store.get(to_email)
    if not record:
        return False

    if datetime.datetime.utcnow() > record['expires_at']:
        # OTP expired
        del _otp_store[to_email]
        return False

    valid = secrets.compare_digest(record['otp'], otp_input)
    if valid:
        # Invalidate OTP after successful use
        del _otp_store[to_email]
    return valid




