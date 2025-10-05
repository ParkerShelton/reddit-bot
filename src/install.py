#!/usr/bin/env python3
"""
Installation script for Reddit Bot dependencies.
This script will check for and install any required packages that are not already installed.
"""
import subprocess
import sys
import pkg_resources
import platform
import os

def check_pip():
    """Check if pip is installed"""
    try:
        import pip
        return True
    except ImportError:
        print("pip is not installed. Installing pip...")
        try:
            subprocess.check_call([sys.executable, "-m", "ensurepip", "--upgrade"])
            return True
        except Exception as e:
            print(f"Failed to install pip: {e}")
            print("Please install pip manually: https://pip.pypa.io/en/stable/installation/")
            return False

def get_installed_packages():
    """Get a dictionary of installed packages and their versions"""
    installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
    return installed_packages

def install_package(package):
    """Install a package using pip"""
    print(f"Installing {package}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ Successfully installed {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")
        return False

def create_directory(directory_path):
    """Create a directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        print(f"Creating directory: {directory_path}")
        os.makedirs(directory_path)
        print(f"✅ Created directory {directory_path}")

def create_api_key_file():
    """Create an empty api_key.txt file if it doesn't exist"""
    # Create it in the root directory, not in src
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    api_key_path = os.path.join(root_dir, "api_key.txt")
    if not os.path.exists(api_key_path):
        print("\nCreating empty api_key.txt file...")
        try:
            with open(api_key_path, 'w') as f:
                f.write("")
            print("✅ Created api_key.txt file")
            print("\n⚠️ IMPORTANT: You need to add your Groq API key to the api_key.txt file")
            print("   Get your free API key from: https://console.groq.com/keys")
        except Exception as e:
            print(f"❌ Failed to create api_key.txt file: {e}")

def main():
    print("=" * 60)
    print("Reddit Bot - Dependency Installation")
    print("=" * 60)
    print(f"Python version: {platform.python_version()}")
    print(f"System: {platform.system()} {platform.version()}")
    print("=" * 60)

    # Check pip installation
    if not check_pip():
        return

    # Required packages from the Python files
    required_packages = {
        "requests": "For web requests",
        "beautifulsoup4": "For HTML parsing",
        "edge-tts": "For text-to-speech functionality",
    }

    installed = get_installed_packages()
    
    packages_to_install = []
    for package in required_packages:
        package_lower = package.lower()
        if package_lower not in installed:
            packages_to_install.append(package)
    
    if not packages_to_install:
        print("✅ All required packages are already installed!")
    else:
        print(f"Missing {len(packages_to_install)} packages. Installing...")
        for package in packages_to_install:
            description = required_packages.get(package, "")
            print(f"\n➤ Installing {package} - {description}")
            install_package(package)
    
    # Create required directories
    print("\nChecking required directories...")
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    create_directory(os.path.join(root_dir, "get-audio"))
    create_directory(os.path.join(root_dir, "old-posts"))
    
    # Create API key file if it doesn't exist
    create_api_key_file()
    
    print("\n" + "="*60)
    print("✅ Installation complete!")
    print("="*60)
    print("\nYou can now use the Reddit bot:")
    print("1. ./run.sh               - Run the interactive console interface (recommended)")
    print("2. python3 src/console_interface.py - Run the interactive console directly")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(os.path.join(script_dir, "voice-over.py")):
        print("\nFor manual operations:")
        print("• python3 src/voice-over.py      - Convert text posts to audio manually")
    
    if os.path.exists(os.path.join(script_dir, "clear-files.py")):
        print("• python3 src/clear-files.py     - Clean up generated files manually")
        
    print("="*60)

if __name__ == "__main__":
    main()
