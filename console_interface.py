import os
import sys
import subprocess
from pathlib import Path
import json
import importlib.util

# Check for required packages
def check_package(package_name):
    """Check if a package is installed"""
    return importlib.util.find_spec(package_name) is not None

def install_package(package_name):
    """Install a package using pip"""
    print(f"Installing {package_name}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        return True
    except subprocess.CalledProcessError:
        print(f"Failed to install {package_name}. Please install it manually: pip install {package_name}")
        return False

def check_requirements():
    """Check if all required packages are installed"""
    required_packages = ["requests", "bs4"]
    missing_packages = [pkg for pkg in required_packages if not check_package(pkg)]
    
    if missing_packages:
        print("Some required packages are missing.")
        install = input("Do you want to install them now? (y/n): ").strip().lower()
        if install.startswith("y"):
            for package in missing_packages:
                if not install_package(package):
                    return False
        else:
            print("Please install the following packages manually:")
            for package in missing_packages:
                print(f"  - {package}")
            return False
    return True

def get_user_input(prompt, default=None):
    """Get input from user with a default value option"""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    else:
        return input(f"{prompt}: ").strip()

def get_boolean_input(prompt, default=True):
    """Get a yes/no input from the user"""
    default_str = "Y/n" if default else "y/N"
    response = input(f"{prompt} [{default_str}]: ").strip().lower()
    
    if not response:
        return default
    return response[0] == 'y'

def create_api_key_file(api_key):
    """Create or update the API key file"""
    with open('api_key.txt', 'w') as f:
        f.write(api_key)
    print("API key saved successfully.")

def main():
    """Main function to collect user input and run the Reddit bot"""
    # Check requirements first
    if not check_requirements():
        print("Required packages are missing. Please install them before running this script.")
        return
    print("\n" + "="*60)
    print("Reddit Post Scraper Configuration")
    print("="*60)
    
    # Get user configuration
    config = {}
    
    # Ask for subreddits
    default_subreddits = "AmITheAsshole,AmIOverreacting"
    subreddits_input = get_user_input("Enter subreddit names (comma-separated)", default_subreddits)
    config['subreddits'] = [s.strip() for s in subreddits_input.split(',')]
    
    # Ask for Groq API key
    api_key = ""
    use_existing = False
    
    # Check if api_key.txt exists
    if os.path.exists('api_key.txt'):
        use_existing = get_boolean_input("Use existing API key from api_key.txt", True)
    
    if not use_existing:
        default_api_key = ""
        api_key = get_user_input("Enter your Groq API key (or leave empty to disable AI cleaning)", default_api_key)
        if api_key:
            create_api_key_file(api_key)
    
    # Hardcode AI cleaning to always be enabled if API key exists
    config['use_ai_cleaning'] = True if api_key or use_existing else False
    
    # Ask for auto-generate audio preference
    default_audio_generation = True
    config['auto_generate_audio'] = get_boolean_input("Automatically generate audio after scraping", default_audio_generation)
    
    # Hardcode output folder to always be "get-audio"
    config['output_folder'] = "get-audio"
    
    # Create the output folder if it doesn't exist
    Path(config['output_folder']).mkdir(exist_ok=True)
    
    # Ask for sort type
    sort_options = ["new", "hot", "top", "rising"]
    print("\nSort options:")
    for i, option in enumerate(sort_options, 1):
        print(f"{i}. {option}")
    
    default_sort = "1"
    sort_choice = get_user_input("Choose sort type (1-4)", default_sort)
    try:
        sort_index = int(sort_choice) - 1
        if 0 <= sort_index < len(sort_options):
            config['sort_type'] = sort_options[sort_index]
        else:
            config['sort_type'] = "new"
    except ValueError:
        config['sort_type'] = "new"
    
    # Ask for post limit
    default_limit = "25"
    limit_input = get_user_input("Number of posts to scrape per subreddit", default_limit)
    try:
        config['limit'] = int(limit_input)
    except ValueError:
        config['limit'] = 25
        
    # Ask for maximum character count
    default_chars = "1500"
    chars_input = get_user_input("Maximum post length in characters (~1500 chars ≈ 1 minute reading time)", default_chars)
    try:
        config['max_chars'] = int(chars_input)
    except ValueError:
        config['max_chars'] = 1500
    
    print("\nConfiguration complete!")
    print("="*60)
    print("Summary:")
    print(f"• Subreddits: {', '.join(config['subreddits'])}")
    print(f"• AI Cleaning: {'Enabled' if config['use_ai_cleaning'] else 'Disabled'} (Fixed setting)")
    print(f"• Auto-generate Audio: {'Yes' if config['auto_generate_audio'] else 'No'}")
    print(f"• Output Folder: {config['output_folder']} (Fixed setting)")
    print(f"• Sort Type: {config['sort_type']}")
    print(f"• Posts Per Subreddit: {config['limit']}")
    print(f"• Maximum Character Count: {config['max_chars']} characters (~{config['max_chars'] // 1500} minute(s) reading time)")
    print("="*60)
    
    # Ask if user wants to proceed
    proceed = get_boolean_input("\nRun the scraper with these settings", True)
    
    if proceed:
        print("\nStarting Reddit scraper...")
        
        # Modify the environment variables to pass configuration
        env = os.environ.copy()
        env["REDDIT_BOT_CONFIG"] = json.dumps(config)
        
        # Call main.py with the configuration
        subprocess.run([sys.executable, "main.py"], env=env)
    else:
        print("Scraper cancelled. Run this script again to configure and start the scraper.")

if __name__ == "__main__":
    main()
