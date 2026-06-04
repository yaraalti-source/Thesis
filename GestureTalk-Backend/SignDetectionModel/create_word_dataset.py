"""
Create dataset for WORD detection (requires BOTH hands visible)

Extracts 84 features per sample:
- Left hand: 21 landmarks × 2 (x, y) = 42 features
- Right hand: 21 landmarks × 2 (x, y) = 42 features
- Total: 84 features
"""

import os
import pickle
import cv2
import mediapipe as mp

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=True, min_detection_confidence=0.3, max_num_hands=2)

DATA_DIR = './data_word'

if not os.path.exists(DATA_DIR):
    print(f"ERROR: {DATA_DIR} folder not found!")
    print("Run 'python collect_word_imgs.py' first to collect word images.")
    exit(1)

data = []
labels = []
skipped = 0

print("Creating WORD dataset (requires BOTH hands)...", flush=True)
print("="*60, flush=True)

for word in os.listdir(DATA_DIR):
    word_path = os.path.join(DATA_DIR, word)
    if not os.path.isdir(word_path):
        continue
    
    word_samples = 0
    word_skipped = 0
    
    for img_name in os.listdir(word_path):
        if not img_name.endswith(('.jpg', '.jpeg', '.png')):
            continue
            
        img_path = os.path.join(word_path, img_name)
        img = cv2.imread(img_path)
        if img is None:
            continue
        
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(img_rgb)
        
        # Require BOTH hands for word detection
        if results.multi_hand_landmarks and len(results.multi_hand_landmarks) == 2:
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
            
            # Both hands must be detected
            if hands_data['Left'] is not None and hands_data['Right'] is not None:
                # Concatenate: Left first, then Right
                data_aux = hands_data['Left'] + hands_data['Right']
                
                if len(data_aux) == 84:
                    data.append(data_aux)
                    labels.append(word)
                    word_samples += 1
                else:
                    word_skipped += 1
            else:
                word_skipped += 1
        else:
            word_skipped += 1
    
    print(f"  {word}: {word_samples} samples (skipped {word_skipped} - missing hands)", flush=True)
    skipped += word_skipped

hands.close()

# Save dataset
with open('data_word.pickle', 'wb') as f:
    pickle.dump({'data': data, 'labels': labels}, f)

print("="*60, flush=True)
print(f"Dataset created: {len(data)} samples", flush=True)
print(f"Skipped: {skipped} images (didn't have both hands)", flush=True)
print(f"Feature size: {len(data[0]) if data else 0} (expected 84)", flush=True)
print(f"Words: {list(set(labels))}", flush=True)
print(f"\nSaved as 'data_word.pickle'", flush=True)
print(f"Now run: python train_transformer_word.py", flush=True)

















