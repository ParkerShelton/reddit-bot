#!/usr/bin/env python3
"""
clean_and_split.py

*   Read *.txt files from <input_dir>
*   Split each file into blocks on the old separator  `---POST_SEPARATOR---`
*   Clean every block (remove noise, tags, hashtags, etc.)
*   Write each cleaned block to <output_dir>/<basename>_block_<n>.txt
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import List

# ----------------------------------------------------------------------
# ------------------------------ cleaning --------------------------------
# ----------------------------------------------------------------------
def clean_line(line: str) -> str | None:
    """Return a cleaned line, or None if it should be omitted."""
    stripped = line.strip()

    # 1. Separator / log / misc headers
    if stripped == "---POST_SEPARATOR---":
        return None
    if stripped.startswith("REDDIT SCRAPER LOG - Started:"):
        return None
    if stripped.startswith("Filter:"):
        return None
    if stripped.startswith("AI Cleaning:"):
        return None
    if stripped.startswith("Subreddits:"):
        return None
    if stripped == "---HASHTAGS---":
        return None
    # Remove shorts titles and descriptions sections
    if stripped == "---SHORTS_TITLES---":
        return None
    if stripped == "---SHORTS_DESCRIPTION---":
        return None
    # Remove post titles (typically first line of each post after gender tag)
    if stripped.startswith("Am I the asshole") or stripped.startswith("AITA"):
        return None

    # 2. Gender tags
    if re.fullmatch(r"<<[A-Z]+>>", stripped):
        return None

    # 3. Pure‑hashtag lines (e.g. "#a #b #c")
    if re.search(r'#\S+', stripped):
        return None

    # 4. Anything else stays
    return line.rstrip("\n")  # keep all other content, but strip the trailing NL


def is_title_line(line: str) -> bool:
    """
    Determine if a line is a post title by checking common patterns.
    Used only for identification, not for filtering.
    """
    line = line.strip().lower()
    # Common AITA title formats
    if line.startswith("am i the asshole"):
        return True
    if line.startswith("aita"):
        return True
    if "am i the asshole" in line:
        return True
    if "aita" in line and len(line) < 100:  # Only match if it's a short line likely to be a title
        return True
    # Other common title patterns
    if re.match(r'^(am i|was i|would i be|wibta|would i be the asshole)', line):
        return True
    return False


def remove_shorts_content(lines: list) -> list:
    """
    Remove shorts titles and descriptions blocks from the content.
    This handles multi-line content between markers.
    """
    result = []
    skip_mode = False
    
    for line in lines:
        # Start skipping if we hit a marker
        if line and (line.strip() == "---SHORTS_TITLES---" or 
                    line.strip() == "---SHORTS_DESCRIPTION---" or 
                    line.strip() == "---HASHTAGS---"):
            skip_mode = True
            continue
            
        # Stop skipping if we hit a separator or end of content
        if skip_mode and (not line.strip() or line.strip() == "---POST_SEPARATOR---"):
            skip_mode = False
            
        # Only add lines when not in skip mode
        if not skip_mode:
            result.append(line)
            
    return result


def remove_inline_hashtags(text: str) -> str:
    """
    Remove any hashtags that might be embedded in the text content.
    """
    # Remove hashtag format like #word or # word
    return re.sub(r'#\s*\w+', '', text)


def should_remove_section(section_lines):
    """
    Check if this section is a scraper header/log or another section to remove entirely.
    Returns True if the section should be skipped entirely.
    """
    if not section_lines:
        return True
        
    # Check for scraper log header
    header_patterns = [
        "REDDIT SCRAPER LOG - Started:", 
        "Subreddits:", 
        "Filter: Posts under", 
        "AI Cleaning:"
    ]
    
    for line in section_lines[:4]:  # Just check first few lines
        for pattern in header_patterns:
            if pattern in line:
                return True
                
    return False

def process_block(block_text: str) -> str:
    """
    Apply clean_line to every line of a *block* and return a single string.
    Empty blocks (after cleaning) result in an empty string.
    
    Enhanced to remove titles and shorts content sections.
    """
    lines = block_text.splitlines()
    
    # Skip scraper log/header sections entirely
    if should_remove_section(lines):
        return ""
    
    # First remove shorts content blocks
    lines = remove_shorts_content(lines)
    
    # Apply line-by-line cleaning
    cleaned = []
    title_line = None
    
    # First look for a title in the first few lines
    for i in range(min(3, len(lines))):
        if lines[i].strip() and is_title_line(lines[i]):
            title_line = lines[i].strip()
            break
    
    # If we found a title, add it first
    if title_line:
        cleaned.append(f"Title: {title_line}")
        # Add a blank line after the title
        cleaned.append("")
        
    # Process all lines
    for i, line in enumerate(lines):
        # Skip the line if it's the title we already added
        if line.strip() == title_line:
            continue
        
        # Apply regular line cleaning
        clean = clean_line(line)
        if clean is not None:
            # Additional cleaning to remove inline hashtags
            clean = remove_inline_hashtags(clean)
            if clean.strip():  # Only add non-empty lines
                cleaned.append(clean)
    
    # Join and do one final cleanup of the entire text
    result = "\n".join(cleaned)
    return result


# ----------------------------------------------------------------------
# ---------------------------- main -------------------------------------
# ----------------------------------------------------------------------
def split_raw_text_into_blocks(raw: str) -> List[str]:
    """
    Split the raw file into blocks.
    We look for lines that are *exactly* `---POST_SEPARATOR---` (ignoring whitespace).
    """
    # Using a capturing group so the separator line is not included in any block.
    # The regex splits on a whole line that is only that separator.
    parts = re.split(r'^\s*---POST_SEPARATOR---\s*$', raw, flags=re.MULTILINE)
    # Remove leading/trailing blank blocks that might appear if the file starts/ends
    # with a separator.
    return [p for p in parts if p.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean Reddit‑scraper noise and split each file into blocks."
    )
    
    # Get the root directory
    root_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=root_dir / "old-posts",
        help="Directory containing the raw *.txt files (default: old-posts)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=root_dir / "cleaned-text",
        help="Directory where cleaned block files will be written (default: cleaned-text)",
    )
    args = parser.parse_args()

    in_dir: Path = args.input
    out_dir: Path = args.output

    if not in_dir.is_dir():
        print(f"❌  Input folder {in_dir} does not exist")
        return

    # Create the output directory if it does not exist
    out_dir.mkdir(parents=True, exist_ok=True)

    txt_files = sorted(in_dir.glob("*.txt"))

    if not txt_files:
        print(f"⚠️  No *.txt files found in {in_dir}")
        return

    for src_file in txt_files:
        raw_text = src_file.read_text(encoding="utf-8")
        blocks = split_raw_text_into_blocks(raw_text)

        if not blocks:
            print(f"⚠️  No blocks found in {src_file}")
            continue

        base_name = src_file.stem  # without .txt

        for idx, block in enumerate(blocks, start=1):
            cleaned = process_block(block)
            # Skip entirely empty blocks (after cleaning)
            if not cleaned.strip():
                continue

            dst_file = out_dir / f"{base_name}_block_{idx}.txt"
            dst_file.write_text(cleaned, encoding="utf-8")
            print(f"[✓] Written: {dst_file}")

        print(f"✅  Processed {src_file} → {len(blocks)} blocks")

# ----------------------------------------------------------------------
if __name__ == "__main__":
    main()
