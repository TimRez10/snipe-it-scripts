import os
import time
import pandas as pd
from common import *
import requests

OUTPUT_FILE = 'users.csv'
LOGIN_URL = os.getenv('API_URL')
if not LOGIN_URL:
    raise ValueError("API_URL environment variable not set.")
DATA_URL = f"{LOGIN_URL}/cgi/gui.cgi"

def main():
    download_dir = os.path.abspath(os.path.join(os.getcwd(), "./files/gatemanager"))
    os.makedirs(download_dir, exist_ok=True) 
    driver = setup_chrome(download_dir)

    post_payload = {
        'FORMDATA': 'op=domain_accounts&subix=5&obj=jdom_04000005_28001003&rec=R'
    }

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

        # remove /admin at the end
        API_URL = LOGIN_URL.rstrip('/admin')

        # Manually add the custom headers
        x_gm_session = driver.execute_script("return sessionStorage.getItem('Ses/admin') ")
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0',
            'Accept': 'text/html, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': API_URL,
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-GM-Session': x_gm_session
        })
        
        # quit Selenium
        print("Closing browser, proceeding with direct request.")
        driver.quit()
        del driver

        # Make the direct POST request
        print(f"Making direct POST request to {DATA_URL} to fetch table data...")
        response = session.post(DATA_URL, data=post_payload)
        
        if response.status_code != 200:
            raise ValueError(f"Request failed with status code {response.status_code}")

        # Parse the HTML response with Pandas
        print("Extracting table data from response...")
        tables_list = pd.read_html(response.text)
        if not tables_list:
            raise ValueError("No tables found in the HTML response.")

        df = tables_list[0] 
        output_file_location = os.path.join(download_dir, OUTPUT_FILE)
        df.to_csv(output_file_location, index=False)
        print(f"Successfully saved user data to {output_file_location}")
    
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