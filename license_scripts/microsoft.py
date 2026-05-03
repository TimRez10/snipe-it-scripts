import csv
from pathlib import Path
from modules.licenses import assign_license_seats
from modules.users import user_mail_to_id_list
from modules.logging import get_logger
from modules.config import load_script_config, get_pwsh_executable, get_microsoft_credentials
from modules.runner import run_ps_stream_logged

# Get the directory and file information dynamically
script_path = Path(__file__)
app_path = script_path.parent.parent
ps_script = str(app_path) + r"/api/microsoft/getUsersForSKU.ps1"
pwsh = get_pwsh_executable()

# Load logging/config
logger = get_logger()
config = load_script_config(script_path)


def main():
    env_vars = get_microsoft_credentials()
    run_ps_stream_logged(ps_script, env_vars, pwsh)

    assignments_path = str(app_path) + r"/files/ms/LicenseAssignments.csv"
    summary_path = str(app_path) + r"/files/ms/LicenseSummary.csv"
        
    # Get license seat counts
    license_seat_counts = {}

    with open(summary_path, newline='', encoding="utf-8-sig") as csvfile:
        logger.info(f"Reading {summary_path}")
        reader = csv.DictReader(csvfile)
        for row in reader:
            sku = row["SKU"]
            total_licenses = row["TotalLicenses"]
            logger.info(f"{sku}:   {row['AssignedLicenses']} assigned, {row['UnassignedLicenses']} unassigned")

            license_id = config["PRODUCT_TO_LICENSE_ID"].get(sku)
            license_seat_counts[license_id] = total_licenses

    # Collect users per license
    license_user_emails = {}

    with open(assignments_path, newline='', encoding="utf-8-sig") as csvfile:
        logger.info(f"Reading {assignments_path}")
        reader = csv.DictReader(csvfile)
        for row in reader:
            sku = row["SKU"]
            email = row["UserPrincipalName"]

            license_id = config["PRODUCT_TO_LICENSE_ID"].get(sku)
            if not license_id:
                logger.warning(f"Unknown product: {sku}")
                continue

            license_user_emails.setdefault(license_id, []).append(email)

    # Convert emails to IDs and assign seats
    for license_id, email_list in license_user_emails.items():
        user_ids = user_mail_to_id_list(email_list)
        seat_count = license_seat_counts.get(license_id, len(user_ids))

        logger.info(f"Attemping to assign {seat_count} seats to {len(user_ids)} users for the license id: {license_id}")
        assign_license_seats(license_id, user_ids, seat_count)

if __name__ == "__main__":
    main()