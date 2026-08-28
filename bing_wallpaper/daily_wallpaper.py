# -*- coding: utf-8 -*-
"""
Daily Wallpaper
============================================================
Rotate the Windows desktop wallpaper daily from a folder of images.
- Reads wallpaper directory from config (or prompts on first run)
- Cycles through images day by day (rotates when reaching the end)
- Sets the wallpaper via Win32 API
- Creates an ok_<timestamp>.txt run record

Usage: python daily_wallpaper.py
"""
import ctypes
import os
import json
from datetime import datetime
import sys

STATE_FILE = "wallpaper_state.json"
CONFIG_FILE = "wallpaper_config.json"


def get_script_dir():
    """Return the script/exe directory."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        return os.path.dirname(os.path.abspath(__file__))


def get_today():
    return datetime.now().strftime("%Y-%m-%d")


def get_timestamp():
    """Return a current timestamp string."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def create_ok_file(wallpaper_dir, wallpaper_file, index, total):
    """Create an ok_<timestamp>.txt file recording the run status."""
    script_dir = get_script_dir()
    timestamp = get_timestamp()
    ok_file_path = os.path.join(script_dir, f"ok_{timestamp}.txt")

    content = f"""Wallpaper updated
Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Wallpaper dir: {wallpaper_dir}
Today's wallpaper: {wallpaper_file}
Index: {index}/{total}
"""
    try:
        with open(ok_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Run record saved: {ok_file_path}")
        return True
    except Exception as e:
        print(f"⚠️ Failed to save run record: {e}")
        return False


def get_wallpaper_dir():
    """Read the wallpaper path from config; prompt & save on first run."""
    script_dir = get_script_dir()
    config_path = os.path.join(script_dir, CONFIG_FILE)

    # Try reading the JSON config
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                path = config.get('wallpaper_dir', '')
                if path and os.path.exists(path):
                    print(f"✅ Read path from config: {path}")
                    return path
                else:
                    print(f"⚠️ Config path is invalid: {path}")
        except json.JSONDecodeError:
            print("⚠️ Config file corrupted, will re-configure")
    else:
        print(f"📄 Config file not found: {config_path}, first-time config")

    # No config or invalid path: prompt the user
    while True:
        path = input("📁 Enter wallpaper directory path: ").strip().strip('"')

        if os.path.exists(path):
            config = {
                'wallpaper_dir': path,
                'last_updated': get_today()
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print(f"✅ Config saved: {config_path}")
            return path
        else:
            print(f"❌ Directory does not exist: {path}, please re-enter")


def get_start_date(wallpaper_dir):
    """Read the start date from the state JSON file."""
    state_path = os.path.join(wallpaper_dir, STATE_FILE)

    if os.path.exists(state_path):
        try:
            with open(state_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
                return state.get('start_date')
        except (json.JSONDecodeError, KeyError):
            print("⚠️ State file corrupted, will re-initialize")

    return None


def save_start_date(wallpaper_dir, start_date):
    """Save the start date to a JSON file."""
    state_path = os.path.join(wallpaper_dir, STATE_FILE)
    state = {
        'start_date': start_date,
        'last_updated': get_today()
    }
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_image_files(wallpaper_dir):
    """Return all image files in the directory, sorted by name."""
    files = []
    for f in os.listdir(wallpaper_dir):
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp')):
            files.append(f)
    files.sort()
    return files


def get_next_wallpaper(wallpaper_dir):
    """Calculate which wallpaper to use today."""
    files = get_image_files(wallpaper_dir)

    if not files:
        print("❌ No images found in wallpaper directory")
        return None, 0, 0

    total = len(files)
    today = get_today()
    today_dt = datetime.strptime(today, "%Y-%m-%d")

    # Read the start date
    start_date = get_start_date(wallpaper_dir)

    # First run: record today as the start date
    if start_date is None:
        start_date = today
        current_index = 1
        print(f"📝 First run, start date: {start_date}")
    else:
        # Calculate days since the start date
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        days_diff = (today_dt - start_dt).days
        current_index = days_diff + 1
        print(f"📅 Start: {start_date}, Today: {today}, Day {current_index}")

    # Rotate if past the total
    if current_index > total:
        current_index = ((current_index - 1) % total) + 1
        print(f"🔄 Looped, current index: {current_index}")

    # Save the start date
    save_start_date(wallpaper_dir, start_date)

    wallpaper_file = files[current_index - 1]
    wallpaper_path = os.path.join(wallpaper_dir, wallpaper_file)

    print(f"📸 Today's wallpaper: {wallpaper_file} ({current_index}/{total})")
    return wallpaper_path, current_index, total


def set_wallpaper(image_path):
    """Set the desktop wallpaper."""
    abs_path = os.path.abspath(image_path)

    SPI_SETDESKWALLPAPER = 20
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDWININICHANGE = 0x02
    SPIF_FLAGS = SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE

    try:
        ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER,
            0,
            abs_path,
            SPIF_FLAGS
        )
        print(f"✅ Wallpaper set: {os.path.basename(image_path)}")
        return True
    except Exception as e:
        print(f"❌ Failed to set wallpaper: {e}")
        return False


def main():
    print("=" * 50)
    print("🖼️  Daily Wallpaper Rotation")
    print("=" * 50)

    # Get wallpaper directory
    wallpaper_dir = get_wallpaper_dir()
    print(f"📁 Wallpaper dir: {wallpaper_dir}")

    # Get image count
    files = get_image_files(wallpaper_dir)
    print(f"📊 Total wallpapers: {len(files)}")

    # Calculate and set today's wallpaper
    wallpaper_path, current_index, total = get_next_wallpaper(wallpaper_dir)

    if wallpaper_path and os.path.exists(wallpaper_path):
        if set_wallpaper(wallpaper_path):
            # After setting, create the ok_<timestamp>.txt file
            wallpaper_file = os.path.basename(wallpaper_path)
            create_ok_file(wallpaper_dir, wallpaper_file, current_index, total)
    else:
        print("❌ Wallpaper file does not exist")

    print("=" * 50)
    print("👋 Done!")
    sys.exit(0)


if __name__ == "__main__":
    main()
