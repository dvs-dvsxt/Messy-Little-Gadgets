# -*- coding: utf-8 -*-
"""
Universal Directory Sync Tool
============================================================
Features:
1. Periodically (default 5s) checks source directory via MD5 hash
2. Compares hash values; if a file was modified (hash mismatch),
   updates the target file
3. Supports ONE-WAY / TWO-WAY sync modes
4. Configurable via MANUAL INPUT or ENVIRONMENT VARIABLES

============================================================
Config priority: Manual Input > Environment Variables

Method 1 - Manual input (recommended, most flexible):
    Run the script and follow the prompts. Just press Enter
    to use the default values.

Method 2 - Environment variables (silent/automation):
    Set these variables before running (no manual input):
      DIRSYNC_SRC     = source directory path
      DIRSYNC_DST     = target directory path
      DIRSYNC_MODE    = oneway / twoway
      DIRSYNC_INTERVAL= seconds (default 5)

    Windows CMD example:
        set DIRSYNC_SRC=D:/src
        set DIRSYNC_DST=D:/dst
        set DIRSYNC_MODE=oneway
        set DIRSYNC_INTERVAL=5
        python sync.py

    PowerShell example:
        $env:DIRSYNC_SRC = "D:/src"
        $env:DIRSYNC_DST = "D:/dst"
        $env:DIRSYNC_MODE = "oneway"
        $env:DIRSYNC_INTERVAL = "5"
        python sync.py
============================================================
Usage: Run the script. Press Ctrl+C to stop.
"""

import os
import sys
import time
import hashlib
import shutil
import datetime
from pathlib import Path

# ============== Defaults ==============
DEFAULT_MODE = "oneway"          # oneway / twoway
DEFAULT_INTERVAL = 5             # seconds

# Environment variable names
ENV_SRC = "DIRSYNC_SRC"
ENV_DST = "DIRSYNC_DST"
ENV_MODE = "DIRSYNC_MODE"
ENV_INTERVAL = "DIRSYNC_INTERVAL"

# State cache file (stores last hashes for change detection)
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".dir_sync_state.json")


# ============== Utility Functions ==============

def log(msg, level="INFO"):
    """Print log message with timestamp."""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")


def get_file_md5(filepath):
    """Compute MD5 hash of a file."""
    md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            # Read in chunks to avoid high memory usage
            for chunk in iter(lambda: f.read(65536), b""):
                md5.update(chunk)
        return md5.hexdigest()
    except Exception as e:
        log(f"Hash failed: {filepath} -> {e}", "ERROR")
        return None


def scan_directory(root_dir):
    """
    Recursively scan a directory.
    Returns {relative_path: {"md5":..., "size":...}}
    Relative paths use "/" separator.
    """
    result = {}
    root = Path(root_dir)
    for root_path, dirs, files in os.walk(root):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for fname in files:
            full_path = os.path.join(root_path, fname)
            rel_path = os.path.relpath(full_path, root).replace("\\", "/")
            try:
                md5 = get_file_md5(full_path)
                size = os.path.getsize(full_path)
                result[rel_path] = {"md5": md5, "size": size}
            except Exception as e:
                log(f"Scan failed: {full_path} -> {e}", "ERROR")
    return result


def load_state():
    """Load the last saved hash state."""
    import json
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"State file read failed: {e}", "WARNING")
    return {}


def save_state(state):
    """Save the current hash state."""
    import json
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log(f"State file save failed: {e}", "ERROR")


def copy_file(src_file, dst_file):
    """Copy a single file to the target location."""
    try:
        # Ensure target directory exists
        os.makedirs(os.path.dirname(dst_file), exist_ok=True)
        shutil.copy2(src_file, dst_file)
        return True
    except Exception as e:
        log(f"Copy failed: {src_file} -> {dst_file} : {e}", "ERROR")
        return False


