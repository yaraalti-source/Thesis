"""
FINAL SIGN LANGUAGE CLASSIFIER
- 1 Hand → LETTER (A-Z) using sklearn MLP (more accurate)
- 2 Hands → WORD using Transformer-MLP
"""

import pickle
import cv2
import mediapipe as mp
import numpy as np
import torch
import torch.nn as nn
import os
from collections import deque, Counter

# Import NLP processor
try:
    from nlp_processor import improve_translation
    NLP_AVAILABLE = True
except ImportError:
    print("[WARNING] NLP processor not available. Running without NLP features.")
    NLP_AVAILABLE = False
    def improve_translation(text, is_sentence=True):
        return text

# ==================== WORD MODEL ====================
# Mean Pooling architecture (77.33% accuracy)
# Note: MultiHeadAttentionPooling class kept for reference but not used in mean pooling model
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
print("SIGN LANGUAGE CLASSIFIER")
print("="*60)

# All 26 letters
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

# ==================== LOAD WORD MODEL (Temporal Transformer) ====================
print("Loading WORD model...")
word_model = None
word_labels = None
word_scaler = None
WORD_FRAMES = 30

try:
    # Accept either original or spaced filenames
    prep_path_options = ['./preprocessing_word.pkl', './preprocessing_word .pkl']
    model_path_options = ['./temporal_transformer_mlp_word_model.pth', './transformer_mlp_word_model.pth', './transformer_mlp_word_model (1).pth']
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
            print(f"  ⚠️  This will cause words to be split into letters. Please retrain with word labels.")
            print(f"  ⚠️  The system will try to filter out letter predictions, but results may be poor.")
    else:
        print("[ERROR] WORD model files not found")
        print("  Required: preprocessing_word.pkl and temporal_transformer_mlp_word_model.pth")
except Exception as e:
    print(f"[ERROR] Word model error: {e}")
    # Reset model to None if loading failed
    word_model = None
    word_labels = None
    word_scaler = None

# ==================== SMOOTHING ====================
SMOOTH_FRAMES = 5
STABLE_COUNT = 3
WORD_FRAMES_BUFFER = 30  # will be overwritten by preprocessing

letter_history = deque(maxlen=SMOOTH_FRAMES)
letter_votes = deque(maxlen=STABLE_COUNT)
word_history = deque(maxlen=SMOOTH_FRAMES)
word_votes = deque(maxlen=STABLE_COUNT)

# ==================== TEXT OUTPUT ====================
detected_text = ""  # Stores the sentence being built
last_letter = ""
last_word = ""
letter_hold_count = 0
word_hold_count = 0
HOLD_THRESHOLD = 15  # Frames to hold before adding to text
WORD_HOLD_THRESHOLD = 5  # Very low threshold for words (faster addition, was 10)
nlp_enabled = NLP_AVAILABLE  # NLP processing toggle (only enabled if NLP is available)

# Word mode lock - prevents switching to letter mode too quickly
word_mode_lock = False
word_mode_lock_frames = 0
WORD_MODE_LOCK_DURATION = 120  # Keep word mode for 120 frames (2 seconds at 60fps) - prevent switching to letters

# ==================== MEDIAPIPE ====================
cap = cv2.VideoCapture(0)
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
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


print("="*60)
print("1 HAND  = LETTER (A-Z)")
print("2 HANDS = WORD")
print("Press 'Q' to quit, 'C' to clear, 'N' to toggle NLP")
print("="*60)

