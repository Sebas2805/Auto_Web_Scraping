import smtplib
import ssl
from email.message import EmailMessage
import os

import time
from datetime import datetime

def send_email(attached_file):
    send_from = os.getenv('EMAIL')
    send_to = os.getenv('EMAIL')
    subject = 'CR Autos Scraping for ' + str(datetime.today().date())
    password = os.getenv('EMAIL_PASSWORD')
    email_body = 'Report Attached'

    # Create the message
    msg = EmailMessage()
    msg['From'] = send_from
    msg['To'] = send_to
    msg['Subject'] = subject
    msg.set_content(email_body)

    # Attached file
    with open(attached_file, 'rb') as f:
        content = f.read()
        msg.add_attachment(content, maintype='application',
                           subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                           filename=attached_file)

    # Send email
    ssl_context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=ssl_context) as smtp:
        smtp.login(send_from, password)
        smtp.send_message(msg)

