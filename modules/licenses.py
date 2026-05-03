import requests
from requests.exceptions import RequestException
import json
from modules.config import setup_global_vars
from modules.users import get_user_email_by_id

global_config = setup_global_vars()
logger = global_config["logger"]
HEADERS = global_config["headers"]
API_URL = global_config["api_url"]


def _get_license_info(license_id: int) -> bool:
    """Helper function to get license information"""
    try:
        r = requests.get(f"{API_URL}/licenses/{license_id}", headers=HEADERS)
        logger.info(f"License ID {license_id} is named \"{r.json().get('name')}\" in ITAMS")
        return True
    except Exception as e:
        logger.critical(f"Failed to contact API: {e}")
        exit(code=1)


def _get_license_seats(license_id: int) -> list:
    """Helper function to get current seats for a license"""
    try:
        r = requests.get(f"{API_URL}/licenses/{license_id}/seats", headers=HEADERS)
    except Exception as e:
        logger.critical(f"Failed to contact API: {e}")
        exit(code=1)
    
    if r.status_code > 399:
        logger.error(f"Failed to retreive seats for license id {license_id}: {r.status_code} - {r.text}")
        return None
    
    return r.json().get("rows", [])


def get_license_seat_count(license_id: int) -> int:
    """Get the current seat count for a license"""
    return len(_get_license_seats(license_id))


def _remove_duplicate_license_seats(license_id: int, current_seats: list) -> None:
    """Helper function to remove duplicate seat assignments"""
    # Track assigned users and their seats
    user_to_seats = {}
    for seat in current_seats:
        assigned_user = seat.get("assigned_user")
        if assigned_user:
            user_id = assigned_user["id"]
            user_to_seats.setdefault(user_id, []).append(seat)

    # Remove duplicates (keep only one seat per user)
    for user_id, seats in user_to_seats.items():
        if len(seats) > 1:
            logger.info(f"Duplicate seats found for user {user_id}, unassigning {len(seats) - 1} extra seats")
            for seat in seats[1:]:
                _unassign_license_seat(license_id, seat["id"], user_id, "Unassigned duplicate by script")


def _unassign_license_seat(license_id: int, seat_id: int, user_id: int, note: str) -> None:
    """Helper function to unassign a seat"""
    payload = {
        "assigned_to": None,
        "asset_id": None,
        "notes": note
    }
    url = f"{API_URL}/licenses/{license_id}/seats/{seat_id}"
    user_email = get_user_email_by_id(user_id)
    try:
        response = requests.put(url, json=payload, headers=HEADERS)
        if response.status_code == 200:
            logger.info(f"Unassigned seat {seat_id} from {user_email}")
        else:
            logger.warning(f"Failed to unassign seat {seat_id}: {response.status_code} - {response.text}")
    except RequestException as e:
        logger.error(f"Exception occurred while unassigning seat {seat_id}: {e}")


def _assign_license_seat(license_id: int, seat_id: int, user_id: int, note: str = None) -> None:
    """Helper function to assign a seat to a user"""
    payload = {"assigned_to": user_id}
    if note:
        payload["notes"] = note
    url = f"{API_URL}/licenses/{license_id}/seats/{seat_id}"
    user_email = get_user_email_by_id(user_id)
    try:
        response = requests.put(url, json=payload, headers=HEADERS)
        if response.status_code == 200:
            logger.info(f"Successfully assigned seat {seat_id} to {user_email}")
        else:
            logger.warning(f"Failed to assign seat {seat_id} to {user_email}: {response.status_code} - {response.text}")
    except RequestException as e:
        logger.error(f"Exception occurred while assigning seat {seat_id} to {user_email}: {e}")


def _set_license_seat_count(license_id: int, seat_count: int) -> bool:
    """Helper function to set the seat count for a license"""
    patch_url = f"{API_URL}/licenses/{license_id}"
    logger.debug(f"Setting seat count to {seat_count}")
    r = requests.patch(patch_url, json={"seats": seat_count}, headers=HEADERS)
    if r.status_code > 399:
        logger.error(f"Failed to patch seat count for license id {license_id}: {r.status_code} - {r.text}")
        return False
    return True


def assign_license_seats_notes(license_id: int, user_ids_and_notes: list[tuple[int, str]], seat_count: int) -> None:
    """Assign license seats to a given list of (user_id, notes) tuples and ensure no duplicates"""
    
    # Step 0: Attempt to contact API
    _get_license_info(license_id)

    # Step 1: Get all current seats
    current_seats = _get_license_seats(license_id)
    if current_seats is None:
        return
    
    logger.debug(f"Current seat count: {len(current_seats)}")

    # Step 1a: Remove duplicates (keep only one seat per user)
    _remove_duplicate_license_seats(license_id, current_seats)

    # Recompute current assigned IDs after removing duplicates
    current_seats = _get_license_seats(license_id)
    if current_seats is None:
        return
    
    logger.debug(f"Seat count after removing duplicates: {len(current_seats)}")
    current_assigned_ids = {seat["assigned_user"]["id"] for seat in current_seats if seat["assigned_user"]}

    # Extract user IDs from tuples and create lookup for notes
    user_notes_map = {user_id: notes for user_id, notes in user_ids_and_notes}
    desired_user_ids = set(user_notes_map.keys())
    
    to_unassign = current_assigned_ids - desired_user_ids
    to_assign = desired_user_ids - current_assigned_ids

    logger.info(f"{len(to_unassign)} seats to unassign, {len(to_assign)} seats to assign")

    # Step 2: Unassign seats
    for seat in current_seats:
        assigned_user = seat.get("assigned_user")
        if assigned_user and assigned_user.get("id") in to_unassign:
            _unassign_license_seat(license_id, seat["id"], assigned_user["id"], "Unassigned by script")

    # Step 3: Set seat count (if needed)
    seat_count = int(seat_count)
    if seat_count < len(user_ids_and_notes):
        seat_count = len(user_ids_and_notes)
    if not _set_license_seat_count(license_id, seat_count):
        return

    # Step 4: Get updated seats
    current_seats = _get_license_seats(license_id)
    if current_seats is None:
        return
    
    open_seats = [seat for seat in current_seats if seat["assigned_user"] is None]
    logger.debug(f"Got number of open seats: {len(open_seats)}") 

    # Step 5: Assign new users with notes
    for user_id, seat in zip(to_assign, open_seats):
        note = user_notes_map.get(user_id)
        _assign_license_seat(license_id, seat['id'], user_id, note)

    # Step 6: Update existing assigned seats if note differs
    for seat in current_seats:
        assigned_user = seat.get("assigned_user")
        if not assigned_user:
            continue

        user_id = assigned_user.get("id")
        if user_id in desired_user_ids:
            current_note = seat.get("notes") or ""
            desired_note = user_notes_map.get(user_id) or ""
            if current_note.strip() != desired_note.strip():
                user_email = get_user_email_by_id(user_id)
                logger.info(f"Updating seat {seat['id']} note for {user_email}")
                _unassign_license_seat(license_id, seat["id"], user_id, "Changing checked-out note")
                _assign_license_seat(license_id, seat["id"], user_id, desired_note)


