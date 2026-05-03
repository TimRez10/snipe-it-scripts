import requests
from modules.config import get_knowbe4_credentials


def fetch_users_from_api(api_url) -> list:
    api_token = get_knowbe4_credentials()
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    response = requests.get(api_url+"/v1/users?per_page=200", headers=headers)
    return response.json()

def fetch_seat_count_from_api(api_url) -> int:
    api_token = get_knowbe4_credentials()
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    response = requests.get(api_url+"/v1/account", headers=headers)
    return response.json()["number_of_seats"]
