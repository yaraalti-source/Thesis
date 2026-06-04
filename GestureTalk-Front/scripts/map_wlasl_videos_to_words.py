"""
Helper script to map WLASL video IDs to word names for organizing sign videos.
This script reads the WLASL video mapping JSON and creates a reference file
showing which video IDs correspond to which words.
"""

import json
import os

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
WLASL_CLASS_LIST = os.path.join(PROJECT_ROOT, 'GestureTalk-Backend/SignDetectionModel/wordset/wlasl_class_list.txt')
NSLT_JSON = os.path.join(PROJECT_ROOT, 'GestureTalk-Backend/SignDetectionModel/wordset/nslt_300.json')
VIDEOS_DIR = os.path.join(PROJECT_ROOT, 'GestureTalk-Backend/SignDetectionModel/wordset/videos')
OUTPUT_MAPPING = os.path.join(PROJECT_ROOT, 'GestureTalk-Front/assets/config/video_word_mapping.json')
OUTPUT_README = os.path.join(PROJECT_ROOT, 'GestureTalk-Front/assets/config/VIDEO_MAPPING_GUIDE.md')

def load_word_mappings():
    """Load word index to word name mapping."""
    idx_to_word = {}
    
    if not os.path.exists(WLASL_CLASS_LIST):
        print(f"Warning: Class list not found at {WLASL_CLASS_LIST}")
        return idx_to_word
    
    with open(WLASL_CLASS_LIST, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) >= 2:
                try:
                    word_idx = int(parts[0].strip())
                    word = parts[1].strip().lower()
                    idx_to_word[word_idx] = word
                except ValueError:
                    continue
    
    return idx_to_word

