# utils/email_alert.py

import socket
import platform
import getpass
import requests
import time
import smtplib
import psutil  # For fetching MAC address
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import os
from dotenv import load_dotenv
import re

# Load environment variables from a .env file
load_dotenv()

# Define MAX_ATTEMPTS if not defined elsewhere
MAX_ATTEMPTS = 5

def is_valid_email(email):
    """Validate the email address format using a regular expression."""
    regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.match(regex, email)

def get_mac_address():
    """Get the MAC address of the first active network interface."""
    mac_address = "N/A"
    for interface, addresses in psutil.net_if_addrs().items():
        for addr in addresses:
            if addr.family == psutil.AF_LINK:  # AF_LINK is the MAC address family
                mac_address = addr.address
                return mac_address  # Return the first found MAC address
    return mac_address

def get_system_info():
    """
    Collect high-sensitive system information for failed authentication attempts.
    
    Returns:
        dict: A dictionary containing system information such as timestamps, IP addresses,
              hostname, OS details, username, and MAC address.
    """
    info = {}

    # Get current timestamp
    info["timestamp"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

    # Public IP Address using ipify (only IP, no location data)
    try:
        ip_info = requests.get('https://api.ipify.org?format=json').json()
        info["public_ip"] = ip_info.get('ip', 'N/A')
    except Exception as e:
        info["public_ip"] = "N/A"
        info["location_error"] = str(e)

    # Local IP Address
    info["local_ip"] = socket.gethostbyname(socket.gethostname())

    # Machine Information
    info["hostname"] = socket.gethostname()
    info["os"] = platform.system()
    info["os_version"] = platform.version()
    info["username"] = getpass.getuser()

    # MAC Address
    info["mac_address"] = get_mac_address()

    return info

def format_email_body(system_info, failed_attempts):
    """
    Create a detailed HTML email body with sensitive information structured.
    
    Args:
        system_info (dict): System information collected from get_system_info().
        failed_attempts (int): Number of failed authentication attempts.
    
    Returns:
        tuple: A tuple containing the HTML email body as a string, logo image data, and icon image data.
    """
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Define relative paths to the resized images
    logo_path = os.path.join(script_dir, "logo_resized.jpg")    # Ensure this file exists
    icon_path = os.path.join(script_dir, "icon_resized.png")    # Ensure this file exists

    # Read the logo image file
    try:
        with open(logo_path, 'rb') as img_file:
            logo_data = img_file.read()
    except FileNotFoundError:
        logo_data = None

    # Read the icon image file
    try:
        with open(icon_path, 'rb') as img_file:
            icon_data = img_file.read()
    except FileNotFoundError:
        icon_data = None

    # HTML Content with updated styles
    html = f"""
    <html>
    <head>
        <style>
            /* General Styles */
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f4f4;
                color: #ffffff; /* Default text color set to white */
                margin: 0;
                padding: 0;
            }}
            .container {{
                width: 80%;
                margin: auto;
                background-color: #1a1a1a;
                padding: 20px;
                border: 1px solid #333333;
                box-shadow: 0 0 10px rgba(0,0,0,0.5);
            }}
            .header {{
                text-align: center;
                padding-bottom: 20px;
                border-bottom: 1px solid #333333;
            }}
            .header img {{
                max-width: 150px;
            }}
            .content {{
                margin-top: 20px;
            }}
            .section {{
                margin-bottom: 15px;
            }}
            /* Title "Security Alert" in Red */
            .section h2 {{
                color: #ff0000; /* Red color for the title */
                border-bottom: 1px solid #333333;
                padding-bottom: 5px;
            }}
            /* Table Styles */
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            table, th, td {{
                border: 1px solid #333333;
            }}
            th, td {{
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #333333;
            }}
            /* Footer Styles */
            .footer {{
                text-align: center;
                font-size: 12px;
                color: #777777;
                border-top: 1px solid #333333;
                padding-top: 10px;
                margin-top: 20px;
            }}
            /* Additional Information Section */
            .additional-info {{
                margin-top: 10px;
            }}
            /* "JAMAL_DH" Styles */
            .alert-issuer {{
                color: #00ff00; /* Green color */
                font-family: 'Courier New', Courier, monospace; /* Monospaced font for hacker aesthetic */
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                {"<img src='cid:logo_image' alt='Company Logo'>" if logo_data else "<h1>Security Alert</h1>"}
            </div>
            <div class="content">
                <div class="section">
                    <h2>Security Alert: {failed_attempts} Failed Authentication Attempts</h2>
                </div>
                <div class="section">
                    <strong>Time of Last Attempt:</strong> {system_info['timestamp']}
                </div>
                <div class="section">
                    <h3>IP Information:</h3>
                    <table>
                        <tr>
                            <th>Public IP Address</th>
                            <td>{system_info['public_ip']}</td>
                        </tr>
                        <tr>
                            <th>Local IP Address</th>
                            <td>{system_info['local_ip']}</td>
                        </tr>
                        <tr>
                            <th>MAC Address</th>
                            <td>{system_info['mac_address']}</td>
                        </tr>
                    </table>
                </div>
                <div class="section">
                    <h3>Machine Information:</h3>
                    <table>
                        <tr>
                            <th>Hostname</th>
                            <td>{system_info['hostname']}</td>
                        </tr>
                        <tr>
                            <th>Operating System</th>
                            <td>{system_info['os']} ({system_info['os_version']})</td>
                        </tr>
                        <tr>
                            <th>Username</th>
                            <td>{system_info['username']}</td>
                        </tr>
                    </table>
                </div>
                <div class="section">
                    <h3>Additional Information:</h3>
                    {"<img src='cid:icon_image' alt='Icon'>" if icon_data else ""}
                    <div class="additional-info">
                        <strong>Alert Issued By:</strong> <span class="alert-issuer">JAMAL_DH</span>
                    </div>
                </div>
            </div>
            <div class="footer">
                &copy; {time.strftime('%Y')} The World Islamic Sciences and Education University. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    return html, logo_data, icon_data

def send_email_alert(subject, html_body, to_email, logo_data=None, icon_data=None):
    """
    Sends an HTML email alert with the given subject and body to the specified email address.
    Optionally attaches logo and icon images embedded within the email.
    
    Args:
        subject (str): The subject line of the email.
        html_body (str): The HTML content of the email body.
        to_email (str): The recipient's email address.
        logo_data (bytes, optional): Binary data of the logo image to embed.
        icon_data (bytes, optional): Binary data of the icon image to embed.
    
    Raises:
        ValueError: If the from_email or to_email addresses are invalid.
        Exception: If sending the email fails for any reason.
    """
    from_email = os.getenv('EMAIL_USER')  
    password = os.getenv('EMAIL_PASS')  # Use an app-specific password if using Gmail

    # Validate email addresses
    if not is_valid_email(from_email):
        raise ValueError("Invalid from_email address.")

    if not is_valid_email(to_email):
        raise ValueError("Invalid to_email address.")

    # Create message container with 'related' to embed images
    msg = MIMEMultipart('related')
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    # Alternative part for HTML content
    msg_alternative = MIMEMultipart('alternative')
    msg.attach(msg_alternative)

    # Attach HTML content
    msg_text = MIMEText(html_body, 'html')
    msg_alternative.attach(msg_text)

    # If logo data is available, attach it with a unique CID
    if logo_data:
        logo = MIMEImage(logo_data)
        logo.add_header('Content-ID', '<logo_image>')
        logo.add_header('Content-Disposition', 'inline', filename="logo.jpg")
        msg.attach(logo)

    # If icon data is available, attach it with a unique CID
    if icon_data:
        icon = MIMEImage(icon_data)
        icon.add_header('Content-ID', '<icon_image>')
        icon.add_header('Content-Disposition', 'inline', filename="icon.png")
        msg.attach(icon)

    try:
        # Connect to Gmail SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Secure the connection

        server.login(from_email, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        # Handle exceptions (log them if logging is implemented)
        print(f"Failed to send email: {e}")

def main():
    """
    Main function to send an email alert upon failed authentication attempts.
    Collects system information, formats the email body, and sends the email.
    """
    system_info = get_system_info()
    subject = "USB Authentication Failed"
    
    # Correctly unpack all three returned values
    email_body, logo_data, icon_data = format_email_body(system_info, MAX_ATTEMPTS)
    
    to_email = "your_alert_email@example.com"  # Replace with actual recipient
    
    # Send the email alert with the correct parameters
    send_email_alert(subject, email_body, to_email, logo_data, icon_data)

if __name__ == "__main__":
    """
    Entry point for the email alert utility.
    When run directly, it sends an email alert with the collected system information.
    """
    main()
