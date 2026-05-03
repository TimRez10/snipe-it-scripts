import os
import time
import sys
import shutil
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

def setup_chrome(download_dir):
    """Initializes a Chrome WebDriver with settings to auto-download files."""
    options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": download_dir, # Force files to save here
        "download.prompt_for_download": False, # Don't ask where to save
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)

    try:
        print(f"Setting download directory to: {download_dir}")
        return webdriver.Chrome(options=options)
    except Exception as e:
        print(f"Error initializing WebDriver: {e}")
        print("Please ensure ChromeDriver is installed and matches your Chrome version.")
        print("Download from: https://chromedriver.chromium.org/downloads")
        sys.exit(1)


def authenticate_to_vendor(driver, login_url):
    """Pauses the script to allow for manual user login."""
    driver.get(login_url)
    print("="*60)
    print(" ACTION REQUIRED: Please log in through the Chrome window.")
    print(" After logging in, press 'Enter' in this terminal...")
    print("="*60)
    input()
    print(f"\nLogin confirmed.")


def wait_for_download(download_dir, filename, files_before, timeout=60):
    """Waits for a file download to complete in the specified directory.
    Robust against transient/rename races and stale listings."""
    print("Download initiated. Waiting for file to complete...")
    end_time = time.time() + timeout

    while time.time() < end_time:
        files_current = set(os.listdir(download_dir))
        new_files = files_current - files_before

        if new_files:
            # prefer fully-complete files (ignore .crdownload/.tmp)
            candidates = [f for f in new_files if not f.endswith(('.crdownload', '.tmp'))]
            if not candidates:
                time.sleep(0.5)
                continue

            # pick the most-recent candidate (by mtime)
            candidates.sort(key=lambda f: os.path.getmtime(os.path.join(download_dir, f)), reverse=True)
            new_filename = candidates[0]
            new_filepath = os.path.join(download_dir, new_filename)
            print(f"Download complete! New file found: {new_filename}")

            # wait for file to actually exist and become size-stable
            last_size = -1
            stable_rounds = 0
            for _ in range(40):  # ~20s max waiting for stability
                if not os.path.exists(new_filepath):
                    time.sleep(0.25)
                    continue
                size = os.path.getsize(new_filepath)
                if size == last_size:
                    stable_rounds += 1
                else:
                    stable_rounds = 0
                    last_size = size
                if stable_rounds >= 3:
                    break
                time.sleep(0.5)

            if not os.path.exists(new_filepath):
                # file disappeared/renamed; try again in main loop
                time.sleep(0.5)
                continue

            # build target name and move with retries in case of race
            file_ext = os.path.splitext(new_filename)[1]
            renamed_filepath = os.path.join(download_dir, filename + file_ext)

            if new_filename == filename + file_ext:
                print("File already has correct name")
                return True

            for attempt in range(6):
                try:
                    if os.path.exists(renamed_filepath):
                        os.remove(renamed_filepath)
                    shutil.move(new_filepath, renamed_filepath)
                    print(f"File renamed to: {filename + file_ext}")
                    return True
                except FileNotFoundError:
                    # file was removed/renamed by browser between detection and move; retry
                    time.sleep(0.25)
                    if not os.path.exists(new_filepath):
                        break
                    continue
                except Exception as e:
                    print(f"Error moving downloaded file: {e}")
                    break

        time.sleep(0.5)

    print(f"Error: Download did not complete after {timeout} seconds.")
    return False


# helper that retries locating+clicking if DOM changes cause a stale element
def safe_click(selector, use_js=False, retries=5, timeout=5, driver=None):
    for _ in range(retries):
        try:
            elem = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            if use_js:
                driver.execute_script("arguments[0].click();", elem)
            else:
                elem.click()
            return True
        except StaleElementReferenceException:
            time.sleep(0.5)
            continue
        except TimeoutException:
            return False
    return False