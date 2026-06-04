# Sign Language Assets Setup Guide

## Quick Setup Instructions

### 1. Download ASL Letter Images (26 images - A to Z)

**Option A: Use free ASL resources**
- Visit [ASL Lifeprint](http://www.lifeprint.com/asl101/pages-signs/a/abc.htm)
- Download letter images A-Z
- Save as: `A.png`, `B.png`, `C.png`, ..., `Z.png`

**Option B: AI Generation (Recommended)**
Use DALL-E or Midjourney with this prompt:
```
"Simple clean illustration of ASL sign language letter [LETTER], 
white background, hand gesture only, front view, professional style"
```

**Option C: Quick placeholder script**
Run the Python script below to generate placeholder images.

### 2. Organize Files

```
assets/signs/
├── letters/
│   ├── A.png
│   ├── B.png
│   ├── C.png
│   └── ... (Z.png)
├── words/
│   └── (videos will go here - optional)
└── README.md (this file)
```

### 3. Copy WLASL Videos (Optional - for better accuracy)

If you want to use real sign videos for common words:

```bash
# From your backend to frontend
cp GestureTalk-Backend/SignDetectionModel/wordset/videos/*.mp4 GestureTalk-Front/assets/signs/words/
```

Note: This is optional. The app will fall back to spelling words letter-by-letter if videos don't exist.

---

## Quick Placeholder Generator

Save this as `generate_placeholder_letters.py` and run it:

```python
from PIL import Image, ImageDraw, ImageFont
import os

# Create output directory
os.makedirs('letters', exist_ok=True)

# Generate placeholder images for each letter
for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
    # Create white background
    img = Image.new('RGB', (400, 400), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a nice font, fallback to default
    try:
        font = ImageFont.truetype("arial.ttf", 180)
    except:
        font = ImageFont.load_default()
    
    # Draw the letter in the center
    text = letter
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (400 - text_width) // 2
    y = (400 - text_height) // 2
    
    draw.text((x, y), text, fill='#4A90E2', font=font)
    
    # Add "ASL" label at bottom
    try:
        small_font = ImageFont.truetype("arial.ttf", 30)
    except:
        small_font = font
    
    draw.text((150, 350), f"ASL {letter}", fill='#666666', font=small_font)
    
    # Save image
    img.save(f'letters/{letter}.png')
    print(f"Generated {letter}.png")

print("\n✓ All 26 letter placeholders generated!")
print("Place these files in: GestureTalk-Front/assets/signs/letters/")
```

Run with:
```bash
pip install pillow
python generate_placeholder_letters.py
```

---

## Current Implementation Status

### ✅ What's Implemented:
- Sign display widget created
- Grid layout for multiple signs
- Letter/word fallback logic
- Image placeholder support
- Video placeholder UI

### 📋 What You Need to Add:
1. **26 letter images** (A-Z) → `assets/signs/letters/`
2. **Optional: Word videos** → `assets/signs/words/`

### 🎯 Recommended Approach:
1. Use the placeholder generator script above for quick testing
2. Replace with real ASL images later
3. Add videos for common words (optional)

---

## File Size Guidelines

- **Letter images**: 100-200 KB each (PNG, 400x400 px)
- **Word videos**: 500KB - 2MB each (MP4, 480p)

**Total assets size:**
- Minimal (letters only): ~5 MB (26 images)
- Full (letters + 300 videos): ~600 MB (not recommended for mobile app)
- Recommended: Letters + 50 common word videos: ~100 MB

---

## Update pubspec.yaml

Already done in the implementation! The assets are declared in:

```yaml
flutter:
  assets:
    - assets/signs/letters/
    - assets/signs/words/
```

---

## Testing

After adding letter images:

1. Restart the app (not hot reload)
2. Go to Voice-to-Sign screen
3. Tap microphone and speak: "Hello"
4. Should see letter images: H-E-L-L-O

If images don't appear, check:
- Files are named correctly (A.png, B.png, etc.)
- Files are in correct folder
- pubspec.yaml includes assets
- App was restarted (not hot reload)

---

**Need help?** Check the widget implementation in:
`lib/widgets/sign_language_display.dart`









