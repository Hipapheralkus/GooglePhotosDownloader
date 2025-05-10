import os
import sys
import time
import csv
import datetime
import subprocess
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, SessionNotCreatedException

# Flush prints immediately for real-time feedback
sys.stdout.reconfigure(line_buffering=True)

# ─── USER CONSTANTS ────────────────────────────────────────────────────
CHROME_BIN        = r"C:\Users\{user}\Desktop\chrome-win64\chrome.exe" # Path to Chrome binary
USER_DATA_DIR     = r"C:\Users\{user}\AppData\Local\Google\Chrome for Testing\User Data" # Path to Chrome user data directory
PROFILE           = "Default" # Chrome profile name (Default, Profile 1, etc.)
CHROMEDRIVER_EXEC = r"C:\Users\{user}\Desktop\chromedriver-win64\chromedriver.exe" # Path to ChromeDriver executable

START_URL         = "https://photos.google.com/quotamanagement/large/photo/{ID}}"
CSV_PATH          = "google_photos_videos.csv"
DOWNLOAD_DIR      = os.path.join(os.getcwd(), "gp_downloads")
WAIT_TIMEOUT      = 10     # explicit Selenium waits (seconds)
DOWNLOAD_ENABLED  = True   # if False, skip download entirely
DOWNLOAD_TIMEOUT  = None   # None = wait indefinitely
DOWNLOAD_STABLE_SEC = 30   # seconds of unchanged size to deem download finished

# Ensure download directory exists
Path(DOWNLOAD_DIR).mkdir(exist_ok=True)

# ─── VERSION HELPERS ───────────────────────────────────────────────────

def wmic_file_version(path: str) -> str:
    try:
        esc = os.path.normpath(path).replace('\\', r'\\')
        out = subprocess.check_output(
            f'wmic datafile where name="{esc}" get Version /value',
            shell=True, text=True, stderr=subprocess.DEVNULL, timeout=3
        )
        for ln in out.splitlines():
            if ln.startswith('Version='):
                return ln.split('=',1)[1].strip()
    except Exception:
        pass
    return "?"

print("Chrome version:", wmic_file_version(CHROME_BIN))
try:
    print("ChromeDriver version:", subprocess.check_output([CHROMEDRIVER_EXEC, '--version'], text=True).split()[1])
except Exception:
    print("ChromeDriver version: ?")

# ─── CSV PREPARATION ───────────────────────────────────────────────────
processed_links = set()
if Path(CSV_PATH).exists():
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        processed_links = {row['link'] for row in csv.DictReader(f)}
csv_file = open(CSV_PATH, 'a', newline='', encoding='utf-8')
writer = csv.DictWriter(csv_file, fieldnames=[
    'link','filename','date','time','latitude','longitude','location','albums'
])
if not processed_links:
    writer.writeheader()

# ─── UTILITY FUNCTIONS ────────────────────────────────────────────────

def kill_chrome():
    subprocess.call('taskkill /F /IM chrome.exe /T', shell=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def wait_profile_unlock():
    lock = Path(USER_DATA_DIR) / PROFILE / 'SingletonLock'
    for _ in range(40):
        if not lock.exists():
            return
        time.sleep(0.3)
    sys.exit('Profile lock remains — close Chrome and retry.')


def wait_for_file_download(file_path: Path, timeout: int | None = DOWNLOAD_TIMEOUT) -> bool:
    tmp_path = file_path.with_suffix(file_path.suffix + '.crdownload')
    start = time.time()
    last_size = -1
    stable_since = time.time()
    while True:
        # if file exists and .crdownload is gone
        if file_path.exists() and not tmp_path.exists():
            size = file_path.stat().st_size
            if size == last_size:
                if time.time() - stable_since >= DOWNLOAD_STABLE_SEC:
                    return True
            else:
                last_size = size
                stable_since = time.time()
        else:
            stable_since = time.time()
        # handle timeout
        if timeout is not None and time.time() - start > timeout:
            return False
        time.sleep(0.5)

# ─── WEBDRIVER FACTORY ─────────────────────────────────────────────────

def build_driver() -> webdriver.Chrome:
    kill_chrome()
    wait_profile_unlock()
    opts = Options()
    opts.binary_location = CHROME_BIN
    opts.add_argument(f"--user-data-dir={USER_DATA_DIR}")
    opts.add_argument(f"--profile-directory={PROFILE}")
    opts.add_argument('--remote-debugging-port=0')
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "safebrowsing.enabled": True
    }
    opts.add_experimental_option('prefs', prefs)
    opts.add_experimental_option('excludeSwitches', ['enable-automation','enable-logging'])
    opts.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(service=Service(CHROMEDRIVER_EXEC, start_timeout=8), options=opts)
    driver.set_window_size(1280, 900)
    return driver

