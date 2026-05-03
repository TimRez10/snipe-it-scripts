from pathlib import Path
from modules.licenses import assign_license_seats, update_license_note_non_company_users
from modules.users import user_mail_to_id_list
from modules.logging import get_logger
from modules.config import get_api_path, load_script_config, get_venv_path
from modules.runner import run_py_stream_logged
import csv

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
    run_py_stream_logged(py_script, env_vars=[], python_exe=venv_python)

    # Collect users
    assignments_path = str(app_path) + r"/files/unifi/admins.csv"
    company_emails = []
    non_company_emails_names = []

    with open(assignments_path, newline='', encoding="utf-8-sig", errors='ignore') as csvfile:
        logger.info(f"Reading {assignments_path}")
        reader = csv.DictReader(csvfile, delimiter=",")
        for row in reader:
            email = row["email"].strip()
            if config["company_domain"] not in email:
                non_company_emails_names.append({"email":row["email"], "name":row["name"]})
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