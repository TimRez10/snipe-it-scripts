from pathlib import Path
from modules.licenses import assign_license_seats, update_license_note_non_company_users
from modules.users import user_mail_to_id_list
from modules.logging import get_logger
from modules.config import load_script_config
from api.api_datto import fetch_users_from_api

# Get the directory and file information dynamically
script_path = Path(__file__)

# Load logging/config
logger = get_logger()
config = load_script_config(script_path)

def main(): 
    user_list = fetch_users_from_api(config["API_URL"])

    # Collect company users
    company_emails = []
    non_company_emails_names = []

    for user in user_list:
        if config["company_domain"] not in user["email"]:
            non_company_emails_names.append({"email":user["email"], "name":user["name"]})
        else:
            company_emails.append(user["email"])

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