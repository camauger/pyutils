import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()


def send_report() -> None:
    msg: MIMEMultipart = MIMEMultipart()
    msg["From"] = "camauger@protonmail.com"
    msg["To"] = "christian@amauger.com"
    msg["Subject"] = "Weekly Report"
    msg.attach(MIMEText("This is your weekly automated report"))

    # ProtonMail Bridge settings
    smtp_server = "127.0.0.1"  # ProtonMail Bridge runs locally
    smtp_port = 1025  # Default ProtonMail Bridge SMTP port

    # Get credentials from environment variables (more secure)
    email: str | None = os.getenv("PROTON_EMAIL")
    password: str | None = os.getenv("PROTON_BRIDGE_PASSWORD")

    if password is None:
        raise ValueError("PROTON_BRIDGE_PASSWORD environment variable is required")
    if email is None:
        raise ValueError("PROTON_EMAIL environment variable is required")
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email, password)
            server.send_message(msg)
            print("✓ Report sent successfully!")
    except Exception as e:
        print(f"✗ Failed to send report: {e}")


if __name__ == "__main__":
    send_report()
