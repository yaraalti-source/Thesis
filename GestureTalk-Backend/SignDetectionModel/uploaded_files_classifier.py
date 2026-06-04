"""
UPLOADED FILES CLASSIFIER
Updated to match final_classifier.py exactly:
- 1 Hand → LETTER (A-Z) using sklearn MLP (mlp_model.p)
- 2 Hands → WORD using Transformer-MLP with Mean Pooling
- Strict validation and temporal smoothing
"""

from fastapi import FastAPI, File, UploadFile
from io import BytesIO
import numpy as np
import cv2
import mediapipe as mp
import pickle
import torch
import torch.nn as nn
import os
import tempfile
from collections import deque, Counter

app = FastAPI()

# ==================== WORD MODEL CLASSES ====================
class TemporalTransformer(nn.Module):
    """Temporal Transformer used in training (256 dim, 8 heads, 6 layers)."""
    def __init__(self, input_dim=84, num_classes=300, hidden_dim=256,
                 num_heads=8, num_layers=6, dropout=0.4, num_frames=30):
        super().__init__()
        self.expects_sequence = True
        self.num_frames = num_frames
        self.hidden_dim = hidden_dim
        
        # Spatial encoder for each frame
        self.spatial_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout * 0.5)
        )
        
        # Frame positional encoding
        self.pos_encoding = nn.Parameter(torch.randn(1, num_frames, hidden_dim) * 0.02)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            activation='gelu',
            batch_first=True
        )
        self.temporal_transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # Classifier head
        self.classifier = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes)
        )
    
    def forward(self, x):
        # x: (batch, frames, 84)
        x = self.spatial_encoder(x)
        # Use only as many positional slots as frames provided
        x = x + self.pos_encoding[:, :x.shape[1], :]
        x = self.temporal_transformer(x)
        x = x.mean(dim=1)
        return self.classifier(x)


class TransformerMLPWord(nn.Module):
    """Single-frame Transformer-MLP (old 128-dim mean-pooling model)."""
    def __init__(self, input_dim=84, num_classes=300, hidden_dim=128, 
                 num_heads=4, num_layers=4, dropout=0.3, attention_heads=4):
        super().__init__()
        self.expects_sequence = False
        self.num_landmarks = 21
        self.features_per_landmark = input_dim // self.num_landmarks
        
        # Simple input projection (matches saved model)
        self.input_projection = nn.Linear(self.features_per_landmark, hidden_dim)
        
        # Positional encoding
        self.positional_encoding = nn.Parameter(
            torch.randn(1, self.num_landmarks, hidden_dim) * 0.02
        )
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            activation='gelu',
            batch_first=True,
            norm_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # Classifier matches saved model: LayerNorm(128) -> Linear(128,128) -> GELU -> Dropout -> Linear(128,300)
        self.classifier = nn.Sequential(
            nn.LayerNorm(hidden_dim),  # classifier.0: [128]
            nn.Linear(hidden_dim, hidden_dim),  # classifier.1: [128, 128]
            nn.GELU(),  # classifier.2 (no params)
            nn.Dropout(dropout),  # classifier.3 (no params)
            nn.Linear(hidden_dim, num_classes)  # classifier.4: [300, 128]
        )
    
    def forward(self, x):
        batch_size = x.shape[0]
        x = x.view(batch_size, self.num_landmarks, self.features_per_landmark)
        x = self.input_projection(x)
        x = x + self.positional_encoding
        x = self.transformer(x)
        
        # Mean pooling only (classifier expects 128, not 256)
        mean_pooled = x.mean(dim=1)
        return self.classifier(mean_pooled)

# ==================== SETUP ====================
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print("=" * 60)
print("UPLOADED FILES CLASSIFIER")
print("=" * 60)

# Letter labels (A-Z)
LETTER_LABELS = {
    0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E', 5: 'F', 6: 'G', 7: 'H', 8: 'I',
    9: 'J', 10: 'K', 11: 'L', 12: 'M', 13: 'N', 14: 'O', 15: 'P', 16: 'Q',
    17: 'R', 18: 'S', 19: 'T', 20: 'U', 21: 'V', 22: 'W', 23: 'X', 24: 'Y', 25: 'Z'
}

