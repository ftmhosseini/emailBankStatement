import base64
import json
from datetime import datetime, timedelta, timezone
from information import *
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


SNAPSHOT_FILE = "last_24h_snapshot.json"
DATA_FILE = "data.json"

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

def get_token(username, password):
    """Request OAuth2 access token using user credentials."""
    credentials = f"{username}:{password}"
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
    permission = False
    now = datetime.now(timezone.utc)
    from_time = (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    to_time = now.strftime("%Y-%m-%dT%H:%M:%S.999Z")
    all_records = get_all_statements(from_time, to_time)
    with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if len(data) == 0:
            permission = True
        else:
            records = all_records
            for index, record in enumerate(records):
                if record in data:
                    records.pop(index)
                    data.pop(index)

            for d in data:
                if d.get("transactionDateTime") < from_time:
                    del data[d]
            if len(data) == 0:
                permission = True
    if permission:
        with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_records, f, indent=2, ensure_ascii=False)
    return records



def get_all_statements(from_time, to_time, limit = 100):
    all_records = []
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
        if response.status_code != 200:
            print("❌ Request failed:", response.status_code, response.text)
            break

        data = response.json()
        # assume your API response contains a list of transactions inside "records"
        # Support both array or nested dict formats
        if isinstance(data, list):
            records = data
        else:
            records = data.get("response", {}).get("accountStatementResponse", [])
            records_count = data.get("response", {}).get("outputRecordCount", 0)
            limit = records_count
            ids = set(item.get("transactionId") for item in records)
            if not len(ids) == len(records):
                send_email_alert("⚠️Repeated transactions","this data has repeated transactions")

            for record in records:
                if record not in all_records:
                    all_records.append(record)

        if not records:
            print(f"✅ All {len(all_records)} records fetched.")
            break

        print(f"📦 Page {page}: got {len(records)} records.")

        # if less than limit returned → that was the last page
        if len(records) < limit:
            break
        else:
            print(f"❌ Page {page}: got {len(records)} records. please check!!")

        page += 1

    return all_records

