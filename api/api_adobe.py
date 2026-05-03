import os
import time
import json
import csv
from common import *
import requests

USERS_OUTPUT_FILE = 'users.csv'
PRODUCTS_OUTPUT_FILE = 'products.csv'
LOGIN_URL = 'https://adminconsole.adobe.com/?trackingid=91BF4Z77&mv=in-product'
ACCOUNT_ID = os.getenv('ADOBE_ORG_ID')
if not ACCOUNT_ID:
    raise ValueError("ADOBE_ORG_ID environment variable not set.")


def get_adobe_data(api_token, mode):
    if mode == 1:
        # Get products
        item = 'products'
        accept = 'text/csv+product'
    elif mode == 2:
        # Get license status report
        item = 'users'
        accept = 'text/csv+license-status-report'
    elif mode == 3:
        # Get users
        item = 'users'
        accept = 'application/json'

    url = f'https://bps-il.adobe.io/jil-api/v2/organizations/{ACCOUNT_ID}/{item}'

    headers = {
        'Accept': accept,
        'Authorization': f'Bearer {api_token}',
        'X-Api-Key': 'ONESIE1'
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise ValueError(f"Request failed with status code {response.status_code}: {response.text}")

    return response.text


def main():
    download_dir = os.path.abspath(os.path.join(os.getcwd(), "./files/adobe"))
    os.makedirs(download_dir, exist_ok=True) 
    driver = setup_chrome(download_dir)

    try:
        # Log in with Selenium
        authenticate_to_vendor(driver, LOGIN_URL)
        print("Successfully authenticated with Selenium.")
        
        # Wait a moment for any session data to be set by JS
        time.sleep(2) 

        # Create a 'requests' session
        session = requests.Session()

        # Transfer all cookies from the Selenium browser to the requests session
        print("Transferring session cookies from Selenium to requests...")
        selenium_cookies = driver.get_cookies()
        for cookie in selenium_cookies:
            session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

        # Get API token from sessionStorage using Selenium
        script = """for (const [key, value] of Object.entries(sessionStorage)) {
            if (value.includes('"tokenValue":')) {
                const obj=JSON.parse(value);
                return obj.tokenValue;
            }
        };"""
        api_token = driver.execute_script(script)
        
        # quit Selenium
        print("Closing browser, proceeding with direct request.")
        driver.quit()
        del driver

        # Get license status report and save to CSV
        data = get_adobe_data(api_token, mode=2)
        users_output_file_location = os.path.join(download_dir, USERS_OUTPUT_FILE)
        with open(users_output_file_location, 'w', encoding='utf-8') as f:
            f.write(data)
        print(f"Successfully saved license status report data to {users_output_file_location}")

        # Get product data and save to CSV
        data = get_adobe_data(api_token, mode=1)
        product_output_file_location = os.path.join(download_dir, PRODUCTS_OUTPUT_FILE)
        with open(product_output_file_location, 'w', encoding='utf-8') as f:
            f.write(data)
        print(f"Successfully saved product data to {product_output_file_location}")

        # Get all users data and add missing users to the license status report
        data = get_adobe_data(api_token, mode=3)
        users_list = json.loads(data)
        with open(users_output_file_location, 'a', encoding='utf-8') as f:
            writer = csv.writer(f)
            for row in users_list:
                email = row['email']
                if 'products' not in row and 'firstName' in row and 'lastName' in row:
                    writer.writerow([email, row["firstName"], row["lastName"],"N/A","","",""])
        print(f"Successfully updated {users_output_file_location} with all users data.")
    
    except Exception as e:
        print(f"\n--- AN UNEXPECTED ERROR OCCURRED ---")
        print(e)
        sys.exit(1)
        
    finally:
        if 'driver' in locals():
            print("Cleaning up and closing the browser.")
            driver.quit() # type: ignore

if __name__ == "__main__":
    main()