"""
Script to update monitor assignments based on Datto data.
The script reads a CSV file mapping users to monitor serial numbers,
checks the ITAMS system for existing monitor assets, and assigns unassigned monitors
to the appropriate users, while respecting a list of ignored manufacturers and serial numbers.

The format of the CSV file is expected to have the following 2 columns:
- Last User: The Windows username of the last user who had the monitor assigned.
  - Example: COMPANY_DOMAIN\jdoe
- Connected Monitor SNs: Comma-separated manufaturer codes + serial numbers of connected monitors.
  - Example: DEL-ABC123,DEL-XYZ789
"""

import csv
from pathlib import Path
from modules.users import user_mail_to_id_dict
from modules.config import get_assignments_file, load_script_config
from modules.assets import get_asset_by_serial, remove_asset_from_cache, check_out_asset
from modules.logging import get_logger

# Get the directory and file information dynamically
script_path = Path(__file__)

# Load logging, config
logger = get_logger()
config = load_script_config(script_path)
ignored_manufacturers = config["ignored_manufacturers"]
ignored_SNs = config["ignored_SNs"]
logger.debug("Loaded config")

def load_datto_data():
    # Get assignments file from user
    try:
        assignments_path = get_assignments_file("monitor assignments")
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        return False
    
    # Collect user-asset SNs assignments
    email_to_assets = {}

    with open(assignments_path, newline='', encoding="utf-8-sig", errors='ignore') as csvfile:
        logger.debug(f"Reading {assignments_path}")
        reader = csv.DictReader(csvfile, delimiter=",")
        for row in reader:
            user_email=row["Last User"].split("\\")[1] + config["company_domain"]
            monitors=row["Connected Monitor SNs"].split(",")
            if monitors:
                email_to_assets[user_email] = monitors
    return email_to_assets


def map_users_to_monitors(email_to_assets: dict):
    unique_monitors = set()
    email_to_user_id = user_mail_to_id_dict(email_to_assets.keys())
    user_id_to_assets = {}
    for email, monitors in email_to_assets.items():
        unique_monitors.update(monitors)
        user_id = email_to_user_id.get(email)
        if not user_id:
            logger.warning(f"User with email {email} not found in ITAMS. Skipping their monitors.")
            continue
        user_id_to_assets[user_id] = monitors

    logger.info(f"Found {len(email_to_user_id)} users with a total of {len(unique_monitors)} unique monitors to process.")

    current_user_id_to_assets = {}
    for monitor in unique_monitors:
        # Exclude monitors we are ignoring
        try:
            sn = monitor.split("-")[1]
            manufac = monitor.split("-")[0]
        except:
            logger.error(f"Invalid monitor: {monitor}")
            continue

        if manufac in ignored_manufacturers:
            logger.info(f"Ignoring {manufac} monitors for now...")
            continue
        if sn in ignored_SNs:
            logger.info(f"Ignoring {sn}...")
            continue
        
        # Check if monitor exists and is unassigned
        asset = get_asset_by_serial(sn)
        if not asset:
            logger.warning(f"Monitor {monitor} with SN {sn} not found in ITAMS. Skipping...")
            continue
        assigned_to = asset["assigned_to"]
        if assigned_to and assigned_to != "None":
            logger.info(f"Monitor {monitor} with SN {sn} is already assigned to {assigned_to["name"]}. Skipping...")
            continue
        # Map current monitor assignment to user
        current_user_id_to_assets.setdefault(assigned_to["id"], []).append(monitor)

    


def main():
    email_to_assets = load_datto_data()
    user_id_to_assets = map_users_to_monitors(email_to_assets)

    for user_id, monitor_list in user_id_to_assets:
        if not monitor_list:
            continue
        logger.debug(f"Attemping to assign monitors {", ".join(monitor_list)} to user {user_id}")
        for monitor in monitor_list:
            if not monitor:
                continue
            if monitor[:3] in ignored_manufacturers:
                logger.info(f"Ignoring {monitor[:3]} monitors for now...")
                continue

            try:
                sn = monitor.split("-")[1]
            except:
                logger.error(f"Invalid monitor: {monitor}")
                continue
            if sn in ignored_SNs:
                logger.info(f"Ignoring {sn}...")
                continue

            asset = get_asset_by_serial(sn)
            
            if asset:  # Update existing
                current_assignee = asset["assigned_to"]
                asset_id = asset["id"]
                logger.debug(f"{monitor} (ID: {asset_id}) currently assigned to: {current_assignee}")
                if current_assignee != "None" and current_assignee:
                    logger.info(f"Asset {monitor} (ID: {asset_id}) is already assigned to {current_assignee["name"]} (ID: {current_assignee["id"]}). Skipping...")
                    if current_assignee["id"] != user_id:
                        logger.warning(f"Assignment conflict for {monitor}: Assigned to {current_assignee["name"]} in ITAMS, Datto has user: {user_id}")
                        remove_asset_from_cache(sn)
                    continue
                payload = {
                    "status_id": 8,
                    "checkout_to_type": "user",
                    "assigned_user": user_id,
                    "name": monitor
                }
                check_out_asset(payload, asset_id)
            else:
                logger.warning(f"{monitor} does not exist in ITAMS.")
            
if __name__ == "__main__":
    main()