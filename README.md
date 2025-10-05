# Reddit Bot with Interactive Console Interface

This project provides a Reddit scraper that extracts posts from specified subreddits, with optional AI cleaning via Groq API, and can generate audio from the text.

## Getting Started

1. The required dependencies will be checked and installed automatically when running the script for the first time. If you prefer to install them manually:
   ```
   pip install requests beautifulsoup4 edge-tts
   ```
   
   You can also run the installation script directly:
   ```
   python3 src/install.py
   ```

2. If you want to use the AI cleaning feature, you'll need a Groq API key. You can provide it during the console interface setup or add it to an `api_key.txt` file.

3. Run the console interface to configure and start the bot by using the provided shell script (recommended):
   ```
   ./run.sh
   ```
   
   This will automatically check for required dependencies and install them if needed.
   
   Alternatively, you can run the console interface directly:
   ```
   python3 src/console_interface.py
   ```
   
   Note: Use `python3` instead of `python` if you're on macOS or Linux where both Python 2 and 3 are installed.

4. Follow the prompts to configure your scraping session:
   - Choose subreddits to scrape
   - Configure audio generation
   - Select sorting options and post limits
   - Set maximum character count for posts (defaults to 1500 chars ≈ 1 minute reading time)

## Features

- Scrapes posts from multiple subreddits
- Filters posts by length (under 1500 characters)
- AI-powered text cleaning using Groq API (optional)
- Automatic hashtag generation for social media
- Automatic gender detection and tagging
- Integration with voice generation (requires voice-over.py)
- Configurable through an easy-to-use console interface

## Note
This tool respects Reddit's robots.txt and implements delays between requests to avoid overloading the servers.
