"""
FINAL SIGN LANGUAGE CLASSIFIER - FULLY ANNOTATED VERSION
This file contains the complete code with detailed explanations for each section.
- 1 Hand → LETTER (A-Z) using sklearn MLP (more accurate)
- 2 Hands → WORD using Transformer-MLP
"""

# ============================================================================
# SECTION 1: IMPORTS AND DEPENDENCIES
# ============================================================================
import pickle  # For loading saved models (sklearn MLP, preprocessing data)
import cv2  # OpenCV for video capture and image processing
import mediapipe as mp  # Google's MediaPipe for hand landmark detection
import numpy as np  # NumPy for numerical operations and array handling
import torch  # PyTorch for deep learning models (Transformer networks)
import torch.nn as nn  # PyTorch neural network modules
import os  # For file system operations (checking if model files exist)
from collections import deque  # Efficient queue for maintaining prediction history

# Try to import NLP processor - optional feature for text improvement
try:
    from nlp_processor import improve_translation  # Custom NLP module for grammar correction
    NLP_AVAILABLE = True  # Flag indicating NLP is available
except ImportError:
    print("[WARNING] NLP processor not available. Running without NLP features.")
    NLP_AVAILABLE = False  # NLP not available - system will work without it
    def improve_translation(text, is_sentence=True):
        return text  # Dummy function that returns text unchanged if NLP unavailable


# ============================================================================
# SECTION 2: NEURAL NETWORK ARCHITECTURE - WORD RECOGNITION MODEL
# ============================================================================

# ----------------------------------------------------------------------------
# TemporalTransformer - THE WORD RECOGNITION MODEL CURRENTLY IN USE
# ----------------------------------------------------------------------------
# THIS IS THE ONLY MODEL USED FOR WORD RECOGNITION IN THE APPLICATION
# 
# EXPLANATION: This is the production model that processes sequences of frames
# (30 frames) to recognize words. It uses a Transformer architecture to understand
# temporal relationships between frames.
# 
# Input: 30 frames × 84 features (2 hands × 21 landmarks × 2 coordinates)
# Architecture: 256 hidden dim, 8 attention heads, 6 transformer layers
# Accuracy: 77.33% on word recognition
# 
# How it works:
# 1. Takes 30 consecutive frames of hand landmarks
# 2. Encodes each frame spatially (84 → 256 dimensions)
# 3. Adds positional encoding to understand frame order
# 4. Processes sequence through 6 transformer layers (temporal understanding)
# 5. Uses mean pooling to combine all frames into single representation
# 6. Classifies into one of 300 word classes
class TemporalTransformer(nn.Module):
    """Temporal Transformer used in training (256 dim, 8 heads, 6 layers)."""
    def __init__(self, input_dim=84, num_classes=300, hidden_dim=256,
                 num_heads=8, num_layers=6, dropout=0.4, num_frames=30):
        super().__init__()
        self.expects_sequence = True  # Flag: this model needs sequences
        self.num_frames = num_frames  # Number of frames in sequence (30)
        self.hidden_dim = hidden_dim  # Hidden dimension (256)
        
        # Spatial encoder: processes each frame independently
        # Converts 84 features (2 hands) → 256 hidden dimensions
        self.spatial_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),  # 84 → 256
            nn.LayerNorm(hidden_dim),  # Normalize activations
            nn.GELU(),  # Activation function (smooth ReLU)
            nn.Dropout(dropout * 0.5)  # Light dropout
        )
        
        # Positional encoding: tells model which frame is which (temporal order)
        # Learnable parameters that encode frame positions
        self.pos_encoding = nn.Parameter(torch.randn(1, num_frames, hidden_dim) * 0.02)
        
        # Transformer encoder layer configuration
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,  # Model dimension: 256
            nhead=num_heads,  # Attention heads: 8 (parallel attention mechanisms)
            dim_feedforward=hidden_dim * 4,  # Feedforward dimension: 1024
            dropout=dropout,  # Dropout rate: 0.4
            activation='gelu',  # Activation function
            batch_first=True  # Batch dimension first
        )
        # Stack 6 transformer layers for deep understanding
        self.temporal_transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # Classifier head: converts transformer output to word predictions
        self.classifier = nn.Sequential(
            nn.LayerNorm(hidden_dim),  # Normalize
            nn.Linear(hidden_dim, hidden_dim * 2),  # 256 → 512
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, hidden_dim),  # 512 → 256
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes)  # 256 → 300 (number of word classes)
        )
    
    def forward(self, x):
        # Input: (batch, frames, 84) - sequence of frames
        x = self.spatial_encoder(x)  # Encode each frame: (batch, frames, 256)
        # Add positional encoding to indicate frame order
        x = x + self.pos_encoding[:, :x.shape[1], :]
        x = self.temporal_transformer(x)  # Process sequence: (batch, frames, 256)
        # NOTE: Uses SIMPLE MEAN POOLING (not MultiHeadAttentionPooling)
        # Mean pooling was chosen over attention pooling because it achieved
        # better accuracy (77.33%) and is simpler/faster.
        x = x.mean(dim=1)  # Average pooling across frames: (batch, 256)
        return self.classifier(x)  # Predict word: (batch, num_classes)


# ============================================================================
# SECTION 3: INITIALIZATION AND MODEL LOADING
# ============================================================================

# Set computation device (GPU if available, else CPU)
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print("="*60)
print("SIGN LANGUAGE CLASSIFIER")
print("="*60)

# Letter label mapping: index → letter (A-Z)
LETTER_LABELS = {
    0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E', 5: 'F', 6: 'G', 7: 'H', 8: 'I',
    9: 'J', 10: 'K', 11: 'L', 12: 'M', 13: 'N', 14: 'O', 15: 'P', 16: 'Q',
    17: 'R', 18: 'S', 19: 'T', 20: 'U', 21: 'V', 22: 'W', 23: 'X', 24: 'Y', 25: 'Z'
}

# ----------------------------------------------------------------------------
# Load Letter Model (sklearn MLP)
# ----------------------------------------------------------------------------
# EXPLANATION: Loads the pre-trained sklearn MLP classifier for letter recognition.
# This model takes 42 features (1 hand × 21 landmarks × 2 coordinates) and
# outputs probabilities for 26 letters (A-Z).
print("Loading LETTER model...")
letter_model = None
try:
    with open('./mlp_model.p', 'rb') as f:
        letter_data = pickle.load(f)  # Load saved model data
        letter_model = letter_data['model']  # Extract the sklearn MLP model
    print(f"[OK] LETTER model loaded - sklearn MLP")
    print(f"  Features: {letter_model.n_features_in_}")  # Should be 42
    print(f"  Classes: A-Z (26 letters)")