# ==================== LOAD LETTER MODEL (sklearn MLP) ====================
print("Loading LETTER model...")
letter_model = None
try:
    with open('./mlp_model.p', 'rb') as f:
        letter_data = pickle.load(f)
        letter_model = letter_data['model']
    print(f"[OK] LETTER model loaded - sklearn MLP")
    print(f"  Features: {letter_model.n_features_in_}")
    print(f"  Classes: A-Z (26 letters)")
except Exception as e:
    print(f"[ERROR] Letter model error: {e}")

# ==================== LOAD WORD MODEL (Transformer) ====================
print("Loading WORD model...")
word_model = None
word_labels = None
word_scaler = None
WORD_FRAMES = 30

try:
    # Accept multiple model file names
    prep_path_options = ['./preprocessing_word.pkl', './preprocessing_word .pkl']
    model_path_options = [
        './temporal_transformer_mlp_word_model.pth',
        './transformer_mlp_word_model.pth',
        './transformer_mlp_word_model (1).pth'
    ]
    prep_path = next((p for p in prep_path_options if os.path.exists(p)), None)
    model_path = next((p for p in model_path_options if os.path.exists(p)), None)
    
    if prep_path and model_path:
        with open(prep_path, 'rb') as f:
            word_prep = pickle.load(f)
            word_scaler = word_prep['scaler']
            word_encoder = word_prep.get('label_encoder', word_prep.get('encoder'))
            WORD_FRAMES = word_prep.get('num_frames', WORD_FRAMES)
        
        if word_encoder is None:
            raise ValueError("Label encoder not found in preprocessing file")
        
        num_word_classes = len(word_encoder.classes_)
        state_dict = torch.load(model_path, map_location=DEVICE, weights_only=False)
        
        # Choose architecture by inspecting checkpoint keys
        if any(k.startswith("spatial_encoder") for k in state_dict.keys()):
            # New temporal transformer (256/8/6, sequences)
            word_model = TemporalTransformer(
                input_dim=84, 
                num_classes=num_word_classes,
                hidden_dim=256,
                num_heads=8,
                num_layers=6,
                dropout=0.4,
                num_frames=WORD_FRAMES
            ).to(DEVICE)
        else:
            # Old single-frame transformer-MLP (128/4/4)
            word_model = TransformerMLPWord(
                input_dim=84,
                num_classes=num_word_classes,
                hidden_dim=128,
                num_heads=4,
                num_layers=4,
                dropout=0.3
            ).to(DEVICE)
            WORD_FRAMES = 1  # Old model uses 1 frame
        
        word_model.load_state_dict(state_dict)
        word_model.eval()
        
        word_labels = {i: str(c).upper() for i, c in enumerate(word_encoder.classes_)}
        if getattr(word_model, "expects_sequence", False):
            print(f"[OK] WORD model loaded - Temporal Transformer")
            print(f"  Architecture: 256/8/6, frames={WORD_FRAMES}")
        else:
            print(f"[OK] WORD model loaded - Single-frame Transformer-MLP")
            print(f"  Architecture: 128/4/4 (mean pooling)")
        print(f"  Classes: {num_word_classes} words")
        print(f"  Sample words: {list(word_labels.values())[:10]}...")
    else:
        print("[ERROR] WORD model files not found")
        print(f"  Required: preprocessing_word.pkl and one of: {model_path_options}")
except Exception as e:
    print(f"[ERROR] Word model error: {e}")
    import traceback
    traceback.print_exc()
    # Reset model to None if loading failed
    word_model = None
    word_labels = None
    word_scaler = None

# ==================== MEDIAPIPE SETUP (Updated Dec 16, 2025) ====================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=True,
    min_detection_confidence=0.6,  # 60% detection confidence - prevents false detections
    min_tracking_confidence=0.5,  # 50% tracking confidence
    max_num_hands=2
)

