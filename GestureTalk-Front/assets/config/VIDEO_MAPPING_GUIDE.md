# WLASL Video to Word Mapping Guide

This guide helps you organize sign language videos for the GestureTalk app.

## Overview

- **Total Words**: 2000
- **Mapped Videos**: 5118
- **Available Video Files**: 11980

## How to Add Sign Videos

### Step 1: Get WLASL Videos

The WLASL (Word-Level American Sign Language) dataset contains sign language videos.
Videos should be placed in: `assets/signs/words/`

### Step 2: Rename Videos

Rename video files to match word names. Use the file-safe name format:

**Format**: `<word_name>.mp4`

**Examples**:
- `hello.mp4` (for word "hello")
- `thank_you.mp4` (for phrase "thank you")
- `ice_cream.mp4` (for phrase "ice cream")

**Important**: 
- Use lowercase letters
- Replace spaces with underscores (`_`)
- Remove special characters
- Use `.mp4` extension

### Step 3: Video Mapping Reference

The mapping file `video_word_mapping.json` contains:
- **wordsToVideos**: Maps each word to its WLASL video IDs
- **videosToWords**: Maps each video ID to its word name

### Step 4: Update Vocabulary

After adding videos, you can update the vocabulary JSON to mark which words have videos:

1. Check which videos you've added to `assets/signs/words/`
2. Update `vocabulary.json` to set `hasVideo: true` for words with videos
3. Or run the vocabulary generator script again (it will detect existing videos)

## Common Words Reference

Here are the first 50 words from the WLASL vocabulary:

1. **book** → `book.mp4`
2. **drink** → `drink.mp4`
3. **computer** → `computer.mp4`
4. **before** → `before.mp4`
5. **chair** → `chair.mp4`
6. **go** → `go.mp4`
7. **clothes** → `clothes.mp4`
8. **who** → `who.mp4`
9. **candy** → `candy.mp4`
10. **cousin** → `cousin.mp4`
11. **deaf** → `deaf.mp4`
12. **fine** → `fine.mp4`
13. **help** → `help.mp4`
14. **no** → `no.mp4`
15. **thin** → `thin.mp4`
16. **walk** → `walk.mp4`
17. **year** → `year.mp4`
18. **yes** → `yes.mp4`
19. **all** → `all.mp4`
20. **black** → `black.mp4`
21. **cool** → `cool.mp4`
22. **finish** → `finish.mp4`
23. **hot** → `hot.mp4`
24. **like** → `like.mp4`
25. **many** → `many.mp4`
26. **mother** → `mother.mp4`
27. **now** → `now.mp4`
28. **orange** → `orange.mp4`
29. **table** → `table.mp4`
30. **thanksgiving** → `thanksgiving.mp4`
31. **what** → `what.mp4`
32. **woman** → `woman.mp4`
33. **bed** → `bed.mp4`
34. **blue** → `blue.mp4`
35. **bowling** → `bowling.mp4`
36. **can** → `can.mp4`
37. **dog** → `dog.mp4`
38. **family** → `family.mp4`
39. **fish** → `fish.mp4`
40. **graduate** → `graduate.mp4`
41. **hat** → `hat.mp4`
42. **hearing** → `hearing.mp4`
43. **kiss** → `kiss.mp4`
44. **language** → `language.mp4`
45. **later** → `later.mp4`
46. **man** → `man.mp4`
47. **shirt** → `shirt.mp4`
48. **study** → `study.mp4`
49. **tall** → `tall.mp4`
50. **white** → `white.mp4`

... and 1950 more words.

## Video File Naming Examples

| Word | File-Safe Name | Video Filename |
|------|---------------|----------------|
| hello | hello | `hello.mp4` |
| thank you | thank_you | `thank_you.mp4` |
| ice cream | ice_cream | `ice_cream.mp4` |
| don't want | dont_want | `dont_want.mp4` |
| high school | high_school | `high_school.mp4` |

## Where to Get Videos

1. **WLASL Dataset**: Download from the official WLASL repository
2. **Extract frames**: Use the video processing scripts in the backend
3. **Custom videos**: Record your own ASL videos following the naming convention

## Notes

- Videos should be in MP4 format
- Recommended resolution: 640x480 or higher
- Recommended length: 1-3 seconds per sign
- File size: Keep videos under 5MB each for app performance

## Scripts Available

- `generate_vocabulary_from_wlasl.py`: Generate vocabulary JSON from WLASL class list
- `map_wlasl_videos_to_words.py`: Map video IDs to word names (this script)
- `check_video_files.py`: Check which videos are available (can be created)

For questions, refer to the main project documentation.
