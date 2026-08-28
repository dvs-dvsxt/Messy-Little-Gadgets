# 🖼️ Bing Wallpaper Suite

> A small suite of **Bing wallpaper** tools: batch download Bing daily wallpapers, and rotate them as your desktop wallpaper daily.

This folder contains two standalone tools for Bing wallpapers.

---

## 🧩 Tools

### ⬇️ Bing Wallpaper Downloader — `bing_wallpaper_downloader.py`
Batch download Bing daily wallpapers from `peapix.com`.
- ⚡ Async concurrent download (aiohttp, 50 concurrent)
- 🔄 Resume: skips already-downloaded files
- 📈 Progress & speed reporting

```bash
pip install aiohttp aiofiles
python bing_wallpaper_downloader.py
```

### 🔁 Daily Wallpaper — `daily_wallpaper.py`
Rotate your Windows desktop wallpaper daily from a folder of images.
- 📁 Reads wallpaper directory from config (prompts on first run)
- 🔄 Cycles through images day by day (rotates at the end)
- 🖥️ Sets wallpaper via Win32 API
- 📄 Creates an `ok_<timestamp>.txt` run record

```bash
python daily_wallpaper.py
```

---

## 📁 Structure

```
bing_wallpaper/
├── bing_wallpaper_downloader.py   # Batch download Bing wallpapers
├── daily_wallpaper.py             # Daily wallpaper rotation
└── README.md                      # This file
```

---

## 📄 License

Part of **Messy-Little-Gadgets** (MIT License).
