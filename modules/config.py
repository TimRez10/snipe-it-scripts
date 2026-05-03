import os
import json
import sys

from modules.logging import get_logger
from pathlib import Path


def setup_global_vars() -> dict:
    """Set up global variables and load secrets/config."""
    # Load secrets
    with open("secrets.json", "r") as f:
        config = json.load(f)

    api_key = config["SNIPEIT_API_KEY"]
    api_url = config["SNIPEIT_API_URL"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # Cache file path
    user_cache_path = "user_id_cache.json"
    asset_cache_path = "asset_id_cache.json"

    try:
        with open(user_cache_path, "r") as f:
            user_id_cache = json.load(f)
    except:
        user_id_cache = {}

    try:
        with open(asset_cache_path, "r") as f:
            asset_id_cache = json.load(f)
    except:
        asset_id_cache = {}

    # Set up default logging
    logger = get_logger()

    return {"user_cache": user_id_cache, 
            "user_cache_path": user_cache_path,
            "asset_cache": asset_id_cache,
            "asset_cache_path": asset_cache_path,
            "api_url": api_url,
            "headers": headers,
            "logger": logger}


global_config = setup_global_vars()
logger = global_config["logger"]


def get_venv_path(script_path: Path) -> Path:
    """Get the path to the Python executable in the virtual environment."""
    app_path = script_path.parent.parent
    if sys.platform == "win32":
        return app_path / "venv" / "Scripts" / "python.exe"
    elif sys.platform.startswith("linux"):
        return app_path / "venv" / "bin" / "python"
    else:
        raise OSError(f"Unsupported platform: {sys.platform}")


def get_pwsh_executable() -> str:
    """Get the path to the PowerShell executable."""
    if sys.platform == "win32":
        return "pwsh.exe"
    elif sys.platform.startswith("linux"):
        return "pwsh"
    else:
        raise OSError(f"Unsupported platform: {sys.platform}")


def get_assignments_file(file_type: str = "assignments") -> str:
    """Prompt user for the assignments file path."""
    print(f"\nPlease enter the full path to your CSV or TXT {file_type} file:")
    file_path = input("> ").strip()

    print(file_path)
    
    # Remove quotes if user pasted a path with quotes
    file_path = file_path.strip('"').strip("'")
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path.lower().endswith((".csv", ".txt")):
        logger.error(f"Invalid file type: {file_path}")
        raise ValueError("File must be a .csv or .txt file")
    
    return file_path


def load_script_config(script_path: Path) -> dict:
    """Load configuration for a specific vendor's script from app_config.json."""
    script_file = script_path.name
    folder_name = script_path.parent.name

    config_path = "app_config.json"
    
    # Extract vendor name from script file (remove .py extension)
    vendor_name = script_file.replace(".py", "")
    
    with open(config_path, "r") as f:
        config = json.load(f)
    
    # Navigate to the correct section based on folder type
    if folder_name == "license_scripts":
        section = "license"
    elif folder_name == "asset_scripts":
        section = "assets"
    elif folder_name == "custom_scripts":
        section = "custom"
    else:
        logger.error(f"Unknown folder type: {folder_name}")
        raise ValueError(f"Unknown folder type: {folder_name}")
    
    # Get the vendor-specific config
    if section not in config:
        logger.error(f"Section '{section}' not found in {config_path}")
        raise KeyError(f"Section '{section}' not found in config")
    
    if vendor_name not in config[section]:
        logger.error(f"Vendor '{vendor_name}' not found in {config_path}['{section}']")
        raise KeyError(f"Vendor '{vendor_name}' not found in config")
    
    return config[section][vendor_name] | {"company_domain": config["company_domain"]}


def _load_secrets() -> dict:
    """Helper function to load secrets from secrets.json."""
    with open("secrets.json", "r") as f:
        return json.load(f)

def _check_if_keys_exists(config: dict, keys: list[str]) -> str:
    """Helper function to check if a key exists in the config and return its value."""
    for key in keys:
        if key not in config:
            logger.error(f"Key '{key}' not found in config")
            return False

        if not config[key]:
            logger.error(f"Key '{key}' is empty in config")
            return False
    return True

def get_datto_credentials() -> tuple[str, str]:
    """ Retrieve Datto API credentials from secrets.json."""
    config = _load_secrets()
    if not _check_if_keys_exists(config, ["DATTO_API_KEY", "DATTO_API_SECRET"]):
        raise ValueError("Datto API credentials are missing or empty in secrets.json")
    api_key = config.get("DATTO_API_KEY")
    api_secret_key = config.get("DATTO_API_SECRET")
    logger.info("Retrieved Datto API credentials.")
    return api_key, api_secret_key


def get_microsoft_credentials() -> dict:
    """ Retrieve Microsoft API credentials from secrets.json."""
    config = _load_secrets()
    if not _check_if_keys_exists(config, ["MICROSOFT_API_CLIENT", "MICROSOFT_API_TENANT", "MICROSOFT_API_SECRET"]):
        raise ValueError("Microsoft API credentials are missing or empty in secrets.json")
    api_key = config.get("MICROSOFT_API_CLIENT")
    api_tenant_id = config.get("MICROSOFT_API_TENANT")
    api_secret_key = config.get("MICROSOFT_API_SECRET")
    logger.info("Retrieved MS API credentials.")
    return {"ClientId": api_key, "TenantId": api_tenant_id, "ClientSecret": api_secret_key}


def get_api_path(script_path: Path) -> str:
    """Get the expected API path for the given script."""
    script_file = script_path.name
    app_path = script_path.parent.parent
    return str(app_path) + f"/api/api_{script_file}"


def get_knowbe4_credentials() -> str:
    """ Retrieve KnowBe4 API token from secrets.json."""
    config = _load_secrets()
    if not _check_if_keys_exists(config, ["KNOWBE4_TOKEN"]):
        raise ValueError("KnowBe4 API token is missing or empty in secrets.json")
    api_token = config.get("KNOWBE4_TOKEN")
    logger.info("Retrieved KnowBe4 API token.")
    return api_token