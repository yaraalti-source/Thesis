"""
Copy WLASL videos to frontend assets with correct naming.
This script maps video IDs to words and copies them with proper names.
"""

import json
import os
import shutil
from collections import defaultdict

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
VIDEO_MAPPING_JSON = os.path.join(PROJECT_ROOT, 'GestureTalk-Front/assets/config/video_word_mapping.json')
VOCABULARY_JSON = os.path.join(PROJECT_ROOT, 'GestureTalk-Front/assets/config/vocabulary.json')
SOURCE_VIDEOS_DIR = os.path.join(PROJECT_ROOT, 'GestureTalk-Backend/SignDetectionModel/wordset/videos')
TARGET_VIDEOS_DIR = os.path.join(PROJECT_ROOT, 'GestureTalk-Front/assets/signs/words')

def copy_videos_for_words(words_to_copy=None, max_videos_per_word=1):
    """
    Copy WLASL videos for specified words.
    
    Args:
        words_to_copy: List of words to copy. If None, copies all words.
        max_videos_per_word: Maximum videos to copy per word (default: 1)
    """
    print("="*60)
    print("Copying WLASL Videos for Words")
    print("="*60)
    
    # Load video mapping
    if not os.path.exists(VIDEO_MAPPING_JSON):
        print(f"Error: Video mapping file not found: {VIDEO_MAPPING_JSON}")
        print("Run map_wlasl_videos_to_words.py first!")
        return
    
    with open(VIDEO_MAPPING_JSON, 'r', encoding='utf-8') as f:
        mapping_data = json.load(f)
    
    words_to_videos = mapping_data.get('wordsToVideos', {})
    
    # Load vocabulary for file-safe names
    file_safe_names = {}
    if os.path.exists(VOCABULARY_JSON):
        with open(VOCABULARY_JSON, 'r', encoding='utf-8') as f:
            vocab_data = json.load(f)
            words_data = vocab_data.get('words', {})
            for word, info in words_data.items():
                file_safe_names[word] = info.get('fileSafeName', word.replace(' ', '_'))
    
    # Check source directory
    if not os.path.exists(SOURCE_VIDEOS_DIR):
        print(f"Error: Source videos directory not found: {SOURCE_VIDEOS_DIR}")
        return
    
    # Create target directory
    os.makedirs(TARGET_VIDEOS_DIR, exist_ok=True)
    
    # Determine which words to process
    if words_to_copy:
        words_to_process = [w.lower() for w in words_to_copy]
    else:
        words_to_process = list(words_to_videos.keys())
    
    print(f"\nProcessing {len(words_to_process)} words...")
    print(f"Source: {SOURCE_VIDEOS_DIR}")
    print(f"Target: {TARGET_VIDEOS_DIR}\n")
    
    copied_count = 0
    skipped_count = 0
    not_found_count = 0
    
    for word in words_to_process:
        word_lower = word.lower()
        if word_lower not in words_to_videos:
            print(f"⚠️  '{word}' not found in video mapping")
            not_found_count += 1
            continue
        
        # Get all video IDs, but limit for actual copying
        all_video_ids = words_to_videos[word_lower]
        if not all_video_ids:
            print(f"⚠️  No videos found for '{word}'")
            skipped_count += 1
            continue
        
        # For finding existing videos, try ALL available IDs
        # For actual copying, use max_videos_per_word limit
        video_ids_to_try = all_video_ids  # Try all until we find one that exists
        
        # Get file-safe name
        file_safe_name = file_safe_names.get(word_lower, word_lower.replace(' ', '_'))
        target_filename = f"{file_safe_name}.mp4"
        target_path = os.path.join(TARGET_VIDEOS_DIR, target_filename)
        
        # Check if already exists
        if os.path.exists(target_path):
            print(f"✓ '{word}' → {target_filename} (already exists)")
            copied_count += 1
            continue
        
        # Try to copy the first available video (check all video IDs until we find one)
        copied = False
        tried_count = 0
        max_to_try = min(len(video_ids_to_try), 20)  # Try up to 20 video IDs
        for video_id in video_ids_to_try[:max_to_try]:
            tried_count += 1
            source_path = os.path.join(SOURCE_VIDEOS_DIR, f"{video_id}.mp4")
            if os.path.exists(source_path):
                try:
                    shutil.copy2(source_path, target_path)
                    if tried_count > 1:
                        print(f"✓ '{word}' → {target_filename} (copied from {video_id}.mp4, tried {tried_count} videos)")
                    else:
                        print(f"✓ '{word}' → {target_filename} (copied from {video_id}.mp4)")
                    copied_count += 1
                    copied = True
                    break
                except Exception as e:
                    print(f"✗ Error copying '{word}' from {video_id}.mp4: {e}")
                    skipped_count += 1
                    break
        
        if not copied:
            print(f"✗ No source video found for '{word}' (tried {tried_count}/{max_to_try} of {len(all_video_ids)} available video IDs)")
            skipped_count += 1
    
    print("\n" + "="*60)
    print("Summary:")
    print(f"  Copied: {copied_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Not found: {not_found_count}")
    print(f"  Total: {len(words_to_process)}")
    print("="*60)
    
    if copied_count > 0:
        print(f"\n✅ Videos copied to: {TARGET_VIDEOS_DIR}")
        print("⚠️  Don't forget to:")
        print("   1. Update pubspec.yaml if needed")
        print("   2. Restart the app (not hot reload)")

if __name__ == '__main__':
    import sys
    
    # Common words to copy first
    common_words = [
        'hello', 'hi', 'goodbye', 'bye', 'thanks', 'thank you', 'please',
        'sorry', 'yes', 'no', 'okay', 'ok', 'welcome',
        'good', 'bad', 'happy', 'sad', 'angry', 'tired', 'sick',
        'fine', 'better', 'love', 'like', 'hate',
        'help', 'eat', 'drink', 'go', 'come', 'want', 'need', 'have',
        'see', 'hear', 'talk', 'walk', 'run', 'sit', 'stand', 'sleep',
        'water', 'food', 'home', 'school', 'work', 'car', 'phone',
        'book', 'door', 'window', 'table', 'chair',
        'family', 'friend', 'mother', 'father', 'brother', 'sister',
        'child', 'baby', 'man', 'woman', 'people',
        'morning', 'afternoon', 'evening', 'night', 'day', 'time',
        'today', 'tomorrow', 'yesterday', 'now', 'later',
        'name', 'meet', 'nice', 'know', 'think', 'understand',
        'learn', 'teach', 'study', 'read', 'write',
    ]
    
    if len(sys.argv) > 1:
        # Copy specific words from command line
        words = sys.argv[1:]
        copy_videos_for_words(words_to_copy=words)
    else:
        # Copy common words by default
        print("No words specified. Copying common words...")
        print("Usage: python copy_wlasl_videos_for_words.py [word1] [word2] ...")
        print("Example: python copy_wlasl_videos_for_words.py hello thanks please\n")
        copy_videos_for_words(words_to_copy=common_words)

