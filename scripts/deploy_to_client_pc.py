#!/usr/bin/env python3
"""
Excel Processor - Client PC Deployment Script

Deploys the application to client PCs with automatic update capability.
Designed to be run from a shared network location.

Usage:
    python deploy_to_client_pc.py
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# Configuration
GITHUB_OWNER = "Andrew-0807"
GITHUB_REPO = "ExcelProcessor"
INSTALL_DIR = "C:\\ExcelProcessor"
SHORTCUT_NAME = "ExcelProcessor"
AUTOSTARTUP = True

def log_message(message):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def create_shortcut(target_path, shortcut_name):
    """Create desktop shortcut."""
    import winshell
    try:
        # Create desktop shortcut
        winshell.Shortcut(
            Path=f"{INSTALL_DIR}\\{SHORTCUT_NAME}.lnk",
            Target=target_path,
            Icon=target_path,
            Description=SHORTCUT_NAME
            WorkingDirectory=INSTALL_DIR
        )
        log_message(f"Created desktop shortcut for {SHORTCUT_NAME}")
        return True
    except Exception as e:
        log_message(f"Error creating shortcut: {e}")
        return False

def check_admin_privileges():
    """Check if running with admin privileges."""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception as e:
        log_message(f"Error checking admin privileges: {e}")
        return False

def deploy_to_client_pc():
    """Main deployment function."""
    log_message("Starting deployment to client PC")
    
    # Check admin privileges
    if not check_admin_privileges():
        log_message("ERROR: Admin privileges required!")
        log_message("Please run as administrator to deploy to client PC")
        return False
    
    # Create installation directory if it doesn't exist
    install_path = Path(INSTALL_DIR)
    try:
        if not install_path.exists():
            os.makedirs(install_path)
            log_message(f"Created installation directory: {install_path}")
    except Exception as e:
        log_message(f"Error creating install directory: {e}")
        return False
    
    # Get current executable path
    current_dir = Path(__file__).resolve().parent
    exe_path = current_dir / "dist" / "ExcelProcessor.exe"
    
    if not exe_path.exists():
        log_message(f"ERROR: Executable not found at {exe_path}")
        return False
    
    try:
        # Copy executable to installation directory
        target_exe_path = install_path / "ExcelProcessor.exe"
        shutil.copy2(exe_path, target_exe_path)
        log_message(f"Copied executable to: {target_exe_path}")
        
        # Create desktop shortcut
        if create_shortcut(target_exe_path, SHORTCUT_NAME):
            log_message("Desktop shortcut created successfully")
        
        # Configure Windows startup if auto-startup is enabled
        if AUTOSTARTUP:
            try:
                # Add to Windows startup folder
                startup_folder = os.path.expanduser("~") / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs"
                startup_shortcut = startup_folder / f"{SHORTCUT_NAME}.lnk"
                
                if not startup_shortcut.exists():
                    shutil.copy2(target_exe_path, startup_shortcut)
                    log_message(f"Added to Windows startup: {startup_shortcut}")
                
                log_message("Windows startup configured")
                
            except Exception as e:
                log_message(f"Error configuring Windows startup: {e}")
        
        # Create uninstaller script
        uninstaller_path = install_path / "uninstall.bat"
        uninstaller_content = f"""@echo off
echo Uninstalling {SHORTCUT_NAME}...
echo This will remove the application and its shortcuts.
echo.
timeout /t 3 > NUL
echo Uninstallation complete.
pause"""
        
        with open(uninstaller_path, 'w') as f:
            f.write(uninstaller_content)
        
        log_message("Deployment completed successfully!")
        log_message(f"Installation directory: {install_path}")
        log_message(f"Executable: {target_exe_path}")
        
        if AUTOSTARTUP:
            log_message("Auto-startup enabled - application will start with Windows")
        
        return True
        
    except Exception as e:
        log_message(f"Deployment failed: {e}")
        return False

def main():
    """Main entry point."""
    print("=" * 60)
    print("Excel Processor - Client PC Deployment")
    print("=" * 60)
    
    success = deploy_to_client_pc()
    
    if success:
        print("\n" + "=" * 60)
        print("DEPLOYMENT SUCCESSFUL!")
        print("=" * 60)
        print(f"\nApplication deployed to: {INSTALL_DIR}")
        print(f"Executable: {INSTALL_DIR}\\{SHORTCUT_NAME}.exe")
        print(f"\nDesktop shortcut: {install_path}\\{SHORTCUT_NAME}.lnk")
        
        if AUTOSTARTUP:
            print("Windows startup: Configured for auto-start")
        
        print("\nClient PCs will automatically check for updates and download new versions.")
        print("\nTo update: Run the application with --check-updates flag")
    else:
        print("\n" + "=" * 60)
        print("DEPLOYMENT FAILED!")
        print("=" * 60)

if __name__ == '__main__':
    main()