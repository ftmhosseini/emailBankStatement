import base64
import json
from datetime import datetime, timedelta, timezone
from information import *
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import encoders

SNAPSHOT_FILE = "last_24h_snapshot.json"
DATA_FILE = "data.json"

def convert_ids_to_string(record):
    if 'transactionId' in record:
        record['transactionId'] = str(record['transactionId'])
    # Repeat for any nested records or different ID keys if necessary
    return record

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

        print(f"✅ Email with attachment '{os.path.basename(SNAPSHOT_FILE)}' sent successfully to {os.environ.get('DESTINATION_EMAIL')}")

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


def get_token():
    """Request OAuth2 access token using user credentials."""
    credentials = f"{os.environ.get('username')}:{os.environ.get('password')}"
    base64_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {base64_credentials}",
        "Cookie": os.environ.get("TOKEN_COOKIE")
    }

    data = {
        "scope": "svc-mgmt-mq-stmt-info",
        "grant_type": "client_credentials"
    }

    print("\n🔐 Getting access token...")
    response = requests.post(os.environ.get("TOKEN_URL"), headers=headers, data=data)

    if response.status_code == 200:
        os.environ["TOKEN"] = response.json().get("access_token")
        print("✅ Access token retrieved successfully.")
        return os.environ["TOKEN"]
    else:
        print("❌ Failed to get token:", response.status_code, response.text)
        return None



def get_24h_statement():

    now = datetime.now(timezone.utc)
    from_time = (now - timedelta(hours=72)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    to_time = now.strftime("%Y-%m-%dT%H:%M:%S.999Z")
    all_records = get_all_statements(from_time, to_time)
    records = all_records.copy()
    with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

        if len(data) != 0:
            # clean_record(d)
            records = [r for r in records if r not in data]

            deleted_data = []
            changeable_keys = ['rowNumber' , 'hyperLinkType', 'categoryId']
            for d in data:
                temp_deleted_data = {}  # collect deleted fields for this record

                orig = next((r for r in all_records
                             if r.get("transactionId") == d.get("transactionId")), None)

                if orig is None:
                    continue  # didn't exist before → skip

                for k, v in d.items():
                    if k not in changeable_keys:
                        if orig.get(k) != v:  # compare to original value
                            if k == 'transactionId' and v > 0:
                                temp_deleted_data[k] = v

                if temp_deleted_data:
                    deleted_data.append(temp_deleted_data)

            # data = [d for d in data if d.get("transactionDateTime") >= from_time and d not in all_records]
            #
            # deleted_data = [d for d in data if d.get('transactionId') > 0]
            if len(deleted_data) != 0:
                send_email_alert(f'deleting {len(deleted_data)} from previous statement form {from_time}', f" data is {deleted_data}")
                send_email_file_attached("deleted data")

    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_records, f, indent=2, ensure_ascii=False)
    return [records, data]



def get_all_statements(from_time, to_time, limit = 100):
    all_records = []
    records_count = 0
    page = 1

    while True:
        headers = {
            "Authorization": f"Bearer {os.environ.get('TOKEN')}",
            "Content-Type": "application/json",
            "Cookie": os.environ.get("STATEMENT_COOKIE")
        }

        body = {
            "offsetNumber": page,
            "offsetLength": limit,
            "accountNumber": os.environ.get("ACCOUNT_NUMBER"),
            "dateTimeRange": {
                "fromDateTime": from_time,
                "toDateTime": to_time
            },
            "languageType": "FARSI"
        }

        response = requests.post(os.environ.get("STATEMENT_URL"), headers=headers, data=json.dumps(body))
        if response.status_code == 401 and response.json().get("error", {}).get("code") == 'AUTHENTICATION_EXCEPTION':
            token = get_token()
            if not token:
                return None
            response = requests.post(os.environ.get("STATEMENT_URL"), headers=headers, data=json.dumps(body))

        response.encoding = 'utf-8'
        data = response.json()
        # assume your API response contains a list of transactions inside "records"
        # Support both array or nested dict formats
        if isinstance(data, list):
            # records = [convert_ids_to_string(record) for record in data]
            records = data
        else:
            records = data.get("response", {}).get("accountStatementResponse", [])
            records_count = data.get("response", {}).get("outputRecordCount", 0)

            ids = set(item.get("transactionId") for item in records)
            if not len(ids) == len(records):
                send_email_alert("⚠️Repeated transactions","this data has repeated transactions")

            for record in records:
                if record not in all_records:
                    # all_records.append(convert_ids_to_string(record))
                    all_records.append(record)

        if not records:
            print(f"✅ All {len(all_records)} records fetched.")
            break

        print(f"📦 Page {page}: got {len(records)} records.")

        # if less than limit returned → that was the last page
        if records_count <= limit:
            break
        else:
            limit = records_count + 1
            print(f"❌ Page {page}: got {len(records)} records. please check!!")

        page += 1

    return all_records

