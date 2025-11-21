import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_report():
    msg = MIMEMultipart()
    msg["From"] = "me@automator.com"
    msg["To"] = "manager@company.com"