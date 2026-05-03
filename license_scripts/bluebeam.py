import csv
from datetime import datetime
from pathlib import Path
from modules.licenses import assign_license_seats_notes
from modules.users import user_mail_notes_to_id_notes
from modules.logging import get_logger
from modules.config import get_api_path, get_venv_path, load_script_config
from modules.runner import run_py_stream_logged

# Get the directory and file information dynamically
script_path = Path(__file__)
app_path = script_path.parent.parent
py_script = get_api_path(script_path)
venv_python = get_venv_path(script_path)

# Load logging/config
logger = get_logger()
config = load_script_config(script_path)

def main():
    # Run Python API / Web Scraper script
    run_py_stream_logged(py_script, env_vars={"BLUEBEAM_ORG_ID": config["ORG_ID"]}, python_exe=venv_python)

    assignments_path = str(app_path) + r"\files\bluebeam\LicenseAssignments.csv"
    license_validity_path = str(app_path) + r"\files\bluebeam\bluebeam_table_export.csv"

    # Collect valid subscriptions and seat counts
    valid_subscriptions = []
    seen_subscriptions = set()
    license_seat_counts = {}

    seen_subscriptions.add("n/a")

    with open(license_validity_path, newline='', encoding="utf-8-sig") as csvfile:
        logger.info(f"Reading {license_validity_path}")
        reader = csv.DictReader(csvfile, delimiter=",")

        for row in reader:
            subscription = row["Serial Number"]
            product = row["Product"]

            if subscription == "n/a":
                continue
            
            total_subs = int(row["Total Subs"].strip())
            end_date = datetime.strptime(row["End Date"].strip(), "%b %d, %Y")
            today = datetime.today()

            if today < end_date:
                license_id = config["PRODUCT_TO_LICENSE_ID"].get(product)
                if not license_id:
                    logger.warning(f"Unknown product in seat count: {product}")
                    continue
                if subscription in seen_subscriptions:
                    continue  # Skip duplicates
                
                if row["Order Status"] == "Active":
                    license_seat_counts[license_id] = license_seat_counts.get(license_id, 0) + total_subs
                    
                seen_subscriptions.add(subscription)
                valid_subscriptions.append({
                    "subscription": subscription,
                    "end_date": row["End Date"],
                    "associated_pos": row["POs"]
                })
            else:
                logger.warning(f"Subscription {subscription} has expired")
    logger.info(f"Found {len(valid_subscriptions)} valid subscriptions")

    # Collect users per license
    license_user_emails_notes = {}

    with open(assignments_path, newline='', encoding="utf-8-sig") as csvfile:
        logger.info(f"Reading {assignments_path}")
        reader = csv.DictReader(csvfile)
        for row in reader:
            product = row["Plan"].strip()
            email = row["Email Address"].strip() 
            subscription = row["Serial Number"].strip()

            if row["Status"].strip() == "Deactivated":
                continue
            
            if not subscription or subscription == "n/a":
                license_id = config["PRODUCT_TO_LICENSE_ID"].get("Unpaid")
                note = f"Unpaid user"
                license_user_emails_notes.setdefault(license_id, []).append((email,note))
                continue

            if subscription not in seen_subscriptions:
                logger.warning(f"{email}'s subscription has expired!")
                continue

            license_id = config["PRODUCT_TO_LICENSE_ID"].get(product)
            if not license_id:
                logger.warning(f"Unknown product: {product}")
                continue
            
            subscription_details = next((sub for sub in valid_subscriptions if sub["subscription"] == subscription), None)
            if subscription_details:
                note = f"License info:\n  SN: {subscription}\n End Date: {subscription_details['end_date']}\n  Associated POs: {subscription_details['associated_pos']}" 

            license_user_emails_notes.setdefault(license_id, []).append((email,note))

    # Convert emails to IDs and assign seats
    for license_id, email_list in license_user_emails_notes.items():
        user_ids_and_notes = user_mail_notes_to_id_notes(email_list)
        seat_count = license_seat_counts.get(license_id, len(user_ids_and_notes))

        logger.info(f"Attemping to assign {seat_count} seats to {len(user_ids_and_notes)} users for the license id: {license_id}")
        assign_license_seats_notes(license_id, user_ids_and_notes, seat_count)
    
if __name__ == "__main__":
    main()