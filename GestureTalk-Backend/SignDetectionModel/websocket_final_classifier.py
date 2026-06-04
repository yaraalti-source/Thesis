"""
WEBSOCKET SERVER FOR FINAL CLASSIFIER
======================================
WebSocket server that uses the same models and logic as final_classifier.py
- 1 Hand → LETTER (A-Z) using sklearn MLP
- 2 Hands → WORD using Transformer-MLP (temporal or single-frame)
"""

import asyncio
import websockets
import cv2
import mediapipe as mp
import numpy as np
import pickle
import torch
import torch.nn as nn
import os
import json
import glob
from collections import deque, Counter

# Import NLP processor (optional)
try:
    from nlp_processor import improve_translation
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False
    def improve_translation(text, is_sentence=True):
        return text

# ==================== MODEL ARCHITECTURES (from final_classifier.py) ====================
class MultiHeadAttentionPooling(nn.Module):
    """Professional multi-head attention pooling layer (not used in 77.33% model)"""
    def __init__(self, hidden_dim, num_heads=4):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.head_dim = hidden_dim // num_heads
        
        assert hidden_dim % num_heads == 0, "hidden_dim must be divisible by num_heads"
        
        self.q_proj = nn.Linear(hidden_dim, hidden_dim)
        self.k_proj = nn.Linear(hidden_dim, hidden_dim)
        self.v_proj = nn.Linear(hidden_dim, hidden_dim)
        self.out_proj = nn.Linear(hidden_dim, hidden_dim)
        self.dropout = nn.Dropout(0.1)
        self.scale = self.head_dim ** -0.5
        
    def forward(self, x):
        batch_size, seq_len, _ = x.shape
        query = self.q_proj(x.mean(dim=1, keepdim=True))
        key = self.k_proj(x)
        value = self.v_proj(x)
        
        query = query.view(batch_size, 1, self.num_heads, self.head_dim).transpose(1, 2)
        key = key.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        value = value.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        
        scores = torch.matmul(query, key.transpose(-2, -1)) * self.scale
        attn_weights = torch.softmax(scores, dim=-1)
        attn_weights = self.dropout(attn_weights)
        
        attn_output = torch.matmul(attn_weights, value)
        attn_output = attn_output.transpose(1, 2).contiguous()
        attn_output = attn_output.view(batch_size, 1, self.hidden_dim)
        output = self.out_proj(attn_output)
        return output.squeeze(1)


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
                 num_heads=4, num_layers=4, dropout=0.3):
        super().__init__()
        self.expects_sequence = False
        self.num_landmarks = 21
        self.features_per_landmark = input_dim // self.num_landmarks
        
        self.input_projection = nn.Linear(self.features_per_landmark, hidden_dim)
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
        
        self.classifier = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes)
        )
    
    def forward(self, x):
        # x: (batch, 84)
        batch_size = x.shape[0]
        x = x.view(batch_size, self.num_landmarks, self.features_per_landmark)
        x = self.input_projection(x)
        x = x + self.positional_encoding
        x = self.transformer(x)
        x = x.mean(dim=1)
        return self.classifier(x)

# ==================== SETUP ====================
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print("="*60)
print("WEBSOCKET FINAL CLASSIFIER SERVER")
print("="*60)
print(f"Device: {DEVICE}")

# All 26 letters
LETTER_LABELS = {
    0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E', 5: 'F', 6: 'G', 7: 'H', 8: 'I',
    9: 'J', 10: 'K', 11: 'L', 12: 'M', 13: 'N', 14: 'O', 15: 'P', 16: 'Q',
    17: 'R', 18: 'S', 19: 'T', 20: 'U', 21: 'V', 22: 'W', 23: 'X', 24: 'Y', 25: 'Z'
}

# ==================== LOAD LETTER MODEL (sklearn MLP) ====================
print("\nLoading LETTER model...")
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

# ==================== LOAD WORD MODEL (Temporal Transformer) ====================
print("\nLoading WORD model...")
word_model = None
word_labels = None
word_scaler = None
WORD_FRAMES = 30

