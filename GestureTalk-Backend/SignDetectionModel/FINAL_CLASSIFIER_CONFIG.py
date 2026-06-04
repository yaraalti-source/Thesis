"""
FINAL CLASSIFIER CONFIGURATION
================================
Optimized settings for accurate and stable letter/word detection.
Use these settings in all classifier files for consistent behavior.

Last Updated: December 16, 2025
All improvements applied to final_classifier.py should use these settings.
"""

# ==================== SMOOTHING & CONSISTENCY ====================
SMOOTH_FRAMES = 20  # Maximum smoothing for highest accuracy and stability
CONSISTENCY_THRESHOLD = 12  # Require prediction to be consistent for 12 out of 20 frames (60%)

# ==================== CONFIDENCE THRESHOLDS ====================
# Letters (1 Hand - sklearn MLP)
MIN_CONFIDENCE_LETTER = 0.25  # Minimum 25% confidence to add letter to text
MIN_CONFIDENCE_LETTER_DISPLAY = 0.10  # Minimum 10% confidence to display letter

# Words (2 Hands - Transformer)
MIN_CONFIDENCE_WORD = 0.25  # Minimum 25% confidence to add word to text (SAME as letters)
MIN_CONFIDENCE_WORD_DISPLAY = 0.10  # Minimum 10% confidence to display word

# ==================== PREDICTION LOCKING ====================
PREDICTION_LOCK_DURATION = 100  # Lock for 100 frames (~1.7 seconds at 60fps)
UNLOCK_CONFIDENCE_DROP = 0.15  # 15% confidence drop triggers unlock check
UNLOCK_CONFIDENCE_GAP = 0.12  # New prediction must be 12%+ better to unlock
UNLOCK_TOP_N_CHECK = 3  # Check if locked prediction is in top 3

# ==================== HOLD THRESHOLDS ====================
HOLD_THRESHOLD_LETTER = 15  # Frames to hold letter before adding (faster response)
HOLD_THRESHOLD_WORD = 0  # Words add immediately (no hold required)

# ==================== HAND DETECTION ====================
# MediaPipe Hand Detection
MIN_DETECTION_CONFIDENCE = 0.6  # 60% detection confidence (prevents false detections like mouse)
MIN_TRACKING_CONFIDENCE = 0.5  # 50% tracking confidence (maintains tracking)

# Hand Validation
MIN_HAND_SIZE_LETTER = 0.05  # Minimum hand size 5% of frame for letters
MIN_HAND_SIZE_WORD = 0.05  # Minimum hand size 5% of frame for words
MIN_HANDEDNESS_CONFIDENCE_LETTER = 0.7  # 70% confidence for hand detection
MIN_HANDEDNESS_CONFIDENCE_WORD = 0.7  # 70% confidence for 2-hand detection

# 2-Hand Validation (Word Mode)
MIN_HAND_DISTANCE = 0.05  # Hands must be 5% of frame apart
MAX_HAND_SIZE_RATIO = 3.5  # Max ratio between hand sizes

# ==================== MODE SWITCHING ====================
WORD_MODE_LOCK_DURATION = 30  # Keep word mode for 30 frames (0.5 seconds)

# ==================== COLOR CODING ====================
# Letters
COLOR_LETTER_LOCKED = (0, 255, 0)  # Green - Locked and stable
COLOR_LETTER_HIGH = (0, 255, 0)  # Green - 40%+ confidence
COLOR_LETTER_GOOD = (0, 200, 255)  # Orange - 25-39% confidence
COLOR_LETTER_MEDIUM = (0, 255, 255)  # Yellow - 10-24% confidence
COLOR_LETTER_LOW = (150, 150, 150)  # Gray - <10% confidence

# Words
COLOR_WORD = (180, 0, 180)  # Purple - Word mode

# ==================== PREDICTION LOGIC ====================
"""
CRITICAL: Always Use HIGHEST CONFIDENCE Prediction

For LETTERS:
1. Get highest confidence: top_idx = np.argmax(avg_probs)
2. Track prediction history
3. Check if highest confidence letter appears 12+ times in 20 frames
4. If yes, LOCK to that highest confidence letter
5. Unlock only if ALL conditions met:
   - Locked letter NOT in top 3, AND
   - Confidence drop >= 15%, AND
   - New highest is 12%+ better

For WORDS:
1. Get highest confidence: top_idx = np.argmax(avg_probs)
2. Filter to words only (2+ characters)
3. Track prediction history
4. Check if highest confidence word appears 12+ times in 20 frames
5. If yes, LOCK to that highest confidence word
6. Unlock only if ALL conditions met (same as letters)
"""

# ==================== HAND SHAPE VALIDATION ====================
"""
validate_hand_shape() function checks:
- Finger proportions (distances from wrist to fingertips)
- Middle finger length (ensures typical hand structure)
- Finger spread (checks fingers aren't too close together)
- Minimum 3 valid fingers in valid range (0.15-0.6 units from wrist)

This prevents false detections of mouse, pens, etc.
"""

# ==================== KEY IMPROVEMENTS SUMMARY ====================
"""
1. HIGHEST CONFIDENCE SELECTION:
   - Always use np.argmax() for most confident prediction
   - Lock to highest confidence (not most common)
   
2. SMART UNLOCK LOGIC:
   - Uses AND logic (all conditions must be met to stay locked)
   - Unlocks when sign clearly changes
   - Different signs give different predictions
   
3. LOWER CONFIDENCE THRESHOLDS:
   - Letters: 25% (was 35-55%)
   - Words: 25% (was 35-45%)
   - Display: 10% for both
   
4. IMPROVED HAND DETECTION:
   - 60% detection confidence (prevents mouse detection)
   - Hand shape validation (filters non-hand objects)
   - 5% minimum hand size (prevents tiny false detections)
   
5. PREDICTION LOCKING:
   - 100-frame lock duration (strong stability)
   - Tracks confidence history
   - Smart unlock when sign changes
   
6. CONSISTENCY:
   - 12/20 frames (60%) required for locking
   - Fast locking for responsiveness
   - Smooth transitions between predictions
"""

# ==================== USAGE EXAMPLE ====================
"""
# In your classifier file:

from FINAL_CLASSIFIER_CONFIG import (
    SMOOTH_FRAMES, CONSISTENCY_THRESHOLD,
    MIN_CONFIDENCE_LETTER, MIN_CONFIDENCE_WORD,
    PREDICTION_LOCK_DURATION, UNLOCK_CONFIDENCE_DROP,
    HOLD_THRESHOLD_LETTER
)

# Use these values instead of hardcoded numbers
letter_history = deque(maxlen=SMOOTH_FRAMES)
# ... rest of your code
"""

print("="*60)
print("FINAL CLASSIFIER CONFIGURATION LOADED")
print("="*60)
print(f"Smooth Frames: {SMOOTH_FRAMES}")
print(f"Consistency: {CONSISTENCY_THRESHOLD}/{SMOOTH_FRAMES} ({CONSISTENCY_THRESHOLD/SMOOTH_FRAMES*100:.0f}%)")
print(f"Letter Confidence: {MIN_CONFIDENCE_LETTER*100:.0f}%")
print(f"Word Confidence: {MIN_CONFIDENCE_WORD*100:.0f}%")
print(f"Lock Duration: {PREDICTION_LOCK_DURATION} frames")
print(f"Hold Threshold: {HOLD_THRESHOLD_LETTER} frames")
print("="*60)









