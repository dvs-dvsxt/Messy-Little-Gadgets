# -*- coding: utf-8 -*-
"""
Bing Wallpaper Downloader
============================================================
Batch download Bing daily wallpapers from peapix.com.
- Async concurrent download (aiohttp)
- Resume: skips already-downloaded files
- Progress & stats reporting

Usage: python bing_wallpaper_downloader.py
"""
import re
import os
import time
import asyncio
import aiohttp
import aiofiles
from urllib.parse import urlparse

# Global state
downloaded_urls = set()
downloaded_ids = set()
semaphore = None
print_lock = asyncio.Lock()


def load_existing_files(download_dir="bing_images"):
    """Load existing files to avoid re-downloading."""
    global downloaded_urls, downloaded_ids
    if not os.path.exists(download_dir):
        return

    for filename in os.listdir(download_dir):
        if filename.endswith('.jpg'):
            # Extract ID from filename
            match = re.search(r'(\d{5})', filename)
            if match:
                downloaded_ids.add(int(match.group(1)))
            downloaded_urls.add(filename)

    print(f"Loaded {len(downloaded_ids)} existing images")


async def download_image(session, url, download_dir="bing_images"):
    """Download and save an image asynchronously."""
    if url in downloaded_urls:
        return None

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://peapix.com/'
        }

        async with session.get(url, headers=headers, timeout=30) as resp:
            if resp.status != 200:
                return None

            # Check content size
            content_length = resp.headers.get('content-length')
            if content_length and int(content_length) < 5 * 1024:
                return None

            # Generate filename and path
            filename = os.path.basename(urlparse(url).path)
            filepath = os.path.join(download_dir, filename)

            # Skip if file already exists
            if os.path.exists(filepath):
                downloaded_urls.add(url)
                return filepath

            # Stream download and save
            async with aiofiles.open(filepath, 'wb') as f:
                async for chunk in resp.content.iter_chunked(8192):  # 8KB per chunk
                    await f.write(chunk)

            # Validate file size (reject error pages)
            if os.path.getsize(filepath) < 5 * 1024:
                os.remove(filepath)
                return None

            downloaded_urls.add(url)
            return filepath

    except Exception as e:
        return None


async def process_one_page(session, page_id, download_dir="bing_images"):
    """Process a single page: extract the image URL and download it."""
    # Skip if already downloaded
    if page_id in downloaded_ids:
        return "skipped"

    page_url = f"https://peapix.com/bing/{page_id}"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        # Get page HTML
        async with session.get(page_url, headers=headers, timeout=15) as resp:
            if resp.status != 200:
                return None
            html = await resp.text()

        # Extract image URL
        pattern = r'<img[^>]+src="(https://img\.peapix\.com/[^"]+_1280\.jpg)"'
        matches = re.findall(pattern, html)

        if not matches:
            return None

        img_url = matches[0]
        original_url = img_url.replace("_1280", "")

        # Skip if URL already downloaded
        if original_url in downloaded_urls:
            return "skipped"

        # Show download status
        async with print_lock:
            print(f"[{page_id}] 📥 Downloading...")

        # Download the image
        result = await download_image(session, original_url, download_dir)

        if result:
            downloaded_ids.add(page_id)
            async with print_lock:
                filename = os.path.basename(result)
                file_size = os.path.getsize(result) / 1024
                print(f"[{page_id}] ✅ Saved: {filename} ({file_size:.1f}KB)")
        else:
            async with print_lock:
                print(f"[{page_id}] ❌ Download failed")

        return result

    except asyncio.TimeoutError:
        async with print_lock:
            print(f"[{page_id}] ⏰ Timeout")
        return None
    except Exception as e:
        async with print_lock:
            print(f"[{page_id}] ❌ Error: {str(e)[:30]}")
        return None


async def worker(session, task_id, download_dir, results):
    """Worker coroutine controlled by the semaphore."""
    async with semaphore:
        result = await process_one_page(session, task_id, download_dir)
        results[task_id] = result


async def async_batch_download(start_id=51418, end_id=56807, max_concurrent=50, download_dir="bing_images"):
    """Main async batch download function."""
    os.makedirs(download_dir, exist_ok=True)

    load_existing_files(download_dir)

    global semaphore
    semaphore = asyncio.Semaphore(max_concurrent)

    total = end_id - start_id + 1
    print("=" * 60)
    print(f"📊 Task: {start_id} -> {end_id} ({total} items)")
    print(f"⚡ Concurrency: {max_concurrent}")
    print(f"📁 Save dir: {download_dir}")
    print(f"💾 Existing: {len(downloaded_ids)}")
    print("=" * 60)
    print()

    start_time = time.time()
    results = {}
    tasks = list(range(start_id, end_id + 1))

    connector = aiohttp.TCPConnector(
        limit=max_concurrent * 2,
        limit_per_host=max_concurrent,
        ttl_dns_cache=300
    )
    timeout = aiohttp.ClientTimeout(total=30, connect=10)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        task_list = [
            worker(session, task_id, download_dir, results)
            for task_id in tasks
        ]

        batch_size = 100
        completed = 0

        for i in range(0, len(task_list), batch_size):
            batch = task_list[i:i + batch_size]
            await asyncio.gather(*batch, return_exceptions=True)

            completed += len(batch)
            elapsed = time.time() - start_time
            speed = completed / elapsed if elapsed > 0 else 0

            async with print_lock:
                print(f"\n{'='*60}")
                print(f"📈 Progress: {completed}/{total} ({completed/total*100:.1f}%)")
                print(f"⚡ Speed: {speed:.1f} items/sec")
                print(f"⏱️  Elapsed: {elapsed:.1f}s")
                print(f"{'='*60}\n")

    # Stats
    success_count = 0
    skipped_count = 0
    failed_ids = []

    for task_id, result in results.items():
        if result == "skipped":
            skipped_count += 1
        elif result:
            success_count += 1
        else:
            failed_ids.append(task_id)

    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print("📊 Download summary:")
    print(f"  ✅ Success: {success_count}")
    print(f"  ⏭️  Skipped (exists): {skipped_count}")
    print(f"  ❌ Failed: {len(failed_ids)}")
    if failed_ids:
        print(f"  🔴 Failed IDs (first 20): {failed_ids[:20]}")
    print(f"  ⏱️  Total time: {elapsed:.1f}s")
    print(f"  📈 Avg speed: {total/elapsed:.1f} items/sec")
    print(f"  📁 Save dir: {os.path.abspath(download_dir)}")
    print("=" * 60)


def batch_download(start_id=51418, end_id=56807, max_concurrent=50, download_dir="bing_images"):
    """Synchronous entry point."""
    asyncio.run(async_batch_download(
        start_id=start_id,
        end_id=end_id,
        max_concurrent=max_concurrent,
        download_dir=download_dir
    ))


if __name__ == "__main__":
    batch_download(
        start_id=51418,
        end_id=56807,
        max_concurrent=50,
        download_dir="bing_images"
    )
