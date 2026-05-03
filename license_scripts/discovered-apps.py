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
ps_script = str(app_path) + r"/api/microsoft/getUsersOfDiscoveredApps.ps1"
pwsh = get_pwsh_executable()

# Load logging/config
logger = get_logger()
config = load_script_config(script_path)

def main():
    env_vars = get_microsoft_credentials()
    run_ps_stream_logged(ps_script, env_vars, pwsh)

    assignments_path = str(app_path) + r"/files/ms/Windows_DiscoveredApps_MultiApp.csv"

    # Collect users per license
    license_user_emails = {}

    with open(assignments_path, newline='', encoding="utf-8-sig") as csvfile:
        logger.info(f"Reading {assignments_path}")
        reader = csv.DictReader(csvfile)

        for row in reader:
            product = row["AppName"]
            email = row["Email"]
            if not email:
                continue

            product_to_license = config["PRODUCT_TO_LICENSE_ID"]
            license_id = None

            for key, lid in product_to_license.items():
                if key.startswith("*"):
                    match_string = key[1:]
                    if match_string.lower() in product.lower():
                        license_id = lid
                        break
                else:
                    if key.lower() == product.lower():
                        license_id = lid
                        break

            if not license_id:
                logger.warning(f"Unknown product: {product}")
                continue

            license_user_emails.setdefault(license_id, []).append(email)

    # Convert emails to IDs and assign seats
    for license_id, email_list in license_user_emails.items():
        user_ids = list(set(user_mail_to_id_list(email_list)))

        logger.info(f"Attemping to assign seats to {len(user_ids)} users for the license id: {license_id}")
        assign_license_seats(license_id, user_ids, len(user_ids))

if __name__ == "__main__":
    main()