try:
    # Accept either original or spaced filenames
    prep_path_options = ['./preprocessing_word.pkl', './preprocessing_word .pkl']
    # Updated to match actual filenames in the directory
    model_path_options = [
        './temporal_transformer_mlp_word_model.pth',  # Primary: Temporal Transformer model
        './transformer_mlp_word_model.pth',  # Fallback: Single-frame Transformer-MLP model
        './temporal_transformer_model.pth',  # Alternative name
        './transformer_mlp_word_model (1).pth'  # Alternative name with space
    ]
    prep_path = next((p for p in prep_path_options if os.path.exists(p)), None)
    model_path = next((p for p in model_path_options if os.path.exists(p)), None)

    if prep_path and model_path:
        with open(prep_path, 'rb') as f:
            word_prep = pickle.load(f)
            word_scaler = word_prep['scaler']
            word_encoder = word_prep.get('label_encoder', word_prep.get('encoder'))
            WORD_FRAMES = word_prep.get('num_frames', WORD_FRAMES)
            WORD_FRAMES_BUFFER = WORD_FRAMES
        
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
            # Old model uses 1 frame; reset buffer to 1
            WORD_FRAMES = 1
            WORD_FRAMES_BUFFER = 1
        
        word_model.load_state_dict(state_dict)
        word_model.eval()
        print(f"[MODEL LOAD] ✅ Word model state dict loaded successfully")
        print(f"[MODEL LOAD] Model device: {next(word_model.parameters()).device}")
        print(f"[MODEL LOAD] Model expects_sequence: {getattr(word_model, 'expects_sequence', False)}")
        
        word_labels = {i: str(c).upper() for i, c in enumerate(word_encoder.classes_)}
        if getattr(word_model, "expects_sequence", False):
            print(f"[OK] WORD model loaded - Temporal Transformer")
            print(f"  Architecture: 256/8/6, frames={WORD_FRAMES}")
        else:
            print(f"[OK] WORD model loaded - Single-frame Transformer-MLP")
            print(f"  Architecture: 128/4/4 (mean pooling)")
        print(f"  Classes: {num_word_classes} words")
        print(f"  Sample words: {list(word_labels.values())[:10]}...")
        print(f"[MODEL LOAD] ✅✅✅ WORD MODEL FULLY LOADED AND READY")
        
        # Check if word labels are actually words or letters
        sample_labels = list(word_labels.values())[:20]
        letter_count = sum(1 for label in sample_labels if len(label) == 1 and label.isalpha())
        word_count = sum(1 for label in sample_labels if len(label) > 1)
        print(f"  Label check: {letter_count} single letters, {word_count} multi-character words in first 20 labels")
        if letter_count > word_count:
            print(f"  ⚠️  WARNING: Word model appears to contain mostly single letters!")
    else:
        print("[ERROR] WORD model files not found")
        print(f"  Preprocessing file checked: {prep_path_options}")
        print(f"  Preprocessing file found: {prep_path}")
        print(f"  Model file checked: {model_path_options}")
        print(f"  Model file found: {model_path}")
        print("  Required: preprocessing_word.pkl and one of the model files")
        print("  Available model files in directory:")
        for f in glob.glob('./*.pth'):
            print(f"    - {f}")
        for f in glob.glob('./*.pkl'):
            print(f"    - {f}")
except Exception as e:
    print(f"[ERROR] Word model error: {e}")
    import traceback
    traceback.print_exc()
    word_model = None
    word_labels = None
    word_scaler = None

# ==================== SMOOTHING ====================
SMOOTH_FRAMES = 5  # For word predictions
LETTER_SMOOTH_FRAMES = 3  # Reduced for faster letter response
STABLE_COUNT = 3
LETTER_STABLE_COUNT = 2  # Reduced for faster letter response
WORD_FRAMES_BUFFER = 30  # will be overwritten by preprocessing (used only for model input size, no actual buffering)

# ==================== MEDIAPIPE ====================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    min_detection_confidence=0.7,  # Relaxed from 0.8 for better detection
    min_tracking_confidence=0.7,  # Relaxed from 0.8
    max_num_hands=2
)

# STRICT validation thresholds - ONLY allow word mode with 2 hands
# RELAXED: Made less strict to prevent false rejections
MIN_HAND_DISTANCE = 0.05  # RELAXED from 0.08 - hands must be 5% of frame apart (was 8%)
MIN_HANDEDNESS_CONFIDENCE = 0.5  # RELAXED from 0.6 - 50% confidence required (was 60%)
MIN_HAND_SIZE = 0.02  # RELAXED from 0.03 - minimum hand bounding box size (was 3%)
MAX_HAND_SIZE_RATIO = 4.0  # RELAXED from 3.5 - max ratio between hand sizes (was 3.5)
hand_count_history = deque(maxlen=5)  # Smaller temporal smoothing window
CONSISTENT_FRAMES_NEEDED = 1  # Immediate switching


def get_hand_center(landmarks):
    x_coords = [lm.x for lm in landmarks.landmark]
    y_coords = [lm.y for lm in landmarks.landmark]
    return (sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords))


def get_hand_size(landmarks):
    x_coords = [lm.x for lm in landmarks.landmark]
    y_coords = [lm.y for lm in landmarks.landmark]
    return max(max(x_coords) - min(x_coords), max(y_coords) - min(y_coords))


