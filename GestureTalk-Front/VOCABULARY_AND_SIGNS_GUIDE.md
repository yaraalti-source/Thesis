# Complete Guide: Adding Signs for Voice-to-Sign Translation

This guide explains how to add sign language videos for all words in the vocabulary system.

## 📋 Overview

The GestureTalk app supports **2000+ words** from the WLASL (Word-Level American Sign Language) dataset. This system allows you to:

1. ✅ **Translate any word from voice to sign language**
2. ✅ **Add sign videos for each word**
3. ✅ **Organize and manage your sign vocabulary**

## 🗂️ System Architecture

### Files and Structure

```
GestureTalk-Front/
├── assets/
│   ├── config/
│   │   ├── vocabulary.json          # All 2000+ words configuration
│   │   ├── video_word_mapping.json  # Video ID to word mapping
│   │   └── VIDEO_MAPPING_GUIDE.md   # Video mapping reference
│   └── signs/
│       ├── letters/                 # A-Z letter images (26 files)
│       └── words/                   # Word sign videos (add here)
│
├── scripts/
│   ├── generate_vocabulary_from_wlasl.py  # Generate vocabulary JSON
│   └── map_wlasl_videos_to_words.py      # Map videos to words
│
└── lib/
    └── widgets/
        └── sign_language_display.dart     # Main widget (uses vocabulary)
```

## 📚 Vocabulary System

### Current Vocabulary

- **Total Words**: 2000+ words from WLASL dataset
- **Vocabulary File**: `assets/config/vocabulary.json`
- **Format**: Each word has:
  ```json
  {
    "hello": {
      "index": 402,
      "hasVideo": false,
      "videoPath": "assets/signs/words/hello.mp4",
      "imagePath": "assets/signs/words/hello.png",
      "fileSafeName": "hello"
    }
  }
  ```

### How Words Are Recognized

1. **Voice Input** → Speech-to-Text converts speech to text
2. **Text Processing** → Words are split and normalized (lowercase)
3. **Vocabulary Lookup** → System checks if word exists in `vocabulary.json`
4. **Sign Display**:
   - ✅ **Word in vocabulary** → Shows as **Purple Word Card** (if video exists)
   - ❌ **Word not in vocabulary** → Shows as **Grey Unknown Card**
   - 🔤 **Names/Single letters** → Shows as **Blue Letter Cards** (spelled out)

## 🎬 Adding Sign Videos

### Method 1: Using WLASL Dataset Videos (Recommended)

**Step 1: Get Videos from Backend**

The WLASL videos are in:
```
GestureTalk-Backend/SignDetectionModel/wordset/videos/
```

**Step 2: Copy and Rename Videos**

1. Copy videos to: `GestureTalk-Front/assets/signs/words/`
2. Rename according to word names:
   - Use the `video_word_mapping.json` file as reference
   - Or check the word name in `vocabulary.json`

**Naming Convention**:
- **Single words**: `hello.mp4`, `water.mp4`, `book.mp4`
- **Multi-word phrases**: Use underscores: `thank_you.mp4`, `ice_cream.mp4`
- **All lowercase**
- **Remove special characters**
- **Use `.mp4` extension**

**Step 3: Verify**

Run the app and test:
- Say "hello" → Should show purple word card if `hello.mp4` exists
- Say "thank you" → Should show cards for "thank" and "you" (or "thank_you" if phrase exists)

### Method 2: Manual Video Addition

**For Custom Videos**:

1. Record or download ASL sign videos
2. Save as MP4 format
3. Name file according to word (see naming convention above)
4. Place in `assets/signs/words/` directory
5. Restart app (not hot reload)

### Method 3: Batch Processing Script (Advanced)

Create a script to automatically copy and rename WLASL videos:

```python
import os
import shutil
import json

# Load video-word mapping
with open('assets/config/video_word_mapping.json', 'r') as f:
    mapping = json.load(f)

# Source and destination
src_dir = '../GestureTalk-Backend/SignDetectionModel/wordset/videos/'
dst_dir = 'assets/signs/words/'

# Copy videos with correct names
for word, video_ids in mapping['wordsToVideos'].items():
    if video_ids:  # If videos exist for this word
        # Use first video ID
        src_video = os.path.join(src_dir, f"{video_ids[0]}.mp4")
        file_safe_name = word.replace(' ', '_')
        dst_video = os.path.join(dst_dir, f"{file_safe_name}.mp4")
        
        if os.path.exists(src_video):
            shutil.copy2(src_video, dst_video)
            print(f"Copied: {word} → {dst_video}")
```

## 🔧 Updating Vocabulary

### Regenerate Vocabulary JSON

If you've added videos or want to refresh the vocabulary:

```bash
python GestureTalk-Front/scripts/generate_vocabulary_from_wlasl.py
```

This will:
- Read all words from WLASL class list
- Check which videos exist in `assets/signs/words/`
- Update `hasVideo` flags in vocabulary.json

### Update Video Mapping

To regenerate the video-word mapping:

```bash
python GestureTalk-Front/scripts/map_wlasl_videos_to_words.py
```

This creates/updates:
- `video_word_mapping.json` - Maps video IDs to words
- `VIDEO_MAPPING_GUIDE.md` - Reference guide

