#!/usr/bin/env python3
"""
Build script for creating standalone ExcelProcessor executable.

This script automates the PyInstaller build process for the Excel Processor
application, ensuring all dependencies and resources are properly bundled.

Usage:
    python build.py

The executable will be created in the dist/ directory.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime


def clean_build():
    """Remove previous build artifacts."""
    print("Cleaning previous build artifacts...")
    build_dirs = ["build", "dist"]

    # Clean main build directories
    for dir_name in build_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"  Removing {dir_name}/...")
            shutil.rmtree(dir_path)

    # Skip cleaning Python cache to avoid permission issues
    print("Skipping Python cache to avoid permission issues...")
    print("Clean complete!")


def check_dependencies():
    """Check if all required dependencies are installed."""
    print("Checking dependencies...")
    # Map package names to import names
    package_map = {
        "PyInstaller": "PyInstaller",
        "pandas": "pandas",
        "openpyxl": "openpyxl",
        "flask": "flask",
        "pystray": "pystray",
        "Pillow": "PIL",
        "requests": "requests",
        "packaging": "packaging",
    }
    missing = []

    for package, import_name in package_map.items():
        try:
            __import__(import_name)
            print(f"  [OK] {package}")
        except ImportError:
            missing.append(package)
            print(f"  [MISSING] {package}")

    if missing:
        print(f"\nError: Missing required packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt pyinstaller")
        sys.exit(1)

    print("All dependencies satisfied!")


def build_exe():
    """Build executable using PyInstaller."""
    print("\nBuilding executable with PyInstaller...")

    # Check if spec file exists
    spec_file = Path("excel_processor.spec")
    if not spec_file.exists():
        print(f"Error: Spec file {spec_file} not found!")
        sys.exit(1)

    # Run PyInstaller
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec_file),
    ]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("\nBuild failed!")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        sys.exit(1)

    print("Build successful!")


def verify_build():
    """Verify the built executable exists and get its size."""
    print("\nVerifying build...")
    exe_path = Path("dist/ExcelProcessor.exe")

    if not exe_path.exists():
        print(f"Error: Executable not found at {exe_path}")
        return False

    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"  [OK] Executable created: {exe_path}")
    print(f"  [OK] Size: {size_mb:.2f} MB")

    return True


def create_build_info():
    """Create a build info file with metadata."""
    print("\nCreating build info...")

    exe_path = Path("dist/ExcelProcessor.exe")
    size_mb = exe_path.stat().st_size / (1024 * 1024)

    # Read version from app_info.py
    version = "unknown"
    app_info_path = Path("app_info.py")
    if app_info_path.exists():
        content = app_info_path.read_text()
        for line in content.split("\n"):
            if "__version__" in line:
                version = line.split("=")[1].strip().strip("\"'")
                break

    build_info = f"""Build Information
==================

Application: Excel Processor
Version: {version}
Build Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Platform: Windows
Executable Size: {size_mb:.2f} MB

Build completed successfully!
"""

    info_path = Path("dist/BUILD_INFO.txt")
    info_path.write_text(build_info)
    print(f"  [OK] Build info created: {info_path}")


def main():
    """Main build function."""
    print("=" * 60)
    print("Excel Processor - Build Script")
    print("=" * 60)

    # Change to project root directory
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    print(f"Working directory: {script_dir}")

    # Execute build steps
    check_dependencies()
    clean_build()
    build_exe()

    if verify_build():
        create_build_info()

        print("\n" + "=" * 60)
        print("BUILD COMPLETE!")
        print("=" * 60)
        print(f"\nExecutable location: {Path('dist/ExcelProcessor.exe').absolute()}")
        print("\nTo test the executable:")
        print("  1. Navigate to dist/")
        print("  2. Double-click ExcelProcessor.exe")
        print("  3. The app should start and open in your browser")
    else:
        print("\nBuild verification failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