# ==================== MAIN LOOP ====================
while True:
    ret, frame = cap.read()
    if not ret:
        break

    H, W, _ = frame.shape
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)

    # Header
    cv2.rectangle(frame, (0, 0), (W, 40), (50, 50, 50), -1)
    cv2.putText(frame, "1 HAND = LETTER  |  2 HANDS = WORD  |  Q = Quit  |  C = Clear  |  N = NLP", 
               (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    
    # Text display area at bottom
    cv2.rectangle(frame, (0, H - 80), (W, H), (40, 40, 40), -1)
    
    # Process text with NLP if enabled and available
    display_text = detected_text if detected_text else "[ Hold sign to add to text ]"
    if nlp_enabled and NLP_AVAILABLE and detected_text:
        try:
            processed_text = improve_translation(detected_text.strip(), is_sentence=True)
            if processed_text and processed_text != detected_text.strip():
                display_text = processed_text
            else:
                display_text = detected_text  # If NLP didn't change anything, show raw
        except Exception as e:
            print(f"[NLP ERROR] {e}")  # Debug: print errors
            import traceback
            traceback.print_exc()
            display_text = detected_text  # Fallback to raw text if NLP fails
    
    cv2.putText(frame, "TEXT:", (10, H - 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 2)
    cv2.putText(frame, display_text, (80, H - 55), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    
    # Show NLP status
    if NLP_AVAILABLE:
        nlp_status = "NLP: ON" if nlp_enabled else "NLP: OFF"
        nlp_color = (0, 255, 0) if nlp_enabled else (100, 100, 100)
    else:
        nlp_status = "NLP: N/A"
        nlp_color = (100, 100, 100)
    cv2.putText(frame, nlp_status, (W - 120, H - 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, nlp_color, 2)
    
    # Show raw text below if NLP is enabled and text exists
    if nlp_enabled and detected_text:
        cv2.putText(frame, f"Raw: {detected_text}", (80, H - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

    if results.multi_hand_landmarks:
        raw_num_hands = len(results.multi_hand_landmarks)
        print(f"\n[MAIN LOOP] ========== Frame Processing ==========")
        print(f"[MAIN LOOP] Raw hand count: {raw_num_hands}")
        print(f"[MAIN LOOP] Word model loaded: {word_model is not None}")
        print(f"[MAIN LOOP] Word scaler loaded: {word_scaler is not None}")
        print(f"[MAIN LOOP] Word labels loaded: {word_labels is not None}")
        print(f"[MAIN LOOP] Word mode lock active: {word_mode_lock} (frames remaining: {word_mode_lock_frames})")
        
        is_valid_two_hands = False
        if raw_num_hands == 2:
            print(f"[MAIN LOOP] 👐 2 HANDS DETECTED - Starting validation...")
            is_valid_two_hands = validate_two_hands(results)
            print(f"[MAIN LOOP] Validation result: {is_valid_two_hands}")
        else:
            print(f"[MAIN LOOP] ✋ {raw_num_hands} hand(s) detected")
        
        # Smooth using raw detections - prioritize word mode when 2 hands detected
        current_detection = 2 if (raw_num_hands == 2 and is_valid_two_hands) else 1
        stable_hand_count = get_stable_hand_count(current_detection)
        
        # Allow word mode if we have 2 hands AND validation passes
        allow_word_mode = False
        if raw_num_hands == 2:
            print(f"[WORD MODE CHECK] Checking if word mode should be allowed...")
            # Allow word mode if validation passes AND word model is loaded
            # RELAXED: Even if validation fails temporarily, allow word mode if we have 2 hands
            # This prevents switching to letter mode when hands are close together temporarily
            if word_model is not None and word_scaler is not None and word_labels is not None:
                print(f"[WORD MODE CHECK] ✅ All word model components are loaded")
                if is_valid_two_hands:
                    allow_word_mode = True
                    word_mode_lock = True  # Lock into word mode
                    word_mode_lock_frames = WORD_MODE_LOCK_DURATION  # Reset to full duration
                    print(f"[WORD MODE CHECK] ✅✅✅ WORD MODE ACTIVATED (validation passed)")
                    print(f"[WORD MODE CHECK] Lock set to {WORD_MODE_LOCK_DURATION} frames")
                    # Clear letter history when entering word mode to prevent letter contamination
                    letter_history.clear()
                    letter_votes.clear()
                    letter_hold_count = 0
                else:
                    print(f"[WORD MODE CHECK] ⚠️ Validation failed, checking lock status...")
                    # Validation failed but we have 2 hands - still allow word mode if lock is active
                    # This prevents switching to letter mode during brief validation failures
                    if word_mode_lock and word_mode_lock_frames > 0:
                        allow_word_mode = True
                        print(f"[WORD MODE CHECK] ✅ Word mode kept active (lock active, {word_mode_lock_frames} frames remaining)")
                    else:
                        # First time detecting 2 hands but validation failed - be lenient
                        # Allow word mode anyway to prevent letter mode interference
                        allow_word_mode = True
                        word_mode_lock = True
                        word_mode_lock_frames = WORD_MODE_LOCK_DURATION // 2  # Shorter lock if validation failed
                        print(f"[WORD MODE CHECK] ⚠️ Word mode activated with lenient mode (validation failed, lock={word_mode_lock_frames} frames)")
                        letter_history.clear()
                        letter_votes.clear()
                        letter_hold_count = 0
            else:
                # Word model not loaded - do NOT allow word mode
                allow_word_mode = False
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

        # Show quick hint when 2 hands are present but validation is failing
        if raw_num_hands == 2 and not is_valid_two_hands and not allow_word_mode:
            cv2.putText(frame, "Two hands seen - spread/resize for WORD mode",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 215, 255), 2)
        
        # ==================== 2 HANDS = WORD ====================
        # CRITICAL: When 2 hands are detected, ALWAYS use word mode (if model is loaded)
        # ABSOLUTE PRIORITY: 2 hands = word mode, no exceptions
        # Block letter mode completely when 2 hands are detected
        print(f"[WORD SECTION] Checking if 2-hand word section should execute...")
        print(f"[WORD SECTION] raw_num_hands == 2: {raw_num_hands == 2}")
        print(f"[WORD SECTION] word_model is not None: {word_model is not None}")
        print(f"[WORD SECTION] word_scaler is not None: {word_scaler is not None}")
        print(f"[WORD SECTION] word_labels is not None: {word_labels is not None}")
        
        if raw_num_hands == 2 and word_model is not None and word_scaler is not None and word_labels is not None:
            print(f"[WORD SECTION] ✅✅✅ ENTERING 2-HAND WORD PROCESSING SECTION")
            print(f"[WORD PROCESSING] ========== Entering Word Processing ==========")
            # Force word mode when 2 hands are detected - override allow_word_mode if needed
            if not allow_word_mode:
                allow_word_mode = True
                word_mode_lock = True
                word_mode_lock_frames = WORD_MODE_LOCK_DURATION
                print(f"[WORD PROCESSING] ⚠️ FORCED: Word mode activated for 2 hands (override)")
            
            print(f"[WORD PROCESSING] allow_word_mode: {allow_word_mode}")
            if allow_word_mode:
                print(f"[WORD PROCESSING] ✅ Processing word prediction...")
                # ABSOLUTE: Clear letter history when entering word mode
                letter_history.clear()
                letter_votes.clear()
                letter_hold_count = 0
                last_letter = ""  # Reset last letter
                
                hands_data = {'Left': None, 'Right': None}
            all_x, all_y = [], []
            
            # Always process both detected hands; order given by MediaPipe
            for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style())
                
                handedness = results.multi_handedness[idx].classification[0].label
                x_ = [lm.x for lm in hand_landmarks.landmark]
                y_ = [lm.y for lm in hand_landmarks.landmark]
                all_x.extend(x_)
                all_y.extend(y_)
                
                min_x, min_y = min(x_), min(y_)
                hand_data = []
                for lm in hand_landmarks.landmark:
                    hand_data.append(lm.x - min_x)
                    hand_data.append(lm.y - min_y)
                hands_data[handedness] = hand_data
            
            # Combine both hands data (Left first, then Right)
            # Handle cases where we might not have both Left and Right labeled correctly
            combined = []
            if raw_num_hands == 2:
                # We have 2 hands - combine them
                if hands_data['Left'] is not None and hands_data['Right'] is not None:
                    # Both Left and Right detected - use them in order
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
                    # Fallback: pad with zeros if we don't have 2 hands
                    for ht in ['Left', 'Right']:
                        combined.extend(hands_data[ht] if hands_data[ht] else [0.0]*42)
            # REMOVED: No longer allow word mode with single hand, even with lock
            # This prevents single-hand word detection
            
            x1 = max(0, int(min(all_x) * W) - 15)
            y1 = max(0, int(min(all_y) * H) - 15)
            x2 = min(W, int(max(all_x) * W) + 15)
            y2 = min(H, int(max(all_y) * H) + 15)
            
            print(f"[WORD PROCESSING] Combined features length: {len(combined)} (expected: 84)")
            print(f"[WORD PROCESSING] Word model type: {'Temporal' if getattr(word_model, 'expects_sequence', False) else 'Single-frame'}")
            
            if word_model and word_scaler and word_labels and len(combined) == 84:
                print(f"[WORD PROCESSING] ✅ All conditions met, starting prediction...")
                try:
                    print(f"[WORD PROCESSING] Scaling features...")
                    data_scaled = word_scaler.transform([combined])[0]
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
                            confidence = avg_probs[top_idx]
                            predicted = word_labels[top_idx]
                            
                            # Debug logging - check if prediction is a letter or word
                            is_letter = len(predicted) == 1 and predicted.isalpha()
                            print(f"WORD PREDICTION (temporal): '{predicted}' (confidence: {confidence:.2f}, length: {len(predicted)}, is_letter: {is_letter})")
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
                            
                            # Purple box for WORD - show stable prediction
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (180, 0, 180), 4)
                            cv2.putText(frame, f"WORD: {stable_predicted}", (x1, y1 - 40),
                                       cv2.FONT_HERSHEY_SIMPLEX, 1.3, (180, 0, 180), 3)
                            cv2.putText(frame, f"{confidence*100:.1f}%", (x1, y1 - 10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 0, 180), 2)
                            
                            top3 = np.argsort(avg_probs)[-3:][::-1]
                            y_off = y2 + 25
                            for i in top3:
                                cv2.putText(frame, f"{word_labels[i]}: {avg_probs[i]*100:.1f}%",
                                           (x1, y_off), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 0, 180), 2)
                                y_off += 18
                            
                            # Add to text using STABLE prediction (not raw prediction)
                            # CRITICAL: Only add complete words, never partial words or letters
                            # ABSOLUTE FILTER: Reject ANY single character prediction (A-Z or any single char)
                            # Only accept predictions that are 2+ characters long
                            if len(stable_predicted) > 1:  # Must be a word (2+ characters), not a letter
                                if stable_predicted == last_word:
                                    word_hold_count += 1
                                    threshold = WORD_HOLD_THRESHOLD
                                    if word_hold_count >= threshold:
                                        # Only add if word is not already at the end of detected_text
                                        if not detected_text.endswith(stable_predicted + " "):
                                            detected_text += stable_predicted + " "
                                            print(f"*** Added WORD: '{stable_predicted}' (length: {len(stable_predicted)}) ***")
                                            word_hold_count = 0  # Reset after adding
                                            last_word = ""  # Clear to allow next word
                                else:
                                    # Word changed - start counting for new word
                                    if stable_predicted != last_word:
                                        word_hold_count = 1
                                        last_word = stable_predicted
                            else:
                                # Single character detected - ABSOLUTELY REJECT it in word mode
                                print(f"❌ REJECTED: Word model predicted single character '{stable_predicted}' (length={len(stable_predicted)}) - IGNORING in word mode")
                                # Don't update last_word or word_hold_count for single characters
                                word_hold_count = 0
                                # Try to get a better prediction from top candidates - MUST be 2+ characters
                                top_candidates = [word_labels[i] for i in np.argsort(avg_probs)[-10:][::-1]]  # Check top 10
                                valid_words = [w for w in top_candidates if len(w) > 1]  # Only words with 2+ characters
                                if valid_words:
                                    print(f"  ✅ Using alternative word prediction: '{valid_words[0]}' (from {len(valid_words)} valid words)")
                                    stable_predicted = valid_words[0]
                                    if stable_predicted == last_word:
                                        word_hold_count += 1
                                    else:
                                        word_hold_count = 1
                                        last_word = stable_predicted
                                else:
                                    print(f"  ⚠️  No valid words found in top 10 predictions. Top candidates: {top_candidates[:5]}")
                                    # Don't add anything - wait for better prediction
                            
                            # Show hold progress
                            threshold = WORD_HOLD_THRESHOLD if confidence > 0.02 else HOLD_THRESHOLD
                            if word_hold_count > 0 and word_hold_count < threshold:
                                progress = int((word_hold_count / threshold) * 100)
                                cv2.putText(frame, f"Hold: {progress}%", (x1, y2 + 70),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            
                            print(f"WORD: {predicted} ({confidence*100:.1f}%)")
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
                        confidence = avg_probs[top_idx]
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

                        cv2.rectangle(frame, (x1, y1), (x2, y2), (180, 0, 180), 4)
                        cv2.putText(frame, f"WORD: {stable_predicted}", (x1, y1 - 40),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1.3, (180, 0, 180), 3)
                        cv2.putText(frame, f"{confidence*100:.1f}%", (x1, y1 - 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 0, 180), 2)

                        top3 = np.argsort(avg_probs)[-3:][::-1]
                        y_off = y2 + 25
                        for i in top3:
                            cv2.putText(frame, f"{word_labels[i]}: {avg_probs[i]*100:.1f}%",
                                       (x1, y_off), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 0, 180), 2)
                            y_off += 18

                        # Add to text using STABLE prediction (not raw prediction)
                        # CRITICAL: Only add complete words, never partial words or letters
                        # ABSOLUTE FILTER: Reject ANY single character prediction (A-Z or any single char)
                        # Only accept predictions that are 2+ characters long
                        if len(stable_predicted) > 1:  # Must be a word (2+ characters), not a letter
                            if stable_predicted == last_word:
                                word_hold_count += 1
                                threshold = WORD_HOLD_THRESHOLD
                                if word_hold_count >= threshold:
                                    # Only add if word is not already at the end of detected_text
                                    if not detected_text.endswith(stable_predicted + " "):
                                        detected_text += stable_predicted + " "
                                        print(f"*** Added WORD: '{stable_predicted}' (length: {len(stable_predicted)}) ***")
                                        word_hold_count = 0  # Reset after adding
                                        last_word = ""  # Clear to allow next word
                            else:
                                # Word changed - start counting for new word
                                if stable_predicted != last_word:
                                    word_hold_count = 1
                                    last_word = stable_predicted
                        else:
                            # Single character detected - ABSOLUTELY REJECT it in word mode
                            print(f"❌ REJECTED: Word model predicted single character '{stable_predicted}' (length={len(stable_predicted)}) - IGNORING in word mode")
                            # Don't update last_word or word_hold_count for single characters
                            word_hold_count = 0
                            # Try to get a better prediction from top candidates - MUST be 2+ characters
                            top_candidates = [word_labels[i] for i in np.argsort(avg_probs)[-10:][::-1]]  # Check top 10
                            valid_words = [w for w in top_candidates if len(w) > 1]  # Only words with 2+ characters
                            if valid_words:
                                print(f"  ✅ Using alternative word prediction: '{valid_words[0]}' (from {len(valid_words)} valid words)")
                                stable_predicted = valid_words[0]
                                if stable_predicted == last_word:
                                    word_hold_count += 1
                                else:
                                    word_hold_count = 1
                                    last_word = stable_predicted
                            else:
                                print(f"  ⚠️  No valid words found in top 10 predictions. Top candidates: {top_candidates[:5]}")
                                # Don't add anything - wait for better prediction

                        threshold = WORD_HOLD_THRESHOLD
                        if word_hold_count > 0 and word_hold_count < threshold:
                            progress = int((word_hold_count / threshold) * 100)
                            cv2.putText(frame, f"Hold: {progress}%", (x1, y2 + 70),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                        print(f"WORD: {predicted} ({confidence*100:.1f}%)")
                except Exception as e:
                    print(f"[WORD PROCESSING] ❌❌❌ ERROR in word prediction: {e}")
                    import traceback
                    traceback.print_exc()
                    cv2.putText(frame, f"ERROR: {str(e)[:30]}", (x1, y1 - 15),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            else:
                print(f"[WORD PROCESSING] ❌ Conditions not met for word prediction:")
                print(f"  - word_model: {word_model is not None}")
                print(f"  - word_scaler: {word_scaler is not None}")
                print(f"  - word_labels: {word_labels is not None}")
                print(f"  - combined length: {len(combined)} (expected: 84)")
                cv2.rectangle(frame, (x1, y1), (x2, y2), (180, 0, 180), 3)
                if not word_model or not word_labels:
                    cv2.putText(frame, "WORD MODEL NOT LOADED", (x1, y1 - 15),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    print("[WORD PROCESSING] ❌ WARNING: Two hands detected but word model not loaded!")
                elif len(combined) != 84:
                    cv2.putText(frame, "INVALID HAND DATA", (x1, y1 - 15),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    print(f"[WORD PROCESSING] ❌ WARNING: Combined features length is {len(combined)}, expected 84")
                else:
                    cv2.putText(frame, "WORD MODE", (x1, y1 - 15),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (180, 0, 180), 2)
                    print(f"[WORD PROCESSING] ⚠️ Unknown condition - showing WORD MODE")
            print(f"[WORD SECTION] ========== Exiting 2-HAND WORD PROCESSING SECTION ==========\n")
        else:
            if raw_num_hands == 2:
                print(f"[WORD SECTION] ❌❌❌ 2 HANDS DETECTED BUT WORD SECTION SKIPPED!")
                print(f"[WORD SECTION] Reason: One or more conditions failed:")
                print(f"  - word_model: {word_model is not None}")
                print(f"  - word_scaler: {word_scaler is not None}")
                print(f"  - word_labels: {word_labels is not None}")
        
        # ==================== 1 HAND = LETTER ====================
        # Process as letter if we have exactly 1 hand
        # CRITICAL: If 2 hands are detected, NEVER process as letter (even if validation fails)
        # ABSOLUTE BLOCK: When 2 hands are detected, letter mode is COMPLETELY disabled
        # Note: Allow letter predictions even with word_mode_lock, but block text addition
        if raw_num_hands == 1:
            # Always process letter predictions (show on screen)
            # But block text addition if word_mode_lock is active (prevents "S U N DAY" issue)
            print(f"[LETTER MODE] Processing 1 hand as letter (word_mode_lock={word_mode_lock})")
            
            # Debug: log when word mode lock is active
            if word_mode_lock:
                if len(hand_count_history) % 10 == 0:
                    print(f"[LETTER MODE] ⚠️ Word mode lock active ({word_mode_lock_frames} frames) - showing predictions but blocking text addition")
            
            # Only clear word history if we're truly switching to letter mode (not just locked)
            if not word_mode_lock and word_mode_lock_frames <= 0:
                word_history.clear()
                word_votes.clear()
            
            # Process letter predictions (always show, but block addition if lock is active)
            # Pick the hand with highest confidence
            best_hand_idx = 0
            if raw_num_hands > 1:
                confidences = [h.classification[0].score for h in results.multi_handedness]
                best_hand_idx = confidences.index(max(confidences))
            
            hand_landmarks = results.multi_hand_landmarks[best_hand_idx]
            handedness = results.multi_handedness[best_hand_idx].classification[0].label
            
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                mp_drawing_styles.get_default_hand_landmarks_style(),
                mp_drawing_styles.get_default_hand_connections_style())
            
            x_ = [lm.x for lm in hand_landmarks.landmark]
            y_ = [lm.y for lm in hand_landmarks.landmark]
            
            min_x, min_y = min(x_), min(y_)
            hand_data = []
            for lm in hand_landmarks.landmark:
                hand_data.append(lm.x - min_x)
                hand_data.append(lm.y - min_y)
            
            if letter_model and len(hand_data) == 42:
                probs = letter_model.predict_proba([np.array(hand_data)])[0]
            
            letter_history.append(probs)
            avg_probs = np.mean(list(letter_history), axis=0)
            
            top_idx = np.argmax(avg_probs)
            confidence = avg_probs[top_idx]
            predicted = LETTER_LABELS[top_idx]
            
            letter_votes.append(predicted)
            if len(letter_votes) >= STABLE_COUNT:
                counts = Counter(letter_votes)
                best, cnt = counts.most_common(1)[0]
                if cnt >= 2:
                    predicted = best
            
            x1 = max(0, int(min(x_) * W) - 15)
            y1 = max(0, int(min(y_) * H) - 15)
            x2 = min(W, int(max(x_) * W) + 15)
            y2 = min(H, int(max(y_) * H) + 15)
            
            # Color by confidence
            if confidence > 0.6:
                color = (0, 255, 0)  # Green
            elif confidence > 0.4:
                color = (0, 200, 255)  # Orange
            else:
                color = (0, 255, 255)  # Yellow
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 4)
            
            # Big letter
            cv2.putText(frame, predicted, (x1, y1 - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 2.0, color, 4)
            cv2.putText(frame, f"{confidence*100:.1f}%", (x1 + 60, y1 - 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            # Top 5 alternatives
            top5 = np.argsort(avg_probs)[-5:][::-1]
            y_off = y2 + 22
            for i in top5:
                cv2.putText(frame, f"{LETTER_LABELS[i]}: {avg_probs[i]*100:.1f}%",
                           (x1, y_off), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                y_off += 18
            
            # Handedness
            cv2.putText(frame, f"[{handedness}]", (x2 - 50, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 2)
            
            # Add to text if held
            # ABSOLUTE BLOCK: Never add letters when 2 hands are detected OR word mode lock is active
            if raw_num_hands == 2:
                # 2 hands detected - ABSOLUTELY BLOCK letter addition
                if len(hand_count_history) % 5 == 0:
                    print(f"🚫 BLOCKED: Letter '{predicted}' - 2 hands detected, letter mode disabled")
                letter_hold_count = 0
            elif not word_mode_lock:
                # Only allow letter addition if 1 hand AND no word mode lock
                if predicted == last_letter:
                    letter_hold_count += 1
                    if letter_hold_count == HOLD_THRESHOLD:
                        detected_text += predicted
                        print(f"*** Added LETTER: {predicted} ***")
                else:
                    letter_hold_count = 0
                    last_letter = predicted
            else:
                # Word mode lock active - do NOT add letters (but predictions are still shown)
                if len(hand_count_history) % 10 == 0:
                    print(f"🚫 BLOCKED: Letter '{predicted}' - word mode lock active (predictions shown but not added to text)")
                letter_hold_count = 0
            
            # Show hold progress
            if letter_hold_count > 0 and letter_hold_count < HOLD_THRESHOLD:
                progress = int((letter_hold_count / HOLD_THRESHOLD) * 100)
                cv2.putText(frame, f"Hold: {progress}%", (x1, y2 + 100),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            print(f"LETTER: {predicted} ({confidence*100:.1f}%) | Top: {[LETTER_LABELS[i] for i in top5[:3]]}")
    
    else:
        # No hands detected
        letter_history.clear()
        letter_votes.clear()
        # Don't clear word history immediately - let word mode lock handle it
        if not word_mode_lock:
            word_history.clear()
            word_votes.clear()
        hand_count_history.clear()  # Reset temporal smoothing
        letter_hold_count = 0
        # Don't reset word_hold_count if in word mode lock
        if not word_mode_lock:
            word_hold_count = 0
        # Decrement word mode lock slowly - keep it active longer
        if word_mode_lock_frames > 0:
            word_mode_lock_frames -= 1
            # Keep lock active for at least 60 frames (1 second) even with no hands
            if word_mode_lock_frames < 60:
                word_mode_lock_frames = 60
        else:
            word_mode_lock = False

    cv2.imshow('Sign Language Classifier', frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('c'):
        detected_text = ""
        print("*** Text cleared ***")
    elif key == ord('n') or key == ord('N'):  # Toggle NLP
        nlp_enabled = not nlp_enabled
        if NLP_AVAILABLE:
            print(f"*** NLP {'ENABLED' if nlp_enabled else 'DISABLED'} ***")
        else:
            print(f"*** NLP toggle: {'ON' if nlp_enabled else 'OFF'} (NLP module not available) ***")
    elif key == ord(' '):  # Space bar adds space
        detected_text += " "
        print("*** Added space ***")
    elif key == 8:  # Backspace
        detected_text = detected_text[:-1]
        print("*** Deleted last character ***")

cap.release()
cv2.destroyAllWindows()
print("Done.")