def assign_license_seats(license_id: int, user_ids: list[int], seat_count: int) -> None:
    """Assign license seats to a given list of user IDs and ensure no duplicates"""

    # Step 0: Attempt to contact API
    _get_license_info(license_id)

    # Step 1: Get all current seats
    current_seats = _get_license_seats(license_id)
    if current_seats is None:
        return
    
    logger.debug(f"Current seat count: {len(current_seats)}")

    # Step 1a: Remove duplicates (keep only one seat per user)
    _remove_duplicate_license_seats(license_id, current_seats)

    # Recompute current assigned IDs after removing duplicates
    current_seats = _get_license_seats(license_id)
    if current_seats is None:
        return
    
    logger.debug(f"Seat count after removing duplicates: {len(current_seats)}")
    current_assigned_ids = {seat["assigned_user"]["id"] for seat in current_seats if seat["assigned_user"]}

    desired_user_ids = set(user_ids)
    to_unassign = current_assigned_ids - desired_user_ids
    to_assign = desired_user_ids - current_assigned_ids

    logger.info(f"{len(to_unassign)} seats to unassign, {len(to_assign)} seats to assign")

    # Step 2: Unassign seats
    for seat in current_seats:
        assigned_user = seat.get("assigned_user")
        if assigned_user and assigned_user.get("id") in to_unassign:
            _unassign_license_seat(license_id, seat["id"], assigned_user["id"], "Unassigned by script")

    # Step 3: Set seat count (if needed)
    seat_count = int(seat_count)
    if seat_count < len(user_ids):
        seat_count = len(user_ids)
    if not _set_license_seat_count(license_id, seat_count):
        return

    # Step 4: Get updated seats
    current_seats = _get_license_seats(license_id)
    if current_seats is None:
        return
    
    open_seats = [seat for seat in current_seats if seat["assigned_user"] is None]
    logger.debug(f"Got number of open seats: {len(open_seats)}") 

    # Step 5: Assign new users (without notes)
    for user_id, seat in zip(to_assign, open_seats):
        _assign_license_seat(license_id, seat['id'], user_id)


def _get_license_note(license_id: int) -> str | bool:
    """Helper function to get license note"""
    r = requests.get(f"{API_URL}/licenses/{license_id}", headers=HEADERS)
    if r.status_code > 399:
        logger.error(f"Failed to get license id {license_id}: {r.status_code} - {r.text}")
        return False
    return r.json().get('notes')


def update_license_notes(license_id: int, license_note: str) -> bool:
    """Helper function to update license note"""
    patch_url = f"{API_URL}/licenses/{license_id}"
    r = requests.patch(patch_url, json={"notes": license_note}, headers=HEADERS)
    if r.status_code > 399:
        logger.error(f"Failed to update license note for license id {license_id}: {r.status_code} - {r.text}")
        return False
    logger.info(f"Updated license note for license ID {license_id}")
    return True


def update_license_note_non_company_users(license_id: int, non_company_emails_names: list[dict[str, str]]) -> bool:
    """Update license note to include non-company users"""
    logger.debug(f"Updating license note for license ID {license_id}")
    marker = "#External Users:"

    external_users_list = []
    for user in non_company_emails_names:
        if user['name']:
            external_users_list.append(f"-\t{user['name']} - {user['email']}")
        else:
            external_users_list.append(f"-\t{user['email']}")

    external_users_string = "\n#External Users:\n" + "\n".join(external_users_list)

    # Get license note
    current_note = _get_license_note(license_id) 
    if current_note is False:
        return False    
    if current_note is None:
        current_note = ""

    # Find the "#External Users" string and split
    if marker in current_note:
        # keep the first part (existing manual notes)
        base_note = current_note.split(marker)[0].rstrip()
    else:
        base_note = current_note.rstrip()

    new_note = base_note + external_users_string
    if new_note.strip() == current_note.strip():
        return True

    return update_license_notes(license_id, new_note)


def get_licenses(query_params: dict = None) -> dict | None:
    """Fetch licenses from the API with optional query parameters."""
    query_string = ""
    if query_params:
        query_string = "?" + "&".join(f"{key}={value}" for key, value in query_params.items())
    url = f"{API_URL}/licenses{query_string}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        return r.json()
    else:
        return None
    

