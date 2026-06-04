# GestureTalk - Complete System Documentation

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Diagrams](#architecture-diagrams)
3. [Backend - Python ML Services](#backend-python-ml-services)
4. [Backend - Laravel API](#backend-laravel-api)
5. [Frontend - Flutter Mobile App](#frontend-flutter-mobile-app)
6. [Voice-to-Sign Translation](#voice-to-sign-translation)
7. [Visual Sign Language Display](#visual-sign-language-display)
8. [ElevenLabs TTS Integration](#elevenlabs-tts-integration)
9. [Data Flow & Communication](#data-flow-communication)
10. [Database Schema](#database-schema)
11. [File Structure](#file-structure)
12. [Technology Stack](#technology-stack)
13. [Performance Metrics](#performance-metrics)

---

## 🎯 System Overview

**GestureTalk** is a comprehensive **bidirectional** sign language translation system that enables:

**Sign → Text/Speech:**
- Real-time translation of American Sign Language (ASL) to text and speech
- Support for both live camera detection and media upload
- Natural voice synthesis using ElevenLabs TTS

**Voice → Sign:**
- Speech-to-text recognition
- Visual display of sign language representations (words and fingerspelling)
- Asset-based sign language visualization

The system consists of three main components:

1. **Flutter Mobile Application** (Frontend) - User interface, camera, microphone, and visual display
2. **Python ML Services** (Backend) - Machine learning models for sign detection
3. **Laravel API** (Backend) - User management, data persistence, TTS generation, and business logic

---

## 📐 Architecture Diagrams

### **1. High-Level System Architecture**

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                        GESTURETALK SYSTEM ARCHITECTURE              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Flutter)                          │
│                    Mobile App (Android/iOS)                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  📱 User Interface Screens                                   │  │
│  │  • Live Translation (Camera + Real-time detection)           │  │
│  │  • Media Upload (Image/Video translation)                    │  │
│  │  • Voice-to-Sign (Speech recognition → Visual display)       │  │
│  │  • History (Past translations)                               │  │
│  │  • Profile (User settings)                                   │  │
│  │  • Statistics (Usage analytics)                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              ↓ ↑                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  🔧 Services Layer                                           │  │
│  │  • Camera Service (Frame capture)                            │  │
│  │  • WebSocket Client (Real-time communication)                │  │
│  │  • HTTP Client (REST API calls)                              │  │
│  │  • Speech-to-Text (speech_to_text package)                   │  │
│  │  • Local Database (SQLite for offline)                       │  │
│  │  • TTS Service (ElevenLabs integration)                      │  │
│  │  • Asset Manager (Sign language images/videos)               │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓ ↑
                    Network Communication
         ┌──────────────────┴──────────────────┐
         ↓                                      ↓
┌─────────────────────────────┐   ┌─────────────────────────────┐
│  BACKEND - ML SERVICES      │   │  BACKEND - LARAVEL API      │
│  (Python + PyTorch)         │   │  (PHP + MySQL)              │
│  Port: 8001, 8002           │   │  Port: 8000                 │
├─────────────────────────────┤   ├─────────────────────────────┤
│                             │   │                             │
│ 🔌 WebSocket Server (8002)  │   │ 🔐 Authentication (JWT)     │
│ • Live translation          │   │ • User login/register       │
│ • Real-time predictions     │   │ • Token management          │
│ • Frame-by-frame processing │   │                             │
│                             │   │ 📊 Translation Management   │
│ 🌐 REST API Server (8001)   │   │ • Save translations         │
│ • Image upload              │   │ • Retrieve history          │
│ • Video upload              │   │ • CRUD operations           │
│ • Batch processing          │   │                             │
│                             │   │ 🔊 Text-to-Speech           │
│ 🤖 ML Models                │   │ • Speech synthesis          │
│ • Letter Model (MLP)        │   │ • Audio management          │
│ • Word Model (Transformer)  │   │                             │
│ • MediaPipe (Hand detection)│   │ 📱 User Management          │
│ • NLP Processor             │   │ • Profile updates           │
│                             │   │ • Settings                  │
└─────────────────────────────┘   └─────────────────────────────┘
         ↓                                      ↓
    Model Files                          MySQL Database
 • mlp_model.p              ┌──────────────────────────────────┐
 • transformer_mlp_word     │  Tables:                         │
   _model.pth               │  • users                         │
 • preprocessing_word.pkl   │  • translations                  │
                            │  • translated_texts              │
                            │  • translated_audios             │
                            └──────────────────────────────────┘
```

---

### **2. Real-Time Translation Flow (Live Camera)**

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃           REAL-TIME TRANSLATION FLOW (WebSocket)                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

USER SHOWS HAND SIGN
      ↓
┌─────────────────────────────────────────────────────────────────┐
│ FLUTTER APP - live_translation_screen.dart                      │
│                                                                  │
│  1. Camera Capture                                              │
│     • CameraController captures frame (30-60 FPS)               │
│     • Encode frame as JPEG bytes                                │
│     File: lib/screens/live_translation_screen.dart (Lines 74-156)
│                                                                  │
│  2. Send via WebSocket                                          │
│     • WebSocketChannel.sink.add(frameBytes)                     │
│     • Connection to ws://SERVER_IP:8002                         │
│     File: lib/screens/live_translation_screen.dart (Line 81)    │
└─────────────────────────────────────────────────────────────────┘
      ↓ [Network: ~10-20ms]
┌─────────────────────────────────────────────────────────────────┐
│ PYTHON - websocket_final_classifier.py                          │
│                                                                  │
│  3. Receive & Decode Frame                                      │
│     frame = np.frombuffer(message, dtype=np.uint8)              │
│     frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)               │
│     File: websocket_final_classifier.py (Lines 449-458)         │
│                                                                  │
│  4. Hand Detection (MediaPipe)                                  │
│     results = hands.process(frame_rgb)                          │
│     • Detect 0, 1, or 2 hands                                   │
│     • Extract 21 landmarks per hand (x, y, z coordinates)       │
│     File: websocket_final_classifier.py (Line 522)              │
│     MediaPipe Config: Lines 327-332                             │
│                                                                  │
│  5. Hand Validation                                             │
│     • validate_hand_shape() - Check finger proportions          │
│     • validate_one_hand() or validate_two_hands()               │
│     • Filter false positives (mouse, pens, etc.)                │
│     Files: Lines 360-456                                        │
│                                                                  │
│  6. Feature Extraction                                          │
│     • Normalize landmarks relative to bounding box              │
│     • 1 hand: 42 features (21 landmarks × 2 coords)             │
│     • 2 hands: 84 features (42 × 2)                             │
│     File: Lines 354-421                                         │
│                                                                  │
│  7. Model Prediction                                            │
│     ┌─────────────────────┬──────────────────────┐             │
│     │  1 HAND DETECTED    │  2 HANDS DETECTED    │             │
│     │                     │                      │             │
│     │  Letter Model (MLP) │  Word Model (Temporal│             │
│     │  • sklearn MLP      │   Transformer)       │             │
│     │  • 42 → 26 classes  │  • PyTorch model     │             │
│     │  • Instant (~1ms)   │  • Wait 30 frames    │             │
│     │  • A-Z letters      │  • 84 → 300 classes  │             │
│     │                     │  • ~500ms total      │             │
│     │  File: Lines 546-   │  File: Lines 610-    │             │
│     │        574           │        719           │             │
│     └─────────────────────┴──────────────────────┘             │
│                                                                  │
│  8. Smoothing & Locking                                         │
│     • Average probabilities over 20 frames                      │
│     • Check consistency (12/20 frames)                          │
│     • Lock prediction for 100 frames if stable                  │
│     • Smart unlock when sign changes                            │
│     Files: Lines 289-306 (config), Lines 111-146 (logic)        │
│                                                                  │
│  9. Send JSON Response                                          │
│     await websocket.send(json.dumps({                           │
│         "type": "letter" or "word",                             │
│         "prediction": "A" or "HELLO",                           │
│         "confidence": 87.5,                                     │
│         "locked": true                                          │
│     }))                                                         │
│     File: Lines 564-568 (letter), 640-644 (word)                │
└─────────────────────────────────────────────────────────────────┘
      ↓ [Network: ~10-20ms]
┌─────────────────────────────────────────────────────────────────┐
│ FLUTTER APP - live_translation_screen.dart                      │
│                                                                  │
│  10. Receive & Parse Response                                   │
│      webSocketChannel.stream.listen((event) {                   │
│          final data = jsonDecode(event.toString());             │
│          final prediction = data['prediction'];                 │
│          final confidence = data['confidence'];                 │
│      })                                                         │
│      File: lib/screens/live_translation_screen.dart (Lines 86-156)
│                                                                  │
│  11. Update UI                                                  │
│      • Append to translation text                               │
│      • Display confidence with color coding                     │
│      • Show "LOCKED" indicator if stable                        │
│      File: Lines 110-123                                        │
│                                                                  │
│  12. Text-to-Speech                                             │
│      • Apply NLP processing (grammar improvement)               │
│      • Send to ElevenLabs API                                   │
│      • Play audio response                                      │
│      File: Lines 124-158                                        │
└─────────────────────────────────────────────────────────────────┘
      ↓
USER HEARS TRANSLATION & SEES TEXT
      ↓
CONTINUOUS LOOP - Next frame processed immediately

⏱️ TOTAL LATENCY:
• Letters: 50-100ms (instant)
• Words: 500-600ms (responsive)
```

---

### **3. Media Upload Flow (Image/Video)**

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃               MEDIA UPLOAD FLOW (REST API)                      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

USER SELECTS IMAGE/VIDEO FILE
      ↓
┌─────────────────────────────────────────────────────────────────┐
│ FLUTTER APP - media_translation_screen.dart                     │
│                                                                  │
│  1. File Selection                                              │
│     • ImagePicker.pickImage() or pickVideo()                    │
│     • User browses gallery or takes photo                       │
│     File: lib/screens/media_translation_screen.dart (Lines 189-206)
│                                                                  │
│  2. HTTP Multipart Upload                                       │
│     final request = http.MultipartRequest('POST', uri)          │
│     request.files.add(MultipartFile.fromPath('file', path))     │
│     • POST to http://SERVER_IP:8001/predict_image or           │
│       /predict_video                                            │
│     File: Lines 201-206                                         │
└─────────────────────────────────────────────────────────────────┘
      ↓ [Upload: depends on file size]
┌─────────────────────────────────────────────────────────────────┐
│ PYTHON - uploaded_files_classifier.py (FastAPI)                │
│                                                                  │
│  3. Receive Upload                                              │
│     @app.post("/predict_image")                                 │
│     async def predict_image(file: UploadFile):                  │
│     File: uploaded_files_classifier.py (Lines 406-423)          │
│                                                                  │
│  4. Decode File                                                 │
│     • For images: cv2.imdecode(image_bytes)                     │
│     • For videos: Save temp file, open with cv2.VideoCapture    │
│     Files: Lines 409-410 (image), 432-437 (video)               │
│                                                                  │
│  5. Process Frame(s)                                            │
│     ┌──────────────────────┬─────────────────────┐             │
│     │  IMAGE               │  VIDEO              │             │
│     │  • Process 1 frame   │  • Extract frames   │             │
│     │  • Immediate result  │  • Process every Nth│             │
│     │                      │  • Build sequence   │             │
│     └──────────────────────┴─────────────────────┘             │
│     Function: process_frame() - Lines 259-403                   │
│                                                                  │
│  6. Hand Detection, Validation, Feature Extraction              │
│     • Same pipeline as real-time (MediaPipe + validation)       │
│     • Same models (MLP for letters, Transformer for words)      │
│     Files: Lines 266-401                                        │
│                                                                  │
│  7. Return JSON Response                                        │
│     For image:                                                  │
│     {                                                           │
│         "type": "letter",                                       │
│         "translation": "A",                                     │
│         "confidence": 87.5                                      │
│     }                                                           │
│                                                                  │
│     For video:                                                  │
│     {                                                           │
│         "translation": "HELLO WORLD",                           │
│         "details": [                                            │
│             {"frame": 30, "prediction": "HELLO", ...},          │
│             {"frame": 90, "prediction": "WORLD", ...}           │
│         ]                                                       │
│     }                                                           │
│     Files: Lines 419-423 (image), 477-480 (video)               │
└─────────────────────────────────────────────────────────────────┘
      ↓ [Network: depends on result size]
┌─────────────────────────────────────────────────────────────────┐
│ FLUTTER APP - media_translation_screen.dart                     │
│                                                                  │
│  8. Parse Response                                              │
│     final responseData = await response.stream.bytesToString(); │
│     final decodedResponse = jsonDecode(responseData);           │
│     File: Lines 212-229                                         │
│                                                                  │
│  9. Display Translation                                         │
│     • Show translated text                                      │
│     • Display confidence                                        │
│     • Show frame details for videos                             │
│     File: Lines 227-257                                         │
└─────────────────────────────────────────────────────────────────┘
      ↓
USER SEES TRANSLATION RESULT

⏱️ TOTAL TIME:
• Image: 2-5 seconds
• Video: 5-30 seconds (depends on length)
```

---

### **4. User Authentication & Data Flow**

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃            AUTHENTICATION & DATA PERSISTENCE FLOW               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

USER OPENS APP
      ↓
┌─────────────────────────────────────────────────────────────────┐
│ FLUTTER APP - login_screen.dart / sign_up_screen.dart          │
│                                                                  │
│  1. User Authentication                                         │
│     • Enter email & password                                    │
│     • POST to http://SERVER_IP:8000/api/login                  │
│     File: lib/screens/login_screen.dart                         │
└─────────────────────────────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────────────────────────────┐
│ LARAVEL API - AuthController.php                               │
│                                                                  │
│  2. Authenticate User                                           │
│     public function login(Request $request) {                   │
│         // Validate credentials                                 │
│         // Generate JWT token                                   │
│         return response()->json(['token' => $token]);           │
│     }                                                           │
│     File: GestureTalk-Backend/app/Http/Controllers/             │
│           AuthController.php                                    │
│                                                                  │
│  3. Database Query                                              │
│     • Query users table                                         │
│     • Verify password hash                                      │
│     • Create JWT token                                          │
│     Database: MySQL                                             │
└─────────────────────────────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────────────────────────────┐
│ FLUTTER APP - Secure Storage                                    │
│                                                                  │
│  4. Store JWT Token                                             │
│     • flutter_secure_storage saves token                        │
│     • Token included in all future API requests                 │
│     • Header: Authorization: Bearer {token}                     │
└─────────────────────────────────────────────────────────────────┘
      ↓
USER AUTHENTICATED - Can now access all features
      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SAVING TRANSLATION TO DATABASE                                  │
│                                                                  │
│  5. After Translation Complete                                  │
│     • Flutter app calls Laravel API                             │
│     • POST /api/translations                                    │
│     • Body: {                                                   │
│         "input_type": "live" or "image" or "video",             │
│         "input_data": file or video_path,                       │
│         "translated_text": "HELLO WORLD"                        │
│       }                                                         │
│     File: lib/screens/live_translation_screen.dart (Lines 533-577)
└─────────────────────────────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────────────────────────────┐
│ LARAVEL API - TranslationController.php                        │
│                                                                  │
│  6. Save to Database                                            │
│     public function store(Request $request) {                   │
│         Translation::create([                                   │
│             'user_id' => auth()->id(),                          │
│             'input_type' => $request->input_type,               │
│             'translated_text' => $request->translated_text      │
│         ]);                                                     │
│     }                                                           │
│     File: GestureTalk-Backend/app/Http/Controllers/             │
│           TranslationController.php                             │
│                                                                  │
│  7. Database Insert                                             │
│     • Insert into translations table                            │
│     • Store user_id, timestamp, translation                     │
│     • Return success response                                   │
│     Database: MySQL - translations table                        │
└─────────────────────────────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────────────────────────────┐
│ FLUTTER APP - history_screen.dart                              │
│                                                                  │
│  8. View Translation History                                    │
│     • GET /api/translations                                     │
│     • Display list of past translations                         │
│     • Filter by date, type, etc.                                │
│     File: lib/screens/history_screen.dart                       │
└─────────────────────────────────────────────────────────────────┘

FLOW SUMMARY:
Login → Get JWT → Use Token → Translate → Save to DB → View History
```

---

## 🐍 Backend - Python ML Services

### **Service 1: WebSocket Server (Real-Time)**

**File:** `websocket_final_classifier.py`  
**Port:** 8002  
**Purpose:** Real-time sign language detection for live camera feed

#### **Key Components:**

```python
# 1. WebSocket Server Setup (Lines 748-757)
async def main():
    async with websockets.serve(handle_connection, "0.0.0.0", 8002):
        await asyncio.Future()

# 2. Connection Handler (Lines 425-745)
async def handle_connection(websocket, path=None):
    # Per-connection state
    letter_history = deque(maxlen=SMOOTH_FRAMES)
    word_history = deque(maxlen=SMOOTH_FRAMES)
    # ... process frames continuously

# 3. MediaPipe Hands Configuration (Lines 327-332)
hands = mp_hands.Hands(
    static_image_mode=False,
    min_detection_confidence=0.6,  # 60%
    min_tracking_confidence=0.5,   # 50%
    max_num_hands=2
)

# 4. Hand Validation (Lines 360-492)
def validate_hand_shape(landmarks):  # Lines 360-418
    # Check finger proportions, spread, structure
    
def validate_two_hands(results):     # Lines 421-456
    # Validate 2-hand detection
    
def validate_one_hand(results):      # Lines 459-492
    # Validate 1-hand detection

# 5. Model Loading (Lines 178-279)
# Letter model: mlp_model.p (sklearn MLP)
# Word model: transformer_mlp_word_model.pth (Temporal Transformer)
```

#### **Models Used:**

| Model | File | Type | Purpose | Lines |
|-------|------|------|---------|-------|
| Letter Model | `mlp_model.p` | sklearn MLP | A-Z detection (1 hand) | 178-189 |
| Word Model | `transformer_mlp_word_model.pth` | Temporal Transformer | Word detection (2 hands) | 191-279 |
| Preprocessing | `preprocessing_word.pkl` | Scaler + Encoder | Feature normalization | 208-213 |

#### **Configuration Parameters:**

```python
# Smoothing & Consistency (Lines 282-288)
SMOOTH_FRAMES = 20                   # 20-frame smoothing window
CONSISTENCY_THRESHOLD = 12           # 12/20 frames required (60%)
MIN_CONFIDENCE_LETTER = 0.25         # 25% minimum for letters
MIN_CONFIDENCE_WORD = 0.25           # 25% minimum for words
MIN_CONFIDENCE_DISPLAY = 0.10        # 10% minimum to display

# Prediction Locking (Lines 297-306)
PREDICTION_LOCK_DURATION = 100       # Lock for 100 frames
UNLOCK_CONFIDENCE_DROP = 0.15        # 15% drop triggers unlock
UNLOCK_CONFIDENCE_GAP = 0.12         # 12% gap triggers unlock

# Hand Detection (Lines 329-343)
MIN_DETECTION_CONFIDENCE = 0.6       # MediaPipe: 60%
MIN_TRACKING_CONFIDENCE = 0.5        # MediaPipe: 50%
MIN_HAND_SIZE_LETTER = 0.05          # 5% of frame
MIN_HAND_SIZE_WORD = 0.05            # 5% of frame
MIN_HANDEDNESS_CONFIDENCE = 0.7      # 70% confidence
```

---

### **Service 2: FastAPI REST Server (Batch Processing)**

**File:** `uploaded_files_classifier.py`  
**Port:** 8001  
**Purpose:** Process uploaded images and videos

#### **API Endpoints:**

```python
# 1. Health Check (Lines 483-491)
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "letter_model": letter_model is not None,
        "word_model": word_model is not None,
        "device": str(DEVICE)
    }

# 2. Image Prediction (Lines 406-423)
@app.post("/predict_image")
async def predict_image(file: UploadFile = File(...)):
    image = np.frombuffer(await file.read(), np.uint8)
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    result = process_frame(image, ...)
    return {
        "type": result["type"],
        "translation": result["prediction"],
        "confidence": result["confidence"]
    }

# 3. Video Prediction (Lines 426-480)
@app.post("/predict_video")
async def predict_video(file: UploadFile = File(...)):
    # Save temp file
    # Process frame-by-frame
    # Build translation string
    return {
        "translation": translation.strip(),
        "details": predictions
    }
```

#### **Same Models & Configuration:**
- Uses same `mlp_model.p` and `transformer_mlp_word_model.pth`
- Same validation and processing logic
- Different interface (HTTP POST instead of WebSocket)

---

### **Machine Learning Models**

#### **Model 1: Letter Classifier (MLP)**

**File:** `mlp_model.p`  
**Type:** scikit-learn Multi-Layer Perceptron  
**Architecture:**
```
Input Layer:     42 features (1 hand × 21 landmarks × 2 coords)
Hidden Layers:   Multiple fully-connected layers with ReLU
Output Layer:    26 neurons (softmax) → A-Z probabilities
```

**Training Data:**
- Dataset location: `data/` directory (organized by letter 0-25)
- Thousands of hand sign images per letter
- Normalized landmark features

**Performance:**
- Accuracy: ~95%+
- Inference time: ~1-2ms
- Model size: ~1MB

**Code References:**
- Loading: `final_classifier.py` Lines 178-189
- Usage: Lines 1095-1260 (letter detection logic)

---

#### **Model 2: Word Classifier (Temporal Transformer)**

**File:** `transformer_mlp_word_model.pth`  
**Type:** PyTorch Temporal Transformer  
**Architecture:**
```
Class: TemporalTransformer (Lines 67-117 in final_classifier.py)

Input:  30 frames × 84 features (temporal sequence)
   ↓
Spatial Encoder (MLP):
   • Linear(84 → 256)
   • LayerNorm + GELU + Dropout
   ↓
Positional Encoding:
   • Add learnable position embeddings
   ↓
Temporal Transformer Encoder (6 layers):
   • Multi-head attention (8 heads)
   • Feedforward MLP (256 → 1024 → 256)
   • Layer normalization + residual connections
   ↓
Mean Pooling:
   • Aggregate across 30 frames
   ↓
Classifier Head (3-layer MLP):
   • Linear(256 → 512)
   • Linear(512 → 256)
   • Linear(256 → 300)
   ↓
Output: 300 word probabilities
```

**Training Data:**
- Dataset location: `wordset/` directory
- Video sequences of ASL words
- WLASL dataset (metadata in `WLASL_v0.3.json`)

**Performance:**
- Accuracy: ~77%+
- Inference time: ~50-100ms (after 30 frames collected)
- Model size: ~20MB

**Code References:**
- Architecture: `final_classifier.py` Lines 67-117
- Loading: Lines 221-232
- Usage: Lines 734-1033 (word detection logic)

---

## 🔴 Backend - Laravel API

### **Purpose:**
User management, authentication, data persistence, and business logic

### **Framework:** Laravel 10 (PHP)  
**Port:** 8000  
**Database:** MySQL

---

### **Controllers**

#### **1. AuthController.php**
**Location:** `GestureTalk-Backend/app/Http/Controllers/AuthController.php`

```php
<?php

class AuthController extends Controller
{
    // User Registration
    public function register(Request $request) {
        // Validate input
        // Hash password
        // Create user in database
        // Return success response
    }
    
    // User Login
    public function login(Request $request) {
        // Validate credentials
        // Verify password
        // Generate JWT token
        // Return token to client
    }
    
    // User Logout
    public function logout(Request $request) {
        // Invalidate JWT token
        // Clear session
        // Return success response
    }
}
```

**Key Features:**
- JWT (JSON Web Token) authentication
- Password hashing with bcrypt
- Input validation
- Token expiration handling

---

#### **2. TranslationController.php**
**Location:** `GestureTalk-Backend/app/Http/Controllers/TranslationController.php`

```php
<?php

class TranslationController extends Controller
{
    // Get all translations for authenticated user
    public function index(Request $request) {
        $translations = Translation::where('user_id', auth()->id())
                                   ->orderBy('created_at', 'desc')
                                   ->get();
        return response()->json($translations);
    }
    
    // Save new translation
    public function store(Request $request) {
        // Validate input
        // Save translation to database
        // Save media file if uploaded
        // Return created translation
    }
    
    // Get specific translation
    public function show($id) {
        // Find translation by ID
        // Verify user owns translation
        // Return translation details
    }
    
    // Update translation
    public function update(Request $request, $id) {
        // Find translation
        // Update fields
        // Save changes
        // Return updated translation
    }
    
    // Delete translation
    public function destroy($id) {
        // Find translation
        // Delete associated files
        // Delete database record
        // Return success response
    }
}
```

---

#### **3. SpeechController.php**
**Location:** `GestureTalk-Backend/app/Http/Controllers/SpeechController.php`

```php
<?php

class SpeechController extends Controller
{
    // Synthesize text to speech
    public function synthesize(Request $request) {
        // Get text from request
        // Call ElevenLabs API
        // Return audio file or URL
    }
}
```

---

#### **4. UserController.php**
**Location:** `GestureTalk-Backend/app/Http/Controllers/UserController.php`

```php
<?php

class UserController extends Controller
{
    // Get user profile
    public function profile() {
        $user = auth()->user();
        return response()->json($user);
    }
    
    // Update user profile
    public function updateProfile(Request $request) {
        // Validate input
        // Update user fields
        // Save changes
        // Return updated user
    }
}
```

---

### **Models (Database)**

#### **1. User Model**
**Location:** `GestureTalk-Backend/app/Models/User.php`

```php
<?php

class User extends Authenticatable
{
    protected $fillable = [
        'name',
        'email',
        'password',
    ];
    
    protected $hidden = [
        'password',
        'remember_token',
    ];
    
    // Relationships
    public function translations() {
        return $this->hasMany(Translation::class);
    }
}
```

**Database Table:** `users`
```sql
CREATE TABLE users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

#### **2. Translation Model**
**Location:** `GestureTalk-Backend/app/Models/Translation.php`

```php
<?php

class Translation extends Model
{
    protected $fillable = [
        'user_id',
        'input_type',
        'input_data',
        'translated_text',
    ];
    
    // Relationships
    public function user() {
        return $this->belongsTo(User::class);
    }
}
```

**Database Table:** `translations`
```sql
CREATE TABLE translations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    input_type ENUM('live', 'image', 'video') NOT NULL,
    input_data TEXT,
    translated_text TEXT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

### **API Routes**

**File:** `GestureTalk-Backend/routes/api.php`

```php
<?php

use Illuminate\Support\Facades\Route;

// Authentication routes
Route::post('/register', [AuthController::class, 'register']);
Route::post('/login', [AuthController::class, 'login']);

// Protected routes (require JWT token)
Route::middleware('auth:api')->group(function () {
    Route::post('/logout', [AuthController::class, 'logout']);
    
    // Translation management
    Route::apiResource('translations', TranslationController::class);
    
    // User profile
    Route::get('/user/profile', [UserController::class, 'profile']);
    Route::put('/user/profile', [UserController::class, 'updateProfile']);
    
    // Text-to-speech
    Route::post('/speech/synthesize', [SpeechController::class, 'synthesize']);
});
```

---

## 📱 Frontend - Flutter Mobile App

### **Main Application File**

**File:** `GestureTalk-Front/lib/main.dart`

```dart
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load();  // Load environment variables
  
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'GestureTalk',
      theme: AppTheme.lightTheme,  // Custom theme
      initialRoute: '/login',
      routes: {
        '/login': (context) => LoginScreen(),
        '/signup': (context) => SignUpScreen(),
        '/home': (context) => LiveTranslationScreen(),
        '/media': (context) => MediaTranslationScreen(),
        '/history': (context) => HistoryScreen(),
        '/profile': (context) => ProfileScreen(),
        '/statistics': (context) => StatisticsScreen(),
      },
    );
  }
}
```

---

### **Key Screens**

#### **1. Live Translation Screen**
**File:** `lib/screens/live_translation_screen.dart`

**Features:**
- Real-time camera capture
- WebSocket connection to ML backend
- Continuous frame streaming
- Display predictions with confidence
- Text-to-speech integration
- Save translation option

**Key Code Sections:**
```dart
// Camera initialization (Lines 60-76)
void _initializeCamera() async {
  cameras = await availableCameras();
  _controller = CameraController(
    cameras[0],
    ResolutionPreset.medium,
  );
  await _controller.initialize();
}

// WebSocket connection (Lines 78-156)
void _connectToWebSocket() {
  final wsUrl = dotenv.env['WEBSOCKET_URL'] ?? 'ws://10.0.2.2:8002';
  final webSocketChannel = WebSocketChannel.connect(Uri.parse(wsUrl));
  
  webSocketChannel.stream.listen((event) {
    final data = jsonDecode(event.toString());
    final prediction = data['prediction'];
    final confidence = data['confidence'];
    
    setState(() {
      _translation += prediction;
    });
    
    _sendTextToElevenLabs(prediction);
  });
}

// Frame capture and send (Lines 200-250)
void _captureAndSendFrame() async {
  if (!_isTranslating) return;
  
  final image = await _controller.takePicture();
  final bytes = await image.readAsBytes();
  
  _webSocketChannel.sink.add(bytes);
  
  // Repeat every 100ms
  Future.delayed(Duration(milliseconds: 100), _captureAndSendFrame);
}

// Text-to-speech (Lines 158-195)
Future<void> _sendTextToElevenLabs(String text) async {
  final apiKey = dotenv.env['ELEVENLABS_API_KEY'];
  final response = await http.post(
    Uri.parse('https://api.elevenlabs.io/v1/text-to-speech/...'),
    headers: {'xi-api-key': apiKey},
    body: jsonEncode({'text': text}),
  );
  
  final audioBytes = response.bodyBytes;
  await _audioPlayer.play(BytesSource(audioBytes));
}
```

---

#### **2. Media Translation Screen**
**File:** `lib/screens/media_translation_screen.dart`

**Features:**
- Image/video file picker
- HTTP multipart upload to ML backend
- Display translation results
- Save to history

**Key Code Sections:**
```dart
// File picker (Lines 120-150)
Future<void> _pickMedia(String type) async {
  final ImagePicker picker = ImagePicker();
  
  if (type == 'image') {
    final XFile? image = await picker.pickImage(source: ImageSource.gallery);
    setState(() => _mediaFile = image);
  } else if (type == 'video') {
    final XFile? video = await picker.pickVideo(source: ImageSource.gallery);
    setState(() => _mediaFile = video);
  }
}

// Upload and translate (Lines 189-257)
Future<void> _translateMedia() async {
  final classifierUrl = dotenv.env['CLASSIFIER_URL'] ?? 'http://10.0.2.2:8001';
  final uri = Uri.parse(
    _mediaFile!.path.endsWith('.mp4') 
      ? '$classifierUrl/predict_video'
      : '$classifierUrl/predict_image'
  );
  
  final request = http.MultipartRequest('POST', uri);
  request.files.add(await http.MultipartFile.fromPath('file', _mediaFile!.path));
  
  final response = await request.send();
  final responseData = await response.stream.bytesToString();
  final decodedResponse = jsonDecode(responseData);
  
  setState(() {
    _translatedText = decodedResponse['translation'];
  });
}
```

---

#### **3. History Screen**
**File:** `lib/screens/history_screen.dart`

**Features:**
- Display list of past translations
- Fetch from Laravel API
- Filter and search
- View details
- Delete translations

```dart
// Fetch history (Lines 40-70)
Future<void> _fetchHistory() async {
  final baseUrl = dotenv.env['BASE_URL'];
  final jwtToken = await _storage.read(key: 'jwt_token');
  
  final response = await http.get(
    Uri.parse('$baseUrl/api/translations'),
    headers: {'Authorization': 'Bearer $jwtToken'},
  );
  
  if (response.statusCode == 200) {
    final data = jsonDecode(response.body) as List;
    setState(() {
      _translations = data.map((e) => Translation.fromJson(e)).toList();
    });
  }
}

// Display list (Lines 100-200)
ListView.builder(
  itemCount: _translations.length,
  itemBuilder: (context, index) {
    final translation = _translations[index];
    return ListTile(
      title: Text(translation.translatedText),
      subtitle: Text(translation.createdAt),
      trailing: IconButton(
        icon: Icon(Icons.delete),
        onPressed: () => _deleteTranslation(translation.id),
      ),
    );
  },
)
```

---

#### **4. Login Screen**
**File:** `lib/screens/login_screen.dart`

**Features:**
- Email/password form
- JWT authentication
- Secure token storage
- Navigation to home

```dart
// Login function (Lines 50-100)
Future<void> _login() async {
  final baseUrl = dotenv.env['BASE_URL'];
  
  final response = await http.post(
    Uri.parse('$baseUrl/api/login'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({
      'email': _emailController.text,
      'password': _passwordController.text,
    }),
  );
  
  if (response.statusCode == 200) {
    final data = jsonDecode(response.body);
    final token = data['token'];
    
    // Store token securely
    await _storage.write(key: 'jwt_token', value: token);
    
    // Navigate to home
    Navigator.pushReplacementNamed(context, '/home');
  } else {
    _showError('Invalid credentials');
  }
}
```

---

#### **5. Voice-to-Sign Screen**
**File:** `lib/screens/voice_to_sign_screen.dart`

**Features:**
- Speech-to-text recognition (using speech_to_text package)
- Real-time transcription display
- Visual sign language display (words and fingerspelling)
- Text-to-speech playback
- Save translations

**Key Code Sections:**
```dart
// Initialize speech recognition (Lines 50-70)
void _initSpeech() async {
  _speechEnabled = await _speechToText.initialize(
    onStatus: (status) => print('Speech status: $status'),
    onError: (error) => print('Speech error: $error'),
  );
  setState(() {});
}

// Start listening (Lines 100-130)
Future<void> _startListening() async {
  setState(() {
    _isListening = true;
    _recognizedText = '';
  });

  await _speechToText.listen(
    onResult: (result) {
      setState(() {
        _recognizedText = result.recognizedWords;
      });
    },
    listenMode: ListenMode.confirmation,
    cancelOnError: true,
    partialResults: true,
  );
}

// Stop listening (Lines 132-145)
Future<void> _stopListening() async {
  await _speechToText.stop();
  setState(() {
    _isListening = false;
  });
  
  // Generate audio for recognized text
  if (_recognizedText.isNotEmpty) {
    await _generateAudio(_recognizedText);
  }
}

// Generate audio via Laravel API (Lines 168-231)
Future<void> _generateAudio(String text) async {
  final uri = Uri.parse('$baseUrl/api/speech');
  
  final response = await http.post(
    uri,
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({'text': text}),
  );

  if (response.statusCode == 200) {
    final audioBytes = response.bodyBytes;
    final tempDir = await getTemporaryDirectory();
    final audioPath = '${tempDir.path}/speech_${DateTime.now().millisecondsSinceEpoch}.mp3';
    
    final file = File(audioPath);
    await file.writeAsBytes(audioBytes);
    
    await _audioPlayer.play(DeviceFileSource(audioPath));
  }
}
```

**Visual Display Integration:**
```dart
// Display sign language visualization (Lines 250-270)
if (_recognizedText.isNotEmpty)
  SignLanguageVisualDisplay(
    text: _recognizedText,
    baseUrl: baseUrl,
  ),
```

---

### **Widgets**

#### **Sign Language Visual Display Widget**
**File:** `lib/widgets/sign_language_display.dart`

**Purpose:** Displays visual representations of sign language for spoken words

**Features:**
- Word-level sign language display (for known words)
- Letter-level fingerspelling (for unknown words or letters)
- Smooth card-based UI with animations
- Placeholder support for missing assets
- Responsive grid layout

**Key Implementation:**
```dart
class SignLanguageVisualDisplay extends StatefulWidget {
  final String text;
  final String? baseUrl;

  const SignLanguageVisualDisplay({
    super.key,
    required this.text,
    this.baseUrl,
  });
}

class _SignLanguageVisualDisplayState extends State<SignLanguageVisualDisplay> {
  // Known words vocabulary (from WLASL dataset)
  final List<String> _knownWords = [
    'hello', 'thanks', 'please', 'sorry', 'yes', 'no', // ... 2000+ words
  ];

  @override
  Widget build(BuildContext context) {
    final words = widget.text.toLowerCase().split(' ');
    
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: words.map((word) {
        // Check if word is in vocabulary
        if (_knownWords.contains(word)) {
          return _buildWordCard(word);
        } else {
          // Spell out unknown words letter by letter
          return _buildLettersForWord(word);
        }
      }).toList(),
    );
  }

  // Display single word sign
  Widget _buildWordCard(String word) {
    return Container(
      width: 120,
      height: 140,
      decoration: AppTheme.glassCard,
      child: Column(
        children: [
          Expanded(
            child: Image.asset(
              'assets/signs/words/${word.toLowerCase()}.png',
              fit: BoxFit.contain,
              errorBuilder: (context, error, stackTrace) {
                return Icon(Icons.sign_language, size: 48);
              },
            ),
          ),
          Text(
            word.toUpperCase(),
            style: GoogleFonts.poppins(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: AppTheme.textPrimary,
            ),
          ),
        ],
      ),
    );
  }

  // Display fingerspelling for unknown words
  Widget _buildLettersForWord(String word) {
    return Wrap(
      spacing: 8,
      children: word.split('').map((letter) {
        return _buildLetterCard(letter);
      }).toList(),
    );
  }

  Widget _buildLetterCard(String letter) {
    return Container(
      width: 80,
      height: 100,
      decoration: AppTheme.glassCard,
      child: Column(
        children: [
          Expanded(
            child: Image.asset(
              'assets/signs/letters/${letter.toUpperCase()}.png',
              fit: BoxFit.contain,
              errorBuilder: (context, error, stackTrace) {
                return Icon(Icons.abc, size: 32);
              },
            ),
          ),
          Text(
            letter.toUpperCase(),
            style: GoogleFonts.poppins(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: AppTheme.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}
```

**Asset Structure:**
```
assets/
  signs/
    words/
      hello.png
      thanks.png
      please.png
      ... (2000+ word signs)
    letters/
      A.png
      B.png
      C.png
      ... (26 letter signs)
```

---

### **Services Layer**

#### **1. Offline Storage Service**
**File:** `lib/services/offline_storage_service.dart`

```dart
class OfflineStorageService {
  static final Database _database;
  
  // Initialize SQLite database
  static Future<void> init() async {
    _database = await openDatabase(
      'gesturetalk.db',
      version: 1,
      onCreate: (db, version) {
        return db.execute(
          'CREATE TABLE translations('
          'id INTEGER PRIMARY KEY,'
          'translated_text TEXT,'
          'input_type TEXT,'
          'created_at TEXT,'
          'synced INTEGER DEFAULT 0'
          ')'
        );
      },
    );
  }
  
  // Save translation offline
  static Future<void> saveTranslation(Translation translation) async {
    await _database.insert('translations', translation.toMap());
  }
  
  // Get unsynced translations
  static Future<List<Translation>> getUnsyncedTranslations() async {
    final maps = await _database.query(
      'translations',
      where: 'synced = ?',
      whereArgs: [0],
    );
    return maps.map((e) => Translation.fromMap(e)).toList();
  }
}
```

---

#### **2. Connectivity Service**
**File:** `lib/services/connectivity_service.dart`

```dart
class ConnectivityService {
  static final Connectivity _connectivity = Connectivity();
  
  // Check if online
  static Future<bool> isOnline() async {
    final result = await _connectivity.checkConnectivity();
    return result != ConnectivityResult.none;
  }
  
  // Listen to connectivity changes
  static Stream<bool> onConnectivityChanged() {
    return _connectivity.onConnectivityChanged.map((result) {
      return result != ConnectivityResult.none;
    });
  }
}
```

---

#### **3. Sync Service**
**File:** `lib/services/sync_service.dart`

```dart
class SyncService {
  // Sync offline translations to server
  static Future<void> syncTranslations() async {
    final isOnline = await ConnectivityService.isOnline();
    if (!isOnline) return;
    
    final unsyncedTranslations = await OfflineStorageService.getUnsyncedTranslations();
    
    for (final translation in unsyncedTranslations) {
      final response = await http.post(
        Uri.parse('$baseUrl/api/translations'),
        headers: {'Authorization': 'Bearer $token'},
        body: jsonEncode(translation.toJson()),
      );
      
      if (response.statusCode == 201) {
        await OfflineStorageService.markAsSynced(translation.id);
      }
    }
  }
}
```

---

### **UI Theme**

**File:** `lib/theme/app_theme.dart`

```dart
class AppTheme {
  static const Color primary = Color(0xFF6200EE);
  static const Color secondary = Color(0xFF03DAC6);
  static const Color background = Color(0xFF121212);
  static const Color surface = Color(0xFF1E1E1E);
  static const Color error = Color(0xFFCF6679);
  
  static ThemeData get lightTheme {
    return ThemeData(
      primaryColor: primary,
      scaffoldBackgroundColor: background,
      colorScheme: ColorScheme.dark(
        primary: primary,
        secondary: secondary,
        surface: surface,
        error: error,
      ),
      textTheme: GoogleFonts.robotoTextTheme(),
    );
  }
}
```

---

## 🎤 Voice-to-Sign Translation

### **Overview**

The Voice-to-Sign Translation feature enables **bidirectional communication** by converting spoken language into visual sign language representations. This allows hearing users to communicate with deaf users by speaking, and the app displays the appropriate sign language.

### **Architecture Flow**

```
┌─────────────────────────────────────────────────────────────┐
│             VOICE-TO-SIGN TRANSLATION FLOW                   │
└─────────────────────────────────────────────────────────────┘

User Speaks
    │
    ▼
┌─────────────────────────────┐
│  Flutter App                │
│  speech_to_text package     │
│  • Microphone access        │
│  • Real-time STT            │
│  • Partial results          │
└─────────────┬───────────────┘
              │
              │ Recognized Text: "Hello my name is Yara"
              ▼
┌─────────────────────────────┐
│  Text Processing            │
│  • Normalize text           │
│  • Split into words         │
│  • Match vocabulary         │
└─────────────┬───────────────┘
              │
              ├──────────────┬──────────────┐
              ▼              ▼              ▼
         Known Word    Known Word    Unknown Word
         "HELLO"       "NAME"        "YARA"
              │              │              │
              ▼              ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ Word Card    │ │ Word Card    │ │ Fingerspell  │
    │ (Single img) │ │ (Single img) │ │ Y-A-R-A      │
    └──────────────┘ └──────────────┘ └──────────────┘
              │              │              │
              └──────────────┴──────────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │  Visual Display             │
              │  SignLanguageVisualDisplay  │
              │  • Card-based UI            │
              │  • Smooth animations        │
              └─────────────────────────────┘
                             │
                             │ (Optional)
                             ▼
              ┌─────────────────────────────┐
              │  Text-to-Speech Playback    │
              │  POST /api/speech           │
              │  • ElevenLabs TTS           │
              │  • Natural voice            │
              └─────────────────────────────┘
```

### **Key Components**

#### **1. Speech Recognition (speech_to_text)**

```dart
// Package: speech_to_text: ^6.1.1

final SpeechToText _speechToText = SpeechToText();
bool _speechEnabled = false;

// Initialize
void _initSpeech() async {
  _speechEnabled = await _speechToText.initialize(
    onStatus: (status) => print('Status: $status'),
    onError: (error) => print('Error: $error'),
  );
}

// Start listening
await _speechToText.listen(
  onResult: (result) {
    setState(() {
      _recognizedText = result.recognizedWords;
    });
  },
  listenMode: ListenMode.confirmation, // Or ListenMode.dictation
  partialResults: true,                // Show text as it's recognized
  cancelOnError: true,
);

// Stop listening
await _speechToText.stop();
```

**Features:**
- ✅ Real-time transcription
- ✅ Partial results (see text as you speak)
- ✅ Multiple languages support
- ✅ Noise cancellation
- ✅ Confidence scores

#### **2. Text Processing & Vocabulary Matching**

```dart
final List<String> _knownWords = [
  'hello', 'thanks', 'please', 'sorry', 'yes', 'no', 'good', 'help',
  'water', 'world', 'you', 'me', 'we', 'love', 'friend', 'family',
  // ... ~2000+ words from WLASL dataset
];

List<Widget> _processTextToCards(String text) {
  final words = text.toLowerCase().split(' ');
  List<Widget> cards = [];
  
  for (var word in words) {
    if (_knownWords.contains(word)) {
      // Display as single word card
      cards.add(_buildWordCard(word));
    } else {
      // Display as fingerspelling
      for (var letter in word.split('')) {
        cards.add(_buildLetterCard(letter));
      }
    }
  }
  
  return cards;
}
```

**Vocabulary Sources:**
- **WLASL (Word-Level American Sign Language)**: 2,000+ common words
- **ASL Fingerspelling**: 26 letters + 10 numbers
- **Common phrases**: Greetings, questions, responses

#### **3. Visual Display System**

The visual display renders sign language using:

**A. Word Cards (for known vocabulary):**
```dart
Container(
  width: 120,
  height: 140,
  decoration: BoxDecoration(
    gradient: LinearGradient(...),
    borderRadius: BorderRadius.circular(16),
    boxShadow: [BoxShadow(...)],
  ),
  child: Column(
    children: [
      // Sign language image
      Image.asset('assets/signs/words/${word}.png'),
      // Word label
      Text(word.toUpperCase()),
    ],
  ),
)
```

**B. Fingerspelling Cards (for unknown words/names):**
```dart
Container(
  width: 80,
  height: 100,
  child: Column(
    children: [
      // Letter sign image
      Image.asset('assets/signs/letters/${letter}.png'),
      // Letter label
      Text(letter.toUpperCase()),
    ],
  ),
)
```

### **Implementation Details**

#### **Screen: voice_to_sign_screen.dart**

**Line Count:** ~650 lines

**State Management:**
```dart
class _VoiceToSignScreenState extends State<VoiceToSignScreen> {
  final SpeechToText _speechToText = SpeechToText();
  final AudioPlayer _audioPlayer = AudioPlayer();
  
  bool _isListening = false;
  bool _speechEnabled = false;
  String _recognizedText = '';
  
  @override
  void initState() {
    super.initState();
    _initSpeech();
  }
}
```

**User Interface:**
- **Header**: Title and description
- **Microphone Button**: Large animated button (glowing when active)
- **Status Indicator**: "Listening..." / "Tap to speak"
- **Transcription Card**: Shows recognized text in real-time
- **Visual Display**: Grid of sign language cards
- **Action Buttons**: Clear, Save, Play Audio

**Animations:**
- Pulse effect on microphone button when listening
- Fade-in for recognized text
- Slide-in animation for sign cards
- Ripple effect on button press

### **User Flow**

1. User navigates to **Voice-to-Sign** screen
2. Taps **microphone button** to start
3. Speaks: "Hello my name is Yara"
4. Real-time transcription appears
5. Visual display shows:
   - HELLO (word card)
   - MY (word card)
   - NAME (word card)
   - IS (word card)
   - Y-A-R-A (fingerspelling)
6. User can:
   - **Play audio** of the text (TTS)
   - **Save** translation to history
   - **Clear** and start over

### **Asset Management**

**Directory Structure:**
```
GestureTalk-Front/
  assets/
    signs/
      words/
        hello.png
        thanks.png
        please.png
        sorry.png
        ... (2000+ words)
      letters/
        A.png
        B.png
        C.png
        ...
        Z.png
```

**Asset Declaration (pubspec.yaml):**
```yaml
flutter:
  assets:
    - assets/signs/words/
    - assets/signs/letters/
```

**Image Requirements:**
- Format: PNG with transparency
- Size: 512x512px recommended
- Background: Transparent
- Content: Clear hand sign demonstration
- Naming: Lowercase for words, uppercase for letters

### **Performance Considerations**

**Speech Recognition:**
- Uses device's native STT engine
- Works offline (if device supports)
- Low latency (~50-100ms)

**Asset Loading:**
- Images loaded on-demand
- Cached after first load
- Placeholder shown during load

**Memory Management:**
- Only visible cards loaded
- Images released when off-screen
- Lazy loading for large lists

### **Error Handling**

```dart
// Speech not available
if (!_speechEnabled) {
  showDialog(
    context: context,
    builder: (context) => AlertDialog(
      title: Text('Speech Recognition Unavailable'),
      content: Text('Please check microphone permissions'),
    ),
  );
}

// Asset not found
errorBuilder: (context, error, stackTrace) {
  return Icon(
    Icons.sign_language,
    size: 48,
    color: AppTheme.textSecondary,
  );
}

// Network error (for TTS)
try {
  await _generateAudio(text);
} catch (e) {
  _showSnackBar('Audio generation failed', isError: true);
}
```

### **Future Enhancements**

- [ ] Video-based sign language (animated GIFs/videos)
- [ ] Multi-language support (ASL, BSL, LSF, etc.)
- [ ] Custom vocabulary upload
- [ ] Phrase suggestions/auto-complete
- [ ] Sign language recording from camera
- [ ] Slow-motion playback for learning

---

## 📺 Visual Sign Language Display

### **Overview**

The Visual Sign Language Display system provides an intuitive, card-based interface for displaying sign language representations of spoken words and phrases.

### **Widget Architecture**

```
SignLanguageVisualDisplay (Stateful Widget)
    │
    ├── State: _SignLanguageVisualDisplayState
    │   │
    │   ├── _knownWords (List<String>) - 2000+ vocabulary
    │   │
    │   └── build() → Wrap Widget
    │       │
    │       ├── Split text into words
    │       │
    │       └── For each word:
    │           ├── If in vocabulary → _buildWordCard()
    │           └── If unknown → _buildLettersForWord()
    │               │
    │               └── For each letter → _buildLetterCard()
```

### **Implementation**

#### **File:** `lib/widgets/sign_language_display.dart`

**Widget Properties:**
```dart
class SignLanguageVisualDisplay extends StatefulWidget {
  final String text;           // Text to display as signs
  final String? baseUrl;       // Optional: for future video support
  
  const SignLanguageVisualDisplay({
    super.key,
    required this.text,
    this.baseUrl,
  });
}
```

### **Card Types**

#### **1. Word Card**

Displays a single sign for an entire word (e.g., "HELLO").

```dart
Widget _buildWordCard(String word) {
  return Container(
    width: 120,
    height: 140,
    decoration: AppTheme.glassCard, // Glass morphism effect
    child: Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // Sign image (80% of card)
        Expanded(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Image.asset(
              'assets/signs/words/${word.toLowerCase()}.png',
              fit: BoxFit.contain,
              errorBuilder: (context, error, stackTrace) {
                // Fallback icon if image not found
                return const Icon(
                  Icons.sign_language,
                  size: 48,
                  color: AppTheme.accentTeal,
                );
              },
            ),
          ),
        ),
        
        // Word label (20% of card)
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: AppTheme.primaryDark.withOpacity(0.3),
            borderRadius: const BorderRadius.only(
              bottomLeft: Radius.circular(16),
              bottomRight: Radius.circular(16),
            ),
          ),
          child: Text(
            word.toUpperCase(),
            textAlign: TextAlign.center,
            style: GoogleFonts.poppins(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: AppTheme.textPrimary,
            ),
          ),
        ),
      ],
    ),
  );
}
```

**Visual Example:**
```
┌──────────────────┐
│                  │
│                  │
│   [HELLO SIGN]   │
│                  │
│                  │
├──────────────────┤
│     HELLO        │
└──────────────────┘
```

#### **2. Letter Card (Fingerspelling)**

Displays individual letter signs for spelling out names or unknown words.

```dart
Widget _buildLetterCard(String letter) {
  return Container(
    width: 80,
    height: 100,
    decoration: AppTheme.glassCard,
    child: Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Expanded(
          child: Padding(
            padding: const EdgeInsets.all(8),
            child: Image.asset(
              'assets/signs/letters/${letter.toUpperCase()}.png',
              fit: BoxFit.contain,
              errorBuilder: (context, error, stackTrace) {
                return const Icon(
                  Icons.abc,
                  size: 32,
                  color: AppTheme.accentBlue,
                );
              },
            ),
          ),
        ),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 6),
          decoration: BoxDecoration(
            color: AppTheme.primaryDark.withOpacity(0.3),
            borderRadius: const BorderRadius.only(
              bottomLeft: Radius.circular(16),
              bottomRight: Radius.circular(16),
            ),
          ),
          child: Text(
            letter.toUpperCase(),
            textAlign: TextAlign.center,
            style: GoogleFonts.poppins(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: AppTheme.textSecondary,
            ),
          ),
        ),
      ],
    ),
  );
}
```

**Visual Example:**
```
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│      │ │      │ │      │ │      │
│ [Y]  │ │ [A]  │ │ [R]  │ │ [A]  │
│      │ │      │ │      │ │      │
├──────┤ ├──────┤ ├──────┤ ├──────┤
│  Y   │ │  A   │ │  R   │ │  A   │
└──────┘ └──────┘ └──────┘ └──────┘
```

### **Layout System**

#### **Wrap Widget**

Uses Flutter's `Wrap` widget for responsive, flowing layout:

```dart
Wrap(
  spacing: 12,              // Horizontal spacing
  runSpacing: 12,           // Vertical spacing
  alignment: WrapAlignment.center,
  children: _buildCards(widget.text),
)
```

**Advantages:**
- Automatically wraps to new line when needed
- Responsive on different screen sizes
- Smooth animations
- No overflow issues

### **Vocabulary Management**

#### **Known Words List**

Currently hardcoded ~2000+ common words from WLASL:

```dart
final List<String> _knownWords = [
  // Greetings & Basic
  'hello', 'goodbye', 'please', 'thanks', 'sorry', 'yes', 'no',
  
  // Questions
  'what', 'where', 'when', 'who', 'why', 'how',
  
  // Common Verbs
  'go', 'come', 'eat', 'drink', 'sleep', 'work', 'play', 'learn',
  
  // Family & People
  'mother', 'father', 'brother', 'sister', 'friend', 'family',
  
  // ... (2000+ more words)
];
```

#### **Future Enhancement: Dynamic Vocabulary**

```dart
// Load from JSON file
Future<void> _loadVocabulary() async {
  final jsonString = await rootBundle.loadString('assets/vocabulary.json');
  final List<dynamic> vocabList = jsonDecode(jsonString);
  setState(() {
    _knownWords = vocabList.map((e) => e.toString()).toList();
  });
}
```

### **Styling & Theme**

#### **Glass Morphism Effect**

```dart
static BoxDecoration glassCard = BoxDecoration(
  gradient: LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Colors.white.withOpacity(0.1),
      Colors.white.withOpacity(0.05),
    ],
  ),
  borderRadius: BorderRadius.circular(16),
  border: Border.all(
    color: Colors.white.withOpacity(0.2),
    width: 1.5,
  ),
  boxShadow: [
    BoxShadow(
      color: Colors.black.withOpacity(0.1),
      blurRadius: 10,
      offset: const Offset(0, 4),
    ),
  ],
);
```

### **Usage Examples**

#### **Example 1: Single Word**

Input: `"HELLO"`

Output:
```
┌──────────────────┐
│                  │
│   [HELLO SIGN]   │
│                  │
├──────────────────┤
│     HELLO        │
└──────────────────┘
```

#### **Example 2: Known Phrase**

Input: `"HELLO MY NAME"`

Output:
```
┌─────────┐  ┌─────────┐  ┌─────────┐
│ [HELLO] │  │  [MY]   │  │ [NAME]  │
├─────────┤  ├─────────┤  ├─────────┤
│  HELLO  │  │   MY    │  │  NAME   │
└─────────┘  └─────────┘  └─────────┘
```

#### **Example 3: Mixed (Known + Unknown)**

Input: `"HELLO YARA"`

Output:
```
┌─────────┐  ┌───┐ ┌───┐ ┌───┐ ┌───┐
│ [HELLO] │  │[Y]│ │[A]│ │[R]│ │[A]│
├─────────┤  ├───┤ ├───┤ ├───┤ ├───┤
│  HELLO  │  │ Y │ │ A │ │ R │ │ A │
└─────────┘  └───┘ └───┘ └───┘ └───┘
```

### **Integration Points**

The widget is used in two main places:

**1. Voice-to-Sign Screen:**
```dart
// In voice_to_sign_screen.dart
if (_recognizedText.isNotEmpty)
  SignLanguageVisualDisplay(
    text: _recognizedText,
    baseUrl: baseUrl,
  ),
```

**2. Future: Sign Learning Screen:**
```dart
// Potential use case
SignLanguageVisualDisplay(
  text: 'Learn these signs: Hello Thanks Please',
  baseUrl: baseUrl,
)
```

---

## 🔊 ElevenLabs TTS Integration

### **Overview**

ElevenLabs provides **natural, human-like text-to-speech** for all translation modes. Instead of robotic voices, users hear realistic speech with natural intonation and emotion.

### **Architecture**

```
┌─────────────────────────────────────────────────────────┐
│          ELEVENLABS TTS INTEGRATION FLOW                 │
└─────────────────────────────────────────────────────────┘

Any Translation Mode
(Live / Upload / Voice-to-Sign)
    │
    │ Text ready: "Hello World"
    ▼
┌─────────────────────────────┐
│  Flutter App                │
│  _sendTextToElevenLabs()    │
└─────────────┬───────────────┘
              │
              │ POST /api/speech
              │ { "text": "Hello World" }
              ▼
┌─────────────────────────────┐
│  Laravel API                │
│  SpeechController.php       │
│  • Validate text            │
│  • Get voice ID from config │
└─────────────┬───────────────┘
              │
              │ POST to ElevenLabs
              │ https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
              ▼
┌─────────────────────────────┐
│  ElevenLabs Cloud API       │
│  • Neural TTS generation    │
│  • Apply voice settings     │
│  • Generate MP3             │
└─────────────┬───────────────┘
              │
              │ MP3 Audio (binary)
              ▼
┌─────────────────────────────┐
│  Laravel API                │
│  • Return audio to client   │
└─────────────┬───────────────┘
              │
              │ Audio bytes
              ▼
┌─────────────────────────────┐
│  Flutter App                │
│  • AudioPlayer plays audio  │
└─────────────────────────────┘
              │
              ▼
          User hears speech
```

### **Backend Implementation**

#### **File:** `app/Http/Controllers/SpeechController.php`

```php
<?php
namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Log;

class SpeechController extends Controller
{
    public function generateSpeech(Request $request)
    {
        // Validate input
        $request->validate([
            'text' => 'required|string|max:5000',
        ]);

        $text = $request->input('text');
        
        // Get ElevenLabs config
        $voiceId = config('services.elevenLabs.voice_id');
        $apiKey = config('services.elevenLabs.api_key');
        $apiURL = "https://api.elevenlabs.io/v1/text-to-speech/{$voiceId}";

        try {
            // Make request to ElevenLabs
            $response = Http::withHeaders([
                'xi-api-key' => $apiKey,
                'Content-Type' => 'application/json',
                'Accept' => 'audio/mpeg',
            ])->post($apiURL, [
                'text' => $text,
                'model_id' => 'eleven_monolingual_v1',
                'voice_settings' => [
                    'stability' => 0.5,           // 0-1: More stable = consistent
                    'similarity_boost' => 0.75,   // 0-1: Higher = more like original
                    'style' => 0.5,               // 0-1: Style exaggeration
                    'use_speaker_boost' => true,  // Better clarity
                ],
            ]);

            if ($response->ok()) {
                // Return audio as response
                return response($response->body())
                    ->header('Content-Type', 'audio/mpeg')
                    ->header('Content-Disposition', 'inline; filename="speech.mp3"');
            } else {
                Log::error('ElevenLabs API error', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);
                return response()->json([
                    'error' => 'Failed to generate speech'
                ], $response->status());
            }
        } catch (\Exception $e) {
            Log::error('Exception in speech generation', [
                'message' => $e->getMessage(),
            ]);
            return response()->json([
                'error' => 'An error occurred while generating speech'
            ], 500);
        }
    }
}
```

#### **Configuration:** `config/services.php`

```php
'elevenLabs' => [
    'voice_id' => env('ELEVEN_LABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM'),
    'api_key' => env('ELEVEN_LABS_API_KEY'),
],
```

#### **Environment Variables:** `.env`

```env
ELEVEN_LABS_API_KEY=your_api_key_here
ELEVEN_LABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM  # Rachel (default)
```

#### **Route:** `routes/api.php`

```php
Route::post('/speech', [SpeechController::class, 'generateSpeech']);
```

### **Frontend Implementation**

#### **Used in All Translation Screens:**

**1. Live Translation Screen** (line ~158-212):
```dart
Future<void> _sendTextToElevenLabs(String text) async {
  if (text.trim().isEmpty) return;

  final uri = Uri.parse('$baseUrl/api/speech');
  
  try {
    final response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'text': text}),
    ).timeout(const Duration(seconds: 30));

    if (response.statusCode == 200) {
      final audioBytes = response.bodyBytes;
      await _playAudioChunk(audioBytes);
    }
  } catch (e) {
    print('Error generating speech: $e');
  }
}

Future<void> _playAudioChunk(Uint8List audioData) async {
  await _audioPlayer.play(BytesSource(audioData));
}
```

**2. Media Translation Screen** (line ~306-374):
```dart
Future<void> _sendTranslationForSpeech(String text) async {
  final uri = Uri.parse('$baseUrl/api/speech');
  
  final response = await http.post(
    uri,
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({'text': text}),
  );

  if (response.statusCode == 200) {
    final audioBytes = response.bodyBytes;
    final audioPath = await _saveAudioFile(audioBytes);
    await _audioPlayer.play(DeviceFileSource(audioPath));
  }
}
```

**3. Voice-to-Sign Screen** (line ~168-231):
```dart
Future<void> _generateAudio(String text) async {
  final uri = Uri.parse('$baseUrl/api/speech');
  
  final response = await http.post(
    uri,
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({'text': text}),
  );

  if (response.statusCode == 200) {
    final audioBytes = response.bodyBytes;
    final tempDir = await getTemporaryDirectory();
    final audioPath = '${tempDir.path}/speech_${DateTime.now().millisecondsSinceEpoch}.mp3';
    
    final file = File(audioPath);
    await file.writeAsBytes(audioBytes);
    
    await _audioPlayer.play(DeviceFileSource(audioPath));
  }
}
```

### **Voice Options**

ElevenLabs provides multiple high-quality voices:

| Voice Name | ID | Description |
|------------|---|-------------|
| Rachel (Default) | 21m00Tcm4TlvDq8ikWAM | American Female, Clear |
| Domi | AZnzlk1XvdvUeBnXmlld | American Female, Young |
| Bella | EXAVITQu4vr4xnSDxMaL | American Female, Soft |
| Antoni | ErXwobaYiN019PkySvjV | American Male, Well-rounded |
| Elli | MF3mGyEYCl7XYWbV9V6O | American Female, Emotional |
| Josh | TxGEqnHWrfWFTfGW9XjX | American Male, Deep |
| Arnold | VR6AewLTigWG4xSOukaG | American Male, Crisp |
| Adam | pNInz6obpgDQGcFmaJgB | American Male, Deep |
| Sam | yoZ06aMxZJJ28mfd3POQ | American Male, Raspy |

### **Voice Settings Explained**

```php
'voice_settings' => [
    'stability' => 0.5,           // 0 = varied, 1 = consistent
    'similarity_boost' => 0.75,   // 0 = varies, 1 = stays true to voice
    'style' => 0.5,               // 0 = neutral, 1 = expressive
    'use_speaker_boost' => true,  // Enhanced clarity
],
```

**Recommendations:**

- **More natural/expressive:** stability=0, style=1
- **More consistent/stable:** stability=1, style=0
- **Balanced (default):** stability=0.5, style=0.5

### **API Limits & Pricing**

#### **Free Tier:**
- 10,000 characters/month
- ~333 characters/day
- All voices available
- Good for development/testing

#### **Paid Plans:**
- **Starter:** $5/month - 30,000 chars
- **Creator:** $22/month - 100,000 chars
- **Pro:** $99/month - 500,000 chars
- **Scale:** $330/month - 2M chars
- **Business:** Custom pricing

#### **Character Counting:**
```
"Hello" = 5 characters
"Hello my name is Yara" = 22 characters
"I want to go to the store" = 27 characters
```

### **Performance Metrics**

- **Latency:** ~500-1500ms (depends on text length)
- **Audio Quality:** 128kbps MP3
- **Supported Text Length:** Up to 5,000 characters per request
- **Languages:** English (optimized for American accent)

### **Error Handling**

```dart
try {
  await _sendTextToElevenLabs(text);
} catch (e) {
  if (e.toString().contains('SocketException')) {
    _showSnackBar('No internet connection', isError: true);
  } else if (e.toString().contains('TimeoutException')) {
    _showSnackBar('Request timed out', isError: true);
  } else {
    _showSnackBar('Audio generation failed', isError: true);
  }
}
```

### **Optimization Tips**

#### **1. Caching**
Cache frequently used phrases:

```dart
final Map<String, String> _audioCache = {};

Future<void> _playWithCache(String text) async {
  if (_audioCache.containsKey(text)) {
    await _audioPlayer.play(DeviceFileSource(_audioCache[text]!));
  } else {
    final audioPath = await _generateAndSaveAudio(text);
    _audioCache[text] = audioPath;
    await _audioPlayer.play(DeviceFileSource(audioPath));
  }
}
```

#### **2. Batching**
Combine multiple words into one request instead of individual calls:

```dart
// Bad: 3 API calls
await _generateAudio('Hello');
await _generateAudio('my');
await _generateAudio('name');

// Good: 1 API call
await _generateAudio('Hello my name');
```

#### **3. Pre-generation**
Pre-generate audio for common phrases at app startup:

```dart
Future<void> _pregenerateCommonPhrases() async {
  final common = ['Hello', 'Thank you', 'Please', 'Sorry'];
  for (var phrase in common) {
    await _generateAndCacheAudio(phrase);
  }
}
```

### **Alternative TTS Options**

If ElevenLabs doesn't suit your needs:

| Service | Pros | Cons |
|---------|------|------|
| **ElevenLabs** | Best quality, natural | Requires API key, costs $ |
| **Google Cloud TTS** | Good quality, multi-language | Requires Google Cloud setup |
| **Amazon Polly** | AWS integration, neural voices | AWS complexity |
| **Azure Speech** | Enterprise-grade | Microsoft ecosystem |
| **flutter_tts** | Free, offline, easy | Robotic, lower quality |

### **Troubleshooting**

**Problem:** "No audio playing"
- Check API key in `.env`
- Verify Laravel server is running
- Check network connection
- View Laravel logs: `storage/logs/laravel.log`

**Problem:** "Quota exceeded"
- Check usage on ElevenLabs dashboard
- Consider upgrading plan
- Implement caching to reduce API calls

**Problem:** "Audio quality issues"
- Try different voice ID
- Adjust voice settings (stability, style)
- Check internet connection speed

---

## 🌐 Data Flow & Communication

### **Network Communication Summary**

```
┌──────────────────────────────────────────────────────────────────┐
│ COMMUNICATION PROTOCOLS                                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 1. WebSocket (Real-time ML)                                     │
│    Flutter ⟷ Python ML (Port 8002)                             │
│    • Bidirectional persistent connection                        │
│    • Low latency (~10-20ms)                                     │
│    • Binary data (JPEG frames)                                  │
│    • JSON responses                                             │
│                                                                  │
│ 2. HTTP POST (Batch ML)                                         │
│    Flutter → Python ML (Port 8001)                              │
│    • Multipart form data (file upload)                          │
│    • JSON responses                                             │
│    • Higher latency (depends on file size)                      │
│                                                                  │
│ 3. REST API (Business Logic)                                    │
│    Flutter ⟷ Laravel (Port 8000)                               │
│    • HTTP GET/POST/PUT/DELETE                                   │
│    • JSON request/response                                      │
│    • JWT token in Authorization header                          │
│                                                                  │
│ 4. External API (Text-to-Speech)                                │
│    Flutter → Laravel → ElevenLabs API                           │
│    • HTTP POST /api/speech with text                            │
│    • Laravel forwards to ElevenLabs                             │
│    • Binary audio (MP3) response                                │
│    • API key in headers                                         │
│                                                                  │
│ 5. Speech Recognition (Voice-to-Sign)                           │
│    Flutter → Device STT Engine                                  │
│    • Native speech_to_text package                              │
│    • Real-time transcription                                    │
│    • Offline capable (if device supports)                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

### **Environment Configuration**

#### **Flutter App (`.env` file)**
```env
# Laravel API
BASE_URL=http://YOUR_SERVER_IP:8000

# Python ML Services
CLASSIFIER_URL=http://YOUR_SERVER_IP:8001
WEBSOCKET_URL=ws://YOUR_SERVER_IP:8002

# External APIs
ELEVENLABS_API_KEY=your_api_key_here
```

#### **Laravel Backend (`.env` file)**
```env
# Database
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=gesturetalk
DB_USERNAME=root
DB_PASSWORD=your_password

# JWT
JWT_SECRET=your_jwt_secret_here
JWT_TTL=60

# App
APP_URL=http://localhost:8000
```

---

## 📊 Database Schema

### **Complete Database Diagram**

```
┌─────────────────────────────────────────────────────────────────┐
│                        MySQL DATABASE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────────────────────────────┐                    │
│  │  users                                  │                    │
│  ├────────────────────────────────────────┤                    │
│  │  id              BIGINT PK              │                    │
│  │  name            VARCHAR(255)           │                    │
│  │  email           VARCHAR(255) UNIQUE    │                    │
│  │  password        VARCHAR(255)           │                    │
│  │  created_at      TIMESTAMP              │                    │
│  │  updated_at      TIMESTAMP              │                    │
│  └────────────────────────────────────────┘                    │
│         │                                                        │
│         │ 1:N (one user has many translations)                  │
│         ↓                                                        │
│  ┌────────────────────────────────────────┐                    │
│  │  translations                           │                    │
│  ├────────────────────────────────────────┤                    │
│  │  id              BIGINT PK              │                    │
│  │  user_id         BIGINT FK              │────→ users.id     │
│  │  input_type      ENUM('live','image',  │                    │
│  │                       'video')          │                    │
│  │  input_data      TEXT (file path/data) │                    │
│  │  translated_text TEXT                   │                    │
│  │  created_at      TIMESTAMP              │                    │
│  │  updated_at      TIMESTAMP              │                    │
│  └────────────────────────────────────────┘                    │
│         │                                                        │
│         │ 1:N (one translation has many text entries)           │
│         ↓                                                        │
│  ┌────────────────────────────────────────┐                    │
│  │  translated_texts                       │                    │
│  ├────────────────────────────────────────┤                    │
│  │  id              BIGINT PK              │                    │
│  │  user_id         BIGINT FK              │────→ users.id     │
│  │  original_text   TEXT                   │                    │
│  │  translated_text TEXT                   │                    │
│  │  created_at      TIMESTAMP              │                    │
│  │  updated_at      TIMESTAMP              │                    │
│  └────────────────────────────────────────┘                    │
│                                                                 │
│  ┌────────────────────────────────────────┐                    │
│  │  translated_audios                      │                    │
│  ├────────────────────────────────────────┤                    │
│  │  id              BIGINT PK              │                    │
│  │  user_id         BIGINT FK              │────→ users.id     │
│  │  audio_path      VARCHAR(255)           │                    │
│  │  text            TEXT                   │                    │
│  │  created_at      TIMESTAMP              │                    │
│  │  updated_at      TIMESTAMP              │                    │
│  └────────────────────────────────────────┘                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Complete File Structure

```
GestureTalk/
│
├── GestureTalk-Backend/                      # Backend (Laravel + Python)
│   │
│   ├── SignDetectionModel/                   # Python ML Services
│   │   │
│   │   ├── 🎯 PRODUCTION FILES
│   │   ├── final_classifier.py               # Standalone classifier (OpenCV)
│   │   ├── websocket_final_classifier.py     # WebSocket server (Port 8002)
│   │   ├── uploaded_files_classifier.py      # FastAPI server (Port 8001)
│   │   │
│   │   ├── 🤖 MODEL FILES
│   │   ├── mlp_model.p                       # Letter model (sklearn MLP)
│   │   ├── transformer_mlp_word_model.pth    # Word model (Temporal Transformer)
│   │   ├── preprocessing_word.pkl            # Feature scaler & encoder
│   │   │
│   │   ├── 📚 DOCUMENTATION
│   │   ├── PROJECT_MODEL_SUMMARY.md          # Technical documentation
│   │   ├── TRANSFORMER_MLP_ARCHITECTURE_DIAGRAM.md  # Architecture diagrams
│   │   ├── COMPLETE_SYSTEM_DOCUMENTATION.md  # This file
│   │   ├── PROJECT_FILES_LIST.md             # Complete file list
│   │   ├── DEPLOYMENT_GUIDE_DEC_2025.md      # Deployment guide
│   │   ├── FINAL_CLASSIFIER_CONFIG.py        # Configuration reference
│   │   │
│   │   ├── 🛠️ UTILITIES
│   │   ├── nlp_processor.py                  # Grammar improvement
│   │   ├── requirements.txt                  # Python dependencies
│   │   ├── get_ip.bat                        # Network utility
│   │   └── start_*.bat                       # Startup scripts
│   │
│   ├── app/                                  # Laravel Application
│   │   ├── Http/
│   │   │   └── Controllers/
│   │   │       ├── AuthController.php        # Authentication
│   │   │       ├── TranslationController.php # Translation CRUD
│   │   │       ├── SpeechController.php      # Text-to-speech
│   │   │       └── UserController.php        # User management
│   │   │
│   │   └── Models/
│   │       ├── User.php                      # User model
│   │       ├── Translation.php               # Translation model
│   │       ├── TranslatedText.php            # Text model
│   │       └── TranslatedAudio.php           # Audio model
│   │
│   ├── routes/
│   │   ├── api.php                           # REST API routes
│   │   └── web.php                           # Web routes
│   │
│   ├── config/
│   │   ├── database.php                      # Database configuration
│   │   ├── jwt.php                           # JWT settings
│   │   └── cors.php                          # CORS settings
│   │
│   └── database/
│       ├── migrations/                       # Database schemas
│       └── seeders/                          # Sample data
│
└── GestureTalk-Front/                        # Frontend (Flutter)
    │
    ├── lib/
    │   │
    │   ├── main.dart                         # App entry point
    │   │
    │   ├── screens/                          # UI Screens
    │   │   ├── live_translation_screen.dart  # 📹 Live camera translation
    │   │   ├── media_translation_screen.dart # 📁 Image/video upload
    │   │   ├── history_screen.dart           # 📊 Translation history
    │   │   ├── login_screen.dart             # 🔐 User login
    │   │   ├── sign_up_screen.dart           # 📝 User registration
    │   │   ├── profile_screen.dart           # 👤 User profile
    │   │   ├── statistics_screen.dart        # 📈 Usage statistics
    │   │   ├── voice_to_sign_screen.dart     # 🎤 Voice to sign
    │   │   └── sync_screen.dart              # 🔄 Data sync
    │   │
    │   ├── services/                         # Backend Integration
    │   │   ├── connectivity_service.dart     # Network monitoring
    │   │   ├── offline_storage_service.dart  # Local database (SQLite)
    │   │   ├── statistics_service.dart       # Analytics
    │   │   └── sync_service.dart             # Cloud sync
    │   │
    │   ├── widgets/                          # Reusable Components
    │   │   ├── bottom_navigation_bar.dart    # Navigation
    │   │   ├── app_lifecycle_wrapper.dart    # State management
    │   │   ├── offline_indicator.dart        # Connection status
    │   │   └── sign_language_display.dart    # 🆕 Sign visualization widget
    │   │
    │   ├── theme/
    │   │   └── app_theme.dart                # UI styling
    │   │
    │   └── utils/
    │       └── nlp_processor.dart            # Text processing
    │
    ├── assets/                               # 🆕 Visual Assets
    │   └── signs/
    │       ├── words/                        # Word-level signs (2000+ images)
    │       │   ├── hello.png
    │       │   ├── thanks.png
    │       │   ├── please.png
    │       │   └── ... (2000+ more)
    │       └── letters/                      # Fingerspelling (26 letters)
    │           ├── A.png
    │           ├── B.png
    │           ├── C.png
    │           └── ... (Z.png)
    │
    ├── pubspec.yaml                          # Flutter dependencies
    └── .env                                  # Environment variables
```

---

## 🛠️ Technology Stack

### **Frontend**
```yaml
Framework: Flutter 3.x
Language: Dart
Platform: Android, iOS

Key Packages:
  - camera: ^0.11.0+2              # Camera access
  - web_socket_channel: ^3.0.1     # WebSocket client
  - http: ^1.2.2                   # HTTP requests
  - image_picker: ^1.1.2           # File picker
  - flutter_secure_storage: ^9.2.2 # Secure storage
  - sqflite: ^2.3.0                # Local database
  - connectivity_plus: ^5.0.2      # Network monitoring
  - audioplayers: ^6.1.0           # Audio playback
  - speech_to_text: ^6.1.1         # Speech recognition (NEW)
  - video_player: ^2.8.0           # Video playback
  - google_fonts: ^6.1.0           # Typography
  - flutter_dotenv: ^5.1.0         # Environment config
  - path_provider: ^2.1.1          # File system paths
```

### **Backend - Python ML**
```yaml
Language: Python 3.10+

Core ML/DL:
  - torch: 2.0+                    # PyTorch (deep learning)
  - scikit-learn: 1.3+             # ML utilities
  - numpy: 1.24+                   # Numerical computing

Computer Vision:
  - opencv-python: 4.8+            # Image processing
  - mediapipe: 0.10+               # Hand detection

Web Services:
  - fastapi: 0.104+                # REST API
  - websockets: 12.0               # WebSocket
  - uvicorn: 0.24+                 # ASGI server
```

### **Backend - Laravel API**
```yaml
Framework: Laravel 10
Language: PHP 8.1+
Database: MySQL 8.0+

Key Packages:
  - php-open-source-saver/jwt-auth # JWT authentication
  - guzzlehttp/guzzle              # HTTP client
  - fruitcake/laravel-cors         # CORS support
```

---

## ⚡ Performance Metrics

### **Latency Measurements**

| Operation | Time | Details |
|-----------|------|---------|
| **Letter Detection** | 50-100ms | Camera → Prediction → Display |
| **Word Detection** | 500-600ms | Includes 30-frame collection |
| **MediaPipe Hand Detection** | 10-20ms | Per frame |
| **MLP Inference** | 1-2ms | Letter model |
| **Transformer Inference** | 50-100ms | Word model (30 frames) |
| **WebSocket Roundtrip** | 10-20ms | Local network |
| **Image Upload** | 2-5 sec | Depends on file size |
| **Video Upload** | 5-30 sec | Depends on video length |

### **Accuracy Metrics**

| Model | Accuracy | Details |
|-------|----------|---------|
| **Letter Model (MLP)** | 95%+ | 26 classes (A-Z) |
| **Word Model (Temporal)** | 77%+ | 300+ classes (words) |
| **Hand Detection (MediaPipe)** | 98%+ | With validation |
| **False Positive Rate** | <2% | After shape validation |

### **Resource Usage**

| Component | RAM | GPU | CPU |
|-----------|-----|-----|-----|
| **Flutter App** | ~100MB | Minimal | 5-10% |
| **WebSocket Server** | ~500MB | Optional | 20-30% |
| **FastAPI Server** | ~400MB | Optional | 15-25% |
| **Laravel API** | ~50MB | N/A | 5-10% |

---

## 🎓 Summary for Thesis

### **System Highlights**

1. **Bidirectional Communication:** Sign-to-Text AND Voice-to-Sign translation
2. **Real-Time Processing:** WebSocket-based streaming achieves 50-100ms latency for letters
3. **Dual-Model Architecture:** Specialized models for letters (MLP) and words (Temporal Transformer)
4. **Visual Sign Language Display:** Card-based UI with 2000+ word signs and fingerspelling
5. **Natural Voice Synthesis:** ElevenLabs TTS integration for high-quality audio
6. **Production-Ready:** Robust validation, error handling, offline support
7. **Full-Stack:** Flutter mobile app + Python ML + Laravel API + MySQL database + External APIs
8. **Scalable:** Modular design, separate services, clear responsibilities
9. **Professional:** JWT authentication, data persistence, multi-modal input/output

### **Key Files to Reference**

**Backend ML:**
- `websocket_final_classifier.py` - Real-time translation backend
- `uploaded_files_classifier.py` - Media upload backend
- `mlp_model.p` - Letter detection model
- `transformer_mlp_word_model.pth` - Word detection model
- `nlp_processor.py` - Grammar improvement

**Backend API:**
- `AuthController.php` - User authentication
- `TranslationController.php` - Data management
- `SpeechController.php` - 🆕 Text-to-speech (ElevenLabs)

**Frontend Screens:**
- `live_translation_screen.dart` - Real-time sign detection UI
- `media_translation_screen.dart` - Upload image/video UI
- `voice_to_sign_screen.dart` - 🆕 Speech-to-sign UI
- `history_screen.dart` - Translation history
- `main.dart` - App structure

**Frontend Widgets:**
- `sign_language_display.dart` - 🆕 Visual sign language cards

**Assets:**
- `assets/signs/words/` - 🆕 2000+ word sign images
- `assets/signs/letters/` - 🆕 26 fingerspelling images

**Documentation:**
- `VOICE_TO_SIGN_IMPLEMENTATION.md` - 🆕 Voice-to-sign feature guide
- `ELEVENLABS_INTEGRATION_GUIDE.md` - 🆕 TTS integration guide

---

## 📝 Document History

**Document Created:** December 16, 2025  
**Last Updated:** December 17, 2025

**Recent Updates:**
- ✅ Added Voice-to-Sign Translation feature (Section 6)
- ✅ Added Visual Sign Language Display system (Section 7)
- ✅ Added ElevenLabs TTS Integration (Section 8)
- ✅ Updated architecture diagrams for bidirectional communication
- ✅ Updated file structure with new screens, widgets, and assets
- ✅ Updated technology stack with new packages (speech_to_text, video_player)
- ✅ Added comprehensive implementation guides for new features

**Total Sections:** 13  
**Total Lines:** 2900+  
**Coverage:** Complete system documentation including all features, architecture, and implementation details  
**Version:** 2.0 Complete System Documentation  
**Status:** ✅ Production Ready  
**Purpose:** Comprehensive reference for thesis and deployment

