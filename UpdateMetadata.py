#!/usr/bin/env python3
"""
Script: Tag videos with GPS coordinates and date/time from CSV input,
then move processed videos to a "ready_for_upload" folder next to the downloads directory.
Only processes video files (.mp4, .mov) located in a specified directory.
CSV expected format (comma-delimited):
    link,filename,date,time,latitude,longitude,location,albums

Only filename, date, time, latitude, longitude, and location are used.
"""
import os
import csv
import argparse
import subprocess
import shutil

# ANSI color codes for output
C_SUCCESS = '\033[92m'
C_FAILURE = '\033[91m'
C_END = '\033[0m'

VIDEO_EXTS = {'.mp4', '.mov'}

def format_time(raw_time):
    """
    Formats time string (HH:MM:SS). Defaults to 13:00:00 if blank.
    """
    if not raw_time or not raw_time.strip():
        return '13:00:00'
    parts = raw_time.split(':')
    parts += ['00'] * (3 - len(parts))
    return ':'.join(p.zfill(2) for p in parts)


def process_video(path, lat, lon, dt_iso, ready_dir):
    """
    Applies GPS and creation_time metadata to a video via ffmpeg,
    then moves it to the ready_for_upload directory.
    """
    tmp = path + '.tmp.mp4'
    cmd = [
        'ffmpeg', '-y', '-i', path,
        '-metadata', f'creation_time={dt_iso}',
        '-metadata', f'com.apple.quicktime.location.ISO6709=+{lat}+{lon}/',
        '-movflags', 'use_metadata_tags',
        '-map_metadata', '0',
        '-codec', 'copy', tmp
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.replace(tmp, path)
        print(f"{C_SUCCESS}✔ Tagged video: {os.path.basename(path)}{C_END}")
        # Move to ready_for_upload
        dest = os.path.join(ready_dir, os.path.basename(path))
        shutil.move(path, dest)
        print(f"{C_SUCCESS}✔ Moved to ready_for_upload: {os.path.basename(dest)}{C_END}")
    except Exception as e:
        print(f"{C_FAILURE}✖ {os.path.basename(path)}: ffmpeg or move error ({e}){C_END}")
        if os.path.exists(tmp):
            os.remove(tmp)


def geocode_location(location, max_fallbacks=3):
    """
    Placeholder for geocoding; replace with actual geocode if needed.
    """
    raise ValueError('Geocoding not implemented; please provide latitude/longitude')


def main():
    parser = argparse.ArgumentParser(description='Batch tag videos via CSV')
    parser.add_argument('-c', '--csv', required=True, help='Input CSV file path')
    parser.add_argument('-d', '--dir', default='./gp_downloads', help='Directory containing video files')
    parser.add_argument('-f', '--fallbacks', type=int, default=3, help='Geocoding fallback count')
    args = parser.parse_args()

    base_dir = args.dir
    if not os.path.isdir(base_dir):
        print(f"{C_FAILURE}✖ Directory not found: {base_dir}{C_END}")
        return

    # Determine parent directory and create ready_for_upload alongside gp_downloads
    parent_dir = os.path.dirname(os.path.abspath(base_dir))
    ready_dir = os.path.join(parent_dir, 'ready_for_upload')
    os.makedirs(ready_dir, exist_ok=True)

    with open(args.csv, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        for row in reader:
            fn = row.get('filename')
            date = row.get('date')
            raw_time = row.get('time')
            lat_str = row.get('latitude')
            lon_str = row.get('longitude')
            location = row.get('location')

            # Skip entries missing required fields
            if not fn or not date or ((not lat_str or not lon_str) and not location):
                print(f"{C_FAILURE}✖ {fn or '<no filename>'}: missing fields{C_END}")
                continue

            path = os.path.join(base_dir, fn)
            ext = os.path.splitext(path)[1].lower()

            # Skip non-video files
            if ext not in VIDEO_EXTS:
                continue

            if not os.path.isfile(path):
                print(f"{C_FAILURE}✖ {fn}: file not found{C_END}")
                continue

            # Determine coordinates
            if lat_str and lon_str:
                try:
                    lat, lon = float(lat_str), float(lon_str)
                except ValueError:
                    print(f"{C_FAILURE}✖ {fn}: invalid latitude/longitude{C_END}")
                    continue
            else:
                try:
                    lat, lon = geocode_location(location, max_fallbacks=args.fallbacks)
                except ValueError as e:
                    print(f"{C_FAILURE}✖ {fn}: geocode error ({e}){C_END}")
                    continue

            # Format timestamp and tag video
            t = format_time(raw_time)
            dt_iso = f"{date}T{t}"
            process_video(path, lat, lon, dt_iso, ready_dir)


if __name__ == '__main__':
    main()