#!/usr/bin/env python3
"""
Clear Main Folder Script
========================

This script clears all files from the main folder structure while preserving directories.
It removes files from:
- ./main/in/
- ./main/out/import/
- ./main/out/temp/csv/
- ./main/out/temp/cleaned/
- ./main/out/temp/import_csv/

Usage: python clear_main_folder.py
"""

import os
import shutil
from pathlib import Path


def clear_files_in_directory(directory_path):
    """
    Clear all files in a directory while preserving subdirectories.
    
    Args:
        directory_path (str): Path to the directory to clear
    """
    if not os.path.exists(directory_path):
        print(f"⚠️  Directory does not exist: {directory_path}")
        return
    
    files_removed = 0
    dirs_preserved = 0
    
    for item in os.listdir(directory_path):
        item_path = os.path.join(directory_path, item)
        
        if os.path.isfile(item_path):
            try:
                os.remove(item_path)
                files_removed += 1
                print(f"   🗑️  Removed file: {item}")
            except Exception as e:
                print(f"   ❌ Failed to remove {item}: {str(e)}")
        elif os.path.isdir(item_path):
            dirs_preserved += 1
            print(f"   📁 Preserved directory: {item}")
    
    print(f"   ✅ Removed {files_removed} files, preserved {dirs_preserved} directories")


def clear_main_folder():
    """Clear all files from the main folder structure."""
    print("🧹 Clearing Main Folder Files")
    print("=" * 50)
    
    # Define directories to clear
    directories_to_clear = [
        "./main/in",
        "./main/out/import",
        "./main/out/temp/csv",
        "./main/out/temp/cleaned", 
        "./main/out/temp/import_csv"
    ]
    
    total_files_removed = 0
    
    for directory in directories_to_clear:
        print(f"\n📂 Clearing: {directory}")
        
        if os.path.exists(directory):
            files_before = len([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])
            clear_files_in_directory(directory)
            files_after = len([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])
            files_removed = files_before - files_after
            total_files_removed += files_removed
        else:
            print(f"   ⚠️  Directory does not exist, skipping...")
    
    print("\n" + "=" * 50)
    print("📊 CLEANUP SUMMARY")
    print("=" * 50)
    print(f"🗑️  Total files removed: {total_files_removed}")
    print("📁 All directories preserved")
    print("✅ Main folder cleanup completed!")


def main():
    """Main function to run the cleanup."""
    try:
        clear_main_folder()
    except KeyboardInterrupt:
        print("\n⚠️  Cleanup interrupted by user")
    except Exception as e:
        print(f"❌ Cleanup failed: {str(e)}")


if __name__ == "__main__":
    main()