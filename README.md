# 🧰 Messy-Little-Gadgets

> A collection of small, handy Python utilities — random little tools for everyday tasks.

**Messy-Little-Gadgets** is a growing collection of miscellaneous Python scripts and tools. Each script is self-contained and solves a simple, practical problem.

---

## 🧩 Included Tools

### 🌳 Directory Tree Analyzer — `directory_tree_analyzer.py`
Analyze a directory with a detailed tree view and rich statistics.
- 🌳 Recursive colored directory tree
- 📊 File/dir count, total size
- 📁 Extension stats (Top 15 with size & percentage)
- 📂 Depth distribution (per-level bar charts)
- 📦 Size bucket distribution (<1KB ~ >1GB)
- 🐘 Top 15 largest files
- 🕳️ Deepest directories

```bash
python directory_tree_analyzer.py
```

### 📊 Resource Monitor — `resource_monitor.py`
Monitor the **Top 10 memory & CPU** consumers, refreshing every 30 seconds.
- 🔝 Memory Top 10 & CPU Top 10 (process / PID / usage / bar)
- 💾 Total memory, CPU usage, core counts
- 🎨 Color-coded usage bars

```bash
python resource_monitor.py
```

### 🔍 Port Checker — `port_checker.py`
Check whether a port is occupied, find the occupying process, and optionally force-kill it.
- 🛡️ UAC elevation (run as admin)
- 🔍 Detect port occupancy (bulk query: `80, 443, 8000-8010`)
- 🕵️ Find occupying process (name / PID / command line)
- 💀 Force-kill the process (with confirmation)
- 🚫 System-critical process protection

```bash
python port_checker.py
```

### 🔄 Directory Sync — `directory_sync.py`
A universal directory synchronization tool.
- 🔁 **One-way / Two-way** sync modes
- 🔍 **MD5-based** change detection
- ⏱️ **Periodic** checking (default 5s)
- ⚙️ **Manual input or env vars** configuration (`DIRSYNC_SRC/DST/MODE/INTERVAL`)

### 🎵 Music Downloader — `music_downloader.py`
A simple Tkinter GUI tool to search and download music from an online source.
- 🔍 **Search** songs by keyword
- ⬇️ **Download** a song by its ID
- 🔥 **Hot songs** list browsing
- 📂 **Custom save path** via file dialog

### 🔐 Argon2 Password Hasher — `argon2_password_hasher.py`
A secure password hashing utility using **Argon2id** (2025 recommended parameters).
- 🧂 **Auto salt** generation
- 💾 **Hash** passwords (Argon2id format)
- ✔️ **Verify** passwords
- 🔄 **Rehash check** for parameter updates

---

## 🖼️ Bing Wallpaper

A self-contained sub-suite for Bing wallpaper tools (in the `bing_wallpaper/` folder):
- **Bing Wallpaper Downloader** — batch download Bing daily wallpapers (async, resume)
- **Daily Wallpaper** — daily desktop wallpaper rotation from a folder

```bash
cd bing_wallpaper
python bing_wallpaper_downloader.py   # download Bing wallpapers
python daily_wallpaper.py             # rotate desktop wallpaper daily
```

See `bing_wallpaper/README.md` for details.

---

## 📁 Project Structure

```
Messy-Little-Gadgets/
├── directory_tree_analyzer.py   # Directory tree analyzer
├── resource_monitor.py          # Memory/CPU Top 10 monitor
├── port_checker.py              # Port occupancy checker
├── directory_sync.py            # Directory sync tool
├── music_downloader.py          # Music download GUI tool
├── argon2_password_hasher.py    # Argon2 password hasher
├── image_resolution_scanner.py  # Image resolution scanner
├── bing_wallpaper/              # 🖼️ Bing wallpaper tools
│   ├── bing_wallpaper_downloader.py
│   ├── daily_wallpaper.py
│   └── README.md
└── README.md                    # This document
```

---

## 📄 License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## 🙏 Note

> Each gadget is independent and minimal. More little tools will be added over time. Feel free to use them in your own projects.