def validate_two_hands(results):
    """STRICT validation for 2 hands - prevents false two-hand detection"""
    print(f"[VALIDATION] ========== Starting 2-hand validation ==========")
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
    
    # Check distance between hands - must be far enough apart
    center1 = get_hand_center(results.multi_hand_landmarks[0])
    center2 = get_hand_center(results.multi_hand_landmarks[1])
    distance = ((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)**0.5
    print(f"[VALIDATION] Distance between hands: {distance:.4f} (min required: {MIN_HAND_DISTANCE})")
    if distance < MIN_HAND_DISTANCE:
        print(f"[VALIDATION] ❌ Failed: Distance {distance:.4f} < {MIN_HAND_DISTANCE}")
        return False
    
    # Check hand sizes - both must be reasonable size
    size1 = get_hand_size(results.multi_hand_landmarks[0])
    size2 = get_hand_size(results.multi_hand_landmarks[1])
    print(f"[VALIDATION] Hand sizes: {size1:.4f}, {size2:.4f} (min required: {MIN_HAND_SIZE})")
    if size1 < MIN_HAND_SIZE or size2 < MIN_HAND_SIZE:
        print(f"[VALIDATION] ❌ Failed: Hand size too small (size1={size1:.4f}, size2={size2:.4f} < {MIN_HAND_SIZE})")
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


def get_stable_hand_count(current_count):
    """Temporal smoothing for stable mode switching - more lenient for word detection"""
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


def extract_hand_features(frame):
    """Extract hand features from frame - returns (features, num_hands, is_valid_two_hands, results)"""
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)
    
    if not results.multi_hand_landmarks:
        return None, 0, False, results
    
    raw_num_hands = len(results.multi_hand_landmarks)
    is_valid_two_hands = raw_num_hands == 2 and validate_two_hands(results)
    
    # ==================== 1 HAND: LETTER ====================
    if raw_num_hands == 1:
        print(f"[FEATURE EXTRACTION] 1 hand detected - extracting letter features (42)")
        hand_landmarks = results.multi_hand_landmarks[0]
        x_ = [lm.x for lm in hand_landmarks.landmark]
        y_ = [lm.y for lm in hand_landmarks.landmark]
        
        min_x, min_y = min(x_), min(y_)
        hand_data = []
        for lm in hand_landmarks.landmark:
            hand_data.append(lm.x - min_x)
            hand_data.append(lm.y - min_y)
        
        features_array = np.array(hand_data, dtype=np.float32)
        print(f"[FEATURE EXTRACTION] Returning: features_length={len(features_array)}, num_hands=1")
        return features_array, 1, False, results
    
    # ==================== 2 HANDS: WORD ====================
    elif raw_num_hands == 2:
        print(f"[FEATURE EXTRACTION] 2 hands detected - extracting word features (84)")
        print(f"[FEATURE EXTRACTION] is_valid_two_hands={is_valid_two_hands}")
        hands_data = {'Left': None, 'Right': None}
        
        for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
            handedness = results.multi_handedness[idx].classification[0].label
            print(f"[FEATURE EXTRACTION] Hand {idx}: {handedness}")
            x_ = [lm.x for lm in hand_landmarks.landmark]
            y_ = [lm.y for lm in hand_landmarks.landmark]
            
            min_x, min_y = min(x_), min(y_)
            hand_data = []
            for lm in hand_landmarks.landmark:
                hand_data.append(lm.x - min_x)
                hand_data.append(lm.y - min_y)
            hands_data[handedness] = hand_data
            print(f"[FEATURE EXTRACTION] {handedness} hand features: {len(hand_data)} values")
        
        # Combine both hands data (Left first, then Right)
        combined = []
        if hands_data['Left'] is not None and hands_data['Right'] is not None:
            combined.extend(hands_data['Left'])
            combined.extend(hands_data['Right'])
        elif len(results.multi_hand_landmarks) == 2:
            # Two hands detected but not labeled as Left/Right - use them in order
            for idx in range(2):
                hand_landmarks = results.multi_hand_landmarks[idx]
                x_ = [lm.x for lm in hand_landmarks.landmark]
                y_ = [lm.y for lm in hand_landmarks.landmark]
                min_x, min_y = min(x_), min(y_)
                hand_data = []
                for lm in hand_landmarks.landmark:
                    hand_data.append(lm.x - min_x)
                    hand_data.append(lm.y - min_y)
                combined.extend(hand_data)
        else:
            # Fallback: pad with zeros
            for ht in ['Left', 'Right']:
                combined.extend(hands_data[ht] if hands_data[ht] else [0.0]*42)
        
        if len(combined) == 84:
            print(f"[FEATURE EXTRACTION] ✓ Combined features: {len(combined)}, returning num_hands=2")
            return np.array(combined, dtype=np.float32), 2, is_valid_two_hands, results
        else:
            print(f"[FEATURE EXTRACTION] ✗ ERROR: Combined features = {len(combined)}, expected 84!")
            print(f"[FEATURE EXTRACTION] Left hand: {hands_data['Left'] is not None}, Right hand: {hands_data['Right'] is not None}")
    
    # Invalid or no hands
    print(f"[FEATURE EXTRACTION] No valid hands detected, returning None")
    return None, 0, False, results


