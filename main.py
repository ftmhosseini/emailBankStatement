from BankStatement import *
from collections import Counter
import time


def main():
    print("=== 🕐 Statement Fetcher with Daily & Weekly Reports ===")
    username = input("Enter your username (client_id): ").strip()
    password = input("Enter your password (client_secret): ").strip()

    token = get_token(username, password)
    if not token:
        return

    while True:
        now = datetime.now(timezone.utc)
        day_key = now.strftime("%Y_%m_%d")
        month_key = now.strftime("%b %Y")
        base_dir = os.environ.get("BASE_DIR", ".")  # fallback to current dir
        month_dir = os.path.join(base_dir, month_key)
        os.makedirs(month_dir, exist_ok=True)

        day_file_path = os.path.join(month_dir, f"{day_key}.json")
        # Get new data
        records = get_24h_statement()
        if records:
            credit_records = [
                (r.get("additionalData2"), r.get("amount"))
                for r in records
                if r.get("creditDebit") == "CREDIT"
            ]
            send_email_alert("✅ CREDIT", f"🚨 Found successful transactions: {credit_records}")
            with open(day_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge both lists
            records += data
            ids = [r.get("transactionId") for r in records if "transactionId" in r]

            duplicates = [item for item, count in Counter(ids).items() if count > 1]
            if duplicates:
                send_email_alert("❌ duplication", f"🚨 Found duplicate transaction IDs: {duplicates}")
                print(f"🚨 Found duplicate transaction IDs: {duplicates}")
            else:
                print("✅ No duplicate transaction IDs found.")
                records.sort(key=lambda r: r.get("transactionDateTime"))
                with open(day_file_path, "w", encoding="utf-8") as f:
                    json.dump(records, f, indent=2, ensure_ascii=False)

            print(f"✅ Saved {len(records)} records to {day_file_path}")
        else:
            print("⚠️ No records found, skipping save.")

        print("\n⏰ Waiting 1 hour before next fetch...\n")
        time.sleep(3600)


if __name__ == "__main__":
    main()