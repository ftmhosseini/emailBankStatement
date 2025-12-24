import os
import json
import boto3
from dotenv import load_dotenv

import smtplib
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import encoders
load_dotenv()

SNAPSHOT_FILE = os.environ.get("SNAPSHOT_FILE")

def send_aws_sqs(queue):
    sqs = boto3.client(
        "sqs",
        region_name=os.environ.get("AWS_REGION"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
    )
    queue_url = os.environ.get("SQS_QUEUE_URL")
    my_list = queue
    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(my_list)
    )

def email_back_up(subject, body):
    sender_email = os.environ.get("EMAIL_ADDRESS")
    sender_password = os.environ.get("EMAIL_PASSWORD")  # use app password, not your Gmail password
    msg = MIMEMultipart()
    msg["From"] = os.environ.get("EMAIL_ADDRESS")
    msg["To"] = os.environ.get("OTHER_EMAIL_ADDRESS")
    msg["Subject"] = subject
    msg.attach(MIMEText(str(body), 'plain'))
    try:
        with open(SNAPSHOT_FILE, "rb") as attachment:
            # Create a MIMEBase object for the attachment
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())

        # **CRITICAL MISSING STEP: Encode the file data**
        encoders.encode_base64(part)

        # Add the header with the file name
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {os.path.basename(SNAPSHOT_FILE)}",
        )
        msg.attach(part)

    except FileNotFoundError:
        print(f"⚠️ Warning: Attachment file not found at {SNAPSHOT_FILE}. Sending email without file.")
    except Exception as e:
        print(f"🛑 Error attaching file: {e}. Sending email without file.")

        # --- 4. Send the Email (CRITICAL MISSING STEP) ---
    try:
        # Connect to the SMTP server using TLS encryption
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)

        print(
            f"✅ Email with attachment '{os.path.basename(SNAPSHOT_FILE)}' sent successfully to {os.environ.get('DESTINATION_EMAIL')}")

    except Exception as e:
        print(f"❌ Failed to send email via SMTP: {e}")

    # sender_email = os.environ.get("EMAIL_ADDRESS")


def send_email_file_attached(subject):
    sender_email = os.environ.get("EMAIL_ADDRESS")
    sender_password = os.environ.get("EMAIL_PASSWORD")  # use app password, not your Gmail password
    msg = MIMEMultipart()
    msg["From"] = os.environ.get("EMAIL_ADDRESS")
    msg["To"] = os.environ.get("DESTINATION_EMAIL")
    msg["Subject"] = subject
    body = "Duplicate transaction IDs found"
    msg.attach(MIMEText(body, 'plain'))
    try:
        with open(SNAPSHOT_FILE, "rb") as attachment:
            # Create a MIMEBase object for the attachment
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())

        # **CRITICAL MISSING STEP: Encode the file data**
        encoders.encode_base64(part)

        # Add the header with the file name
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {os.path.basename(SNAPSHOT_FILE)}",
        )
        msg.attach(part)

    except FileNotFoundError:
        print(f"⚠️ Warning: Attachment file not found at {SNAPSHOT_FILE}. Sending email without file.")
    except Exception as e:
        print(f"🛑 Error attaching file: {e}. Sending email without file.")

        # --- 4. Send the Email (CRITICAL MISSING STEP) ---
    try:
        # Connect to the SMTP server using TLS encryption
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)

        print(
            f"✅ Email with attachment '{os.path.basename(SNAPSHOT_FILE)}' sent successfully to {os.environ.get('DESTINATION_EMAIL')}")

    except Exception as e:
        print(f"❌ Failed to send email via SMTP: {e}")


def send_email_alert(subject, body):
    sender_email = os.environ.get("EMAIL_ADDRESS")
    sender_password = os.environ.get("EMAIL_PASSWORD")  # use app password, not your Gmail password

    msg = MIMEMultipart()
    msg["From"] = os.environ.get("EMAIL_ADDRESS")
    msg["To"] = os.environ.get("DESTINATION_EMAIL")
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print(f"✅ Email sent to {os.environ.get('DESTINATION_EMAIL')}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
    # send_aws_sqs(body)