def sync_one_way(src_dir, dst_dir):
    """
    One-way sync: only copy/update from src -> dst.
    Does NOT delete any file in the target (even if removed from source).
    Returns: (new_count, updated_count)
    """
    new_count = 0
    changed_count = 0
    current_state = scan_directory(src_dir)

    for rel_path, file_info in current_state.items():
        src_full = os.path.join(src_dir, rel_path.replace("/", "\\"))
        dst_full = os.path.join(dst_dir, rel_path.replace("/", "\\"))

        if not os.path.exists(dst_full):
            # Target does not exist -> new file
            if copy_file(src_full, dst_full):
                log(f"[NEW] {rel_path}")
                new_count += 1
        else:
            # Target exists -> compare hash
            dst_md5 = get_file_md5(dst_full)
            if dst_md5 == file_info["md5"]:
                # Target matches source, skip
                continue
            else:
                # Hash mismatch, update target (source wins)
                if copy_file(src_full, dst_full):
                    log(f"[UPDATED] {rel_path} (hash mismatch)")
                    changed_count += 1

    return new_count, changed_count


def sync_two_way(dir_a, dir_b):
    """
    Two-way sync: synchronize both directories with each other.
    Returns counts of all operations.
    """
    a_b_new = 0
    a_b_up = 0
    b_a_new = 0
    b_a_up = 0
    deleted = 0

    state_a = scan_directory(dir_a)
    state_b = scan_directory(dir_b)

    # 1. A -> B sync (copy from A to B)
    for rel_path, file_info in state_a.items():
        src_full = os.path.join(dir_a, rel_path.replace("/", "\\"))
        dst_full = os.path.join(dir_b, rel_path.replace("/", "\\"))

        if not os.path.exists(dst_full):
            if copy_file(src_full, dst_full):
                log(f"[A->B NEW] {rel_path}")
                a_b_new += 1
        else:
            dst_md5 = get_file_md5(dst_full)
            if dst_md5 != file_info["md5"]:
                if copy_file(src_full, dst_full):
                    log(f"[A->B UPDATED] {rel_path}")
                    a_b_up += 1

    # 2. B -> A sync (copy from B to A)
    for rel_path, file_info in state_b.items():
        src_full = os.path.join(dir_b, rel_path.replace("/", "\\"))
        dst_full = os.path.join(dir_a, rel_path.replace("/", "\\"))

        if not os.path.exists(dst_full):
            if copy_file(src_full, dst_full):
                log(f"[B->A NEW] {rel_path}")
                b_a_new += 1
        else:
            dst_md5 = get_file_md5(dst_full)
            if dst_md5 != file_info["md5"]:
                if copy_file(src_full, dst_full):
                    log(f"[B->A UPDATED] {rel_path}")
                    b_a_up += 1

    # 3. Delete orphan files (only in two-way mode)
    # Delete files in A that do not exist in B
    for rel_path in list(state_a.keys()):
        if rel_path not in state_b:
            try:
                full_path = os.path.join(dir_a, rel_path.replace("/", "\\"))
                if os.path.exists(full_path):
                    os.remove(full_path)
                    log(f"[DELETED A] {rel_path}")
                    deleted += 1
            except Exception as e:
                log(f"Delete failed: {rel_path} -> {e}", "ERROR")

    # Delete files in B that do not exist in A
    for rel_path in list(state_b.keys()):
        if rel_path not in state_a:
            try:
                full_path = os.path.join(dir_b, rel_path.replace("/", "\\"))
                if os.path.exists(full_path):
                    os.remove(full_path)
                    log(f"[DELETED B] {rel_path}")
                    deleted += 1
            except Exception as e:
                log(f"Delete failed: {rel_path} -> {e}", "ERROR")

    return a_b_new, a_b_up, b_a_new, b_a_up, deleted


