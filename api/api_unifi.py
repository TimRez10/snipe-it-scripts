
import os
import csv
from common import *

LOGIN_URL = 'https://account.ui.com/login?redirect=https%3A%2F%2Funifi.ui.com%2Fadmins-list'
TABLE_SELECTOR = '.table__1p5n8DUj'
OUTPUT_FILE = 'admins.csv'

script = """
var callback = arguments[arguments.length - 1];

caches.open('largeLists')
.then(cache => cache.match('https://cache.svc.ui.com/portal%3Aadmins'))
.then(response => {
    if (!response) {
    throw new Error('Entry not found in largeLists');
    }
    return response.json();
})
.then(data => callback(data.userList))
.catch(err => callback({ error: err.message }));
"""

def main():
    download_dir = os.path.abspath(os.path.join(os.getcwd(), "./files/unifi"))
    os.makedirs(download_dir, exist_ok=True)
    driver = setup_chrome(download_dir)

    try:
        authenticate_to_vendor(driver, LOGIN_URL)
        print("Extracting table data...")
        df = driver.execute_async_script(script)

        output_file_location = os.path.join(download_dir, OUTPUT_FILE)
        with open(output_file_location, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["email", "name"])
            writer.writeheader()

            for row in df:  # df is the list of dicts from Selenium
                writer.writerow({
                    "email": row.get("email", ""),
                    "name": row.get("name", "")
                })

        print(f"Saved {len(df)} rows to {output_file_location}")


    except Exception as e:
        print(f"\n--- AN UNEXPECTED ERROR OCCURRED ---")
        print(e)

    finally:
        if 'driver' in locals():
            print("Cleaning up and closing the browser.")
            driver.quit()


if __name__ == "__main__":
    main()