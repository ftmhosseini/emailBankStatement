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
            records = sorted(records, key=lambda r: r["transactionDateTime"])
            for curr, nxt in zip(records, records[1:]):
                if abs(curr["balance"] - nxt["balance"]) not in (abs(curr["amount"]), abs(nxt["amount"])):
                    send_email_alert(
                        f"❌ Transaction {curr.get('transactionId')}",
                        f"🚨 This transaction doesn't change the balance properly"
                    )

            # for index in range(len(records)-1):
            #     if abs(records[index].get("balance") - records[index+1].get("balance")) != abs(records[index].get("amount")) or abs(records[index].get("balance") - records[index+1].get("balance")) != abs(records[index+1].get("amount")):
            #         send_email_alert(f"❌ transaction {records[index].get('transactionId')}", f"🚨 this transaction doesn't change the balance")
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
            if os.path.exists(day_file_path):
                with open(day_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = []

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

        print("\n⏰ Waiting 6 hour before next fetch...\n")
        time.sleep(21600)


if __name__ == "__main__":
    main()