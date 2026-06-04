"""
Generate vocabulary configuration JSON file from WLASL class list.
This creates a comprehensive vocabulary file that maps all words to their sign paths.
"""

import json
import os
import sys

# Add parent directory to path to access backend wordset
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Configuration
BACKEND_WORDSET_DIR = '../../GestureTalk-Backend/SignDetectionModel/wordset'
CLASS_LIST_FILE = os.path.join(BACKEND_WORDSET_DIR, 'wlasl_class_list.txt')
OUTPUT_JSON = '../assets/config/vocabulary.json'

def load_wlasl_words():
    """Load all words from WLASL class list."""
    words = {}
    
    if not os.path.exists(CLASS_LIST_FILE):
        print(f"Warning: Class list file not found at {CLASS_LIST_FILE}")
        print("Using fallback common words list...")
        return get_fallback_words()
    
    try:
        with open(CLASS_LIST_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split('\t')
                if len(parts) >= 2:
                    word_idx = parts[0].strip()
                    word = parts[1].strip().lower()
                    
                    # Skip empty words
                    if word:
                        words[word] = {
                            'index': int(word_idx),
                            'hasVideo': False,  # Will be updated if video exists
                            'videoPath': f'assets/signs/words/{word}.mp4',
                            'imagePath': f'assets/signs/words/{word}.png',
                        }
        print(f"Loaded {len(words)} words from WLASL class list")
    except Exception as e:
        print(f"Error loading WLASL class list: {e}")
        print("Using fallback common words list...")
        return get_fallback_words()
    
    return words

def get_fallback_words():
    """Fallback vocabulary with common words if WLASL list unavailable."""
    common_words = [
        'hello', 'hi', 'goodbye', 'bye', 'thanks', 'thank', 'please', 
        'sorry', 'yes', 'no', 'okay', 'welcome',
        'good', 'bad', 'happy', 'sad', 'angry', 'tired', 'sick', 
        'fine', 'better', 'love', 'like', 'hate',
        'help', 'eat', 'drink', 'go', 'come', 'want', 'need', 'have',
        'see', 'hear', 'talk', 'walk', 'run', 'sit', 'stand', 'sleep',
        'water', 'food', 'home', 'school', 'work', 'car', 'phone',
        'book', 'door', 'window', 'table', 'chair',
        'family', 'friend', 'mother', 'father', 'brother', 'sister',
        'child', 'baby', 'man', 'woman', 'people',
        'morning', 'afternoon', 'evening', 'night', 'day', 'time',
        'today', 'tomorrow', 'yesterday', 'now', 'later',
        'name', 'meet', 'nice', 'know', 'think', 'understand',
        'learn', 'teach', 'study', 'read', 'write',
    ]
    
    words = {}
    for idx, word in enumerate(common_words):
        words[word] = {
            'index': idx,
            'hasVideo': False,
            'videoPath': f'assets/signs/words/{word}.mp4',
            'imagePath': f'assets/signs/words/{word}.png',
        }
    
    return words

def check_video_availability(words, videos_dir):
    """Check which words have available video files."""
    if not os.path.exists(videos_dir):
        print(f"Warning: Videos directory not found at {videos_dir}")
        return words
    
    available_videos = set()
    if os.path.exists(videos_dir):
        for filename in os.listdir(videos_dir):
            if filename.endswith('.mp4'):
                # Remove extension and convert to lowercase
                video_word = filename[:-4].lower()
                available_videos.add(video_word)
    
    # Update words with video availability
    updated_count = 0
    for word in words:
        if word in available_videos:
            words[word]['hasVideo'] = True
            updated_count += 1
    
    print(f"Found {updated_count} words with available video files")
    return words

def generate_vocabulary_config():
    """Generate the vocabulary configuration JSON file."""
    print("="*60)
    print("Generating Vocabulary Configuration")
    print("="*60)
    
    # Load words from WLASL
    words = load_wlasl_words()
    
    # Check video availability (optional - requires backend path)
    videos_dir = os.path.join(BACKEND_WORDSET_DIR, 'videos')
    words = check_video_availability(words, videos_dir)
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(OUTPUT_JSON)
    os.makedirs(output_dir, exist_ok=True)
    
    # Create vocabulary structure
    vocabulary = {
        'version': '1.0.0',
        'totalWords': len(words),
        'wordsWithVideos': sum(1 for w in words.values() if w['hasVideo']),
        'words': words,
        'metadata': {
            'source': 'WLASL (Word-Level American Sign Language)',
            'generatedBy': 'generate_vocabulary_config.py',
        }
    }
    
    # Write to JSON file
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(vocabulary, f, indent=2, ensure_ascii=False)
    
    print(f"\nVocabulary configuration saved to: {OUTPUT_JSON}")
    print(f"Total words: {len(words)}")
    print(f"Words with videos: {sum(1 for w in words.values() if w['hasVideo'])}")
    print("\n✅ Vocabulary configuration generated successfully!")
    
    return OUTPUT_JSON

if __name__ == '__main__':
    generate_vocabulary_config()









