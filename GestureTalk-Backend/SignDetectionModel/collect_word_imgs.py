"""
Collect images for WORD signs (using BOTH hands)

Each word will have its own folder in ./data_word/
Example words: hello, thanks, please, sorry, help, etc.
"""

import os
import cv2

DATA_DIR = './data_word'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Define your word classes here
WORD_CLASSES = ['hello', 'thanks', 'please', 'sorry', 'help', 'yes', 'no', 'love', 'friend', 'family']
DATASET_SIZE = 100  # Images per word

print("="*60)
print("WORD IMAGE COLLECTOR (Two Hands)")
print("="*60)
print(f"Words to collect: {WORD_CLASSES}")
print(f"Images per word: {DATASET_SIZE}")
print("="*60)

cap = cv2.VideoCapture(0)

for word in WORD_CLASSES:
    word_dir = os.path.join(DATA_DIR, word)
    if not os.path.exists(word_dir):
        os.makedirs(word_dir)
    
    # Check if already collected
    existing = len([f for f in os.listdir(word_dir) if f.endswith('.jpg')])
    if existing >= DATASET_SIZE:
        print(f"Skipping '{word}' - already has {existing} images")
        continue
    
    print(f"\nCollecting: '{word.upper()}' (show BOTH hands)")
    print("Press 'Q' when ready...")
    
    # Wait for user to be ready
    while True:
        ret, frame = cap.read()
        cv2.putText(frame, f"WORD: {word.upper()}", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (128, 0, 128), 3, cv2.LINE_AA)
        cv2.putText(frame, "Show BOTH hands - Press 'Q' to start", (50, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.imshow('Collect Word Images', frame)
        if cv2.waitKey(25) == ord('q'):
            break
    
    # Collect images
    counter = existing
    while counter < DATASET_SIZE:
        ret, frame = cap.read()
        
        # Show progress
        cv2.putText(frame, f"WORD: {word.upper()}", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (128, 0, 128), 3, cv2.LINE_AA)
        cv2.putText(frame, f"Recording: {counter}/{DATASET_SIZE}", (50, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
        
        cv2.imshow('Collect Word Images', frame)
        cv2.waitKey(25)
        
        # Save image
        cv2.imwrite(os.path.join(word_dir, f'{counter}.jpg'), frame)
        counter += 1
    
    print(f"Collected {DATASET_SIZE} images for '{word}'")

cap.release()
cv2.destroyAllWindows()

print("\n" + "="*60)
print("Collection complete!")
print(f"Now run: python create_word_dataset.py")
print("="*60)

