# Configuration (Updated - more lenient like websocket for better detection)
MIN_HAND_DISTANCE = 0.05  # Hands must be 5% of frame apart
MIN_HANDEDNESS_CONFIDENCE = 0.5  # RELAXED: 50% confidence required (was 70%) - like websocket
MIN_HANDEDNESS_CONFIDENCE_LETTER = 0.7  # 70% confidence for single hand
MIN_HAND_SIZE_LETTER = 0.05  # Minimum hand size 5% of frame for letters
MIN_HAND_SIZE_WORD = 0.02  # RELAXED: 2% minimum hand size (was 5%) - like websocket
MAX_HAND_SIZE_RATIO = 4.0  # RELAXED: 4.0 max ratio (was 3.5) - like websocket

# Smoothing & Consistency (Updated Dec 16, 2025)
SMOOTH_FRAMES = 20  # Maximum smoothing for highest accuracy
CONSISTENCY_THRESHOLD = 12  # Require 12 out of 20 frames (60% consistency)
MIN_CONFIDENCE_LETTER = 0.25  # Minimum 25% confidence for letters
MIN_CONFIDENCE_WORD = 0.25  # Minimum 25% confidence for words (SAME as letters)
MIN_CONFIDENCE_DISPLAY = 0.10  # Minimum 10% confidence to display

# Prediction lock settings
PREDICTION_LOCK_DURATION = 100  # Frames to lock prediction once stable
UNLOCK_CONFIDENCE_DROP = 0.15  # 15% confidence drop triggers unlock
UNLOCK_CONFIDENCE_GAP = 0.12  # New prediction must be 12%+ better to unlock

# Temporal smoothing
hand_count_history = deque(maxlen=5)
CONSISTENT_FRAMES_NEEDED = 1  # Immediate switching (like websocket)

print("=" * 60)
print("1 HAND  = LETTER (A-Z)")
print("2 HANDS = WORD")
print("=" * 60)


def get_hand_center(landmarks):
    """Get center point of hand landmarks"""
    x_coords = [lm.x for lm in landmarks.landmark]
    y_coords = [lm.y for lm in landmarks.landmark]
    return (sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords))


def get_hand_size(landmarks):
    """Get bounding box size of hand"""
    x_coords = [lm.x for lm in landmarks.landmark]
    y_coords = [lm.y for lm in landmarks.landmark]
    width = max(x_coords) - min(x_coords)
    height = max(y_coords) - min(y_coords)
    return max(width, height)  # Return the larger dimension


