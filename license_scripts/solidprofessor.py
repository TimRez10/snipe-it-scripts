import csv
from pathlib import Path
from modules.licenses import assign_license_seats
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

    assignments_path = str(app_path) + r"/files/solidprofessor/users.csv"
    seat_count_file = str(app_path) + r"/files/solidprofessor/seat_count.txt"

    with open(seat_count_file, 'r') as f:
        f.readline()
        second_line = f.readline()
        seat_count = int(second_line)

    # Collect users
    user_emails = []

    with open(assignments_path, newline='', encoding="utf-8", errors='ignore') as csvfile:
        logger.info(f"Reading {assignments_path}")
        reader = csv.DictReader(csvfile, delimiter=",")
        for row in reader:
            email = row["Email (Click to sort ascending)"].strip()
            if config["company_domain"] not in email:
                continue
            user_emails.append(email)

    if not user_emails:
        logger.warning(f"No emails found.")
        return False

    # Convert emails to IDs and assign seats
    user_ids = user_mail_to_id_list(user_emails)

    logger.info(f"Attemping to assign {seat_count} seats to {len(user_ids)} users for the license id: {config["LICENSE_ID"]}")
    assign_license_seats(config["LICENSE_ID"], user_ids, seat_count)

if __name__ == "__main__":
    main()