import csv
from pathlib import Path
from modules.licenses import assign_license_seats, get_license_seat_count
from modules.users import user_mail_to_id_list
from modules.logging import get_logger
from modules.config import get_assignments_file, load_script_config

# Get the directory and file information dynamically
script_path = Path(__file__)

# Load logging/config
logger = get_logger()
config = load_script_config(script_path)

def main():
    # Get assignments file from user
    try:
        logger.info("Export User Data to CSV Format from the following link: https://manage.autodesk.com/all-account-export")
        assignments_path = get_assignments_file()
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        return False
    
    # Collect users per license
    license_user_emails = {}

    with open(assignments_path, newline='', encoding="utf-8-sig") as csvfile:
        logger.info(f"Reading {assignments_path}")
        reader = csv.DictReader(csvfile)
        for row in reader:
            product = row["offering_name"].strip()
            if not product:
                product = "N/A"
            email = row["email"].strip()

            license_id = config["PRODUCT_TO_LICENSE_ID"].get(product)

            if not license_id:
                logger.warning(f"Unknown product: {product}")
                continue

            license_user_emails.setdefault(license_id, set()).add(email)

    # Convert emails to IDs and assign seats
    for license_id, email_list in license_user_emails.items():
        seat_count = get_license_seat_count(license_id)
        license_name = next((key for key, value in config["PRODUCT_TO_LICENSE_ID"].items() if value == license_id), None)

        if license_name == "N/A":
            seat_count = len(user_ids)
        else:
            print(f"Enter seat count for {license_name} (leave blank for {seat_count}):")
            choice = input("> ").strip()

            if choice:
                if choice.isdigit():
                    seat_count = int(choice)
                else:
                    print(f"Invalid input: {choice}")
                    exit(code=1)
        
        

        user_ids = user_mail_to_id_list(email_list)
        logger.info(f"Attemping to assign {seat_count} seats to {len(user_ids)} users for the license id: {license_id}")
        assign_license_seats(license_id, user_ids, seat_count)


if __name__ == "__main__":
    main()