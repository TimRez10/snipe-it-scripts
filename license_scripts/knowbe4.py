from pathlib import Path
from api.api_knowbe4 import *
from modules.licenses import assign_license_seats, get_license_seat_count
from modules.users import user_mail_to_id_list
from modules.logging import get_logger
from modules.config import load_script_config

# Get the directory and file information dynamically
script_path = Path(__file__)

# Load logging/config
logger = get_logger()
config = load_script_config(script_path)

def main():
    users_json = fetch_users_from_api(config["API_URL"])

    # Collect users
    company_emails = []
    for user in users_json:
        email = user["email"]

        if config["company_domain"] not in email:
            logger.warning(f'Non-company user: email:{user["email"]}, name:{user["first_name"]} {user["last_name"]}')
        else:
            company_emails.append(email)
    
    if not company_emails:
        logger.warning(f"No emails found.")
        return False

    # Convert emails to IDs and assign seats
    user_ids = user_mail_to_id_list(company_emails)
    seat_count = fetch_seat_count_from_api(config["API_URL"])

    print(f"Enter seat count for KnowBe4 (leave blank for {seat_count}):")
    choice = input("> ").strip()

    if choice:
        if choice.isdigit():
            seat_count = int(choice)
        else:
            print(f"Invalid input: {choice}")
            return False


    logger.info(f"Attemping to assign seats to {len(user_ids)} users for the license id: {config["LICENSE_ID"]}")
    assign_license_seats(config["LICENSE_ID"], user_ids, seat_count)


if __name__ == "__main__":
    main()