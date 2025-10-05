import time
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys
import json

# Default Configuration
TTS_SCRIPT_NAME = "voice-over.py"  # Name of your TTS script

# Check for configuration from console_interface.py
config_json = os.environ.get("REDDIT_BOT_CONFIG", "{}")
try:
    config = json.loads(config_json)
    # Use config values or fall back to defaults
    subreddits = config.get('subreddits', ['AmITheAsshole', 'AmIOverreacting'])
    USE_AI_CLEANING = config.get('use_ai_cleaning', True)
    AUTO_GENERATE_AUDIO = config.get('auto_generate_audio', True)
    OUTPUT_FOLDER = config.get('output_folder', "get-audio")
    SORT_TYPE = config.get('sort_type', 'new')
    POST_LIMIT = config.get('limit', 25)
    MAX_CHARS = config.get('max_chars', 1500)  # New parameter for max characters
    
    print(f"Using configuration from console interface")
    
except json.JSONDecodeError:
    # Default configuration if no valid config found
    subreddits = ['AmITheAsshole', 'AmIOverreacting']
    USE_AI_CLEANING = True  # Set to False to disable AI processing
    AUTO_GENERATE_AUDIO = True  # Set to False to disable automatic audio generation
    OUTPUT_FOLDER = "get-audio"  # Folder where text files will be saved
    SORT_TYPE = 'new'
    POST_LIMIT = 25
    MAX_CHARS = 1500  # Default max characters

# API Key (reads from api_key.txt file, or falls back to environment variable)
def load_api_key():
    """Load API key from api_key.txt file or environment variable"""
    # Try to read from file first
    try:
        with open('api_key.txt', 'r') as f:
            key = f.read().strip()
            if key:
                return key
    except FileNotFoundError:
        pass
    
    # Fall back to environment variable
    return os.getenv("GROQ_API_KEY", "")

GROQ_API_KEY = load_api_key()

if not GROQ_API_KEY:
    print("⚠ Warning: No API key found. Please create 'api_key.txt' with your Groq API key or set GROQ_API_KEY environment variable.")
    print("AI cleaning will be disabled.")
    USE_AI_CLEANING = False

def generate_hashtags_with_ai(post):
    """Use AI to generate relevant hashtags for social media"""
    if not USE_AI_CLEANING or not GROQ_API_KEY:
        return ""
    
    prompt = f"""Based on this Reddit post, generate 5 or so relevant hashtags for YouTube and TikTok.
Focus on: the main topic, emotions, relationships, conflicts, and general AITA/Reddit content.
Return ONLY the hashtags separated by spaces, no explanations or numbering. Make sure everything is in LOWERCASE

Post: {post}

Hashtags:"""

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 200
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        hashtags = result['choices'][0]['message']['content'].strip()
        return hashtags
    except Exception as e:
        print(f"⚠ Hashtag generation failed: {e}")
        return ""

def clean_text_with_ai(title, content):
    """Cleans and tags a whole post (title + content) at once"""
    combined_text = f"{title}. {content}"
    
    if not USE_AI_CLEANING or not combined_text:
        return title, content
    
    prompt = f"""You are a grammar and spelling corrector. Fix ALL errors in this text:
- Correct ALL spelling mistakes
- Fix ALL grammar errors (verb tenses, subject-verb agreement, pronouns, etc.)
- Expand common abbreviations (like "2" to "to", "ur" to "your", "bro" to "brother")
- Fix punctuation errors
- Make "AIO" be "Am I overreacting"
- Make "AITA" be "Am I the asshole"
- A number followed by an M or an F should be changed to: XXM = XX male, XXF = XX female, XXm = XX male, XXf = XX female
- If the text makes it clear the speaker is **male** (e.g., says "I (21M)" or "I am a dad"), prepend the ENTIRE text with: <<MALE>> .
- If the text makes it clear the speaker is **female** (e.g., says "I (19F)" or "I am a mom"), prepend the ENTIRE text with: <<FEMALE>> .
- If gender is not clear, prepend the ENTIRE text with: <<MALE>> .
- Put the content on multiple lines so it is easier to read

IMPORTANT:
- Only insert one gender tag (at the very start).
- Keep the exact same tone, style, and meaning. Do not rewrite sentences.
- Return ONLY the corrected text with no explanations.

Text to correct:
{combined_text}"""

    try:
        return clean_with_groq(prompt)
    except Exception as e:
        print(f"⚠ AI cleaning failed: {e}, using original text")
        return content