def get_config():
    """
    Get configuration.
    Priority: Manual Input > Environment Variables.
    Returns: (src_dir, dst_dir, sync_mode, interval)
    """
    print("=" * 60)
    print("Directory Sync Tool")
    print("=" * 60)

    src = os.environ.get(ENV_SRC, "").strip()
    dst = os.environ.get(ENV_DST, "").strip()
    mode = os.environ.get(ENV_MODE, "").strip().lower()
    interval_str = os.environ.get(ENV_INTERVAL, "").strip()

    # Check if environment variables are fully configured (silent mode)
    env_configured = bool(src and dst)

    if env_configured:
        # Use environment variable config
        if not mode:
            mode = DEFAULT_MODE
        if not interval_str:
            interval = DEFAULT_INTERVAL
        else:
            try:
                interval = int(interval_str)
            except ValueError:
                log(f"Environment variable {ENV_INTERVAL} is not a valid number: {interval_str}, using default {DEFAULT_INTERVAL}", "WARNING")
                interval = DEFAULT_INTERVAL

        src_dir = src
        dst_dir = dst
        sync_mode = mode
        log("Environment variables detected, silent mode enabled")
    else:
        # Manual input mode
        print("\n[ Configure directories ]")

        # Source directory (required)
        while True:
            src_input = input("Source directory (required): ").strip()
            if src_input:
                src_dir = src_input
                break
            print("Source directory cannot be empty!")

        # Target directory (required)
        while True:
            dst_input = input("Target directory (required): ").strip()
            if dst_input:
                dst_dir = dst_input
                break
            print("Target directory cannot be empty!")

        # Sync mode
        mode_input = input(f"Sync mode (oneway/twoway) [default: {DEFAULT_MODE}]: ").strip().lower()
        if mode_input in ("oneway", "1"):
            sync_mode = "oneway"
        elif mode_input in ("twoway", "2"):
            sync_mode = "twoway"
        else:
            sync_mode = DEFAULT_MODE

        # Sync interval
        interval_input = input(f"Sync interval (seconds) [default: {DEFAULT_INTERVAL}]: ").strip()
        if interval_input:
            try:
                interval = int(interval_input)
                if interval <= 0:
                    raise ValueError
            except ValueError:
                log(f"Invalid interval: {interval_input}, using default {DEFAULT_INTERVAL}", "WARNING")
                interval = DEFAULT_INTERVAL
        else:
            interval = DEFAULT_INTERVAL

    # Validate mode
    if sync_mode not in ("oneway", "twoway"):
        log(f"Invalid sync mode: {sync_mode}, using default {DEFAULT_MODE}", "WARNING")
        sync_mode = DEFAULT_MODE

    return src_dir, dst_dir, sync_mode, interval


def main():
    log("=" * 60)
    log("Directory Sync Script Started")
    log("=" * 60)

    # Get configuration
    src_dir, dst_dir, sync_mode, interval = get_config()

    mode_text = "One-way (src -> dst)" if sync_mode == "oneway" else "Two-way (mutual)"
    log(f"Source directory: {src_dir}")
    log(f"Target directory: {dst_dir}")
    log(f"Sync mode: {mode_text}")
    log(f"Check interval: {interval} seconds")
    log("=" * 60)

    # Check if source directory exists
    if not os.path.exists(src_dir):
        log(f"Source directory does not exist: {src_dir}", "ERROR")
        sys.exit(1)

    # Create target directory if it does not exist
    if not os.path.exists(dst_dir):
        log(f"Target directory does not exist: {dst_dir}, will create it", "WARNING")
        os.makedirs(dst_dir, exist_ok=True)

    # Load last state
    state = load_state()
    is_first_run = not state
    if is_first_run:
        log("First run, performing full sync...")

    try:
        while True:
            try:
                if sync_mode == "oneway":
                    # One-way sync
                    new_count, up_count = sync_one_way(src_dir, dst_dir)

                    if new_count or up_count:
                        log(f"One-way sync done: NEW {new_count}, UPDATED {up_count}")
                    else:
                        log("One-way sync done: no changes")

                else:  # twoway
                    # Two-way sync
                    abn, abu, ban, bau, dcount = sync_two_way(src_dir, dst_dir)

                    if abn or abu or ban or bau or dcount:
                        log(f"Two-way sync done: A->B NEW {abn}, A->B UPDATED {abu}, B->A NEW {ban}, B->A UPDATED {bau}, DELETED {dcount}")
                    else:
                        log("Two-way sync done: no changes")

                # Save current state
                current_state = scan_directory(src_dir)
                save_state(current_state)

            except KeyboardInterrupt:
                raise
            except Exception as e:
                log(f"Sync error: {e}", "ERROR")

            # Wait for next cycle
            time.sleep(interval)

    except KeyboardInterrupt:
        log("\nCtrl+C received, script stopped")
        sys.exit(0)


if __name__ == "__main__":
    main()
