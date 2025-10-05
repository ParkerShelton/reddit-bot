"""
Convert Reddit posts from text file to AI voice audio files
Uses Microsoft Edge TTS (completely free, no API key needed)
"""
import edge_tts
import asyncio
import re
from pathlib import Path
import glob
import os
import shutil

# Configuration
INPUT_FOLDER = "get-audio"  # Folder containing text files
OUTPUT_FOLDER = "audio_posts"
ARCHIVE_FOLDER = "old-posts"  # Folder to move processed files to
VOICE = "en-US-AriaNeural"  # Female voice (natural sounding)
# Other good voices:
# "en-US-GuyNeural" - Male
# "en-US-JennyNeural" - Female
# "en-GB-SoniaNeural" - British Female
# "en-AU-NatashaNeural" - Australian Female

def extract_voice_and_text(text):
    voice = VOICE  # default

    # Look for gender markers anywhere in the text
    if "<<MALE>>" in text:
        voice = "en-US-GuyNeural"
    elif "<<FEMALE>>" in text:
        voice = "en-US-JennyNeural"

    # Remove ALL markers so they never get spoken
    text = re.sub(r"<<(MALE|FEMALE)>>", "", text).strip()
    
    return voice, text

def parse_reddit_posts(filename):
    """Extract posts from the text file"""
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    posts = []
    
    # Split by the custom separator
    sections = content.split('---POST_SEPARATOR---')
    
    print(f"   DEBUG: Split into {len(sections)} sections")
    
    for idx, section in enumerate(sections):
        section = section.strip()
        
        print(f"   DEBUG: Processing section {idx}, length: {len(section)}")
        
        # Skip empty sections or header
        if not section:
            print(f"   DEBUG: Section {idx} is empty, skipping")
            continue
            
        if 'REDDIT SCRAPER LOG' in section:
            print(f"   DEBUG: Section {idx} is header, skipping")
            continue
        
        # Split into lines and remove empty ones
        lines = [line.strip() for line in section.split('\n') if line.strip()]
        
        print(f"   DEBUG: Section {idx} has {len(lines)} lines")
        
        if not lines:
            print(f"   DEBUG: Section {idx} has no lines, skipping")
            continue
        
        # Find where to stop (hashtags or original content)
        content_lines = []
        for line in lines:
            if '---HASHTAGS---' in line or '[ORIGINAL CONTENT' in line:
                break
            # Skip metadata lines
            if any(kw in line for kw in ['ORIGINAL LENGTH:', 'CLEANED LENGTH:', 'CONTENT LENGTH:']):
                continue
            content_lines.append(line)
        
        print(f"   DEBUG: Section {idx} has {len(content_lines)} content lines")
        
        if len(content_lines) < 2:  # Need at least title + some content
            print(f"   DEBUG: Section {idx} doesn't have enough content (need 2+ lines)")
            continue
        
        # First line is title (with gender marker), rest is body
        title = content_lines[0]
        body = ' '.join(content_lines[1:])
        
        posts.append({
            'title': title,
            'content': body
        })
        print(f"  ✓ Found post {len(posts)}: {title[:70]}...")
    
    print(f"   DEBUG: Total posts found: {len(posts)}")
    return posts

async def text_to_speech(text, output_file, voice=VOICE):
    """Convert text to speech using Edge TTS"""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

async def process_posts(posts, output_folder):
    """Convert all posts to audio files"""
    Path(output_folder).mkdir(exist_ok=True)
    
    for i, post in enumerate(posts, 1):
        # Create safe filename from title
        safe_title = re.sub(r'[^\w\s-]', '', post['title'])[:50]
        output_file = f"{output_folder}/post_{i:02d}_{safe_title}.mp3"
        
        # Combine title and content for audio (without saying "Title:")
        full_text = f"{post['title']}. {post['content']}"
        
        # Detect gender markers & choose correct voice
        voice, cleaned_text = extract_voice_and_text(full_text)

        print(f"Converting post {i}/{len(posts)} with {voice}: {post['title'][:50]}...")

        try:
            await text_to_speech(cleaned_text, output_file, voice=voice)
            print(f"✓ Saved to: {output_file}")
        except Exception as e:
            print(f"✗ Error converting post {i}: {e}")

    
    print(f"\n✅ Done! {len(posts)} posts converted to audio in '{output_folder}' folder")

async def main():
    # Check if get-audio folder exists
    if not os.path.exists(INPUT_FOLDER):
        print(f"❌ Error: '{INPUT_FOLDER}' folder not found!")
        print(f"Please create a '{INPUT_FOLDER}' folder and put your text files in it.")
        return
    
    # Find all .txt files in the get-audio folder
    text_files = glob.glob(os.path.join(INPUT_FOLDER, "*.txt"))
    
    if not text_files:
        print(f"❌ No text files found in '{INPUT_FOLDER}' folder!")
        return
    
    print(f"Found {len(text_files)} text file(s) in '{INPUT_FOLDER}' folder:")
    for file in text_files:
        print(f"  - {os.path.basename(file)}")
    print()
    
    all_posts = []
    
    # Process each text file
    for text_file in text_files:
        print(f"📄 Reading posts from: {os.path.basename(text_file)}")
        posts = parse_reddit_posts(text_file)
        print(f"   Found {len(posts)} posts\n")
        all_posts.extend(posts)
    
    if all_posts:
        print(f"🎙️ Total posts to convert: {len(all_posts)}\n")
        await process_posts(all_posts, OUTPUT_FOLDER)
        
        # Create old-posts folder if it doesn't exist
        Path(ARCHIVE_FOLDER).mkdir(exist_ok=True)
        
        # Move all processed text files to old-posts folder
        print(f"\n📦 Moving processed files to '{ARCHIVE_FOLDER}' folder...")
        for text_file in text_files:
            filename = os.path.basename(text_file)
            destination = os.path.join(ARCHIVE_FOLDER, filename)
            
            # If file already exists in archive, add a number to avoid overwriting
            if os.path.exists(destination):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(destination):
                    destination = os.path.join(ARCHIVE_FOLDER, f"{base}_{counter}{ext}")
                    counter += 1
            
            shutil.move(text_file, destination)
            print(f"   ✓ Moved: {filename} → {ARCHIVE_FOLDER}/")
        
        print(f"\n✅ All done! Audio files in '{OUTPUT_FOLDER}/', text files archived in '{ARCHIVE_FOLDER}/'")
    else:
        print("❌ No posts found in any files!")

if __name__ == "__main__":
    # Install required package first: pip install edge-tts
    asyncio.run(main())