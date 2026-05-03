import csv
from pathlib import Path
from modules.licenses import assign_license_seats
from modules.users import user_mail_to_id_list
from modules.logging import get_logger
from modules.config import load_script_config, get_venv_path, get_api_path
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
    return_code = run_py_stream_logged(py_script, env_vars={"ADOBE_ORG_ID": config["ORG_ID"]}, python_exe=venv_python)
    if return_code != 0:
        logger.exception(f"Error gathering Adobe data. Exiting script")
        return False
    
    assignments_path = str(app_path) + r"/files/adobe/users.csv"
    products_path = str(app_path) + r"/files/adobe/products.csv"

    license_seat_counts = {}

    # Get license seat counts
    with open(products_path, mode='r', encoding="utf-8-sig") as csvfile:
        logger.info(f"Reading {products_path}")
        reader = csv.DictReader(csvfile)
        for row in reader: 
            product = row["Product"].split(" (")[0].strip()
            total_licenses = row["Quota"].strip()
            license_id = config["PRODUCT_TO_LICENSE_ID"].get(product)
            license_seat_counts[license_id] = total_licenses
    license_id = config["PRODUCT_TO_LICENSE_ID"].get("N/A")
    license_seat_counts[license_id] = 1
    
    # Collect users per license
    license_user_emails = {}
    
    try:
        with open(assignments_path, mode='r', encoding="utf-8-sig") as csvfile:
            logger.info(f"Reading {assignments_path}")
            reader = csv.DictReader(csvfile)

            # Remove BOM
            reader.fieldnames = [name.lstrip('﻿ï»¿') for name in reader.fieldnames]
            
            for row in reader:
                product = row["Product"].split(" (")[0].strip()
                email = row["Username"].strip().lower()
                
                license_id = config["PRODUCT_TO_LICENSE_ID"].get(product)
                if not license_id:
                    logger.warning(f"Unknown product: {product}")
                    continue

                if config["company_domain"] not in email:
                    logger.warning(f'Non-company user: email:{email}, name:{row["First Name"]} {row["Last Name"]}')
                    continue

                license_user_emails.setdefault(license_id, []).append(email)
    
    except Exception as e:
        logger.exception(f"Error reading assignments file: {e}")
        return False
    
    # Convert emails to IDs and assign seats
    for license_id, email_list in license_user_emails.items():
        seat_count = license_seat_counts.get(license_id, len(email_list))
        
        user_ids = user_mail_to_id_list(email_list)
        logger.info(
            f"Attempting to assign {seat_count} seats to {len(user_ids)} users for the license id: {license_id}"
        )
        assign_license_seats(license_id, user_ids, seat_count)
    
    return True


if __name__ == "__main__":
    main()