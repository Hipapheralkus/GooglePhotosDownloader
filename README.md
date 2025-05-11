# Google Photos → Pixel 1 Migration Scripts

This repository contains scripts to streamline migrating your largest files from Google Photos to a Pixel 1 device, leveraging the unlimited original-quality storage, while preserving original metadata.

---

## 📦 Repository Contents

- **SeleniumScraper.py**
  - Navigates the Google Photos web UI via Selenium to download your largest photos and videos.
  - Logs each item's metadata (link, filename, date/time taken, GPS coordinates, location name, album list) into `google_photos_videos.csv` for later processing.

- **UpdateMetadata.py**
  - Reads `google_photos_videos.csv` and applies GPS and creation-time metadata to each video file using `ffmpeg`.
  - Moves processed files into a `ready_for_upload/` directory alongside `gp_downloads/` for easy transfer to your Pixel 1.

---

## 🚀 Why This Approach?

1. **Pixel 1 Unlimited Storage:**  Pixel 1 historically offers free original-quality backups—ideal for bulky archives.
2. **Web UI Scraping via Selenium:**  The Google Photos web interface exposes large items at `/quotamanagement/large`- we automate it to handle paging, downloads, and metadata extraction reliably.
3. **Decoupled Download & Tagging:**  Separating download (Selenium) from metadata tagging (`ffmpeg`) avoids complex browser-based metadata hacks and ensures precise timestamp/GPS application.
4. **CSV as Single Source of Truth:**  Capturing metadata in a CSV makes the workflow repeatable, auditable, and future-proof for further automation (e.g., album re-linking).

---

## ⚙️ Prerequisites

