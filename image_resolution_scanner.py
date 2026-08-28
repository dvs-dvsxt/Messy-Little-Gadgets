# -*- coding: utf-8 -*-
"""
Image Resolution Scanner
============================================================
Scans all images in a folder, extracts resolution info
(width, height, file size, format, mode, aspect ratio),
and exports results + statistics to a JSON file.

Features:
- Multi-threaded scanning (ThreadPoolExecutor)
- Per-image resolution & metadata extraction
- Aggregate statistics (formats, resolutions, total pixels/size)
- Progress reporting (every 100 images)
- Exports to JSON

Usage: python image_resolution_scanner.py
"""
import os
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
from datetime import datetime
import time
from pathlib import Path


class ImageResolutionScanner:
    def __init__(self, folder_path, output_json="image_resolutions.json", max_workers=16):
        """
        Initialize the image resolution scanner.

        Args:
            folder_path: folder containing images
            output_json: output JSON file path
            max_workers: number of worker threads
        """
        self.folder_path = Path(folder_path)
        self.output_json = output_json
        self.max_workers = max_workers
        self.results = []
        self.stats = {
            "total_images": 0,
            "processed_images": 0,
            "failed_images": 0,
            "image_formats": {},
            "resolutions": {}
        }
        self.lock = threading.Lock()
        self.supported_formats = {'.jpg'}

    def get_image_files(self):
        """Get all image files in the folder."""
        image_files = []
        for ext in self.supported_formats:
            image_files.extend(self.folder_path.glob(f'*{ext}'))
            image_files.extend(self.folder_path.glob(f'*{ext.upper()}'))
        return image_files

    def process_image(self, image_path):
        """
        Process a single image and extract resolution info.

        Args:
            image_path: path to the image file

        Returns:
            dict: image info including resolution metadata
        """
        try:
            # Open image with PIL to get dimensions
            with Image.open(image_path) as img:
                width, height = img.size
                file_size = os.path.getsize(image_path)  # bytes
                file_size_kb = file_size / 1024  # KB
                file_size_mb = file_size_kb / 1024  # MB

                # Get image format
                img_format = img.format if img.format else 'Unknown'

                # Get image mode (RGB, RGBA, L, etc.)
                img_mode = img.mode

                result = {
                    "filename": image_path.name,
                    "filepath": str(image_path),
                    "width": width,
                    "height": height,
                    "resolution": f"{width}x{height}",
                    "total_pixels": width * height,
                    "file_size_bytes": file_size,
                    "file_size_kb": round(file_size_kb, 2),
                    "file_size_mb": round(file_size_mb, 2),
                    "format": img_format,
                    "mode": img_mode,
                    "aspect_ratio": round(width / height, 3) if height > 0 else 0
                }

                # Update statistics (thread-safe)
                with self.lock:
                    self.stats["processed_images"] += 1

                    # Count image formats
                    if img_format not in self.stats["image_formats"]:
                        self.stats["image_formats"][img_format] = 0
                    self.stats["image_formats"][img_format] += 1

                    # Count resolutions
                    resolution_key = f"{width}x{height}"
                    if resolution_key not in self.stats["resolutions"]:
                        self.stats["resolutions"][resolution_key] = 0
                    self.stats["resolutions"][resolution_key] += 1

                return result

        except Exception as e:
            with self.lock:
                self.stats["failed_images"] += 1
                self.stats["total_images"] = len(self.image_files)
            print(f"Failed to process: {image_path.name} - {str(e)}")
            return {
                "filename": image_path.name,
                "filepath": str(image_path),
                "error": str(e),
                "status": "failed"
            }

    def scan(self):
        """Start scanning all images."""
        print(f"Scanning folder: {self.folder_path}")
        start_time = time.time()

        # Get all image files
        self.image_files = self.get_image_files()
        self.stats["total_images"] = len(self.image_files)

        if not self.image_files:
            print("No image files found!")
            return

        print(f"Found {len(self.image_files)} image(s), processing with {self.max_workers} threads...")

        # Process with thread pool
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_file = {executor.submit(self.process_image, img_path): img_path
                              for img_path in self.image_files}

            # Process completed tasks
            for idx, future in enumerate(as_completed(future_to_file), 1):
                img_path = future_to_file[future]
                try:
                    result = future.result()
                    if result:
                        self.results.append(result)
                        # Print progress every 100 images
                        if idx % 100 == 0 or idx == len(self.image_files):
                            processed = self.stats["processed_images"] + self.stats["failed_images"]
                            print(f"Progress: {processed}/{len(self.image_files)} processed")
                except Exception as e:
                    print(f"Error processing task: {img_path.name} - {str(e)}")
                    with self.lock:
                        self.stats["failed_images"] += 1

        # Generate final statistics
        self.generate_statistics()

        # Save JSON results
        self.save_to_json()

        elapsed_time = time.time() - start_time
        print(f"\nScan complete! Time elapsed: {elapsed_time:.2f} seconds")
        print(f"Processed: {self.stats['processed_images']} image(s)")
        print(f"Failed: {self.stats['failed_images']} image(s)")
        print(f"Results saved to: {self.output_json}")

    def generate_statistics(self):
        """Generate aggregate statistics."""
        total_pixels = sum([r.get("total_pixels", 0) for r in self.results if "total_pixels" in r])
        total_size_mb = sum([r.get("file_size_mb", 0) for r in self.results if "file_size_mb" in r])

        self.stats.update({
            "total_pixels": total_pixels,
            "total_size_mb": round(total_size_mb, 2),
            "total_size_gb": round(total_size_mb / 1024, 2),
            "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "folder_path": str(self.folder_path),
            "thread_count": self.max_workers
        })

    def save_to_json(self):
        """Save results to a JSON file."""
        output_data = {
            "statistics": self.stats,
            "images": self.results
        }

        with open(self.output_json, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"JSON file saved: {self.output_json}")


def main():
    # Configuration - change these to your own paths
    folder_path = input("Enter image folder path: ").strip()
    output_json = "image_resolutions.json"
    thread_count = 16

    # Check folder exists
    if not os.path.exists(folder_path):
        print(f"Error: folder path does not exist - {folder_path}")
        return

    # Create the scanner and run
    scanner = ImageResolutionScanner(
        folder_path=folder_path,
        output_json=output_json,
        max_workers=thread_count
    )

    scanner.scan()

    print("\nProgram finished!")
    print(f"View detailed results in: {output_json}")


if __name__ == "__main__":
    main()
