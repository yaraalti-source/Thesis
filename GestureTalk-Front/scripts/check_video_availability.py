"""Quick script to check video availability for specific words."""
import json
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIDEO_MAPPING = os.path.join(PROJECT_ROOT, 'GestureTalk-Front/assets/config/video_word_mapping.json')
SOURCE_VIDEOS_DIR = os.path.join(PROJECT_ROOT, 'GestureTalk-Backend/SignDetectionModel/wordset/videos')

with open(VIDEO_MAPPING, 'r') as f:
    mapping = json.load(f)

words_to_check = ['hello', 'water', 'book', 'please', 'yes', 'no']

print("Checking video availability:\n")
for word in words_to_check:
    word_lower = word.lower()
    if word_lower in mapping['wordsToVideos']:
        video_ids = mapping['wordsToVideos'][word_lower]
        print(f"{word}:")
        print(f"  In mapping: YES ({len(video_ids)} video IDs)")
        if video_ids:
            first_video = video_ids[0]
            video_path = os.path.join(SOURCE_VIDEOS_DIR, f"{first_video}.mp4")
            exists = os.path.exists(video_path)
            print(f"  First video file ({first_video}.mp4): {'EXISTS' if exists else 'NOT FOUND'}")
            if exists:
                size = os.path.getsize(video_path) / 1024  # KB
                print(f"  File size: {size:.1f} KB")
        print()
    else:
        print(f"{word}: NOT in mapping")
        print()