def map_videos_to_words():
    """Map video IDs to words using NSLT JSON."""
    print("="*60)
    print("Mapping WLASL Videos to Words")
    print("="*60)
    
    # Load word mappings
    idx_to_word = load_word_mappings()
    print(f"\nLoaded {len(idx_to_word)} word mappings")
    
    # Load video data
    if not os.path.exists(NSLT_JSON):
        print(f"\nWarning: NSLT JSON not found at {NSLT_JSON}")
        print("Creating basic mapping from class list only...")
        return create_basic_mapping(idx_to_word)
    
    with open(NSLT_JSON, 'r', encoding='utf-8') as f:
        video_data = json.load(f)
    
    print(f"Loaded {len(video_data)} video entries from NSLT JSON")
    
    # Check available videos
    available_videos = set()
    if os.path.exists(VIDEOS_DIR):
        for filename in os.listdir(VIDEOS_DIR):
            if filename.endswith('.mp4'):
                video_id = filename[:-4]  # Remove .mp4 extension
                available_videos.add(video_id)
        print(f"Found {len(available_videos)} video files in videos directory")
    
    # Build mapping: word -> list of video IDs
    word_to_videos = {}
    video_to_word = {}
    
    for video_id, info in video_data.items():
        if 'action' in info and len(info['action']) > 0:
            word_idx = info['action'][0]
            if word_idx in idx_to_word:
                word = idx_to_word[word_idx]
                
                if word not in word_to_videos:
                    word_to_videos[word] = []
                word_to_videos[word].append(video_id)
                video_to_word[video_id] = word
    
    # Create output mapping structure
    mapping = {
        'version': '1.0.0',
        'totalWords': len(word_to_videos),
        'totalVideos': len(video_to_word),
        'wordsToVideos': word_to_videos,
        'videosToWords': video_to_word,
        'availableVideoFiles': list(available_videos) if available_videos else [],
    }
    
    # Save JSON mapping
    output_dir = os.path.dirname(OUTPUT_MAPPING)
    os.makedirs(output_dir, exist_ok=True)
    
    with open(OUTPUT_MAPPING, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Video-word mapping saved to: {OUTPUT_MAPPING}")
    print(f"   Mapped {len(word_to_videos)} words to {len(video_to_word)} videos")
    
    # Create README guide
    create_guide(mapping, idx_to_word)
    
    return mapping

def create_basic_mapping(idx_to_word):
    """Create basic mapping from word list only (when NSLT JSON unavailable)."""
    mapping = {
        'version': '1.0.0',
        'totalWords': len(idx_to_word),
        'wordsToVideos': {word: [] for word in idx_to_word.values()},
        'videosToWords': {},
        'note': 'Basic mapping created from class list. Video mappings require NSLT JSON.',
    }
    
    output_dir = os.path.dirname(OUTPUT_MAPPING)
    os.makedirs(output_dir, exist_ok=True)
    
    with open(OUTPUT_MAPPING, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Basic mapping saved to: {OUTPUT_MAPPING}")
    return mapping

def create_guide(mapping, idx_to_word):
    """Create a README guide for video mapping."""
    guide = f"""# WLASL Video to Word Mapping Guide

This guide helps you organize sign language videos for the GestureTalk app.

## Overview

- **Total Words**: {len(idx_to_word)}
- **Mapped Videos**: {len(mapping.get('videosToWords', {}))}
- **Available Video Files**: {len(mapping.get('availableVideoFiles', []))}

## How to Add Sign Videos

### Step 1: Get WLASL Videos

The WLASL (Word-Level American Sign Language) dataset contains sign language videos.
Videos should be placed in: `assets/signs/words/`

### Step 2: Rename Videos

Rename video files to match word names. Use the file-safe name format:

**Format**: `<word_name>.mp4`

**Examples**:
- `hello.mp4` (for word "hello")
- `thank_you.mp4` (for phrase "thank you")
- `ice_cream.mp4` (for phrase "ice cream")

**Important**: 
- Use lowercase letters
- Replace spaces with underscores (`_`)
- Remove special characters
- Use `.mp4` extension

### Step 3: Video Mapping Reference

The mapping file `video_word_mapping.json` contains:
- **wordsToVideos**: Maps each word to its WLASL video IDs
- **videosToWords**: Maps each video ID to its word name

### Step 4: Update Vocabulary

After adding videos, you can update the vocabulary JSON to mark which words have videos:

1. Check which videos you've added to `assets/signs/words/`
2. Update `vocabulary.json` to set `hasVideo: true` for words with videos
3. Or run the vocabulary generator script again (it will detect existing videos)

## Common Words Reference

Here are the first 50 words from the WLASL vocabulary:

"""
    
    # Add first 50 words
    words_list = list(idx_to_word.values())[:50]
    for i, word in enumerate(words_list, 1):
        file_safe = word.replace(' ', '_')
        guide += f"{i}. **{word}** → `{file_safe}.mp4`\n"
    
    guide += f"""
... and {len(idx_to_word) - 50} more words.

## Video File Naming Examples

| Word | File-Safe Name | Video Filename |
|------|---------------|----------------|
| hello | hello | `hello.mp4` |
| thank you | thank_you | `thank_you.mp4` |
| ice cream | ice_cream | `ice_cream.mp4` |
| don't want | dont_want | `dont_want.mp4` |
| high school | high_school | `high_school.mp4` |

## Where to Get Videos

1. **WLASL Dataset**: Download from the official WLASL repository
2. **Extract frames**: Use the video processing scripts in the backend
3. **Custom videos**: Record your own ASL videos following the naming convention

## Notes

- Videos should be in MP4 format
- Recommended resolution: 640x480 or higher
- Recommended length: 1-3 seconds per sign
- File size: Keep videos under 5MB each for app performance

## Scripts Available

- `generate_vocabulary_from_wlasl.py`: Generate vocabulary JSON from WLASL class list
- `map_wlasl_videos_to_words.py`: Map video IDs to word names (this script)
- `check_video_files.py`: Check which videos are available (can be created)

For questions, refer to the main project documentation.
"""
    
    with open(OUTPUT_README, 'w', encoding='utf-8') as f:
        f.write(guide)
    
    print(f"✅ Video mapping guide saved to: {OUTPUT_README}")

if __name__ == '__main__':
    map_videos_to_words()









