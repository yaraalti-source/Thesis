import os
import pickle
import cv2
import mediapipe as mp
import numpy as np

# Initialize Mediapipe Hands model for detecting multiple hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=True, min_detection_confidence=0.3, max_num_hands=2)

# Directory containing the dataset of images
DATA_DIR = './data'
data = []   # List to store the processed hand landmark data
labels = [] # List to store the corresponding labels for each image

# Loop through each subdirectory in the data folder
for dir_ in os.listdir(DATA_DIR):
    dir_path = os.path.join(DATA_DIR, dir_)
    if os.path.isdir(dir_path):  # Check if it's a directory
        # Loop through each image in the subdirectory
        for img_path in os.listdir(dir_path):
            img = cv2.imread(os.path.join(dir_path, img_path))  # Read the image
            if img is None:
                continue
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert image to RGB format

            # Process the image to detect hand landmarks
            results = hands.process(img_rgb)
            if results.multi_hand_landmarks:  # If hand landmarks are detected
                data_aux = []  # Temporary list to store normalized landmark data for both hands
                
                # Create a dictionary to store hand data by handedness
                hands_data = {'Left': None, 'Right': None}
                
                # Process each detected hand
                for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    # Get handedness (Left or Right)
                    handedness = results.multi_handedness[idx].classification[0].label
                    
                    x_ = []  # List to store x-coordinates of landmarks
                    y_ = []  # List to store y-coordinates of landmarks

                    # Extract x and y coordinates of each hand landmark
                    for i in range(len(hand_landmarks.landmark)):
                        x = hand_landmarks.landmark[i].x
                        y = hand_landmarks.landmark[i].y
                        x_.append(x)
                        y_.append(y)

                    # Normalize the landmarks by subtracting the minimum x and y values
                    min_x = min(x_)
                    min_y = min(y_)

                    # Store the normalized coordinates
                    hand_data = []
                    for i in range(len(hand_landmarks.landmark)):
                        x = hand_landmarks.landmark[i].x
                        y = hand_landmarks.landmark[i].y
                        hand_data.append(x - min_x)
                        hand_data.append(y - min_y)
                    
                    hands_data[handedness] = hand_data
                
                # Concatenate hand data in consistent order: Left hand first, then Right hand
                for hand_type in ['Left', 'Right']:
                    if hands_data[hand_type] is not None:
                        data_aux.extend(hands_data[hand_type])
                    else:
                        # Pad with zeros if hand is not detected (42 features per hand)
                        data_aux.extend([0.0] * 42)
                
                # Only add data if we have valid features (84 features for two hands)
                if len(data_aux) == 84:
                    data.append(data_aux)
                    labels.append(dir_)

# Save the processed data and labels into a pickle file
with open('data.pickle', 'wb') as f:
    pickle.dump({'data': data, 'labels': labels}, f)

print(f"Dataset created successfully with {len(data)} samples.")
print(f"Feature vector size: {len(data[0]) if data else 0} (84 expected for two hands)")
