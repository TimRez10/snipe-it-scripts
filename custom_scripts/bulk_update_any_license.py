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
        logger.info("Enter the license ID to update")
        license_id = input("> ").strip()
        logger.info("TXT file only! Ensure the TXT file has one email per newline.")
        assignments_path = get_assignments_file()
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        return False

    # Collect users
    company_emails = []
    non_company_emails_names = []

    with open(assignments_path, newline='', encoding="utf-8") as txtfile:
        logger.info(f"Reading {assignments_path}")
        for line in txtfile:
            email = line.strip()

            if " " in email:
                continue

            if "@" in line:
                if config["company_domain"] in line:
                    logger.debug(f"Found email: {email}")
                    company_emails.append(email)
                else:
                    non_company_emails_names.append({"email":email, "name":""})
    
    if not company_emails:
        logger.warning(f"No emails found.")
        return False

    # Convert emails to IDs and assign seats
    user_ids = user_mail_to_id_list(company_emails)

    seat_count = len(user_ids)

    print(f"Enter seat count (leave blank for {seat_count}):")
    choice = input("> ").strip()

    if choice:
        if choice.isdigit():
            seat_count = int(choice)
        else:
            print(f"Invalid input: {choice}")
            exit(code=1)


    logger.info(f"Attemping to assign seats to {len(user_ids)} users for the license id: {license_id}")
    assign_license_seats(license_id, user_ids, seat_count)

    update_license_note_non_company_users(license_id, non_company_emails_names)


if __name__ == "__main__":
    main()