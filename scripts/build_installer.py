#!/usr/bin/env python3
"""Build the app (PyInstaller) then compile dist\\ExcelProcessor-Setup.exe (Inno Setup).

Usage:
    python scripts/build_installer.py

For a new release: bump __version__ in scripts/app_info.py, then run this.
"""

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app_info import __version__  # noqa: E402


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent

    subprocess.run([sys.executable, "scripts/build.py"], cwd=project_root, check=True)

    iscc = shutil.which("iscc")
    if not iscc:
        print("Error: iscc (Inno Setup) not found on PATH.", file=sys.stderr)
        sys.exit(1)

    subprocess.run(
        [iscc, f"/DMyAppVersion={__version__}", "installer.iss"],
        cwd=project_root,
        check=True,
    )

    print(f"\nSetup.exe ready: {project_root / 'dist' / 'ExcelProcessor-Setup.exe'}")


if __name__ == "__main__":
    main()
