import csv
from pathlib import Path
from modules.licenses import assign_license_seats
from modules.logging import get_logger
from modules.assets import get_asset_by_serial
from modules.config import get_assignments_file, load_script_config

# Get the directory and file information dynamically
script_path = Path(__file__)

# Load logging/config
logger = get_logger()
config = load_script_config(script_path)

def main():
    # Get assignments file from user
    try:
        logger.info("Export to CSV from the following link: https://www.pdf-xchange.com/myaccount")
        logger.info("Ensure you are logged in to an account that has access to all PDFx-Change products.")
        assignments_path = get_assignments_file()
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        return False
    
    # Collect devices per license
    license_device_serials = {}
    seat_counts = {}

    with open(assignments_path, newline='', encoding="utf-8-sig") as csvfile:
        logger.info(f"Reading {assignments_path}")
        reader = csv.DictReader(csvfile, delimiter=";")
        for row in reader:
            product = row["Product"].strip()
            license_vol = row["License Volume"].strip()
            devices_string = row["Activation List"].strip()

            devices = devices_string.split(",")

            license_id = config["PRODUCT_TO_LICENSE_ID"].get(product)
            seat_counts

            if not license_id:
                logger.warning(f"Unknown product: {product}")
                continue

            seat_counts[license_id] = int(license_vol.split(' ')[0])
            license_device_serials[license_id] = set(devices)

    # Get user ids from license_device_serials
    license_user_ids = {}
    for license_id, device_list in license_device_serials.items():
        for asset_sn in device_list:
            device = get_asset_by_serial(asset_sn)
            license_user_ids.setdefault(license_id, set()).add(device["assigned_to"]["id"])

    # Assign seats
    for license_id, user_ids in license_user_ids.items():
        seat_count = seat_counts[license_id]
        logger.info(f"Attemping to assign {seat_count} seats to {len(user_ids)} users for the license id: {license_id}")
        assign_license_seats(license_id, user_ids, seat_count)


if __name__ == "__main__":
    main()