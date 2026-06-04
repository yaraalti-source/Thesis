# How to Copy WLASL Videos for Words

## Quick Start

### Copy Common Words (50+ words)

```bash
python GestureTalk-Front/scripts/copy_wlasl_videos_for_words.py
```

This will copy videos for 50+ common words like: hello, thanks, please, yes, no, etc.

### Copy Specific Words

```bash
# Copy specific words
python GestureTalk-Front/scripts/copy_wlasl_videos_for_words.py hello thanks please yes no
```

### Copy All Words (2000+ videos)

⚠️ **Warning**: This will copy 2000+ videos and may take time!

```python
# Edit the script and set words_to_copy=None in copy_videos_for_words()
python GestureTalk-Front/scripts/copy_wlasl_videos_for_words.py
```

## What It Does

1. ✅ Reads video-word mapping from `video_word_mapping.json`
2. ✅ Finds the correct video ID for each word
3. ✅ Copies videos from backend to frontend assets
4. ✅ Renames videos with correct file-safe names
5. ✅ Skips videos that already exist

## Output

Videos are copied to:
```
GestureTalk-Front/assets/signs/words/
```

With correct names like:
- `hello.mp4`
- `thank_you.mp4`
- `ice_cream.mp4`

## After Copying

1. **Restart the app** (not hot reload) to see the videos
2. Test by saying the words in the Voice-to-Sign screen
3. Each word should now show its unique sign video!

## Troubleshooting

### "Video mapping file not found"
Run first:
```bash
python GestureTalk-Front/scripts/map_wlasl_videos_to_words.py
```

### "Source videos directory not found"
Make sure WLASL videos are in:
```
GestureTalk-Backend/SignDetectionModel/wordset/videos/
```

### Videos not showing in app
1. Check file names match exactly (lowercase, underscores)
2. Restart app completely (not hot reload)
3. Check pubspec.yaml includes `assets/signs/words/`









