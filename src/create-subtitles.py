#!/usr/bin/env python3
import os
import re
import requests
import json
from pathlib import Path
from typing import Optional, Iterable, Union
import pysrt
import subprocess
import sys

# Use absolute path to the clean-text.py script in the same directory
CLEAN_TEXT_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clean-text.py")

# --------------------------------------------------------------------------- #
# 1️⃣  API‑KEY helper – raises if we can't find a key
# --------------------------------------------------------------------------- #
def load_api_key() -> str:
    """Return the Groq API key.

    1. Try to read api_key.txt from the root directory
    2. If that fails, look in the ``GROQ_API_KEY`` environment variable
    3. Raise an explicit error if still missing
    """
    # Get the root directory path
    root_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    api_key_path = root_dir / "api_key.txt"
    
    # Try to read from file in root directory
    if api_key_path.is_file():
        key = api_key_path.read_text(encoding="utf-8").strip()
        if key:
            return key
    
    # Fallback to environment variable
    key = os.getenv("GROQ_API_KEY")
    if key:
        return key
    
    # Failed to find a key
    raise FileNotFoundError(
        f"Could not find a Groq API key. "
        f"Searched in: {api_key_path}. "
        f"Set it in api_key.txt in the project root or via GROQ_API_KEY environment variable."
    )

# --------------------------------------------------------------------------- #
# 2️⃣  Global API key – only load once
# --------------------------------------------------------------------------- #
API_KEY = load_api_key()

# Get the root directory and current path for better error messages
ROOT_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CURRENT_DIR = Path(os.getcwd())

# Instead of using old-posts directly, use the cleaned files
CLEANED_FOLDER = ROOT_DIR / "cleaned-text"  # folder with cleaned text files

# Create subtitles folder in root directory
OUT_FOLDER = ROOT_DIR / "subtitles"  # folder to write .srt files

# Create output folder if it doesn't exist
OUT_FOLDER.mkdir(exist_ok=True, parents=True)
CLEANED_FOLDER.mkdir(exist_ok=True, parents=True)

# Define old-posts folder for running clean-text.py
OLD_POSTS_FOLDER = ROOT_DIR / "old-posts"

# Print current working directory and paths for debugging
print(f"Current working directory: {CURRENT_DIR}")
print(f"Root directory: {ROOT_DIR}")
print(f"Old posts folder: {OLD_POSTS_FOLDER}")
print(f"Cleaned files folder: {CLEANED_FOLDER}")
print(f"Output folder: {OUT_FOLDER}")

# --------------------------------------------------------------------------- #
# 3️⃣  Helpers
# --------------------------------------------------------------------------- #
def _unique_srt_path(path: Path) -> Path:
    """Return a Path that does not yet exist by appending ``_001`` etc."""
    if not path.exists():
        return path

    stem, suffix = path.stem, path.suffix
    counter = 1
    while True:
        candidate = path.with_name(f"{stem}_{counter:03d}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1

# --------------------------------------------------------------------------- #
# 4️⃣  Main function
# --------------------------------------------------------------------------- #
def clean_transcript_text(text):
    """Clean transcript text before sending to LLM.
    Removes header lines, markers, etc."""
    # Split into lines
    lines = text.strip().split('\n')
    cleaned_lines = []
    skip_section = False
    
    # Define patterns to identify and remove
    header_patterns = ["REDDIT SCRAPER LOG", "Subreddits:", "Filter:", "AI Cleaning:"]
    section_markers = ["---POST_SEPARATOR---", "---HASHTAGS---", "---SHORTS_TITLES---", "---SHORTS_DESCRIPTION---"]
    
    for line in lines:
        # Skip header lines
        if any(pattern in line for pattern in header_patterns):
            continue
            
        # Skip section marker lines
        if any(marker in line for marker in section_markers):
            skip_section = True
            continue
            
        # Reset skip flag on empty line after a marker
        if skip_section and not line.strip():
            skip_section = False
            continue
            
        # Skip lines while in a marker section
        if skip_section:
            continue
            
        # Skip gender tags
        if line.strip().startswith("<<") and line.strip().endswith(">>"):
            continue
            
        # Skip hashtags
        if line.strip().startswith("#"):
            continue
            
        # Add clean lines
        if line.strip():
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)


