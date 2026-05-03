import csv
from pathlib import Path
from modules.licenses import assign_license_seats, update_license_note_non_company_users
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
        logger.info("Export the user list as a CSV from the following link:")
        logger.info(config["URL"])
        assignments_path = get_assignments_file()
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        return False

    # Collect users
    company_emails = []
    non_company_emails_names = []

    with open(assignments_path, newline='', encoding="utf-8-sig") as csvfile:
        logger.info(f"Reading {assignments_path}")
        reader = csv.DictReader(csvfile)
        for row in reader:
            email = row["Email"].strip()
            if config["company_domain"] not in email:
                non_company_emails_names.append({"email":row["Email"], "name":f"{row['First Name']} {row['Last Name']}"})
            else:
                company_emails.append(email)
    
    if not company_emails:
        logger.warning(f"No emails found.")
        return False

    # Convert emails to IDs and assign seats
    user_ids = user_mail_to_id_list(company_emails)

    logger.info(f"Attemping to assign seats to {len(user_ids)} users for the license id: {config["LICENSE_ID"]}")
    assign_license_seats(config["LICENSE_ID"], user_ids, len(user_ids))

    update_license_note_non_company_users(config["LICENSE_ID"], non_company_emails_names)

if __name__ == "__main__":
    main()