def validate_hand_shape(landmarks):
    """
    Validate that detected landmarks form a proper hand shape.
    Checks finger proportions and hand structure to filter out false positives (mouse, etc.)
    (Updated Dec 16, 2025)
    """
    try:
        # Get key landmarks (wrist, fingertips, palm)
        wrist = landmarks.landmark[0]
        thumb_tip = landmarks.landmark[4]
        index_tip = landmarks.landmark[8]
        middle_tip = landmarks.landmark[12]
        ring_tip = landmarks.landmark[16]
        pinky_tip = landmarks.landmark[20]
        
        # Calculate distances from wrist to fingertips
        def distance(p1, p2):
            return ((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)**0.5
        
        thumb_dist = distance(wrist, thumb_tip)
        index_dist = distance(wrist, index_tip)
        middle_dist = distance(wrist, middle_tip)
        ring_dist = distance(wrist, ring_tip)
        pinky_dist = distance(wrist, pinky_tip)
        
        # Check if all fingertips are at reasonable distances from wrist
        min_dist = 0.15  # Minimum distance from wrist to fingertip
        max_dist = 0.6   # Maximum distance from wrist to fingertip
        
        distances = [thumb_dist, index_dist, middle_dist, ring_dist, pinky_dist]
        
        # At least 3 fingers should be within valid range
        valid_fingers = sum(1 for d in distances if min_dist < d < max_dist)
        if valid_fingers < 3:
            return False
        
        # Check that middle finger is typically longest (or close)
        if middle_dist < max(distances) * 0.7:
            return False
        
        # Check finger spread - fingers shouldn't be too close together
        finger_tips = [index_tip, middle_tip, ring_tip, pinky_tip]
        spreads = []
        for i in range(len(finger_tips) - 1):
            spread = distance(finger_tips[i], finger_tips[i+1])
            spreads.append(spread)
        
        # Average spread should be reasonable (not too small like a mouse)
        avg_spread = sum(spreads) / len(spreads)
        if avg_spread < 0.03:  # Fingers too close together
            return False
        
        return True
        
    except Exception as e:
        # If validation fails, reject the detection
        return False


def validate_two_hands(results):
    """
    RELAXED validation for 2 hands (like websocket_final_classifier.py).
    Returns True only if ALL conditions are met:
    - Exactly 2 hands detected
    - Both have reasonable confidence (50%+)
    - Hands are far apart (5%+ of frame)
    - Both hands are reasonable size (2%+)
    - Hand sizes are similar (not one tiny false detection)
    Note: Shape validation removed for uploaded files (too strict for static images)
    """
    print(f"[VALIDATION] Starting 2-hand validation...")
    if len(results.multi_hand_landmarks) != 2:
        print(f"[VALIDATION] ❌ Failed: Expected 2 hands, got {len(results.multi_hand_landmarks)}")
        return False
    
    # Check handedness confidence
    for idx, hand_info in enumerate(results.multi_handedness):
        confidence = hand_info.classification[0].score
        if confidence < MIN_HANDEDNESS_CONFIDENCE:
            print(f"[VALIDATION] ❌ Failed: Hand {idx} confidence {confidence:.3f} < {MIN_HANDEDNESS_CONFIDENCE}")
            return False
        print(f"[VALIDATION] ✓ Hand {idx} confidence: {confidence:.3f}")
    
    # REMOVED: Shape validation - too strict for static images
    # For uploaded files, we trust MediaPipe's detection more
    
    # Check distance between hands
    center1 = get_hand_center(results.multi_hand_landmarks[0])
    center2 = get_hand_center(results.multi_hand_landmarks[1])
    distance = ((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)**0.5
    print(f"[VALIDATION] Distance between hands: {distance:.4f} (min required: {MIN_HAND_DISTANCE})")
    if distance < MIN_HAND_DISTANCE:
        print(f"[VALIDATION] ❌ Failed: Distance {distance:.4f} < {MIN_HAND_DISTANCE}")
        return False
    
    # Check hand sizes
    size1 = get_hand_size(results.multi_hand_landmarks[0])
    size2 = get_hand_size(results.multi_hand_landmarks[1])
    print(f"[VALIDATION] Hand sizes: {size1:.4f}, {size2:.4f} (min required: {MIN_HAND_SIZE_WORD})")
    
    # Both hands must be minimum size
    if size1 < MIN_HAND_SIZE_WORD or size2 < MIN_HAND_SIZE_WORD:
        print(f"[VALIDATION] ❌ Failed: Hand size too small (size1={size1:.4f}, size2={size2:.4f} < {MIN_HAND_SIZE_WORD})")
        return False
    
    # Hand sizes should be similar (prevent false tiny detection)
    if min(size1, size2) > 0:
        size_ratio = max(size1, size2) / min(size1, size2)
        print(f"[VALIDATION] Hand size ratio: {size_ratio:.2f} (max allowed: {MAX_HAND_SIZE_RATIO})")
        if size_ratio > MAX_HAND_SIZE_RATIO:
            print(f"[VALIDATION] ❌ Failed: Size ratio {size_ratio:.2f} > {MAX_HAND_SIZE_RATIO}")
            return False
    
    print(f"[VALIDATION] ✅ All checks passed - 2 hands validated!")
    return True


def validate_one_hand(results):
    """
    Validate 1 hand detection with proper checks to prevent false positives.
    (Updated Dec 16, 2025)
    """
    if not results or not results.multi_hand_landmarks:
        return False
        
    # Check if exactly 1 hand detected
    if len(results.multi_hand_landmarks) != 1:
        return False
    
    # Check handedness confidence
    if results.multi_handedness:
        confidence = results.multi_handedness[0].classification[0].score
        if confidence < MIN_HANDEDNESS_CONFIDENCE_LETTER:
            return False
    
    # Check hand size (prevents small objects like mouse)
    hand_size = get_hand_size(results.multi_hand_landmarks[0])
    if hand_size < MIN_HAND_SIZE_LETTER:
        return False
    
    # Validate hand shape (prevents non-hand objects)
    if not validate_hand_shape(results.multi_hand_landmarks[0]):
        return False
    
    return True


def get_stable_hand_count(current_count):
    """
    Use temporal smoothing to get stable hand count.
    More lenient - immediately switch to word mode when 2 hands detected (like websocket).
    """
    hand_count_history.append(current_count)
    
    # If we detect 2 hands, immediately switch to word mode (no delay)
    if current_count == 2:
        return 2
    
    # Only require 1 frame of single hand to switch back to letter mode
    if len(hand_count_history) < 1:
        return 1
    
    ones = sum(1 for c in hand_count_history if c == 1)
    # Need at least 2 consecutive single-hand frames to switch to letter mode
    return 1 if ones >= 2 else 2


def process_frame(frame: np.ndarray, letter_history=None, word_history=None, 
                  letter_prediction_history=None, word_prediction_history=None,
                  locked_letter=None, locked_letter_frames=0, locked_letter_confidence_history=None,
                  locked_word=None, locked_word_frames=0, locked_word_confidence_history=None) -> dict:
    """
    Process a single frame to predict the hand sign (Updated Dec 16, 2025).
    Uses STRICT validation, temporal smoothing, and prediction locking.
    Returns dict with 'type' (letter/word), 'prediction', 'confidence', and 'locked' flag
    """
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)
    
    if not results.multi_hand_landmarks:
        if letter_history is not None:
            letter_history.clear()
        if word_history is not None:
            word_history.clear()
        if letter_prediction_history is not None:
            letter_prediction_history.clear()
        if word_prediction_history is not None:
            word_prediction_history.clear()
        hand_count_history.clear()  # Reset history when no hands
        print("[DEBUG] No hands detected in frame")
        return {"type": "none", "prediction": "", "confidence": 0.0, "locked": False}
    
    raw_num_hands = len(results.multi_hand_landmarks)
    
    # Determine if this is truly 2 valid hands
    is_valid_two_hands = raw_num_hands == 2 and validate_two_hands(results)
    
    print(f"[DEBUG] raw_num_hands={raw_num_hands}, is_valid_two_hands={is_valid_two_hands}")
    print(f"[DEBUG] word_model loaded: {word_model is not None}, word_scaler: {word_scaler is not None}, word_labels: {word_labels is not None}")
    
    # Use temporal smoothing for stable mode switching
    current_detection = 2 if is_valid_two_hands else 1
    stable_hand_count = get_stable_hand_count(current_detection)
    
    # ==================== 2 HANDS = WORD (Updated Dec 16, 2025) ====================
    # CRITICAL: Check raw_num_hands directly first (like websocket_final_classifier.py)
    # This ensures 2 hands are processed as words immediately, not after temporal smoothing
    if raw_num_hands == 2 and is_valid_two_hands and word_model and word_scaler and word_labels:
        print(f"[DEBUG] ✅ Entering 2-HAND WORD processing section")
        if letter_history is not None:
            letter_history.clear()
        if letter_prediction_history is not None:
            letter_prediction_history.clear()
        
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
        
        # Combine both hands data (Left first, then Right)
        combined = []
        for ht in ['Left', 'Right']:
            combined.extend(hands_data[ht] if hands_data[ht] else [0.0] * 42)
        
        if len(combined) == 84:
            data_scaled = word_scaler.transform([combined])[0]
            
            # Handle both model types
            if getattr(word_model, "expects_sequence", False):
                # TemporalTransformer needs sequences
                # For single frame processing, repeat the frame to create a sequence
                # This is a workaround for images; videos should collect actual frames
                sequence = np.tile(data_scaled, (WORD_FRAMES, 1))  # Repeat frame WORD_FRAMES times
                input_tensor = torch.FloatTensor(sequence).unsqueeze(0).to(DEVICE)  # [1, frames, 84]
            else:
                # TransformerMLPWord uses single frame
                input_tensor = torch.FloatTensor(data_scaled).unsqueeze(0).to(DEVICE)  # [1, 84]
            
            with torch.no_grad():
                outputs = word_model(input_tensor)
                probs = torch.softmax(outputs, dim=1)[0].cpu().numpy()
            
            # Apply smoothing if history provided (for probability smoothing, not frame collection)
            if word_history is not None:
                word_history.append(probs)
                avg_probs = np.mean(list(word_history), axis=0)
            else:
                avg_probs = probs
            
            # Get highest confidence prediction
            top_idx = np.argmax(avg_probs)
            confidence = float(avg_probs[top_idx])
            
            # Safety check for word_labels
            if word_labels is None or top_idx >= len(word_labels):
                return {"type": "error", "prediction": "Word model error", "confidence": 0.0, "locked": False}
            
            predicted = word_labels[top_idx]
            
            # Track prediction for consistency
            if word_prediction_history is not None:
                word_prediction_history.append(predicted)
            
            # ALWAYS USE HIGHEST CONFIDENCE (Updated Dec 16, 2025)
            stable_predicted = predicted
            confidence_highest = confidence
            
            # Filter to words only (2+ chars)
            if len(stable_predicted) == 1:
                # Single char - try to find valid word with good confidence
                top_candidates = np.argsort(avg_probs)[-10:][::-1]
                for idx in top_candidates:
                    if len(word_labels[idx]) > 1 and avg_probs[idx] >= MIN_CONFIDENCE_WORD:
                        stable_predicted = word_labels[idx]
                        confidence_highest = float(avg_probs[idx])
                        break
            
            # Return prediction if it meets confidence threshold
            # For uploaded files, use lower threshold (10%) to ensure we return something
            min_threshold = MIN_CONFIDENCE_DISPLAY  # 10% for uploaded files
            print(f"[DEBUG] Word prediction: '{stable_predicted}', confidence: {confidence_highest:.2%}, threshold: {min_threshold:.2%}")
            if len(stable_predicted) > 1 and confidence_highest >= min_threshold:
                print(f"[DEBUG] Returning word: {stable_predicted}")
                return {"type": "word", "prediction": stable_predicted, "confidence": confidence_highest, "locked": False}
            elif len(stable_predicted) > 1:
                # Return even if below threshold for debugging
                print(f"[DEBUG] Returning word below threshold: {stable_predicted} ({confidence_highest:.2%})")
                return {"type": "word", "prediction": stable_predicted, "confidence": confidence_highest, "locked": False}
            else:
                print(f"[DEBUG] No valid word found (predicted: '{stable_predicted}', confidence: {confidence_highest:.2%})")
                return {"type": "word", "prediction": "", "confidence": confidence_highest, "locked": False}
    elif raw_num_hands == 2:
        # 2 hands detected but word processing didn't happen - log why
        print(f"[DEBUG] ⚠️ 2 hands detected but word section skipped:")
        print(f"  - is_valid_two_hands: {is_valid_two_hands}")
        print(f"  - word_model: {word_model is not None}")
        print(f"  - word_scaler: {word_scaler is not None}")
        print(f"  - word_labels: {word_labels is not None}")
        # Don't fall through to letter mode - return empty
        return {"type": "word", "prediction": "", "confidence": 0.0, "locked": False}
    
    # ==================== 1 HAND = LETTER (Updated Dec 16, 2025) ====================
    # CRITICAL: Only process letters if we have exactly 1 hand
    # If 2 hands are detected (even if validation failed), don't process as letter
    if raw_num_hands == 1 and letter_model:
        print(f"[DEBUG] ✅ Entering 1-HAND LETTER processing section")
        if word_history is not None:
            word_history.clear()
        if word_prediction_history is not None:
            word_prediction_history.clear()
        
        # Pick the hand with highest confidence
        best_hand_idx = 0
        if raw_num_hands > 1:
            confidences = [h.classification[0].score for h in results.multi_handedness]
            best_hand_idx = confidences.index(max(confidences))
        
        hand_landmarks = results.multi_hand_landmarks[best_hand_idx]
        
        x_ = [lm.x for lm in hand_landmarks.landmark]
        y_ = [lm.y for lm in hand_landmarks.landmark]
        min_x, min_y = min(x_), min(y_)
        
        hand_data = []
        for lm in hand_landmarks.landmark:
            hand_data.append(lm.x - min_x)
            hand_data.append(lm.y - min_y)
        
        if len(hand_data) == 42:
            probs = letter_model.predict_proba([np.array(hand_data)])[0]
            
            # Apply smoothing if history provided
            if letter_history is not None:
                letter_history.append(probs)
                avg_probs = np.mean(list(letter_history), axis=0)
            else:
                avg_probs = probs
            
            # ALWAYS USE HIGHEST CONFIDENCE (Updated Dec 16, 2025)
            top_idx = np.argmax(avg_probs)
            confidence = float(avg_probs[top_idx])
            predicted = LETTER_LABELS[top_idx]
            
            # Track prediction for consistency
            if letter_prediction_history is not None:
                letter_prediction_history.append(predicted)
            
            # Return prediction if it meets confidence threshold
            # For uploaded files, use lower threshold (10%) to ensure we return something
            min_threshold = MIN_CONFIDENCE_DISPLAY  # 10% for uploaded files
            print(f"[DEBUG] Letter prediction: '{predicted}', confidence: {confidence:.2%}, threshold: {min_threshold:.2%}")
            if confidence >= min_threshold:
                print(f"[DEBUG] Returning letter: {predicted}")
                return {"type": "letter", "prediction": predicted, "confidence": confidence, "locked": False}
            else:
                # Return even if below threshold for debugging
                print(f"[DEBUG] Returning letter below threshold: {predicted} ({confidence:.2%})")
                return {"type": "letter", "prediction": predicted if confidence > 0.05 else "", "confidence": confidence, "locked": False}
    
    return {"type": "none", "prediction": "", "confidence": 0.0, "locked": False}


@app.post("/predict_image")
async def predict_image(file: UploadFile = File(...)):
    """Predict the sign language character from an uploaded image (Updated Dec 16, 2025)."""
    image = np.frombuffer(await file.read(), np.uint8)
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    
    if image is None:
        return {"type": "error", "translation": "Invalid image file", "confidence": 0.0, "locked": False}
    
    # Initialize smoothing for single image
    letter_history = deque(maxlen=SMOOTH_FRAMES)
    word_history = deque(maxlen=SMOOTH_FRAMES)
    letter_prediction_history = deque(maxlen=SMOOTH_FRAMES)
    word_prediction_history = deque(maxlen=SMOOTH_FRAMES)
    
    result = process_frame(image, letter_history, word_history, 
                          letter_prediction_history, word_prediction_history)
    
    # Debug logging
    print(f"[IMAGE] Type: {result['type']}, Prediction: '{result['prediction']}', Confidence: {result['confidence']:.2%}")
    
    # If no prediction but we detected something, provide helpful message
    if not result["prediction"]:
        if result["type"] == "none":
            result["prediction"] = "No hands detected"
        elif result["type"] == "word" and result["confidence"] > 0:
            # Word detected but confidence too low - return it anyway for debugging
            result["prediction"] = f"Low confidence word ({(result['confidence']*100):.1f}%)"
        elif result["type"] == "letter" and result["confidence"] > 0:
            # Letter detected but confidence too low - return it anyway for debugging
            result["prediction"] = f"Low confidence letter ({(result['confidence']*100):.1f}%)"
    
    return {
        "type": result["type"],
        "translation": result["prediction"] if result["prediction"] else "",
        "confidence": round(result["confidence"] * 100, 2),
        "locked": result.get("locked", False)
    }


@app.post("/predict_video")
async def predict_video(file: UploadFile = File(...)):
    """Predict the sign language characters from an uploaded video (Updated Dec 16, 2025)."""
    
    # Use temporary file with proper cleanup
    temp_video_path = None
    try:
        # Create temporary file
        temp_fd, temp_video_path = tempfile.mkstemp(suffix='.mp4')
        os.close(temp_fd)
        
        # Stream file in chunks to avoid memory issues
        with open(temp_video_path, 'wb') as f:
            while True:
                chunk = await file.read(8192)  # Read in 8KB chunks
                if not chunk:
                    break
                f.write(chunk)

        video_capture = cv2.VideoCapture(temp_video_path)
        if not video_capture.isOpened():
            return {"message": "Error opening video file"}

        # Get video properties
        fps = video_capture.get(cv2.CAP_PROP_FPS)
        total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        video_duration = total_frames / fps if fps > 0 else 0
        
        # Limit video processing to 60 seconds max to prevent timeouts
        MAX_VIDEO_DURATION = 60.0
        if video_duration > MAX_VIDEO_DURATION:
            video_capture.release()
            return {
                "message": f"Video too long ({video_duration:.1f}s). Maximum duration is {MAX_VIDEO_DURATION} seconds.",
                "translation": "",
                "details": []
            }
        
        # Optimize frame sampling: process every 0.5 seconds (or every frame if FPS < 2)
        # This balances accuracy with processing speed
        if fps > 2:
            interval = max(1, int(fps * 0.5))  # Process every 0.5 seconds
        else:
            interval = 1  # Process every frame for very low FPS videos
        
        print(f"[VIDEO] Processing video: {total_frames} frames, {fps:.2f} FPS, {video_duration:.2f}s duration")
        print(f"[VIDEO] Processing every {interval} frame(s)")

        # Initialize smoothing for video processing
        letter_history = deque(maxlen=SMOOTH_FRAMES)
        word_history = deque(maxlen=SMOOTH_FRAMES)
        letter_prediction_history = deque(maxlen=SMOOTH_FRAMES)
        word_prediction_history = deque(maxlen=SMOOTH_FRAMES)

        predictions = []
        frame_count = 0
        processed_frames = 0
        max_frames_to_process = 300  # Limit to prevent excessive processing
        
        while True:
            ret, frame = video_capture.read()
            if not ret:
                break
            frame_count += 1
            
            # Process frame at interval
            if frame_count % interval == 0:
                if processed_frames >= max_frames_to_process:
                    print(f"[VIDEO] Reached max processing limit ({max_frames_to_process} frames)")
                    break
                
                result = process_frame(frame, letter_history, word_history, 
                                      letter_prediction_history, word_prediction_history)
                processed_frames += 1
                
                if result["prediction"]:
                    predictions.append({
                        "type": result["type"],
                        "prediction": result["prediction"],
                        "confidence": round(result["confidence"] * 100, 2),
                        "frame": frame_count,
                        "locked": result.get("locked", False)
                    })

        video_capture.release()
        print(f"[VIDEO] Processed {processed_frames} frames, found {len(predictions)} predictions")

        # Build translation string
        translation = ""
        for p in predictions:
            if p["type"] == "word":
                translation += p["prediction"] + " "
            else:
                translation += p["prediction"]

        return {
            "translation": translation.strip(),
            "details": predictions
        }
    except Exception as e:
        print(f"[VIDEO] Error processing video: {e}")
        import traceback
        traceback.print_exc()
        return {
            "message": f"Error processing video: {str(e)}",
            "translation": "",
            "details": []
        }
    finally:
        # Clean up temporary file
        if temp_video_path and os.path.exists(temp_video_path):
            try:
                os.remove(temp_video_path)
            except Exception as e:
                print(f"[VIDEO] Error removing temp file: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "letter_model": letter_model is not None,
        "word_model": word_model is not None,
        "device": str(DEVICE)
    }
