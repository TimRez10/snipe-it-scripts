import csv
from pathlib import Path
from modules.licenses import assign_license_seats
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
        logger.info("Follow the instructions in the following article to get a CSV extract of the user list:")
        logger.info("https://www.mlc-cad.com/solidworks-help-center/how-to-export-pdm-user-list/")
        assignments_path = get_assignments_file()
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        return False

    # Collect users
    user_emails = []

    with open(assignments_path, newline='', encoding="utf-16", errors='ignore') as csvfile:
        logger.info(f"Reading {assignments_path}")
        next(csvfile) # Skip first line
        reader = csv.DictReader(csvfile, delimiter=";")
        for row in reader:
            if not row["Email"]:
                continue
            email = row["Email"].strip()
            if config["company_domain"] not in email:
                continue

            user_emails.append(email)

    if not user_emails:
        logger.warning(f"No emails found.")
        return False

    # Convert emails to IDs and assign seats
    user_ids = user_mail_to_id_list(user_emails)

    logger.info(f"Attemping to assign seats to {len(user_ids)} users for the license id: {config["LICENSE_ID"]}")
    assign_license_seats(config["LICENSE_ID"], user_ids, len(user_ids))

if __name__ == "__main__":
    main()