def llm_chunked_srt(
    txt_path: Union[str, Path],
    out_folder: Optional[Union[str, Path]] = None,
    *,
    model: str = "llama-3.1-8b-instant",
    temperature: float = 0.2,
    max_tokens: int = 1200,   # more generous default
) -> Path:
    """Convert a plain‑text transcript to an SRT file.

    The LLM produces *plain* subtitle lines (one per line); timestamps are
    generated locally at ~5 s per line.  The resulting file is written to
    ``<txt_path>.srt`` inside ``out_folder`` (or the same directory as the
    transcript if ``out_folder`` is ``None``).  If the file already exists,
    a ``_001`` suffix is appended.
    """
    txt_path = Path(txt_path).expanduser().resolve()

    # ---- 1️⃣  Validate input file ---------------------------------------
    if not txt_path.is_file():
        raise FileNotFoundError(f"No transcript found at {txt_path}")

    # ---- 2️⃣  Destination path ------------------------------------------
    out_path = txt_path.with_suffix(".srt")
    if out_folder is not None:
        folder = Path(out_folder).expanduser().resolve()
        folder.mkdir(parents=True, exist_ok=True)
        out_path = folder / out_path.name

    # ---- 3️⃣  Ask the LLM to chunk --------------------------------------
    raw_transcript = txt_path.read_text(encoding="utf-8")
    # Clean the transcript before sending to LLM
    transcript = clean_transcript_text(raw_transcript)

    # Split the transcript into lines first, to preserve exact formatting
    lines = transcript.split('\n')
    
    # We need to make sure each line isn't too long for a subtitle
    # Maximum characters per subtitle line (standard subtitle recommendation)
    max_chars_per_subtitle = 42
    
    blocks = []
    
    # Process title separately to ensure it's shown first
    title_line = None
    content_lines = []
    
    for i, line in enumerate(lines):
        if i == 0 and line.startswith('Title:'):
            # This is a title line
            title_line = line
        else:
            # This is a content line
            if line.strip():  # Only keep non-empty lines
                content_lines.append(line)
    
    # First add the title if it exists
    if title_line:
        # Remove the "Title: " prefix
        clean_title = title_line.replace("Title: ", "", 1)
        
        # Split title into parts if it's too long
        if len(clean_title) > max_chars_per_subtitle:
            # Try to split at a sensible point
            mid_point = clean_title[:max_chars_per_subtitle].rfind(' ')
            if mid_point == -1:  # No space found
                mid_point = max_chars_per_subtitle
                
            blocks.append(clean_title[:mid_point])
            blocks.append(clean_title[mid_point:].strip())
        else:
            blocks.append(clean_title)
    
    # Now add content lines, splitting only if they're too long
    for line in content_lines:
        if not line.strip():
            continue
            
        # If the line is short enough, keep it as is
        if len(line) <= max_chars_per_subtitle:
            blocks.append(line)
        else:
            # Split long lines, preferably at spaces
            current_pos = 0
            while current_pos < len(line):
                # Find a good breaking point near max_chars
                if current_pos + max_chars_per_subtitle >= len(line):
                    # This is the last piece
                    blocks.append(line[current_pos:])
                    break
                    
                # Try to find a space to break at
                break_pos = line[current_pos:current_pos + max_chars_per_subtitle].rfind(' ')
                if break_pos == -1:  # No space found
                    break_pos = max_chars_per_subtitle
                
                blocks.append(line[current_pos:current_pos + break_pos])
                current_pos += break_pos + 1  # +1 to skip the space
    
    # These are our raw blocks with original text preserved exactly
    raw_blocks = blocks

    # ---- 4️⃣  Clean blocks (strip, remove empties) ----------------------
    blocks = [b.strip() for b in raw_blocks if b.strip()]
    if not blocks:
        raise ValueError("No subtitle blocks could be generated from the transcript.")

    # ---- 5️⃣  Build the SRT ---------------------------------------------
    subs = pysrt.SubRipFile()
    start_sec = 0.0
    interval = 5.0  # fixed 5‑s windows

    for idx, block in enumerate(blocks, start=1):
        subs.append(
            pysrt.SubRipItem(
                index=idx,
                start=pysrt.SubRipTime(seconds=start_sec),
                end=pysrt.SubRipTime(seconds=start_sec + interval),
                text=block,
            )
        )
        start_sec += interval

    # ---- 6️⃣  Ensure we don't overwrite -------------------------------
    final_path = _unique_srt_path(out_path)

    # ---- 7️⃣  Write the file -------------------------------------------
    # `pysrt` has a dedicated `save()` method which is more robust
    subs.save(str(final_path), encoding="utf-8")

    return final_path

# --------------------------------------------------------------------------- #
# 5️⃣  Example usage
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    print(f"Looking for text files in: {OLD_POSTS_FOLDER}")
    print(f"Cleaned files will be in: {CLEANED_FOLDER}")
    print(f"Subtitles will be saved to: {OUT_FOLDER}")
    
    # First run the clean-text script to process raw files into cleaned blocks
    if os.path.exists(CLEAN_TEXT_SCRIPT):
        print(f"Running text cleaning script: {CLEAN_TEXT_SCRIPT}")
        try:
            result = subprocess.run([sys.executable, CLEAN_TEXT_SCRIPT], check=True)
            print("Text cleaning completed successfully")
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Error running Clean Text script: {e}")
    else:
        print(f"Clean text script not found at: {CLEAN_TEXT_SCRIPT}")
    
    # Find cleaned text files to process for subtitles
    cleaned_files = list(CLEANED_FOLDER.glob("*_block_*.txt"))
    
    if not cleaned_files:
        print(f"\n⚠️ Warning: No cleaned text files found in {CLEANED_FOLDER}")
        print("Check if clean-text.py is working properly.")
        sys.exit(1)
    else:
        print(f"\nFound {len(cleaned_files)} cleaned text file(s) to process:")
        for file in cleaned_files:
            print(f"  - {file.name}")
    
    # Process each cleaned text file to generate SRT files
    print("\nGenerating subtitle files...")
    success_count = 0
    
    for txt_path in cleaned_files:
        try:
            print(f"Processing: {txt_path.name}")
            result = llm_chunked_srt(str(txt_path), OUT_FOLDER)
            print(f"✅ SRT written to: {result}")
            success_count += 1
        except Exception as e:
            print(f"❌ Error processing {txt_path.name}: {e}")
    
    print(f"\n✅ Subtitle generation complete! Created {success_count} out of {len(cleaned_files)} subtitle files in '{OUT_FOLDER}'.")
