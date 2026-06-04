# Quick Guide: Adding Sign Videos for Words

## ✅ Script is Now Fixed!

The script now **automatically tries multiple video IDs** until it finds one that exists, so you can successfully copy videos even if the first few IDs don't have files.

## How to Use

### Copy Videos for Specific Words

```bash
# Copy videos for specific words
python GestureTalk-Front/scripts/copy_wlasl_videos_for_words.py water book yes no please
```

### Copy Common Words (50+ words)

```bash
# Run without arguments to copy common words
python GestureTalk-Front/scripts/copy_wlasl_videos_for_words.py
```

## What the Script Does

1. ✅ Looks up word in video mapping
2. ✅ Gets all available video IDs for that word
3. ✅ **Tries multiple video IDs** (up to 20) until finding one that exists
4. ✅ Copies the video with correct file-safe name
5. ✅ Skips videos that already exist

## Example Output

```
✓ 'water' → water.mp4 (copied from 62500.mp4, tried 5 videos)
✓ 'book' → book.mp4 (copied from 07074.mp4, tried 4 videos)
✓ 'yes' → yes.mp4 (copied from 64292.mp4, tried 7 videos)
```

This means it tried multiple video IDs until finding ones that actually exist!

## Note About "hello"

"hello" is not in the `nslt_300.json` mapping file (which contains 300 words). If you need "hello", you can:

1. **Check if it's in a larger mapping file** (like `nslt_2000.json`)
2. **Manually find and copy the video**:
   ```bash
   # Find video ID for "hello" in the full vocabulary
   # Then copy manually
   cp GestureTalk-Backend/SignDetectionModel/wordset/videos/[VIDEO_ID].mp4 \
      GestureTalk-Front/assets/signs/words/hello.mp4
   ```

## After Copying Videos

1. **Restart your app** (not hot reload!)
2. **Test by saying the words** in Voice-to-Sign screen
3. **Each word should now show its unique sign video!**

## Troubleshooting

### "No source video found"
- The script tries up to 20 video IDs per word
- If none exist, those video IDs may not be in your videos directory
- Try a different word or check if videos are actually downloaded

### Videos not showing in app
- Make sure you **restarted the app** (not hot reload)
- Check file names match exactly (lowercase, underscores)
- Verify videos are in `assets/signs/words/` directory

## Summary

✅ Script now tries multiple video IDs automatically  
✅ Successfully copies videos for words like: water, book, yes, no, please  
✅ Each word gets its unique sign video  
✅ Ready to use!









