import csv
from pathlib import Path
from modules.licenses import assign_license_seats_notes, update_license_note_non_company_users
from modules.users import user_mail_notes_to_id_notes
from modules.logging import get_logger
from modules.config import get_api_path, load_script_config, get_venv_path
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
    run_py_stream_logged(py_script, env_vars={"API_URL": config["API_URL"]}, python_exe=venv_python)

    assignments_path = str(app_path) + r"/files/gatemanager/users.csv"

    # Collect users
    company_emails = []
    non_company_emails_names = []

    with open(assignments_path, newline='', encoding="utf-8-sig", errors='ignore') as csvfile:
        logger.info(f"Reading {assignments_path}")
        reader = csv.DictReader(csvfile, delimiter=",")
        for row in reader:
            email = row["Email"].strip()
            if config["company_domain"] not in email:
                non_company_emails_names.append({"email":row["Email"], "name":row["Name"]})
            else:
                note = f"Role: {row["Role"]}\nDomain: {row["Domain"]}"
                company_emails.append((email,note))

    if not company_emails:
        logger.warning(f"No emails found.")
        return False

    # Convert emails to IDs and assign seats
    user_ids_and_notes = user_mail_notes_to_id_notes(company_emails)

    logger.info(f"Attemping to assign seats to {len(user_ids_and_notes)} users for the license id: {config['LICENSE_ID']}")
    assign_license_seats_notes(config["LICENSE_ID"], user_ids_and_notes, len(user_ids_and_notes))

    update_license_note_non_company_users(config["LICENSE_ID"], non_company_emails_names)

if __name__ == "__main__":
    main()