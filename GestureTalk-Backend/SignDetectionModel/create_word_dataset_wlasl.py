"""
Create WORD dataset from WLASL videos
Uses nslt_100.json for video-to-word mapping
"""

import os
import json
import cv2
import pickle
import mediapipe as mp
import numpy as np
from collections import defaultdict

# ==================== CONFIGURATION ====================
WORDSET_DIR = './wordset'
VIDEOS_DIR = os.path.join(WORDSET_DIR, 'videos')
# Use nslt_300 to target 300 words for the improved dataset
JSON_FILE = os.path.join(WORDSET_DIR, 'nslt_300.json')
CLASS_LIST = os.path.join(WORDSET_DIR, 'wlasl_class_list.txt')

# Settings - adjust these as needed
MAX_WORDS = 300           # Number of words to include (None for all available)
MAX_VIDEOS_PER_WORD = 100 # Target videos per word
FRAMES_PER_VIDEO = 30     # Frames to extract per video (temporal model target)

print("="*60, flush=True)
print("WLASL WORD DATASET CREATOR", flush=True)
print("="*60, flush=True)

# ==================== LOAD WORD LIST ====================
print("\nLoading word class list...", flush=True)
idx_to_word = {}
with open(CLASS_LIST, 'r') as f:
    for line in f:
        parts = line.strip().split('\t')
        if len(parts) == 2:
            idx_to_word[int(parts[0])] = parts[1]

print(f"Found {len(idx_to_word)} words in class list", flush=True)

# ==================== LOAD VIDEO MAPPINGS ====================
print("Loading video mappings...", flush=True)
with open(JSON_FILE, 'r') as f:
    video_data = json.load(f)

print(f"Found {len(video_data)} video entries", flush=True)

# Get available video files
available_videos = set(f.replace('.mp4', '') for f in os.listdir(VIDEOS_DIR) if f.endswith('.mp4'))
print(f"Available video files: {len(available_videos)}", flush=True)

# Build word to video mapping
word_to_videos = defaultdict(list)
for video_id, info in video_data.items():
    if video_id in available_videos:
        # action field contains word indices - take the first one
        if 'action' in info and len(info['action']) > 0:
            word_idx = info['action'][0]
            if word_idx in idx_to_word:
                word = idx_to_word[word_idx]
                word_to_videos[word].append(video_id)

print(f"Words with available videos: {len(word_to_videos)}", flush=True)

# ==================== SETUP MEDIAPIPE ====================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=True, min_detection_confidence=0.3, max_num_hands=2)

# ==================== PROCESS VIDEOS ====================
data = []
labels = []
processed = 0
skipped = 0

# Select words to process
words_to_process = sorted(word_to_videos.keys(), key=lambda w: -len(word_to_videos[w]))
if MAX_WORDS:
    words_to_process = words_to_process[:MAX_WORDS]

print(f"\nProcessing {len(words_to_process)} words...", flush=True)
print("="*60, flush=True)

for word_idx, word in enumerate(words_to_process):
    word_videos = word_to_videos[word][:MAX_VIDEOS_PER_WORD]
    word_samples = 0
    
    for video_id in word_videos:
        video_path = os.path.join(VIDEOS_DIR, f"{video_id}.mp4")
        
        if not os.path.exists(video_path):
            skipped += 1
            continue
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            skipped += 1
            continue
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames < FRAMES_PER_VIDEO:
            cap.release()
            skipped += 1
            continue
        
        # Extract frames evenly distributed
        frame_indices = np.linspace(0, total_frames - 1, FRAMES_PER_VIDEO, dtype=int)
        
        for frame_idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                continue
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(frame_rgb)
            
            if results.multi_hand_landmarks and len(results.multi_hand_landmarks) >= 1:
                hands_data = {'Left': None, 'Right': None}
                
                for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    handedness = results.multi_handedness[idx].classification[0].label
                    
                    x_ = [lm.x for lm in hand_landmarks.landmark]
                    y_ = [lm.y for lm in hand_landmarks.landmark]
                    
                    min_x, min_y = min(x_), min(y_)
                    hand_data = []
                    for lm in hand_landmarks.landmark:
                        hand_data.append(lm.x - min_x)
                        hand_data.append(lm.y - min_y)
                    
                    hands_data[handedness] = hand_data
                
                # Combine: Left first, then Right (pad with zeros if missing)
                combined_data = []
                for hand_type in ['Left', 'Right']:
                    if hands_data[hand_type] is not None:
                        combined_data.extend(hands_data[hand_type])
                    else:
                        combined_data.extend([0.0] * 42)
                
                if len(combined_data) == 84:
                    data.append(combined_data)
                    labels.append(word)
                    word_samples += 1
                    processed += 1
        
        cap.release()
    
    print(f"  [{word_idx+1:2d}/{len(words_to_process)}] {word:15s}: {word_samples} samples", flush=True)

hands.close()

# ==================== SAVE DATASET ====================
print("="*60, flush=True)
print(f"\nTotal samples: {processed}", flush=True)
print(f"Skipped videos: {skipped}", flush=True)
print(f"Unique words: {len(set(labels))}", flush=True)

if processed > 0:
    with open('data_word.pickle', 'wb') as f:
        pickle.dump({'data': data, 'labels': labels}, f)
    
    print(f"\n✓ Dataset saved as 'data_word.pickle'", flush=True)
    print(f"\nWords included:", flush=True)
    from collections import Counter
    for word, count in Counter(labels).most_common():
        print(f"  {word}: {count} samples", flush=True)
    print(f"\nNext step: Run 'python train_word_model.py'", flush=True)
else:
    print("\n✗ No data extracted! Check video files.", flush=True)
