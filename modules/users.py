import requests
import json
from modules.config import setup_global_vars

global_config = setup_global_vars()
logger = global_config["logger"]
HEADERS = global_config["headers"]
API_URL = global_config["api_url"]
CACHE_PATH = global_config["user_cache_path"]
user_id_cache = global_config["user_cache"]


def _fetch_user_id_from_api(email: str) -> int | None:
    """Helper function to fetch user ID from API for a given email"""
    try:
        logger.debug(f"Calling API to find a user with the email: {email}")
        resp = requests.get(f"{API_URL}/users?email={email}", headers=HEADERS)
    except Exception as e:
        logger.critical(f"Failed to contact API: {e}")
        exit(code=1)
    
    if resp.status_code > 399:
        logger.error(f"Failed to retreive user info for email {email}: {resp.status_code} - {resp.text}")
        exit(code=1)
    
    data = resp.json()
    if data.get("rows"):
        user_id = data["rows"][0]["id"]
        user_id_cache[email] = user_id
        return user_id
    else:
        logger.warning(f"User not found: {email}")
        return None


def user_mail_to_id_list(email_list: list[str]) -> list[int]:
    """Convert a list of emails to user IDs using the API"""
    result = []
    for email in email_list:
        if email in user_id_cache:
            result.append(user_id_cache[email])
            continue

        user_id = _fetch_user_id_from_api(email)
        if user_id:
            result.append(user_id)

    # Save updated cache
    with open(CACHE_PATH, "w") as f:
        json.dump(user_id_cache, f, indent=2)

    return result


def get_user_email_by_id(user_id: int) -> str | None:
    """Fetch user email from API or cache for a given user ID"""
    try:
        if user_id in user_id_cache.values():
            for email, uid in user_id_cache.items():
                if uid == user_id:
                    return email
        logger.debug(f"Calling API to find a user with the ID: {user_id}")
        resp = requests.get(f"{API_URL}/users/{user_id}", headers=HEADERS)
    except Exception as e:
        logger.critical(f"Failed to contact API: {e}")
        exit(code=1)
    
    if resp.status_code > 399:
        logger.error(f"Failed to retreive user info for ID {user_id}: {resp.status_code} - {resp.text}")
        exit(code=1)
    
    data = resp.json()
    return data.get("email")


def user_mail_to_id_dict(email_list: list[str]) -> dict[str, int]:
    """Convert a list of emails to a dict of email -> user ID using the API"""
    result = {}
    for email in email_list:
        if email in user_id_cache:
            result[email] = user_id_cache[email]
            continue

        user_id = _fetch_user_id_from_api(email)
        if user_id:
            result[email] = user_id

    # Save updated cache
    with open(CACHE_PATH, "w") as f:
        json.dump(user_id_cache, f, indent=2)

    return result


def user_mail_notes_to_id_notes(email_notes_list: list[tuple[str, str]]) -> list[tuple[int, str]]:
    """Convert a list of (email, notes) tuples to (user_id, notes) tuples using the API"""
    result = []
    
    for email, notes in email_notes_list:
        if email in user_id_cache:
            user_id = user_id_cache[email]
        else:
            user_id = _fetch_user_id_from_api(email)
        
        if user_id:
            result.append((user_id, notes))
    
    # Save updated cache
    with open(CACHE_PATH, "w") as f:
        json.dump(user_id_cache, f, indent=2)
    
    return result