## 📖 Word Examples

### Common Words Already Supported

The vocabulary includes all these words (and 1900+ more):

**Greetings**: hello, hi, goodbye, bye, thanks, thank you, please, sorry, welcome

**Emotions**: happy, sad, angry, tired, sick, fine, better, good, bad, love, like, hate

**Actions**: help, eat, drink, go, come, want, need, have, see, hear, talk, walk, run, sit, stand, sleep

**Objects**: water, food, home, school, work, car, phone, book, door, window, table, chair

**People**: family, friend, mother, father, brother, sister, child, baby, man, woman, people

**Time**: morning, afternoon, evening, night, day, time, today, tomorrow, yesterday, now, later

### Multi-Word Phrases

Some phrases are treated as single words:
- "thank you" → `thank_you.mp4`
- "ice cream" → `ice_cream.mp4`
- "don't want" → `dont_want.mp4`
- "high school" → `high_school.mp4`

## 🎯 Quick Start: Adding Your First Signs

**Example: Add sign for "hello"**

1. **Find video**:
   ```bash
   # Check video mapping
   cat assets/config/video_word_mapping.json | grep -A 5 "hello"
   ```

2. **Copy video**:
   ```bash
   # From backend videos directory
   cp GestureTalk-Backend/SignDetectionModel/wordset/videos/[VIDEO_ID].mp4 \
      GestureTalk-Front/assets/signs/words/hello.mp4
   ```

3. **Test in app**:
   - Open app
   - Go to Voice-to-Sign screen
   - Say "hello"
   - Should see purple word card with video

## ⚙️ Technical Details

### How Vocabulary Loading Works

1. **App Startup**: `VocabularyManager` loads `vocabulary.json`
2. **Word Recognition**: `_isCommonWord()` checks vocabulary
3. **Video Display**: Widget looks for video file at path specified in vocabulary
4. **Fallback**: If video doesn't exist, shows placeholder icon

### Code Flow

```dart
Voice Input
    ↓
Speech-to-Text: "Hello my name is Yara"
    ↓
SignLanguageDisplay._parseTextToSigns()
    ↓
For each word:
    ├─ "hello" → VocabularyManager.hasWord("hello") → true
    │   └─ Show Word Card (purple) with video
    ├─ "my" → VocabularyManager.hasWord("my") → true
    │   └─ Show Word Card (purple) with video
    ├─ "name" → VocabularyManager.hasWord("name") → true
    │   └─ Show Word Card (purple) with video
    ├─ "is" → VocabularyManager.hasWord("is") → false (if not in vocab)
    │   └─ Show Unknown Card (grey)
    └─ "yara" → _shouldSpellOut("yara") → true (name)
        └─ Show Letter Cards: Y-A-R-A (blue)
```

## 📝 Best Practices

1. **Video Quality**:
   - Format: MP4
   - Resolution: 640x480 or higher
   - Duration: 1-3 seconds per sign
   - File size: < 5MB per video

2. **File Naming**:
   - Always use lowercase
   - Replace spaces with underscores
   - Remove special characters
   - Be consistent

3. **Performance**:
   - Don't add all 2000 videos at once (large app size)
   - Add most commonly used words first
   - Use letter spelling for uncommon words

4. **Testing**:
   - Test each word after adding video
   - Verify file names match vocabulary
   - Restart app (not hot reload) after adding assets

## 🐛 Troubleshooting

### Video Not Showing?

1. **Check file name**: Must match word exactly (lowercase, underscores)
2. **Check file location**: Must be in `assets/signs/words/`
3. **Check pubspec.yaml**: Must include `assets/signs/words/`
4. **Restart app**: Hot reload won't load new assets
5. **Check vocabulary.json**: Word must exist with correct `fileSafeName`

### Word Not Recognized?

1. **Check vocabulary.json**: Word must be in the vocabulary
2. **Check word format**: System converts to lowercase automatically
3. **Check for variations**: Some words have aliases (e.g., "hi" → "hello")

### Script Errors?

1. **Check paths**: Ensure WLASL class list exists at expected path
2. **Check permissions**: Ensure you can write to output directories
3. **Check Python version**: Requires Python 3.6+

## 📚 Additional Resources

- **WLASL Dataset**: [Official WLASL Repository](https://github.com/dxli94/WLASL)
- **ASL Resources**: 
  - [ASL Lifeprint](http://www.lifeprint.com/)
  - [Handspeak](https://www.handspeak.com/)
- **Video Mapping Guide**: See `assets/config/VIDEO_MAPPING_GUIDE.md`

## ✅ Summary

You now have:

1. ✅ **Complete vocabulary system** with 2000+ words
2. ✅ **Scripts to generate and manage vocabulary**
3. ✅ **System to add sign videos for each word**
4. ✅ **Clear naming conventions and file structure**
5. ✅ **Documentation and guides**

**Next Steps**:
1. Start by adding videos for most common words (hello, thanks, yes, no, etc.)
2. Test each word in the app
3. Gradually expand to more words as needed
4. Use letter spelling for words you don't have videos for

For questions or issues, refer to the code comments or project documentation.