- **Python 3.x** with `selenium` installed:  `pip install selenium`
- **Chrome** and corresponding **ChromeDriver** binaries (must match version). Download both from:

  [https://googlechromelabs.github.io/chrome-for-testing/](https://googlechromelabs.github.io/chrome-for-testing/)

- **ffmpeg** installed and available on your `PATH` for metadata operations.
- A logged-in Google account in your main Chrome instance (so Selenium can reuse your session).

---

## 🛠️ Setup & Configuration

1. **Copy a large-item link:**
   - Visit [https://photos.google.com/quotamanagement/large](https://photos.google.com/quotamanagement/large) and copy the URL of the first item - e.g., `https://photos.google.com/quotamanagement/large/photo/{uniqueID}`.
   - Paste it into the `START_URL` constant in `SeleniumScraper.py`.

2. **Configure Chrome & Profile Paths:**
   - In `SeleniumScraper.py`, update:
     - `CHROME_BIN` → path to your Chrome executable
     - `USER_DATA_DIR` & `PROFILE` → to reuse your logged-in profile. You can find this by opening `chrome://version` and checking the `Profile Path`. The last segment is `PROFILE`, for example `	C:\Users\user\AppData\Local\Google\Chrome for Testing\User Data\Default` means the `USER_DATA_DIR = C:\Users\user\AppData\Local\Google\Chrome for Testing\User Data` and `PROFILE = Default`
     - `CHROMEDRIVER_EXEC` → path to matching ChromeDriver binary

3. **Download Directory:**
   - By default, downloads go to `./gp_downloads/`; adjust `DOWNLOAD_DIR` if needed.

4. **CSV Log:**
   - The first run creates `google_photos_videos.csv` with headers. Subsequent runs append only new links.

---

## ▶️ Usage Workflow

1. **Download & Log Metadata**
   ```bash
   python SeleniumScraper.py
   ```
   - Automates paging through `/quotamanagement/large`, downloads each file, and logs metadata.

2. **Tag & Prepare for Upload**
   ```bash
   python UpdateMetadata.py -c google_photos_videos.csv
   ```
   - Applies `creation_time` and `location` tags to each video via `ffmpeg`.
   - Moves tagged files into `ready_for_upload/` for side-loading onto your Pixel 1.

3. **Pixel 1 setup**
   - Create a new folder, e.g. "Big Files" on Pixel 1
   - Go to **Collections → On this device → Big Files**.
   - Turn on **Backup** to send everything to Google Photos.
   - For file removal from Google Photos, use its filename in the Google Photos search. That way you'll have only a single result, which you can put into Trash:
  `https://photos.google.com/search/{filename}`
   - Once in Trash, upload it via your Pixel 1, and when everything is confirmed working, you can permanently delete the item from Trash to reclaim space.
   - Move large files from PC to `Big Files` on your Pixel 1
   - Once it is uploaded, use Google Photos → “Free up space on this device” to remove local copies of already backed-up files. As Pixel 1 has limited storage available, it is good to remove it asap. 
---

## ⚠️ Drawbacks & Future Improvements

- **No Automatic Deletion:**  The scripts do **not** remove originals from Google Photos to avoid accidental data loss. Manual trashing is recommended once verified.
- **Album Re-linking Missing:**  While album names are logged, re-adding items to their original albums is not implemented.
- **Face-Detection Uploads Fail:**  Pixel’s face-based auto-upload won’t trigger on files side-loaded from Pixel 1; manual sorting or future scripts required.
- **Geocoding Placeholder:**  If GPS data is missing, a `geocode_location()` stub exists but needs real implementation or integration with a geocoding API.
- **Visibility of Processed Items:** Once the biggest videos are moved to Pixel 1, they no longer appear in Google Photos’ “Large photos & videos” section. Therefore, each run starts from the first link in that section (rather than resuming from the last processed one) to ensure newly large files are captured.

---

## 💡 Recommendations

- When you want to remove a file, use its filename in the Google Photos search. That way you'll have only a single result, which you can put into Trash:
  `https://photos.google.com/search/{filename}`
  Once in Trash, upload it via your Pixel 1, and when everything is confirmed working, you can permanently delete the item from Trash to reclaim space.

## 📱 Continuous Phone Backup via Pixel 1

To automatically back up new photos and videos from your main phone to Google Photos via Pixel 1:

1. Turn off automatic backup on your current phone.
2. Install [Resilio Sync](https://play.google.com/store/apps/details?id=com.resilio.sync) on both devices.
3. On your main phone:

   * Use Google Photos → “Free up space on this device” to remove local copies of already backed-up files.
   * In the Sync app, tap **Add → Add backup → Custom → DCIM/Camera**.
   * Tap **Info** and display the **QR code**.
   * In the Resilio Sync app, go to **Settings → General** and turn off **Auto Sleep**.
   * Disable battery optimization for Resilio Sync in Android App settings so synchronization runs continuously.
4. On your Pixel 1:

   * Scan the QR code.
   * Disable “Selective sync” so that all files synchronize.
   * In the Resilio Sync app, go to **Settings → General** and turn off **Auto Sleep**.
   * Disable battery optimization for Resilio Sync in Android App settings so synchronization runs continuously.
5. On Pixel 1, open Google Photos:

   * Go to **Collections → On this device → Camera**.
   * Turn on **Backup** to send everything to Google Photos.
6. On your PC, connect your main phone and open the `\DCIM\Camera\.sync\IgnoreList` (a pre-defined existing file after you set up Resilio Sync folder) and add:

   ```
   .trashed*
   .pending*
   ```

   This prevents syncing of temporary or trashed files, so only real photos and videos are synchronized.
7. You can go to [https://photos.google.com/search/\_tra\_](https://photos.google.com/search/_tra_) to check newly added Photos/Videos and observe if everything works
8. You can leave your Pixel 1 in charger constantly, so that the Sync happens all the time without any interaction.
---

## 🤝 Contributing

Feel free to create enhancements, particularly:
- Automating album re-linking
- Safe deletion of Google Photos items post-verification
- Automatically move files from PC to Pixel 1 -> check periodically if files were uploaded -> remove them from Pixel 1 to make space -> repeat
