from dotenv import load_dotenv, set_key

from BankStatement import *
from SendEmail import *
from collections import Counter
import time

# every 6 hours
# DATA_FETCH_INTERVAL = timedelta(hours=6)
# every one hour
DATA_FETCH_INTERVAL = timedelta(hours=1)
def main():

    last_data_fetch = datetime.min.replace(tzinfo=timezone.utc)

    print("=== 🕐 Statement Fetcher with Daily & Weekly Reports ===")
    username_input= input("Enter your username (client_id): ").strip()
    set_key(".env", "username", username_input)
    password_input = input("Enter your password (client_secret): ").strip()
    set_key(".env", "password", password_input)
    load_dotenv(override=True)

    get_token()
    while True:
        now = datetime.now(timezone.utc)
        try:
            if now - last_data_fetch >= DATA_FETCH_INTERVAL:
                print("⬇️ Fetching new data...")
                # day_key = now.strftime("%Y_%m_%d")
                date_keys = []
                for i in range(3):
                    # Subtract 'i' days (0 for today, 1 for yesterday, 2 for day before)
                    target_date = now - timedelta(days=i)

                    # Format the date as 'YYYY_MM_DD'
                    day_key = target_date.strftime("%Y_%m_%d")
                    date_keys.append(day_key)
                month_key = now.strftime("%b %Y")
                base_dir = os.environ.get("BASE_DIR", ".")  # fallback to current dir
                month_dir = os.path.join(base_dir, month_key)
                os.makedirs(month_dir, exist_ok=True)
                day_file_paths = [ os.path.join(month_dir, f"{day_key}.json") for day_key in date_keys ]
            # Get new data
                [records, deletedData] = get_24h_statement()

                if records:
                    records = sorted(records, key=lambda r: r["transactionId"])
                    for curr, nxt in zip(records, records[1:]):
                        if int(curr["transactionId"]) > 0 and int(nxt["transactionId"]) > 0:
                            if abs(int(curr["balance"]) - int(nxt["balance"])) not in (abs(int(curr["amount"])), abs(int(nxt["amount"]))):
                                send_email_alert(
                                    f"❌ Transaction {curr.get('transactionId')}",
                                    f"🚨 This transaction doesn't change the balance properly ${records}"
                                )

                    credit_records = [
                        (r.get("additionalData2"), r.get("amount"), r.get("balance"))
                        for r in records
                        if r.get("creditDebit") == "CREDIT"
                    ]
                    debit_commission_records = [
                        r.get("amount")
                        for r in records
                        if r.get("creditDebit") == "DEBIT" and r.get("transactionCode")  == "553"
                    ]
                    debit_records = [
                        (r.get("additionalData2"), r.get("amount"), r.get("balance"))
                        for r in records
                        if r.get("creditDebit") == "DEBIT" and r.get("transactionCode") != "553"
                    ]
                    send_email_alert("✅ CREDIT", f"🚨 Found successful transactions: {credit_records} \n"
                                                 f"found debit transactions: {debit_records}\n"
                                                 f"and totally commission transactions: {sum(debit_commission_records)}")
                    data = []
                    for day_file_path in day_file_paths:
                        if os.path.exists(day_file_path):
                            try:
                                with open(day_file_path, "r", encoding="utf-8") as f:
                                    # Load the data from the single file and extend the main list
                                    file_data = json.load(f)
                                    data.extend(file_data)
                                    print(f"✅ Loaded {len(file_data)} records from {day_file_path}")
                            except json.JSONDecodeError:
                                print(f"❌ Error decoding JSON file: {day_file_path}")
                            except Exception as e:
                                print(f"❌ An error occurred reading {day_file_path}: {e}")
                        else:
                            print(f"⚠️ File not found: {day_file_path}")

                    # Merge both lists
                    data = [d for d in data if d not in deletedData]

                    records += data
                    ids = [r.get("transactionId") for r in records if "transactionId" in r]

                    duplicates = [item for item, count in Counter(ids).items() if count > 1]
                    if duplicates:
                        send_email_alert("❌ duplication", f"🚨 Found duplicate transaction IDs: {duplicates}")
                        print(f"🚨 Found duplicate transaction IDs: {duplicates}")
                        # with open(Duplication_FILE, "w", encoding="utf-8") as f:
                        #     json.dump(records, f, indent=2, ensure_ascii=False)
                        send_email_file_attached(f"🚨 Found duplicate transaction IDs: {duplicates}")
                    else:
                        print("✅ No duplicate transaction IDs found.")
                        records.sort(key=lambda r: r.get("transactionDateTime"))
                        for day_file_path in day_file_paths:
                            filename = os.path.basename(day_file_path)
                            day_key = filename.replace('.json', '')
                            try:
                                naive_day_start = datetime.strptime(day_key, "%Y_%m_%d")
                                day_start = naive_day_start.replace(tzinfo=timezone.utc)
                            except ValueError:
                                print(f"❌ Skipping {day_file_path}: Invalid date key format found in filename.")
                                continue

                            day_end = day_start + timedelta(days=1)

                            # 3. Filter the Records
                            daily_records = []
                            for record in records:
                                time_str = record.get("transactionDateTime")

                                if time_str:
                                    try:
                                        tx_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                                        if day_start <= tx_time <= day_end:
                                            daily_records.append(record)
                                    except ValueError:
                                        # Handle cases where the timestamp format is invalid
                                        print(f"⚠️ Warning: Invalid time format in record: {time_str}")
                            if daily_records:
                                with open(day_file_path, "w", encoding="utf-8") as f:
                                    json.dump(daily_records, f, indent=2, ensure_ascii=False)
                                print(f"✅ Successfully saved {len(daily_records)} records to {day_file_path}")
                            else:
                                print(
                                    f"⚠️ No records found for {day_key}. File {day_file_path} saved as empty list or skipped.")

                last_data_fetch = now
                print(f"⏰ Next data fetch in {DATA_FETCH_INTERVAL}.\n")
        except Exception as e:
            email_back_up("error occurs", str(e))
        finally:
            time.sleep(DATA_FETCH_INTERVAL.total_seconds())



if __name__ == "__main__":
    main()