# ─── PER-PHOTO PROCESSOR ──────────────────────────────────────────────

def process_link(url: str) -> str | None:
    driver = build_driver()
    wait = WebDriverWait(driver, WAIT_TIMEOUT)
    actions = ActionChains(driver)
    driver.get(url)
    time.sleep(1)
    try:
        wait.until(EC.url_contains('/quotamanagement/large/photo/'))
    except TimeoutException:
        print('⚠️  Failed to load photo page; skipping.')
        driver.quit()
        return None

    # detect Next button label
    next_label = None
    for btn in driver.find_elements(By.XPATH, '//*[@aria-label]'):
        lab = (btn.get_attribute('aria-label') or '').lower()
        if 'next' in lab:
            next_label = btn.get_attribute('aria-label')
            break

    # get filename
    try:
        filename = driver.find_element(By.CSS_SELECTOR, "[aria-label^='Filename:' ]").get_attribute('aria-label').split(': ',1)[1]
    except Exception:
        filename = ''
    file_path = DOWNLOAD_DIR and Path(DOWNLOAD_DIR)/filename

    # download logic
    downloaded = False
    if DOWNLOAD_ENABLED and filename:
        if file_path.exists() and not file_path.with_suffix(file_path.suffix + '.crdownload').exists():
            downloaded = True
            print('File exists — skipping download.', flush=True)
        else:
            try:
                driver.find_element(By.XPATH, "//button[contains(@aria-label,'Download')]").click()
                print('Download started…', flush=True)
                downloaded = wait_for_file_download(file_path)
                if downloaded:
                    print('Download finished.', flush=True)
                else:
                    print('⚠️  Download timeout — skipping metadata.', flush=True)
            except Exception as e:
                print('⚠️  Download error:', e, flush=True)

    # write metadata only if downloaded (or download disabled)
    if downloaded or not DOWNLOAD_ENABLED:
        if url not in processed_links:
            def field(css, conv=lambda x: x):
                try:
                    raw = driver.find_element(By.CSS_SELECTOR, css).get_attribute('aria-label').split(': ',1)[1]
                    return conv(raw)
                except Exception:
                    return ''
            date_val = field("[aria-label^='Date taken:' ]", lambda x: datetime.datetime.strptime(x,'%b %d, %Y').strftime('%Y-%m-%d'))
            time_val = field("[aria-label^='Time taken:' ]", lambda x: datetime.datetime.strptime(x.split(',')[-1].strip(), '%I:%M %p').strftime('%H:%M:%S'))
            try:
                loc_href = driver.find_element(By.CSS_SELECTOR, "a[href*='q=loc:']").get_attribute('href')
                lat,lon = loc_href.split('q=loc:')[1].split('&')[0].split(',')
            except Exception:
                lat = lon = ''
            try:
                place = driver.find_element(By.CSS_SELECTOR, "div[data-show-alias-location='true']").text.splitlines()[0]
            except Exception:
                place = ''
            albums = []
            for ul in driver.find_elements(By.TAG_NAME,'ul'):
                prev = driver.execute_script('return arguments[0].previousElementSibling;',ul)
                while prev:
                    if prev.text.strip() == 'Albums':
                        albums = [li.text.splitlines()[0] for li in ul.find_elements(By.TAG_NAME,'li')]
                        break
                    prev = driver.execute_script('return arguments[0].previousElementSibling;', prev)
                if albums: break
            writer.writerow({'link':url,'filename':filename,'date':date_val,'time':time_val,'latitude':lat,'longitude':lon,'location':place,'albums':';'.join(albums)})
            csv_file.flush()
            processed_links.add(url)
            print('Metadata saved.', flush=True)
    else:
        print('Skipping metadata because download failed.', flush=True)

    # navigate to next
    next_url = None
    if next_label:
        try:
            driver.find_element(By.CSS_SELECTOR, f"[aria-label='{next_label}']").click()
            wait.until(EC.url_changes(url))
            next_url = driver.current_url
        except TimeoutException:
            next_url = None
    driver.quit()
    return next_url

# ─── MASTER LOOP ───────────────────────────────────────────────────────
if __name__ == '__main__':
    current_link = START_URL
    item_no = 0
    while current_link:
        item_no += 1
        print(f"===== Processing item {item_no} =====", flush=True)
        current_link = process_link(current_link)
    print('All done!', flush=True)
    csv_file.close()