# ==================== HELPER FUNCTIONS ====================
async def safe_send(websocket, message_dict):
    """Safely send WebSocket message, handling connection errors"""
    try:
        await websocket.send(json.dumps(message_dict))
    except (websockets.exceptions.ConnectionClosed, websockets.exceptions.ConnectionClosedOK, websockets.exceptions.ConnectionClosedError) as e:
        print(f"[WebSocket] Connection closed while sending: {e}")
        raise  # Re-raise to trigger connection cleanup
    except Exception as e:
        print(f"[WebSocket] Error sending message: {e}")
        # Don't re-raise for other errors, just log them

# ==================== WEBSOCKET HANDLER ====================
async def handle_connection(websocket, path=None):
    """Handle WebSocket connection for real-time sign language detection"""
    print(f"\n[WebSocket] Client connected")
    
    # Per-connection state (smoothing)
    letter_history = deque(maxlen=LETTER_SMOOTH_FRAMES)  # Reduced for faster response
    letter_votes = deque(maxlen=LETTER_STABLE_COUNT)  # Reduced for faster response
    word_history = deque(maxlen=SMOOTH_FRAMES)
    word_votes = deque(maxlen=STABLE_COUNT)
    hand_count_history = deque(maxlen=5)
    
    # Text output state
    last_letter = ""
    last_word = ""
    letter_hold_count = 0
    word_hold_count = 0
    HOLD_THRESHOLD = 15  # Frames to hold before adding to text
    WORD_HOLD_THRESHOLD = 5  # Very low threshold for words (faster addition, was 10)
    
    # Word mode lock - prevents switching to letter mode too quickly
    word_mode_lock = False
    word_mode_lock_frames = 0
    WORD_MODE_LOCK_DURATION = 120  # Keep word mode for 120 frames (2 seconds at 60fps) - prevent switching to letters
    
    last_letter = ""
    last_word = ""
    
    try:
        async for message in websocket:
            try:
                # Decode frame
                frame = np.frombuffer(message, dtype=np.uint8)
                frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
                
                if frame is None:
                    await safe_send(websocket, {
                        "type": "error",
                        "prediction": "",
                        "confidence": 0.0
                    })
                    continue
                
                # Extract features (returns features, num_hands, is_valid_two_hands, results)
                features, num_hands, is_valid_two_hands, results = extract_hand_features(frame)
                
                print(f"\n[MAIN LOOP] ========== Frame Processing ==========")
                print(f"[MAIN LOOP] Raw hand count: {num_hands}")
                print(f"[MAIN LOOP] Word model loaded: {word_model is not None}")
                print(f"[MAIN LOOP] Word scaler loaded: {word_scaler is not None}")
                print(f"[MAIN LOOP] Word labels loaded: {word_labels is not None}")
                print(f"[MAIN LOOP] Word mode lock active: {word_mode_lock} (frames remaining: {word_mode_lock_frames})")
                print(f"[MAIN LOOP] Features extracted: {features is not None}")
                print(f"[MAIN LOOP] Features length: {len(features) if features is not None else 'None'}")
                print(f"[MAIN LOOP] Valid two hands: {is_valid_two_hands}")
                
                if features is None:
                    # No hands detected - reset tracking to allow new letters/words when hand returns
                    hand_count_history.append(0)
                    letter_history.clear()
                    letter_votes.clear()
                    
                    # Don't clear word history immediately - let word mode lock handle it
                    if not word_mode_lock:
                        word_history.clear()
                        word_votes.clear()
                    
                    # Reset last letter/word when no hands - allows re-adding same sign after removing hand
                    last_letter = ""
                    last_word = ""
                    letter_hold_count = 0
                    word_hold_count = 0
                    
                    # Decrement word mode lock slowly - keep it active longer
                    if word_mode_lock_frames > 0:
                        word_mode_lock_frames -= 1
                        # Keep lock active for at least 60 frames (1 second) even with no hands
                        if word_mode_lock_frames < 60:
                            word_mode_lock_frames = 60
                    else:
                        word_mode_lock = False
                    
                    await safe_send(websocket, {
                        "type": "none",
                        "prediction": "",
                        "confidence": 0.0
                    })
                    continue
                
                raw_num_hands = num_hands
                
                # CRITICAL: Log hand detection for debugging
                print(f"[HAND DETECTION] raw_num_hands={raw_num_hands}, is_valid_two_hands={is_valid_two_hands}, features_length={len(features) if features is not None else 0}")
                
                # Smooth using raw detections - prioritize word mode when 2 hands detected
                current_detection = 2 if (raw_num_hands == 2 and is_valid_two_hands) else 1
                stable_hand_count = get_stable_hand_count(current_detection)
                
                # Allow word mode ONLY if we have 2 hands AND validation passes
                allow_word_mode = False
                if raw_num_hands == 2:
                    print(f"[WORD MODE CHECK] 👐 2 HANDS DETECTED - Checking if word mode should be allowed...")
                    print(f"[WORD MODE CHECK] Validation result: {is_valid_two_hands}")
                    # Only allow word mode when validation passes - prevents false detections
                    if is_valid_two_hands and word_model is not None and word_scaler is not None and word_labels is not None:
                        print(f"[WORD MODE CHECK] ✅ All word model components are loaded")
                        print(f"[WORD MODE CHECK] ✅ Validation passed - allowing word mode")
                        allow_word_mode = True
                        word_mode_lock = True  # Lock into word mode
                        word_mode_lock_frames = WORD_MODE_LOCK_DURATION  # Reset to full duration
                        print(f"[WORD MODE CHECK] ✅✅✅ WORD MODE ACTIVATED")
                        print(f"[WORD MODE CHECK] Lock set to {WORD_MODE_LOCK_DURATION} frames")
                        # Clear letter history when entering word mode
                        letter_history.clear()
                        letter_votes.clear()
                        print(f"[WORD MODE] ✓ Two hands VALIDATED - entering word mode")
                    elif not is_valid_two_hands:
                        print(f"[WORD MODE CHECK] ⚠ Two hands detected but validation FAILED - NOT allowing word mode")
                        print(f"[WORD MODE CHECK]   (Hands too close or other validation issue)")
                        # Don't reset lock if it's already active - let it count down
                        if word_mode_lock and word_mode_lock_frames > 0:
                            print(f"[WORD MODE CHECK]   Lock still active ({word_mode_lock_frames} frames) - maintaining lock but not processing words")
                        allow_word_mode = False
                    else:
                        print(f"[WORD MODE CHECK] ❌❌❌ WORD MODE BLOCKED - Missing components:")
                        print(f"  - word_model: {word_model is not None}")
                        print(f"  - word_scaler: {word_scaler is not None}")
                        print(f"  - word_labels: {word_labels is not None}")
                else:
                    print(f"[WORD MODE CHECK] Skipped (only {raw_num_hands} hand(s) detected)")
                
                # Use word mode lock - if lock is active, prevent letter mode from taking over
                if word_mode_lock and word_mode_lock_frames > 0:
                    if raw_num_hands == 2 and is_valid_two_hands:
                        # Still have valid 2 hands - keep word mode and reset lock
                        if word_model is not None and word_scaler is not None and word_labels is not None:
                            allow_word_mode = True
                            word_mode_lock_frames = WORD_MODE_LOCK_DURATION  # Reset lock to full duration
                    elif raw_num_hands == 1:
                        # Only 1 hand temporarily - decrement lock but keep blocking letters
                        word_mode_lock_frames -= 1
                        allow_word_mode = False  # Don't process words with 1 hand
                    else:
                        word_mode_lock = False
                        allow_word_mode = False
                elif word_mode_lock_frames <= 0:
                    word_mode_lock = False
                    allow_word_mode = False
                
                # ==================== MODE SELECTION: 2 HANDS (WORD) HAS PRIORITY ====================
                # CRITICAL: When 2 hands are detected, ALWAYS use word mode (if model is loaded)
                # ABSOLUTE PRIORITY: 2 hands = word mode, no exceptions
                print(f"\n[MODE DECISION] raw_num_hands={raw_num_hands}, word_mode_lock={word_mode_lock}")
                print(f"[MODE DECISION] Checking if: raw_num_hands == 2? {raw_num_hands == 2}")
                print(f"[MODE DECISION] Word model loaded? {word_model is not None}")
                print(f"[MODE DECISION] Word scaler loaded? {word_scaler is not None}")
                print(f"[MODE DECISION] Word labels loaded? {word_labels is not None}")
                
                # ==================== 2 HANDS: WORD ====================
                print(f"[WORD SECTION] Checking if 2-hand word section should execute...")
                print(f"[WORD SECTION] raw_num_hands == 2: {raw_num_hands == 2}")
                print(f"[WORD SECTION] word_model is not None: {word_model is not None}")
                print(f"[WORD SECTION] word_scaler is not None: {word_scaler is not None}")
                print(f"[WORD SECTION] word_labels is not None: {word_labels is not None}")
                
                if raw_num_hands == 2:
                    print(f"[WORD SECTION] ✅✅✅ ENTERING 2-HAND WORD PROCESSING SECTION")
                    # Check if word model components are loaded
                    if word_model is not None and word_scaler is not None and word_labels is not None:
                        # CRITICAL: Only process word predictions if validation passed
                        if not is_valid_two_hands:
                            print(f"[WORD PROCESSING] ⚠️ Skipping word prediction - validation failed (hands too close or invalid)")
                            print(f"[WORD PROCESSING]   This prevents false word predictions from invalid 2-hand detections")
                            print(f"[WORD SECTION] ========== Exiting 2-HAND WORD PROCESSING SECTION (validation failed) ==========\n")
                            # Don't send any prediction - let the letter mode or none mode handle it
                            # The word_mode_lock will still count down if active
                            continue
                        
                        print(f"[WORD PROCESSING] ========== Entering Word Processing ==========")
                        print(f"[WORD PROCESSING] allow_word_mode: {allow_word_mode}")
                        print(f"[WORD PROCESSING] is_valid_two_hands={is_valid_two_hands}, features_length={len(features) if features is not None else 0}")
                        print(f"[WORD PROCESSING] ✅ Processing word prediction...")
                        
                        # Ensure word mode is enabled since validation passed
                        if not allow_word_mode:
                            print(f"[WORD MODE] Enabling word mode for validated 2 hands")
                            allow_word_mode = True
                            word_mode_lock = True
                            word_mode_lock_frames = WORD_MODE_LOCK_DURATION
                        
                        if allow_word_mode:
                            # ABSOLUTE: Clear letter history when entering word mode
                            letter_history.clear()
                            letter_votes.clear()
                            
                            if word_model is None or word_scaler is None or word_labels is None:
                                await safe_send(websocket, {
                                    "type": "error",
                                    "prediction": "Word model not loaded",
                                    "confidence": 0.0
                                })
                                continue
                            
                            print(f"[WORD PROCESSING] Combined features length: {len(features)} (expected: 84)")
                            print(f"[WORD PROCESSING] Word model type: {'Temporal' if getattr(word_model, 'expects_sequence', False) else 'Single-frame'}")
                            
                            if len(features) != 84:
                                print(f"[WORD PROCESSING] ❌ Invalid features length: {len(features)}, expected 84")
                                await safe_send(websocket, {
                                    "type": "error",
                                    "prediction": "Invalid hand features",
                                    "confidence": 0.0
                                })
                                continue
                            
                            try:
                                print(f"[WORD PROCESSING] ✅ All conditions met, starting prediction...")
                                print(f"[WORD PROCESSING] Scaling features...")
                                data_scaled = word_scaler.transform([features])[0]
                                print(f"[WORD PROCESSING] Features scaled, shape: {data_scaled.shape}")
                                
                                if getattr(word_model, "expects_sequence", False):
                                    # Temporal model: INSTANT prediction - repeat current frame 30 times (no buffering)
                                    print(f"[WORD PROCESSING] Temporal model detected - making INSTANT prediction (no buffer)")
                                    # Repeat current frame to fill the required sequence length
                                    seq = np.tile(data_scaled, (WORD_FRAMES_BUFFER, 1)).astype(np.float32)
                                    print(f"[WORD PROCESSING] Sequence shape: {seq.shape} (repeated current frame {WORD_FRAMES_BUFFER} times)")
                                    input_tensor = torch.FloatTensor(seq).unsqueeze(0).to(DEVICE)  # (1, frames, 84)
                                    print(f"[WORD PROCESSING] Input tensor shape: {input_tensor.shape}, device: {DEVICE}")
                                    
                                    with torch.no_grad():
                                        print(f"[WORD PROCESSING] Running model forward pass...")
                                        outputs = word_model(input_tensor)
                                        print(f"[WORD PROCESSING] Model output shape: {outputs.shape}")
                                        probs = torch.softmax(outputs, dim=1)[0].cpu().numpy()
                                        print(f"[WORD PROCESSING] Probabilities shape: {probs.shape}, max prob: {probs.max():.4f}")
                                    
                                    word_history.append(probs)
                                    avg_probs = np.mean(list(word_history), axis=0)
                                    
                                    top_idx = np.argmax(avg_probs)
                                    confidence = float(avg_probs[top_idx])
                                    predicted = word_labels[top_idx]
                                    
                                    # Debug logging - check if prediction is a letter or word
                                    is_letter = len(predicted) == 1 and predicted.isalpha()
                                    print(f"WORD PREDICTION (temporal, instant): '{predicted}' (confidence: {confidence:.2f}, length: {len(predicted)}, is_letter: {is_letter})")
                                    if is_letter:
                                        print(f"WARNING: Word model predicted a single letter '{predicted}' instead of a word!")
                                        print(f"  Top 5 predictions: {[word_labels[i] for i in np.argsort(avg_probs)[-5:][::-1]]}")
                                    
                                    word_votes.append(predicted)
                                    # Use voting to get stable prediction
                                    stable_predicted = predicted
                                    if len(word_votes) >= STABLE_COUNT:
                                        counts = Counter(word_votes)
                                        best, cnt = counts.most_common(1)[0]
                                        if cnt >= 2:
                                            stable_predicted = best
                                    
                                    # Filter to words only (2+ chars) if top prediction is single char
                                    if len(stable_predicted) == 1:
                                        # Single char - find valid word from top candidates
                                        top_candidates = np.argsort(avg_probs)[-10:][::-1]
                                        for idx in top_candidates:
                                            if len(word_labels[idx]) > 1:
                                                stable_predicted = word_labels[idx]
                                                confidence = float(avg_probs[idx])
                                                break
                                    
                                    # Send prediction - filter to valid words
                                    if len(stable_predicted) > 1:
                                        await safe_send(websocket, {
                                            "type": "word",
                                            "prediction": stable_predicted,
                                            "confidence": round(confidence * 100, 2)
                                        })
                                    else:
                                        # Try to find a valid word from top candidates
                                        top_candidates_indices = np.argsort(avg_probs)[-10:][::-1]
                                        valid_words = [(word_labels[i], avg_probs[i]) for i in top_candidates_indices 
                                                      if len(word_labels[i]) > 1]
                                        if valid_words:
                                            stable_predicted, candidate_confidence = valid_words[0]
                                            await safe_send(websocket, {
                                                "type": "word",
                                                "prediction": stable_predicted,
                                                "confidence": round(candidate_confidence * 100, 2)
                                            })
                                        else:
                                            await safe_send(websocket, {
                                                "type": "word",
                                                "prediction": "",
                                                "confidence": 0.0
                                            })
                                else:
                                    # Single-frame model: infer immediately
                                    print(f"[WORD PROCESSING] Single-frame model - running inference immediately...")
                                    input_tensor = torch.FloatTensor(data_scaled).unsqueeze(0).to(DEVICE)
                                    print(f"[WORD PROCESSING] Input tensor shape: {input_tensor.shape}, device: {DEVICE}")
                                    with torch.no_grad():
                                        print(f"[WORD PROCESSING] Running model forward pass...")
                                        outputs = word_model(input_tensor)
                                        print(f"[WORD PROCESSING] Model output shape: {outputs.shape}")
                                        probs = torch.softmax(outputs, dim=1)[0].cpu().numpy()
                                        print(f"[WORD PROCESSING] Probabilities shape: {probs.shape}, max prob: {probs.max():.4f}")
                                    
                                    word_history.append(probs)
                                    avg_probs = np.mean(list(word_history), axis=0)
                                    
                                    top_idx = np.argmax(avg_probs)
                                    confidence = float(avg_probs[top_idx])
                                    predicted = word_labels[top_idx]
                                    
                                    # Debug logging - check if prediction is a letter or word
                                    is_letter = len(predicted) == 1 and predicted.isalpha()
                                    print(f"WORD PREDICTION (single-frame): '{predicted}' (confidence: {confidence:.2f}, length: {len(predicted)}, is_letter: {is_letter})")
                                    if is_letter:
                                        print(f"WARNING: Word model predicted a single letter '{predicted}' instead of a word!")
                                        print(f"  Top 5 predictions: {[word_labels[i] for i in np.argsort(avg_probs)[-5:][::-1]]}")
                                    
                                    word_votes.append(predicted)
                                    # Use voting to get stable prediction
                                    stable_predicted = predicted
                                    if len(word_votes) >= STABLE_COUNT:
                                        counts = Counter(word_votes)
                                        best, cnt = counts.most_common(1)[0]
                                        if cnt >= 2:
                                            stable_predicted = best
                                    
                                    # Filter to words only (2+ chars) if top prediction is single char
                                    if len(stable_predicted) == 1:
                                        # Single char - find valid word from top candidates
                                        top_candidates = np.argsort(avg_probs)[-10:][::-1]
                                        for idx in top_candidates:
                                            if len(word_labels[idx]) > 1:
                                                stable_predicted = word_labels[idx]
                                                confidence = float(avg_probs[idx])
                                                break
                                    
                                    # Send prediction - filter to valid words
                                    if len(stable_predicted) > 1:
                                        await safe_send(websocket, {
                                            "type": "word",
                                            "prediction": stable_predicted,
                                            "confidence": round(confidence * 100, 2)
                                        })
                                    else:
                                        # Try to find a valid word from top candidates
                                        top_candidates_indices = np.argsort(avg_probs)[-10:][::-1]
                                        valid_words = [(word_labels[i], avg_probs[i]) for i in top_candidates_indices 
                                                      if len(word_labels[i]) > 1]
                                        if valid_words:
                                            stable_predicted, candidate_confidence = valid_words[0]
                                            await safe_send(websocket, {
                                                "type": "word",
                                                "prediction": stable_predicted,
                                                "confidence": round(candidate_confidence * 100, 2)
                                            })
                                        else:
                                            await safe_send(websocket, {
                                                "type": "word",
                                                "prediction": "",
                                                "confidence": 0.0
                                            })
                            except Exception as e:
                                print(f"[WORD PROCESSING] ❌❌❌ ERROR in word prediction: {e}")
                                import traceback
                                traceback.print_exc()
                                await safe_send(websocket, {
                                    "type": "error",
                                    "prediction": str(e),
                                    "confidence": 0.0
                                })
                        print(f"[WORD SECTION] ========== Exiting 2-HAND WORD PROCESSING SECTION ==========\n")
                    else:
                        # 2 hands detected but word model components not loaded
                        print(f"[WORD SECTION] ❌❌❌ 2 HANDS DETECTED BUT WORD SECTION SKIPPED!")
                        print(f"[WORD SECTION] Reason: One or more conditions failed:")
                        print(f"  - word_model: {word_model is not None}")
                        print(f"  - word_scaler: {word_scaler is not None}")
                        print(f"  - word_labels: {word_labels is not None}")
                        await safe_send(websocket, {
                            "type": "error",
                            "prediction": "Word model not loaded - cannot process 2 hands",
                            "confidence": 0.0
                        })
                
                # ==================== 1 HAND: LETTER ====================
                # Process as letter if we have exactly 1 hand
                # Note: Always show letter predictions, even with word_mode_lock (prevents confusion)
                elif raw_num_hands == 1:
                    print(f"[✓ LETTER MODE ACTIVATED] Processing 1 hand as letter (features={len(features)}, word_mode_lock={word_mode_lock})")
                    
                    if word_mode_lock:
                        print(f"[LETTER MODE] ⚠️ Word mode lock active ({word_mode_lock_frames} frames) - showing predictions")
                    
                    # Only clear word history if we're truly switching to letter mode (not just locked)
                    if not word_mode_lock and word_mode_lock_frames <= 0:
                        word_history.clear()
                        word_votes.clear()
                    
                    # Predict letter
                    if letter_model is not None and len(features) == 42:
                        print(f"[LETTER PROCESSING] ✅ Processing letter prediction...")
                        probs = letter_model.predict_proba([features])[0]
                        letter_history.append(probs)
                        avg_probs = np.mean(list(letter_history), axis=0)
                        
                        top_idx = np.argmax(avg_probs)
                        confidence = float(avg_probs[top_idx])
                        predicted = LETTER_LABELS[top_idx]
                        
                        letter_votes.append(predicted)
                        if len(letter_votes) >= LETTER_STABLE_COUNT:
                            counts = Counter(letter_votes)
                            best, cnt = counts.most_common(1)[0]
                            if cnt >= 2:
                                predicted = best
                        
                        # Only send if letter changed (prevents repetitive sends of same letter)
                        letter_changed = (predicted != last_letter)
                        
                        if letter_changed:
                            # Letter changed - reset hold count and update last_letter
                            letter_hold_count = 0
                            last_letter = predicted
                            # Send immediately when letter changes for responsive feedback
                            await safe_send(websocket, {
                                "type": "letter",
                                "prediction": predicted,
                                "confidence": round(confidence * 100, 2)
                            })
                        else:
                            # Same letter - increment hold count but don't send every frame
                            letter_hold_count += 1
                            # Only send periodically (every 10 frames) to reduce repetition
                            # This keeps the UI updated without flooding with identical predictions
                            if letter_hold_count % 10 == 0:
                                await safe_send(websocket, {
                                    "type": "letter",
                                    "prediction": predicted,
                                    "confidence": round(confidence * 100, 2)
                                })
                    else:
                        # Reset tracking when no valid prediction
                        if letter_model is None:
                            last_letter = ""
                            letter_hold_count = 0
                        await safe_send(websocket, {
                            "type": "none",
                            "prediction": "",
                            "confidence": 0.0
                        })
                
                # ==================== NEITHER MODE ====================
                else:
                    print(f"[⚠ NO MODE] Neither letter nor word mode activated!")
                    print(f"   raw_num_hands={raw_num_hands}, word_mode_lock={word_mode_lock}")
                    print(f"   letter_model loaded? {letter_model is not None}")
                    print(f"   word_model loaded? {word_model is not None}")
                    print(f"   word_scaler loaded? {word_scaler is not None}")
                    print(f"   word_labels loaded? {word_labels is not None}")
                    if raw_num_hands == 2:
                        print(f"   [DEBUG] 2 hands detected but word mode not activated!")
                        print(f"   [DEBUG] This should not happen - checking why...")
                    await safe_send(websocket, {
                        "type": "none",
                        "prediction": "",
                        "confidence": 0.0
                    })
                
            except Exception as e:
                print(f"Error processing frame: {e}")
                import traceback
                traceback.print_exc()
                await safe_send(websocket, {
                    "type": "error",
                    "prediction": str(e),
                    "confidence": 0.0
                })
                
    except websockets.exceptions.ConnectionClosed:
        print("[WebSocket] Client disconnected")
    except Exception as e:
        print(f"[WebSocket] Connection error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Start the WebSocket server"""
    print("\n" + "="*60)
    print("Starting WebSocket server on 0.0.0.0:8002...")
    print("="*60)
    async with websockets.serve(handle_connection, "0.0.0.0", 8002):
        print("[OK] WebSocket server is running!")
        print("     Waiting for connections from Flutter app...")
        print("     Connect to: ws://YOUR_IP:8002")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    print("\nWebSocket Final Classifier Server starting...")
    asyncio.run(main())

