import requests
import json
from modules.config import setup_global_vars

global_config = setup_global_vars()
logger = global_config["logger"]
HEADERS = global_config["headers"]
API_URL = global_config["api_url"]
CACHE_PATH = global_config["asset_cache_path"]
asset_id_cache = global_config["asset_cache"]


def _fetch_asset_from_api(sn: str) -> dict | None:
    """Helper function to fetch asset from API for a given SN"""
    try:
        logger.debug(f"Calling API to find a asset with the SN: {sn}")
        url = f"{API_URL}/hardware/byserial/{sn}"
        resp = requests.get(url, headers=HEADERS)
    except Exception as e:
        logger.critical(f"Failed to contact API: {e}")
        exit(code=1)
    
    if resp.status_code > 399:
        logger.error(f"Failed to retreive asset info for SN {sn}: {resp.status_code} - {resp.text}")
        exit(code=1)
    
    data = resp.json()
    if data.get("rows"):
        asset = data["rows"][0]
        asset_id_cache[sn] = {"id": asset["id"], "assigned_to": asset["assigned_to"]}
        return asset
    else:
        logger.warning(f"SN not found: {sn}")
        return None
    

def get_asset_by_serial(sn: str, ignore_cache: bool =False) -> dict | None:
    """Get asset by serial number."""
    sn = sn.strip()
    result = None
    if sn in asset_id_cache and not ignore_cache:
        logger.debug(f"Loading {sn} from cache.")
        result = asset_id_cache[sn]
    else:
        asset = _fetch_asset_from_api(sn)
        if asset:
            result = asset

    # Save updated cache
    with open(CACHE_PATH, "w") as f:
        json.dump(asset_id_cache, f, indent=2)
    return result


def remove_asset_from_cache(sn: str) -> None:
    """Remove asset from cache by serial number."""
    sn = sn.strip()
    if sn in asset_id_cache:
        del asset_id_cache[sn]
    logger.debug(f"Deleted {sn} from cache.")


def check_out_asset(payload: dict, asset_id: int) -> bool:
    """Check out an asset to a user."""
    r = requests.post(f"{API_URL}/hardware/{asset_id}/checkout", json=payload, headers=HEADERS)
    if r.ok:
        logger.info(f"Checked-out asset {payload["name"]} to user ID {payload["assigned_user"]}")
        return True
    else:
        logger.error(f"Failed to checkout {payload["name"]}: {r.status_code} - {r.text}")
    return False


def update_asset_notes(asset_id: int, notes: str) -> bool:
    """Update the notes of an asset."""
    patch_body = {"notes": notes}
    r = requests.patch(f"{API_URL}/hardware/{asset_id}", json=patch_body, headers=HEADERS)
    if r.ok:
        logger.info(f"Updated notes for asset ID {asset_id}")
        return True
    else:
        logger.error(f"Failed to update notes for asset ID {asset_id}: {r.status_code} - {r.text}")
    return False


def get_assets(query_params: dict = None) -> dict | None:
    """Fetch assets from the API with optional query parameters."""
    query_string = ""
    if query_params:
        query_string = "?" + "&".join(f"{key}={value}" for key, value in query_params.items())
    url = f"{API_URL}/hardware{query_string}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        return r.json()
    else:
        logger.error(f"Error: {r.status_code} {r.text}")
        return None