except Exception as e:
    print(f"[ERROR] Letter model error: {e}")

# ----------------------------------------------------------------------------
# Load Word Model (TemporalTransformer)
# ----------------------------------------------------------------------------
# EXPLANATION: Loads the TemporalTransformer word recognition model.
# The system automatically detects the model architecture by checking if the
# checkpoint contains "spatial_encoder" keys (which indicates TemporalTransformer).
# 
# NOTE: The code supports loading both old and new models for backward compatibility,
# but the CURRENT PRODUCTION MODEL is TemporalTransformer (sequence-based, 30 frames).
print("Loading WORD model...")
word_model = None
word_labels = None  # Dictionary mapping class index → word string
word_scaler = None  # Scaler for normalizing input features
WORD_FRAMES = 30  # Default: 30 frames for temporal model

try:
    # Try multiple possible filenames (handles variations)
    # NOTE: The system looks for TemporalTransformer model files first
    prep_path_options = ['./preprocessing_word.pkl', './preprocessing_word .pkl']
    model_path_options = [
        './temporal_transformer_model.pth',  # PRIMARY: TemporalTransformer (CURRENT MODEL)
        './temporal_transformer_mlp_word_model.pth',  # Alternative temporal name
        './transformer_mlp_word_model.pth',  # Fallback: Old single-frame model (for compatibility)
        './transformer_mlp_word_model (1).pth'  # Alternative old model name
    ]
    # Find first existing file
    prep_path = next((p for p in prep_path_options if os.path.exists(p)), None)
    model_path = next((p for p in model_path_options if os.path.exists(p)), None)

    if prep_path and model_path:
        # Load preprocessing data (scaler, label encoder)
        with open(prep_path, 'rb') as f:
            word_prep = pickle.load(f)
            word_scaler = word_prep['scaler']  # Feature scaler (normalization)
            word_encoder = word_prep.get('label_encoder', word_prep.get('encoder'))
            WORD_FRAMES = word_prep.get('num_frames', WORD_FRAMES)  # Get frame count
            WORD_FRAMES_BUFFER = WORD_FRAMES
        
        if word_encoder is None:
            raise ValueError("Label encoder not found in preprocessing file")
        
        num_word_classes = len(word_encoder.classes_)  # Number of word classes
        state_dict = torch.load(model_path, map_location=DEVICE, weights_only=False)

        # Auto-detect architecture by checking checkpoint keys
        # CURRENT MODEL: TemporalTransformer (has "spatial_encoder" in checkpoint)
        if any(k.startswith("spatial_encoder") for k in state_dict.keys()):
            # ✅ TemporalTransformer detected - THIS IS THE CURRENT PRODUCTION MODEL
            word_model = TemporalTransformer(
                input_dim=84,  # 2 hands × 21 landmarks × 2 coords
                num_classes=num_word_classes,
                hidden_dim=256,  # 256 dimensions
                num_heads=8,  # 8 attention heads
                num_layers=6,  # 6 transformer layers
                dropout=0.4,
                num_frames=WORD_FRAMES  # 30 frames
            ).to(DEVICE)
        else:
            # ⚠️ OLD MODEL DETECTED - NOT THE CURRENT PRODUCTION MODEL
            # This code path is for backward compatibility only.
            # The CURRENT PRODUCTION MODEL is TemporalTransformer (above).
            # If you see this message, you're using an old model file.
            # 
            # NOTE: The old TransformerMLPWord class is not included in this
            # annotated documentation. Only TemporalTransformer is documented
            # as it is the model currently in use.
            print("[WARNING] Old single-frame model detected!")
            print("[INFO] Current production model is TemporalTransformer.")
            print("[INFO] Please use temporal_transformer_model.pth for best results.")
            # For backward compatibility, we would load old model here, but it's
            # not documented in this annotated file. See original final_classifier.py
            raise ValueError("Old model not supported in annotated version. Use TemporalTransformer.")
        
        # Load trained weights into model
        word_model.load_state_dict(state_dict)
        word_model.eval()  # Set to evaluation mode (no training)
        
        # Create label dictionary: index → word string
        word_labels = {i: str(c).upper() for i, c in enumerate(word_encoder.classes_)}
        
        # Print model info
        # The current production model is always TemporalTransformer
        if getattr(word_model, "expects_sequence", False):
            print(f"[OK] WORD model loaded - TemporalTransformer (CURRENT PRODUCTION MODEL)")
            print(f"  Architecture: 256 hidden dim / 8 heads / 6 layers")
            print(f"  Frames: {WORD_FRAMES} (sequence-based)")
            print(f"  Accuracy: 77.33%")
        else:
            # This should not happen with current setup
            print(f"[WARNING] Old model detected - not recommended for production")
        print(f"  Classes: {num_word_classes} words")
        print(f"  Sample words: {list(word_labels.values())[:10]}...")
        
        # Check if model actually contains words or just letters (validation)
        sample_labels = list(word_labels.values())[:20]
        letter_count = sum(1 for label in sample_labels if len(label) == 1 and label.isalpha())
        word_count = sum(1 for label in sample_labels if len(label) > 1)
        print(f"  Label check: {letter_count} single letters, {word_count} multi-character words in first 20 labels")
        if letter_count > word_count:
            print(f"  ⚠️  WARNING: Word model appears to contain mostly single letters!")
            print(f"  ⚠️  This will cause words to be split into letters. Please retrain with word labels.")
    else:
        print("[ERROR] WORD model files not found")
except Exception as e:
    print(f"[ERROR] Word model error: {e}")
    word_model = None
    word_labels = None
    word_scaler = None


# ============================================================================
# SECTION 4: SMOOTHING AND PREDICTION CONFIGURATION
# ============================================================================

# Smoothing parameters: average predictions over multiple frames for stability
SMOOTH_FRAMES = 30  # Number of frames to average over (30 = ~0.5 seconds at 60fps)
WORD_FRAMES_BUFFER = 30  # Buffer size for temporal model (will be overwritten)
CONSISTENCY_THRESHOLD = 25  # Require 25/30 frames (83%) to lock prediction
MIN_CONFIDENCE_LETTER = 0.10  # 10% minimum confidence for letter display
MIN_CONFIDENCE_WORD = 0.10  # 10% minimum confidence for word display
MIN_CONFIDENCE_DISPLAY = 0.05  # 5% minimum to show prediction at all