def clean_with_groq(prompt):
    """Use Groq's free API (very fast)"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile",  # Fast and free
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 2000
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=30)
    response.raise_for_status()
    result = response.json()
    return result['choices'][0]['message']['content'].strip()

def get_random_headers():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
    ]
    
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }

session = requests.Session()

def get_post_content(permalink):
    """Get the full content of a Reddit post"""
    if not permalink:
        return None, 0
    
    print(f"Getting content from: {permalink}")
    headers = get_random_headers()
    
    try:
        response = session.get(permalink, headers=headers, timeout=30)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            post_container = soup.find('div', {'data-type': 'link'})
            if post_container:
                content_div = post_container.find('div', class_='usertext-body')
                if content_div:
                    content_p = content_div.find('div', class_='md')
                    if content_p:
                        content = content_p.get_text(separator='\n', strip=True)
                        return content, len(content)
                    else:
                        content = content_div.get_text(strip=True)
                        return content, len(content)
            
            expando = soup.find('div', class_='expando')
            if expando:
                content_div = expando.find('div', class_='usertext-body')
                if content_div:
                    content_p = content_div.find('div', class_='md')
                    if content_p:
                        content = content_p.get_text(separator='\n', strip=True)
                        return content, len(content)
            
            thing_div = soup.find('div', class_='thing', attrs={'data-type': 'link'})
            if thing_div:
                usertext = thing_div.find('div', class_='usertext-body')
                if usertext:
                    md_div = usertext.find('div', class_='md')
                    if md_div:
                        content = md_div.get_text(separator='\n', strip=True)
                        return content, len(content)
            
            return None, 0
        else:
            return None, 0
    except Exception as e:
        print(f"Error fetching content: {e}")
        return None, 0

def save_post_to_file(title, post_content, filename):
    """Save post data to a text file with AI-cleaned content"""    
    # Clean content and title with AI before saving
    if USE_AI_CLEANING:
        print(f"🤖 Cleaning title and content with AI...")
        cleaned_post = clean_text_with_ai(title, post_content)
        
        print(f"🏷️ Generating hashtags...")
        hashtags = generate_hashtags_with_ai(cleaned_post)
    else:
        cleaned_title = title
        cleaned_content = post_content
        hashtags = ""
    
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"---POST_SEPARATOR---\n")
        if USE_AI_CLEANING:
            f.write(f"{cleaned_post}\n")
        else:
            f.write(f"{cleaned_title}\n")
            f.write(f"{cleaned_content}\n")
        
        # Add hashtags section
        if hashtags:
            f.write(f"\n---HASHTAGS---\n{hashtags}\n")

def process_response(response, filename):
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            posts = soup.find_all('div', class_='thing')
            
            regular_posts = []
            for post in posts:
                author_elem = post.find('a', class_='author')
                author = author_elem.get_text() if author_elem else 'Unknown'
                
                if not any(mod_indicator in author.lower() for mod_indicator in ['mod', 'automod', 'aitamod']):
                    if not post.find('span', class_='stickied-tagline'):
                        regular_posts.append(post)
            
            posts_processed = 0
            posts_checked = 0
            
            for post in regular_posts:
                if posts_processed >= 3:
                    break
                    
                posts_checked += 1
                
                try:
                    title_elem = post.find('a', class_='title')
                    title = title_elem.get_text() if title_elem else 'No title'
                    
                    score_elem = post.find('div', class_='score unvoted')
                    if not score_elem:
                        score_elem = post.find('div', class_='score likes')
                    if not score_elem:
                        score_elem = post.find('div', class_='score dislikes')
                    score = score_elem.get_text() if score_elem else '0'
                    
                    author_elem = post.find('a', class_='author')
                    author = author_elem.get_text() if author_elem else 'Unknown'
                    
                    link_elem = post.find('a', class_='title')
                    url = link_elem.get('href') if link_elem else ''
                    
                    permalink = post.get('data-permalink', '')
                    if permalink:
                        full_permalink = f"https://old.reddit.com{permalink}"
                        
                        time.sleep(random.uniform(3, 6))
                        post_content, content_length = get_post_content(full_permalink)
                        
                        if post_content and content_length <= MAX_CHARS:  # Using MAX_CHARS from config
                            save_post_to_file(title, post_content, filename)
                            print(f"✓ Saved post: '{title}' ({content_length} chars)")
                            posts_processed += 1
                        else:
                            if content_length > MAX_CHARS:
                                print(f"✗ Skipping post '{title}' - too long ({content_length} characters)")
                            else:
                                print(f"✗ Skipping post '{title}' - no content found")
                    
                except Exception as e:
                    print(f"Error parsing post: {e}")
                    continue
            
            print(f"Checked {posts_checked} posts, saved {posts_processed} posts under {MAX_CHARS} characters")
                
        except Exception as e:
            print(f"Error parsing HTML: {e}")
            print("Response content:", response.text[:500])
    else:
        print(f"Request failed with status code: {response.status_code}")
        print("Response content:", response.text[:500])

def respectful_delay():
    time.sleep(random.uniform(15, 25))

def scrape_with_delays(urls, filename):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ai_status = f"AI Cleaning: {'ENABLED (Groq)' if USE_AI_CLEANING else 'DISABLED'}"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"REDDIT SCRAPER LOG - Started: {timestamp}\n")
        f.write(f"Subreddits: {subreddits}\n")
        f.write(f"Filter: Posts under {MAX_CHARS} characters\n")
        f.write(f"{ai_status}\n")
    
    print("Establishing session...")
    home_response = session.get('https://old.reddit.com/', headers=get_random_headers())
    print(f"Homepage status: {home_response.status_code}")
    time.sleep(random.uniform(3, 7))
    
    for url in urls:
        print(f"Scraping: {url}")
        headers = get_random_headers()
        response = session.get(url, headers=headers, timeout=30)
        process_response(response, filename)
        respectful_delay()

def generate_reddit_urls(subreddits, sort_type='new', limit=25):
    urls = []
    for subreddit in subreddits:
        url = f'https://old.reddit.com/r/{subreddit}/{sort_type}/?limit={limit}'
        urls.append(url)
    return urls

# Create get-audio folder if it doesn't exist
Path(OUTPUT_FOLDER).mkdir(exist_ok=True)

output_filename = os.path.join(OUTPUT_FOLDER, f"reddit_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

print(f"Starting scraper... Posts will be saved to: {output_filename}")
print(f"AI Cleaning: {'ENABLED (Groq)' if USE_AI_CLEANING else 'DISABLED'}")
print(f"Max character limit: {MAX_CHARS} characters")

urls = generate_reddit_urls(subreddits, SORT_TYPE, POST_LIMIT)
scrape_with_delays(urls, output_filename)

print(f"\nScraping complete! Check '{output_filename}' for saved posts.")

# Automatically run TTS script if enabled
if AUTO_GENERATE_AUDIO:
    print(f"\n{'='*80}")
    print("🎙️ Starting automatic audio generation...")
    print(f"{'='*80}\n")
    
    # Check if TTS script exists
    if os.path.exists(TTS_SCRIPT_NAME):
        try:
            # Run the TTS script
            result = subprocess.run([sys.executable, TTS_SCRIPT_NAME], check=True)
            print(f"\n{'='*80}")
            print("✅ Audio generation complete!")
            print(f"{'='*80}")
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Error running TTS script: {e}")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
    else:
        print(f"⚠ Warning: TTS script '{TTS_SCRIPT_NAME}' not found in current directory.")
        print(f"Skipping automatic audio generation.")
else:
    print(f"\n💡 Tip: Run '{TTS_SCRIPT_NAME}' to convert posts to audio!")
