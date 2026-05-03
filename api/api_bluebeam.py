import os
import time
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from common import *

ACCOUNT_ID = os.getenv('BLUEBEAM_ORG_ID')
if not ACCOUNT_ID:
    raise ValueError("BLUEBEAM_ORG_ID environment variable not set.")
LOGIN_URL = 'https://app.bluebeam.com/'
ACCOUNT_PAGE_URL = f'https://app.bluebeam.com/org-admin/account/{ACCOUNT_ID}'
TAB_BUTTON_ID = 'tabs--tab--2'
TABLE_SELECTOR = r'#tabs--panel--2 > div > div.rounded-lg.border.border-solid.h-\[400px\].relative.flex.w-full.grow.flex-col.items-center.justify-start.overflow-hidden.border-light-gray > div > table'
OUTPUT_FILE = 'bluebeam_table_export.csv'

USERS_PAGE_URL = f'https://app.bluebeam.com/org-admin/users/{ACCOUNT_ID}'
EXPORT_BUTTON_SELECTOR = r'#tabs--panel--0 > div > div.flex.w-full.flex-row.items-center.justify-between > div.flex.shrink-0.flex-row.items-center.justify-end.whitespace-nowrap > button.cursor-pointer.items-center.rounded-lg.px-6.font-medium.disabled\:cursor-default.focus-visible\:outline-primary-blue.focus-visible\:outline.focus-visible\:outline-2.focus-visible\:outline-offset-2.border-none.bg-transparent.text-primary-blue.hover\:underline.disabled\:text-black\/20.disabled\:no-underline.skyline-text-button-2.min-h-\[32px\].flex.gap-2'
EXPORT_CONFIRM_BTN_ID = "orgadmin-export-users-dialog-confirm-btn"

def main():
    download_dir = os.path.abspath(os.path.join(os.getcwd(), "./files/bluebeam"))
    os.makedirs(download_dir, exist_ok=True) 
    driver = setup_chrome(download_dir)

    try:
        authenticate_to_vendor(driver, LOGIN_URL)
        driver.get(ACCOUNT_PAGE_URL)
        wait = WebDriverWait(driver, 30)

        print("Waiting for tab button")
        # use safe_click (retries on stale elements)
        if not safe_click(f"#{TAB_BUTTON_ID}", use_js=False, driver=driver, timeout=30):
            raise TimeoutError("Error: Timed out or stale when clicking tab button.")

        print("Waiting for specific table to be present in HTML")
        try:
            table_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, TABLE_SELECTOR))
            )
            print("Correct table found in HTML. Giving it 2 seconds to load data...")
            time.sleep(2) 
        except TimeoutException:
            raise TimeoutError(f"Error: Timed out waiting for table with specific selector.")
            
        print("Extracting table data...")
        try:
            table_element = driver.find_element(By.CSS_SELECTOR, TABLE_SELECTOR)
            table_html = table_element.get_attribute('outerHTML')
            tables_list = pd.read_html(table_html)
        except (ValueError, NoSuchElementException):
            raise ValueError("Error: Could not find or parse the table HTML.")

        if not tables_list:
            raise ValueError("Error: No tables were extracted from the element.")

        df = tables_list[0] 
        output_file_location = download_dir + "/" + OUTPUT_FILE
        df.to_csv(output_file_location, index=False)
        
        print("--- PART 1 SUCCESS! ---")
        print(f"Subscriptions table saved to: {output_file_location}")
        
        print("Starting user export...")
        driver.get(USERS_PAGE_URL)

        print("Waiting for export button")
        # safe click the export button (longer timeout)
        if not safe_click(EXPORT_BUTTON_SELECTOR, use_js=False, driver=driver, timeout=30):
            raise TimeoutError(f"Error: Timed out or stale when clicking export button.")

        print("Waiting for confirm button") 
        time.sleep(1)
        files_before = set(os.listdir(download_dir))
        try:
            # safe click confirm (menu dialogs can re-render)
            if not safe_click(f"#{EXPORT_CONFIRM_BTN_ID}", use_js=False, driver=driver, timeout=30):
                raise TimeoutError(f"Error: Timed out or stale when clicking confirm button.")
        except TimeoutException:
            raise TimeoutError(f"Error: Timed out waiting for confirm button.")
        
        wait_for_download(download_dir, "LicenseAssignments", files_before)

        print("--- PART 2 SUCCESS! ---")

    except Exception as e:
        print(f"\n--- AN UNEXPECTED ERROR OCCURRED ---")
        print(e)
        
    finally:
        if 'driver' in locals():
            print("Cleaning up and closing the browser.")
            driver.quit()

if __name__ == "__main__":
    main()