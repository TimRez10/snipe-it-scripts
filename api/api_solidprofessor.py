import os
import time
import re
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from common import *

LOGIN_URL = 'https://plt.solidprofessor.com/login'
ADMIN_URL = 'https://plt.solidprofessor.com/admin-tools/members'
TABLE_SELECTOR = '.table'
SEAT_COUNT_SELECTOR = "[data-at='member-status-span']"
OUTPUT_FILE = 'users.csv'
SEAT_COUNT_OUTPUT_FILE = 'seat_count.txt'


def main():
    download_dir = os.path.abspath(os.path.join(os.getcwd(), "./files/solidprofessor"))
    os.makedirs(download_dir, exist_ok=True) 
    driver = setup_chrome(download_dir)

    try:
        authenticate_to_vendor(driver, LOGIN_URL)
        wait = WebDriverWait(driver, 30)
        driver.get(ADMIN_URL)

        print("Waiting for specific table to be present in HTML")
        try:
            table_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, TABLE_SELECTOR))
            )
            print("Correct table found in HTML. Giving it 2 seconds to load data...")
            time.sleep(2) 
        except TimeoutException:
            print(f"Error: Timed out waiting for table with specific selector.")
            return

        print("Extracting table data...")
        try:
            table_element = driver.find_element(By.CSS_SELECTOR, TABLE_SELECTOR)
            table_html = table_element.get_attribute('outerHTML')
            tables_list = pd.read_html(table_html) # type: ignore
        except (ValueError, NoSuchElementException):
            print("Error: Could not find or parse the table HTML.")
            return

        if not tables_list:
            print("Error: No tables were extracted from the element.")
            return

        df = tables_list[0] 
        # Get seat count
        total_seats = None
        try:
            status_elem = driver.find_element(By.CSS_SELECTOR, SEAT_COUNT_SELECTOR)
            status_text = status_elem.text.strip()
            active_m = re.search(r'(\d+)\s+Active', status_text, re.I)
            inactive_m = re.search(r'(\d+)\s+Inactive', status_text, re.I)
            seats_m = re.search(r'(\d+)\s+Seats\s+Available', status_text, re.I)

            active = int(active_m.group(1)) if active_m else 0
            inactive = int(inactive_m.group(1)) if inactive_m else 0
            seats_available = int(seats_m.group(1)) if seats_m else 0

            total_seats = active + inactive + seats_available
        except NoSuchElementException:
            total_seats = None

        output_file_location = download_dir + "/" + OUTPUT_FILE
        df.to_csv(output_file_location, index=False)

        try:
            with open(download_dir + "/" + SEAT_COUNT_OUTPUT_FILE, 'w', encoding='utf-8') as file:
                file.write("Total Seats\n")
                file.write(str(total_seats))
            print(f"Successfully wrote to {SEAT_COUNT_OUTPUT_FILE}")
        except IOError as e:
            print(f"Error writing to {SEAT_COUNT_OUTPUT_FILE}: {e}")

    except Exception as e:
        print(f"\n--- AN UNEXPECTED ERROR OCCURRED ---")
        print(e)
        
    finally:
        if 'driver' in locals():
            print("Cleaning up and closing the browser.")
            driver.quit()

if __name__ == "__main__":
    main()