# History buffers: store recent predictions for averaging
letter_history = deque(maxlen=SMOOTH_FRAMES)  # Probability distributions for letters
word_history = deque(maxlen=SMOOTH_FRAMES)  # Probability distributions for words
word_sequence_buffer = deque(maxlen=WORD_FRAMES)  # Raw features for temporal model

# Prediction tracking: maintain history of predicted letters/words
letter_prediction_history = deque(maxlen=SMOOTH_FRAMES)  # Track letter predictions
word_prediction_history = deque(maxlen=SMOOTH_FRAMES)  # Track word predictions

# Prediction locking system: ensures one sign = one letter/word
# EXPLANATION: When a prediction is consistent enough, it gets "locked" so the
# same sign always produces the same output, preventing flickering.
locked_letter = None  # Currently locked letter (if any)
locked_letter_frames = 0  # Frames remaining in lock
locked_letter_confidence_history = deque(maxlen=20)  # Track confidence over time
locked_word = None  # Currently locked word (if any)
locked_word_frames = 0  # Frames remaining in lock
locked_word_confidence_history = deque(maxlen=20)  # Track confidence over time

# Locking parameters
PREDICTION_LOCK_DURATION = 300  # Lock for 300 frames (~5 seconds at 60fps)
UNLOCK_CONFIDENCE_DROP = 0.35  # 35% confidence drop triggers unlock check
UNLOCK_CONFIDENCE_GAP = 0.30  # New prediction must be 30%+ better to unlock

# Text output tracking
detected_text = ""  # Accumulated sentence being built
last_letter = ""  # Last letter added (prevents duplicates)
last_word = ""  # Last word added (prevents duplicates)
letter_hold_count = 0  # Frames user has held current letter sign
word_hold_count = 0  # Frames user has held current word sign
HOLD_THRESHOLD = 15  # Frames to hold before adding letter (prevents accidental additions)
nlp_enabled = NLP_AVAILABLE  # NLP processing toggle

# Word mode lock: prevents rapid switching between letter/word modes
word_mode_lock = False  # Is word mode currently locked?
word_mode_lock_frames = 0  # Frames remaining in word mode lock
WORD_MODE_LOCK_DURATION = 30  # Keep word mode for 30 frames (0.5 seconds)


# ============================================================================
# SECTION 5: MEDIAPIPE HAND DETECTION SETUP
# ============================================================================

# Initialize video capture from default camera (index 0)
cap = cv2.VideoCapture(0)

# MediaPipe hand detection setup
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils  # For drawing hand landmarks
mp_drawing_styles = mp.solutions.drawing_styles  # Drawing styles

# Configure hand detector
hands = mp_hands.Hands(
    static_image_mode=False,  # Video mode (not static images)
    min_detection_confidence=0.6,  # 60% confidence required to detect hand
    min_tracking_confidence=0.5,  # 50% confidence to keep tracking
    max_num_hands=2  # Maximum 2 hands (for word detection)
)


# ============================================================================
# SECTION 6: VALIDATION THRESHOLDS
# ============================================================================

# Word detection (2 hands) thresholds
MIN_HAND_DISTANCE = 0.02  # Hands must be 2% of frame apart
MIN_HANDEDNESS_CONFIDENCE = 0.7  # 70% confidence for hand detection
MIN_HAND_SIZE_WORD = 0.05  # Minimum 5% of frame size (filters small objects)
MAX_HAND_SIZE_RATIO = 3.5  # Max size ratio between hands (ensures similar sizes)

# Letter detection (1 hand) thresholds
MIN_HAND_SIZE_LETTER = 0.05  # Minimum 5% of frame size
MIN_HANDEDNESS_CONFIDENCE_LETTER = 0.7  # 70% confidence required
hand_count_history = deque(maxlen=5)  # Temporal smoothing for hand count


# ============================================================================
# SECTION 7: HELPER FUNCTIONS
# ============================================================================

def get_hand_center(landmarks):
    """Calculate center point of hand (average of all landmark positions)"""
    x_coords = [lm.x for lm in landmarks.landmark]  # X coordinates
    y_coords = [lm.y for lm in landmarks.landmark]  # Y coordinates
    return (sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords))  # Average


def get_hand_size(landmarks):
    """Calculate hand size as percentage of frame (max of width or height)"""
    x_coords = [lm.x for lm in landmarks.landmark]
    y_coords = [lm.y for lm in landmarks.landmark]
    # Return maximum span (width or height) as percentage
    return max(max(x_coords) - min(x_coords), max(y_coords) - min(y_coords))


