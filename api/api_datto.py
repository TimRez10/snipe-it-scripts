import requests
from modules.config import get_datto_credentials

def get_account_users(api_url, access_token, page=0, max_results=250):
    print("Fetching account users...")
    full_url = f"{api_url}/api/v2/account/users"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Swagger defines 'page' and 'max' as query parameters
    query_params = {
        "page": page,
        "max": max_results
    }

    try:
        response = requests.get(
            full_url,
            headers=headers,
            params=query_params
        )
            
        response.raise_for_status()
        print("Users fetched successfully.")
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"API Request failed: {e}")
        return None
    

def get_oauth_token(api_url, api_key, api_secret_key):
    print("Generating OAuth token...")
    full_url = f"{api_url.rstrip('/')}/auth/oauth/token"
    
    basic_auth = ('public-client', 'public')    
    form_data = {
        "grant_type": "password",
        "username": api_key,
        "password": api_secret_key
    }

    try:
        response = requests.post(
            full_url, 
            auth=basic_auth, 
            data=form_data
        )
        response.raise_for_status()
        print("Token generated successfully.")
        return response.json().get("access_token")
        
    except requests.exceptions.RequestException as e:
        print(f"Token generation failed: {e}")
        return None

def fetch_users_from_api(api_url):
    api_key, api_secret_key = get_datto_credentials()
    access_token = get_oauth_token(api_url, api_key, api_secret_key)
    if not access_token:
        print("Failed to obtain access token.")
        return

    users_data = get_account_users(api_url, access_token)
    if not users_data:
        print("Failed to retrieve users.")
        return
    
    user_list = []
    for user in users_data.get('users'):
        if user.get('status') != 'active':
            continue
        username = user['firstName'] + " " + user['lastName']
        user_list.append({"email": user['email'], "name": username})
    return user_list