def validate_hand_shape(landmarks):
    """
    Validate that detected landmarks form a proper hand shape.
    Filters out false positives like mouse, random objects, etc.
    Checks:
    1. Finger-to-wrist distances are reasonable
    2. Middle finger is typically longest
    3. Fingers have reasonable spread (not too close together)
    """
    try:
        # Get key landmarks: wrist and all fingertips
        wrist = landmarks.landmark[0]  # Wrist is landmark 0
        thumb_tip = landmarks.landmark[4]  # Thumb tip
        index_tip = landmarks.landmark[8]  # Index finger tip
        middle_tip = landmarks.landmark[12]  # Middle finger tip
        ring_tip = landmarks.landmark[16]  # Ring finger tip
        pinky_tip = landmarks.landmark[20]  # Pinky tip
        
        # Calculate 3D distance between two points
        def distance(p1, p2):
            return ((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)**0.5
        
        # Measure distances from wrist to each fingertip
        thumb_dist = distance(wrist, thumb_tip)
        index_dist = distance(wrist, index_tip)
        middle_dist = distance(wrist, middle_tip)
        ring_dist = distance(wrist, ring_tip)
        pinky_dist = distance(wrist, pinky_tip)
        
        # Check 1: Fingertips should be at reasonable distances from wrist
        min_dist = 0.15  # Minimum distance (too close = invalid)
        max_dist = 0.6   # Maximum distance (too far = invalid)
        distances = [thumb_dist, index_dist, middle_dist, ring_dist, pinky_dist]
        
        # At least 3 fingers should be in valid range
        valid_fingers = sum(1 for d in distances if min_dist < d < max_dist)
        if valid_fingers < 3:
            return False  # Not enough valid fingers
        
        # Check 2: Middle finger should be longest (or close to it)
        # This filters out mouse-like shapes where all fingers are same length
        if middle_dist < max(distances) * 0.7:
            return False  # Middle finger too short relative to longest
        
        # Check 3: Finger spread - fingers shouldn't be too close together
        finger_tips = [index_tip, middle_tip, ring_tip, pinky_tip]
        spreads = []
        for i in range(len(finger_tips) - 1):
            spread = distance(finger_tips[i], finger_tips[i+1])
            spreads.append(spread)
        
        # Average spread should be reasonable (prevents detecting mouse)
        avg_spread = sum(spreads) / len(spreads)
        if avg_spread < 0.03:  # Fingers too close together
            return False
        
        return True  # All checks passed - valid hand shape
        
    except Exception as e:
        return False  # If any error, reject detection


def validate_two_hands(results):
    """
    STRICT validation for 2-hand detection.
    Prevents false positives by checking:
    1. Exactly 2 hands detected
    2. High confidence for both hands
    3. Both hands have valid shapes
    4. Hands are far enough apart
    5. Both hands are reasonable size
    6. Hand sizes are similar
    """
    if len(results.multi_hand_landmarks) != 2:
        return False  # Must have exactly 2 hands
    
    # Check handedness confidence (MediaPipe's confidence score)
    for hand_info in results.multi_handedness:
        if hand_info.classification[0].score < MIN_HANDEDNESS_CONFIDENCE:
            return False  # Confidence too low
    
    # Validate both hands have proper shape
    if not validate_hand_shape(results.multi_hand_landmarks[0]):
        return False
    if not validate_hand_shape(results.multi_hand_landmarks[1]):
        return False
    
    # Check distance between hands - must be far enough apart
    center1 = get_hand_center(results.multi_hand_landmarks[0])
    center2 = get_hand_center(results.multi_hand_landmarks[1])
    distance = ((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)**0.5
    if distance < MIN_HAND_DISTANCE:
        return False  # Hands too close together
    
    # Check hand sizes - both must be reasonable
    size1 = get_hand_size(results.multi_hand_landmarks[0])
    size2 = get_hand_size(results.multi_hand_landmarks[1])
    if size1 < MIN_HAND_SIZE_WORD or size2 < MIN_HAND_SIZE_WORD:
        return False  # One or both hands too small
    
    # Hand sizes should be similar (prevents false tiny detection)
    if min(size1, size2) > 0:
        size_ratio = max(size1, size2) / min(size1, size2)
        if size_ratio > MAX_HAND_SIZE_RATIO:
            return False  # Size difference too large
    
    return True  # All checks passed


def validate_one_hand(results):
    """
    Validate 1-hand detection with proper checks.
    Returns True if:
    - Exactly 1 hand detected
    - High confidence
    - Proper size
    - Valid hand shape
    """
    if not results or not results.multi_hand_landmarks:
        return False
        
    if len(results.multi_hand_landmarks) != 1:
        return False  # Must have exactly 1 hand
    
    # Check confidence
    if results.multi_handedness:
        confidence = results.multi_handedness[0].classification[0].score
        if confidence < MIN_HANDEDNESS_CONFIDENCE_LETTER:
            return False
    
    # Check size
    hand_size = get_hand_size(results.multi_hand_landmarks[0])
    if hand_size < MIN_HAND_SIZE_LETTER:
        return False
    
    # Check shape
    if not validate_hand_shape(results.multi_hand_landmarks[0]):
        return False
    
    return True


def get_stable_hand_count(current_count):
    """
    Temporal smoothing for stable mode switching.
    Prevents rapid flickering between letter/word modes.
    - If 2 hands detected → immediately switch to word mode
    - Need 2 consecutive single-hand frames to switch to letter mode
    """
    hand_count_history.append(current_count)
    if current_count == 2:
        return 2  # Immediately switch to word mode
    if len(hand_count_history) < 1:
        return 1
    ones = sum(1 for c in hand_count_history if c == 1)
    return 1 if ones >= 2 else 2  # Need 2 consecutive ones


# ============================================================================
# SECTION 8: MAIN PROCESSING LOOP
# ============================================================================

print("="*60)
print("1 HAND  = LETTER (A-Z)")
print("2 HANDS = WORD")
print("Press 'Q' to quit, 'C' to clear, 'N' to toggle NLP")
print("="*60)

while True:
    # ------------------------------------------------------------------------
    # Frame Capture and Preprocessing
    # ------------------------------------------------------------------------
    ret, frame = cap.read()  # Read frame from camera
    if not ret:
        break  # Exit if camera fails
    
    H, W, _ = frame.shape  # Get frame dimensions (height, width)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert BGR → RGB
    results = hands.process(frame_rgb)  # Process with MediaPipe
    
    # ------------------------------------------------------------------------
    # UI Rendering: Header and Text Display
    # ------------------------------------------------------------------------
    # Draw header bar at top
    cv2.rectangle(frame, (0, 0), (W, 40), (50, 50, 50), -1)
    cv2.putText(frame, "1 HAND = LETTER  |  2 HANDS = WORD  |  Q = Quit  |  C = Clear  |  N = NLP", 
               (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    
    # Draw text display area at bottom
    cv2.rectangle(frame, (0, H - 80), (W, H), (40, 40, 40), -1)
    
    # Process text with NLP if enabled
    display_text = detected_text if detected_text else "[ Hold sign to add to text ]"
    if nlp_enabled and NLP_AVAILABLE and detected_text:
        try:
            processed_text = improve_translation(detected_text.strip(), is_sentence=True)
            if processed_text and processed_text != detected_text.strip():
                display_text = processed_text  # Show NLP-improved text
            else:
                display_text = detected_text  # Show raw if no change
        except Exception as e:
            print(f"[NLP ERROR] {e}")
            display_text = detected_text  # Fallback to raw
    
    # Display text
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
    
    # Show raw text if NLP is enabled
    if nlp_enabled and detected_text:
        cv2.putText(frame, f"Raw: {detected_text}", (80, H - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

    # ------------------------------------------------------------------------
    # Hand Detection and Mode Selection
    # ------------------------------------------------------------------------
    if results.multi_hand_landmarks:
        raw_num_hands = len(results.multi_hand_landmarks)  # Count detected hands
        is_valid_two_hands = raw_num_hands == 2 and validate_two_hands(results)
        
        # Determine current detection state
        current_detection = 2 if (raw_num_hands == 2 and is_valid_two_hands) else 1
        stable_hand_count = get_stable_hand_count(current_detection)
        
        # --------------------------------------------------------------------
        # Word Mode Logic (2 Hands)
        # --------------------------------------------------------------------
        allow_word_mode = False
        if raw_num_hands == 2:
            # Check if word model is loaded and validation passes
            if word_model is not None and word_scaler is not None and word_labels is not None:
                if is_valid_two_hands:
                    allow_word_mode = True
                    word_mode_lock = True  # Lock into word mode
                    word_mode_lock_frames = WORD_MODE_LOCK_DURATION
                    # Clear letter history to prevent contamination
                    letter_history.clear()
                    letter_prediction_history.clear()
                    letter_hold_count = 0
                    locked_letter = None
                    locked_letter_frames = 0
                    locked_letter_confidence_history.clear()
                else:
                    # Validation failed but still allow word mode if lock is active
                    if word_mode_lock and word_mode_lock_frames > 0:
                        allow_word_mode = True
                    else:
                        # First time - be lenient, allow word mode anyway
                        allow_word_mode = True
                        word_mode_lock = True
                        word_mode_lock_frames = WORD_MODE_LOCK_DURATION // 2
                        # Clear letter buffers
                        letter_history.clear()
                        letter_prediction_history.clear()
                        letter_hold_count = 0
                        locked_letter = None
                        locked_letter_frames = 0
                        locked_letter_confidence_history.clear()
        
        # Clear word mode lock if only 1 hand detected
        if raw_num_hands == 1:
            if word_mode_lock:
                print(f"[CLEAR WORD LOCK] Only 1 hand detected - clearing word mode lock")
            word_mode_lock = False
            word_mode_lock_frames = 0
            allow_word_mode = False
        
        # Update word mode lock
        if word_mode_lock and word_mode_lock_frames > 0:
            if raw_num_hands == 2 and is_valid_two_hands:
                if word_model is not None and word_scaler is not None and word_labels is not None:
                    allow_word_mode = True
                    word_mode_lock_frames = WORD_MODE_LOCK_DURATION
            else:
                word_mode_lock = False
                word_mode_lock_frames = 0
                allow_word_mode = False
        elif word_mode_lock_frames <= 0:
            word_mode_lock = False
            allow_word_mode = False
        
        # Show hint if 2 hands detected but validation failing
        if raw_num_hands == 2 and not is_valid_two_hands and not allow_word_mode:
            cv2.putText(frame, "Two hands seen - spread/resize for WORD mode",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 215, 255), 2)
        
        # ====================================================================
        # WORD DETECTION (2 HANDS)
        # ====================================================================
        if raw_num_hands == 2 and raw_num_hands != 1 and word_model is not None and word_scaler is not None and word_labels is not None:
            if not allow_word_mode:
                allow_word_mode = True
                word_mode_lock = True
                word_mode_lock_frames = WORD_MODE_LOCK_DURATION
            
            if allow_word_mode:
                # Clear letter history
                letter_history.clear()
                letter_prediction_history.clear()
                letter_hold_count = 0
                locked_letter = None
                locked_letter_frames = 0
                locked_letter_confidence_history.clear()
                
                # Extract hand data
                hands_data = {'Left': None, 'Right': None}
                all_x, all_y = [], []
                
                # Process both hands
                for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    # Draw landmarks on frame
                    mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style())
                    
                    # Get handedness (Left/Right)
                    handedness = results.multi_handedness[idx].classification[0].label
                    x_ = [lm.x for lm in hand_landmarks.landmark]
                    y_ = [lm.y for lm in hand_landmarks.landmark]
                    all_x.extend(x_)
                    all_y.extend(y_)
                    
                    # Normalize coordinates (relative to hand's min position)
                    min_x, min_y = min(x_), min(y_)
                    hand_data = []
                    for lm in hand_landmarks.landmark:
                        hand_data.append(lm.x - min_x)  # Normalized x
                        hand_data.append(lm.y - min_y)  # Normalized y
                    hands_data[handedness] = hand_data
                
                # Combine both hands: Left (42) + Right (42) = 84 features
                combined = []
                if raw_num_hands == 2:
                    if hands_data['Left'] is not None and hands_data['Right'] is not None:
                        combined.extend(hands_data['Left'])
                        combined.extend(hands_data['Right'])
                    elif len(results.multi_hand_landmarks) == 2:
                        # Fallback: use hands in order if not labeled
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
                
                # Calculate bounding box for visualization
                x1 = max(0, int(min(all_x) * W) - 15) if all_x else 0
                y1 = max(0, int(min(all_y) * H) - 15) if all_y else 0
                x2 = min(W, int(max(all_x) * W) + 15) if all_x else W
                y2 = min(H, int(max(all_y) * H) + 15) if all_y else H
                
                # Process word prediction
                if word_model and word_scaler and word_labels and len(combined) == 84:
                    try:
                        # Normalize features using scaler
                        data_scaled = word_scaler.transform([combined])[0]
                        
                        # Check if model expects sequences (temporal) or single frames
                        if getattr(word_model, "expects_sequence", False):
                            # ================================================
                            # TEMPORAL MODEL PATH (Sequence-based)
                            # ================================================
                            # Add frame to buffer
                            word_sequence_buffer.append(data_scaled)
                            
                            # Process when buffer is full
                            if len(word_sequence_buffer) == WORD_FRAMES_BUFFER:
                                # Convert to tensor: (1, frames, 84)
                                seq = np.array(word_sequence_buffer, dtype=np.float32)
                                input_tensor = torch.FloatTensor(seq).unsqueeze(0).to(DEVICE)
                                
                                # Run inference
                                with torch.no_grad():
                                    outputs = word_model(input_tensor)
                                    probs = torch.softmax(outputs, dim=1)[0].cpu().numpy()
                                
                                # Add to history for smoothing
                                word_history.append(probs)
                                avg_probs = np.mean(list(word_history), axis=0)
                                
                                # Get top prediction
                                top_idx = np.argmax(avg_probs)
                                confidence = avg_probs[top_idx]
                                predicted = word_labels[top_idx]
                                
                                # Handle prediction locking (same logic as single-frame below)
                                stable_predicted = predicted
                                confidence_highest = confidence
                                
                                if locked_word and locked_word_frames > 0:
                                    # Check if should keep locked
                                    locked_idx = list(word_labels.values()).index(locked_word)
                                    locked_confidence = avg_probs[locked_idx]
                                    locked_word_confidence_history.append(locked_confidence)
                                    avg_locked_confidence = np.mean(list(locked_word_confidence_history))
                                    
                                    top2_indices = np.argsort(avg_probs)[-2:]
                                    confidence_drop = avg_locked_confidence - locked_confidence
                                    highest_confidence = np.max(avg_probs)
                                    confidence_gap = highest_confidence - locked_confidence
                                    highest_idx = np.argmax(avg_probs)
                                    highest_predicted = word_labels[highest_idx]
                                    
                                    keep_locked = (locked_idx in top2_indices and 
                                                 confidence_drop < UNLOCK_CONFIDENCE_DROP and 
                                                 confidence_gap < UNLOCK_CONFIDENCE_GAP and
                                                 highest_predicted == locked_word)
                                    
                                    if keep_locked:
                                        top_idx = np.argmax(avg_probs)
                                        stable_predicted = word_labels[top_idx]
                                        confidence_highest = avg_probs[top_idx]
                                        locked_word_frames -= 1
                                        
                                        # Filter to words only
                                        if len(stable_predicted) == 1:
                                            top_candidates = np.argsort(avg_probs)[-10:][::-1]
                                            for idx in top_candidates:
                                                if len(word_labels[idx]) > 1:
                                                    stable_predicted = word_labels[idx]
                                                    confidence_highest = avg_probs[idx]
                                                    break
                                    else:
                                        new_word = word_labels[np.argmax(avg_probs)]
                                        print(f"🔓 UNLOCKED WORD: '{locked_word}' → '{new_word}'")
                                        locked_word = None
                                        locked_word_frames = 0
                                        locked_word_confidence_history.clear()
                                
                                # Update prediction if not locked
                                if locked_word is None or locked_word_frames <= 0:
                                    top_idx_highest = np.argmax(avg_probs)
                                    stable_predicted = word_labels[top_idx_highest]
                                    confidence_highest = avg_probs[top_idx_highest]
                                    
                                    # Filter to words only
                                    if len(stable_predicted) == 1:
                                        top_candidates = np.argsort(avg_probs)[-10:][::-1]
                                        for idx in top_candidates:
                                            if len(word_labels[idx]) > 1:
                                                stable_predicted = word_labels[idx]
                                                confidence_highest = avg_probs[idx]
                                                break
                                    
                                    # Track for locking
                                    word_prediction_history.append(stable_predicted)
                                    
                                    # Check if should lock
                                    if len(word_prediction_history) >= CONSISTENCY_THRESHOLD and len(stable_predicted) > 1:
                                        from collections import Counter
                                        prediction_counts = Counter(word_prediction_history)
                                        most_common_prediction, most_common_count = prediction_counts.most_common(1)[0]
                                        
                                        if most_common_count >= CONSISTENCY_THRESHOLD and len(most_common_prediction) > 1:
                                            if most_common_prediction == stable_predicted:
                                                locked_word = most_common_prediction
                                                locked_word_frames = PREDICTION_LOCK_DURATION
                                                locked_word_confidence_history.clear()
                                                locked_idx = list(word_labels.values()).index(most_common_prediction)
                                                locked_confidence = avg_probs[locked_idx]
                                                locked_word_confidence_history.append(locked_confidence)
                                                print(f"🔒 LOCKED: '{most_common_prediction}'")
                                
                                # Visualize
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (180, 0, 180), 4)
                                cv2.putText(frame, f"WORD: {stable_predicted}", (x1, y1 - 40),
                                       cv2.FONT_HERSHEY_SIMPLEX, 1.3, (180, 0, 180), 3)
                                cv2.putText(frame, f"{confidence_highest*100:.1f}%", (x1, y1 - 10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 0, 180), 2)
                                
                                # Show top 3 alternatives
                                top3 = np.argsort(avg_probs)[-3:][::-1]
                                y_off = y2 + 25
                                for i in top3:
                                    cv2.putText(frame, f"{word_labels[i]}: {avg_probs[i]*100:.1f}%",
                                               (x1, y_off), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 0, 180), 2)
                                    y_off += 18
                                
                                # Add word to text if conditions met
                                if len(stable_predicted) > 1 and confidence_highest >= MIN_CONFIDENCE_WORD:
                                    if locked_word_frames > 0:
                                        if not detected_text.endswith(stable_predicted + " "):
                                            detected_text += stable_predicted + " "
                                            print(f"*** Added WORD: '{stable_predicted}' ***")
                                        last_word = stable_predicted
                                    elif stable_predicted != last_word:
                                        if not detected_text.endswith(stable_predicted + " "):
                                            detected_text += stable_predicted + " "
                                            print(f"*** Added WORD: '{stable_predicted}' ***")
                                        last_word = stable_predicted
                            else:
                                # Show buffer progress
                                cv2.putText(frame, f"Buffering word frames: {len(word_sequence_buffer)}/{WORD_FRAMES_BUFFER}",
                                           (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 0, 180), 2)
                        else:
                            # ================================================
                            # SINGLE-FRAME MODEL PATH
                            # ================================================
                            # Convert to tensor: (1, 84)
                            input_tensor = torch.FloatTensor(data_scaled).unsqueeze(0).to(DEVICE)
                            
                            # Run inference
                            with torch.no_grad():
                                outputs = word_model(input_tensor)
                                probs = torch.softmax(outputs, dim=1)[0].cpu().numpy()
                            
                            # Add to history for smoothing
                            word_history.append(probs)
                            avg_probs = np.mean(list(word_history), axis=0)
                            
                            # Get top prediction
                            top_idx = np.argmax(avg_probs)
                            confidence = avg_probs[top_idx]
                            predicted = word_labels[top_idx]
                            
                            # Handle locking (same logic as temporal model)
                            stable_predicted = predicted
                            confidence_highest = confidence
                            
                            if locked_word and locked_word_frames > 0:
                                locked_idx = list(word_labels.values()).index(locked_word)
                                locked_confidence = avg_probs[locked_idx]
                                locked_word_confidence_history.append(locked_confidence)
                                avg_locked_confidence = np.mean(list(locked_word_confidence_history))
                                
                                top2_indices = np.argsort(avg_probs)[-2:]
                                confidence_drop = avg_locked_confidence - locked_confidence
                                highest_confidence = np.max(avg_probs)
                                confidence_gap = highest_confidence - locked_confidence
                                highest_idx = np.argmax(avg_probs)
                                highest_predicted = word_labels[highest_idx]
                                
                                keep_locked = (locked_idx in top2_indices and 
                                             confidence_drop < UNLOCK_CONFIDENCE_DROP and 
                                             confidence_gap < UNLOCK_CONFIDENCE_GAP and
                                             highest_predicted == locked_word)
                                
                                if keep_locked:
                                    stable_predicted = locked_word
                                    confidence_highest = locked_confidence
                                    locked_word_frames -= 1
                                else:
                                    new_word = word_labels[np.argmax(avg_probs)]
                                    print(f"🔓 UNLOCKED WORD: '{locked_word}' → '{new_word}'")
                                    locked_word = None
                                    locked_word_frames = 0
                                    locked_word_confidence_history.clear()
                                    word_prediction_history.clear()
                            
                            # Update prediction if not locked
                            if locked_word is None or locked_word_frames <= 0:
                                top_idx_highest = np.argmax(avg_probs)
                                stable_predicted = word_labels[top_idx_highest]
                                confidence_highest = avg_probs[top_idx_highest]
                                
                                if len(stable_predicted) == 1:
                                    top_candidates = np.argsort(avg_probs)[-10:][::-1]
                                    for idx in top_candidates:
                                        if len(word_labels[idx]) > 1:
                                            stable_predicted = word_labels[idx]
                                            confidence_highest = avg_probs[idx]
                                            break
                                
                                word_prediction_history.append(stable_predicted)
                                
                                if len(word_prediction_history) >= CONSISTENCY_THRESHOLD and len(stable_predicted) > 1:
                                    from collections import Counter
                                    prediction_counts = Counter(word_prediction_history)
                                    most_common_prediction, most_common_count = prediction_counts.most_common(1)[0]
                                    
                                    if most_common_count >= CONSISTENCY_THRESHOLD and len(most_common_prediction) > 1:
                                        if most_common_prediction == stable_predicted:
                                            locked_word = most_common_prediction
                                            locked_word_frames = PREDICTION_LOCK_DURATION
                                            locked_word_confidence_history.clear()
                                            locked_word_confidence_history.append(confidence_highest)
                                            print(f"🔒 LOCKED WORD: '{locked_word}'")
                            
                            # Visualize
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (180, 0, 180), 4)
                            cv2.putText(frame, f"WORD: {stable_predicted}", (x1, y1 - 40),
                                       cv2.FONT_HERSHEY_SIMPLEX, 1.3, (180, 0, 180), 3)
                            cv2.putText(frame, f"{confidence_highest*100:.1f}%", (x1, y1 - 10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 0, 180), 2)
                            
                            # Show top 3 alternatives
                            top3 = np.argsort(avg_probs)[-3:][::-1]
                            y_off = y2 + 25
                            for i in top3:
                                cv2.putText(frame, f"{word_labels[i]}: {avg_probs[i]*100:.1f}%",
                                           (x1, y_off), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 0, 180), 2)
                                y_off += 18
                            
                            # Add word to text
                            if len(stable_predicted) > 1 and confidence_highest >= MIN_CONFIDENCE_WORD:
                                if locked_word_frames > 0:
                                    if not detected_text.endswith(stable_predicted + " "):
                                        detected_text += stable_predicted + " "
                                        print(f"*** Added WORD: '{stable_predicted}' ***")
                                    last_word = stable_predicted
                                elif stable_predicted != last_word:
                                    if not detected_text.endswith(stable_predicted + " "):
                                        detected_text += stable_predicted + " "
                                        print(f"*** Added WORD: '{stable_predicted}' ***")
                                    last_word = stable_predicted
                    except Exception as e:
                        print(f"ERROR in word prediction: {e}")
                        import traceback
                        traceback.print_exc()
        
        # ====================================================================
        # LETTER DETECTION (1 HAND)
        # ====================================================================
        elif raw_num_hands == 1:
            # Clear word mode lock
            if word_mode_lock:
                word_mode_lock = False
                word_mode_lock_frames = 0
                allow_word_mode = False
            
            # Clear word buffers if switching to letter mode
            if not word_mode_lock and word_mode_lock_frames <= 0:
                word_history.clear()
                word_prediction_history.clear()
                word_sequence_buffer.clear()
                locked_word = None
                locked_word_frames = 0
                locked_word_confidence_history.clear()
            
            # Process letter detection
            try:
                best_hand_idx = 0  # Only one hand, so index 0
                hand_landmarks = results.multi_hand_landmarks[best_hand_idx]
                
                # Get handedness
                handedness = "Unknown"
                if results.multi_handedness and len(results.multi_handedness) > best_hand_idx:
                    try:
                        handedness = results.multi_handedness[best_hand_idx].classification[0].label
                    except (AttributeError, IndexError):
                        pass
                
                # Draw landmarks
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style())
                
                # Extract coordinates
                x_ = [lm.x for lm in hand_landmarks.landmark]
                y_ = [lm.y for lm in hand_landmarks.landmark]
                
                # Normalize coordinates
                min_x, min_y = min(x_), min(y_)
                hand_data = []
                for lm in hand_landmarks.landmark:
                    hand_data.append(lm.x - min_x)  # Normalized x
                    hand_data.append(lm.y - min_y)  # Normalized y
                
                # Predict letter if model loaded and data valid
                if letter_model and len(hand_data) == 42:
                    # Get probabilities for all 26 letters
                    probs = letter_model.predict_proba([np.array(hand_data)])[0]
                    
                    # Add to history for smoothing
                    letter_history.append(probs)
                    avg_probs = np.mean(list(letter_history), axis=0)
                    
                    # Get highest confidence prediction
                    top_idx = np.argmax(avg_probs)
                    confidence = avg_probs[top_idx]
                    predicted = LETTER_LABELS[top_idx]
                    
                    # Handle prediction locking
                    if locked_letter and locked_letter_frames > 0:
                        locked_idx = list(LETTER_LABELS.values()).index(locked_letter)
                        locked_confidence = avg_probs[locked_idx]
                        locked_letter_confidence_history.append(locked_confidence)
                        avg_locked_confidence = np.mean(list(locked_letter_confidence_history))
                        
                        top2_indices = np.argsort(avg_probs)[-2:]
                        confidence_drop = avg_locked_confidence - locked_confidence
                        highest_confidence = np.max(avg_probs)
                        confidence_gap = highest_confidence - locked_confidence
                        highest_idx = np.argmax(avg_probs)
                        highest_predicted = LETTER_LABELS[highest_idx]
                        
                        keep_locked = (locked_idx in top2_indices and 
                                     confidence_drop < UNLOCK_CONFIDENCE_DROP and 
                                     confidence_gap < UNLOCK_CONFIDENCE_GAP and
                                     highest_predicted == locked_letter)
                        
                        if keep_locked:
                            top_idx = np.argmax(avg_probs)
                            predicted = LETTER_LABELS[top_idx]
                            confidence = avg_probs[top_idx]
                            locked_letter_frames -= 1
                        else:
                            new_letter = LETTER_LABELS[np.argmax(avg_probs)]
                            print(f"🔓 UNLOCKED LETTER: '{locked_letter}' → '{new_letter}'")
                            locked_letter = None
                            locked_letter_frames = 0
                            locked_letter_confidence_history.clear()
                            letter_prediction_history.clear()
                    
                    # Update prediction if not locked
                    if locked_letter is None or locked_letter_frames <= 0:
                        top_idx = np.argmax(avg_probs)
                        predicted = LETTER_LABELS[top_idx]
                        confidence = avg_probs[top_idx]
                        
                        letter_prediction_history.append(predicted)
                        
                        # Check if should lock
                        if len(letter_prediction_history) >= CONSISTENCY_THRESHOLD:
                            from collections import Counter
                            prediction_counts = Counter(letter_prediction_history)
                            most_common_prediction, most_common_count = prediction_counts.most_common(1)[0]
                            
                            if most_common_count >= CONSISTENCY_THRESHOLD:
                                if most_common_prediction == predicted:
                                    locked_letter = most_common_prediction
                                    locked_letter_frames = PREDICTION_LOCK_DURATION
                                    locked_letter_confidence_history.clear()
                                    locked_letter_confidence_history.append(confidence)
                                    print(f"🔒 LOCKED LETTER: '{locked_letter}'")
                    else:
                        letter_prediction_history.append(predicted)
                    
                    # Calculate bounding box
                    x1 = max(0, int(min(x_) * W) - 15)
                    y1 = max(0, int(min(y_) * H) - 15)
                    x2 = min(W, int(max(x_) * W) + 15)
                    y2 = min(H, int(max(y_) * H) + 15)
                    
                    # Color by confidence
                    if locked_letter_frames > 0:
                        color = (0, 255, 0)  # Green - locked
                    elif confidence >= 0.40:
                        color = (0, 255, 0)  # Green - very high
                    elif confidence >= MIN_CONFIDENCE_LETTER:
                        color = (0, 200, 255)  # Orange - good
                    elif confidence >= MIN_CONFIDENCE_DISPLAY:
                        color = (0, 255, 255)  # Yellow - medium
                    else:
                        color = (150, 150, 150)  # Gray - low
                    
                    # Visualize
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 4)
                    cv2.putText(frame, predicted, (x1, y1 - 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 2.0, color, 4)
                    cv2.putText(frame, f"{confidence*100:.1f}%", (x1 + 60, y1 - 25),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                    
                    # Show top 5 alternatives
                    top5 = np.argsort(avg_probs)[-5:][::-1]
                    y_off = y2 + 22
                    for i in top5:
                        cv2.putText(frame, f"{LETTER_LABELS[i]}: {avg_probs[i]*100:.1f}%",
                                   (x1, y_off), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                        y_off += 18
                    
                    # Show handedness
                    cv2.putText(frame, f"[{handedness}]", (x2 - 50, y1 - 5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 2)
                    
                    # Add letter to text
                    if raw_num_hands == 2:
                        letter_hold_count = 0  # Block if 2 hands
                    elif not word_mode_lock:
                        add_allowed = (locked_letter_frames > 0) or (confidence >= MIN_CONFIDENCE_LETTER)
                        
                        if add_allowed:
                            if locked_letter_frames > 0:
                                # Locked - add immediately
                                last_char_in_text = detected_text.strip()[-1] if detected_text.strip() else ""
                                if last_char_in_text != predicted:
                                    if detected_text and not detected_text.endswith(" "):
                                        detected_text += " " + predicted
                                    else:
                                        detected_text += predicted
                                    print(f"*** Added LETTER: {predicted} ***")
                                    last_letter = predicted
                                    letter_hold_count = HOLD_THRESHOLD
                            elif predicted == last_letter:
                                # Same letter - increment hold counter
                                letter_hold_count += 1
                                if letter_hold_count >= HOLD_THRESHOLD:
                                    last_char_in_text = detected_text.strip()[-1] if detected_text.strip() else ""
                                    if last_char_in_text != predicted:
                                        if detected_text and not detected_text.endswith(" "):
                                            detected_text += " " + predicted
                                        else:
                                            detected_text += predicted
                                        print(f"*** Added LETTER: {predicted} ***")
                                    letter_hold_count = HOLD_THRESHOLD
                            else:
                                # Different letter - reset counter
                                letter_hold_count = 1
                                last_letter = predicted
                        else:
                            letter_hold_count = 0
                    else:
                        letter_hold_count = 0
                    
                    # Show hold progress
                    if letter_hold_count > 0 and letter_hold_count < HOLD_THRESHOLD:
                        progress = int((letter_hold_count / HOLD_THRESHOLD) * 100)
                        cv2.putText(frame, f"Hold: {progress}%", (x1, y2 + 100),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    # Show lock status
                    if locked_letter_frames > 0:
                        cv2.putText(frame, "LOCKED", (x2 - 80, y2 + 25),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            except Exception as e:
                print(f"ERROR in letter processing: {e}")
                import traceback
                traceback.print_exc()
    
    else:
        # ====================================================================
        # NO HANDS DETECTED
        # ====================================================================
        # Reset all tracking when no hands detected
        letter_history.clear()
        letter_prediction_history.clear()
        locked_letter = None
        locked_letter_frames = 0
        locked_letter_confidence_history.clear()
        
        if not word_mode_lock:
            word_history.clear()
            word_prediction_history.clear()
            word_sequence_buffer.clear()
            locked_word = None
            locked_word_frames = 0
            locked_word_confidence_history.clear()
        
        hand_count_history.clear()
        letter_hold_count = 0
        last_letter = ""
        last_word = ""
        
        if not word_mode_lock:
            word_hold_count = 0
        
        # Decrement word mode lock
        if word_mode_lock_frames > 0:
            word_mode_lock_frames -= 1
        else:
            word_mode_lock = False

    # ------------------------------------------------------------------------
    # Display Frame and Handle User Input
    # ------------------------------------------------------------------------
    cv2.imshow('Sign Language Classifier', frame)  # Show frame
    key = cv2.waitKey(1) & 0xFF  # Wait for key press (1ms delay)
    
    if key == ord('q'):
        break  # Quit
    elif key == ord('c'):
        detected_text = ""  # Clear text
        print("*** Text cleared ***")
    elif key == ord('n') or key == ord('N'):
        nlp_enabled = not nlp_enabled  # Toggle NLP
        if NLP_AVAILABLE:
            print(f"*** NLP {'ENABLED' if nlp_enabled else 'DISABLED'} ***")
    elif key == ord(' '):
        detected_text += " "  # Add space
        print("*** Added space ***")
    elif key == 8:  # Backspace
        detected_text = detected_text[:-1]  # Delete last character
        print("*** Deleted last character ***")

# Cleanup
cap.release()  # Release camera
cv2.destroyAllWindows()  # Close all windows
print("Done.")

