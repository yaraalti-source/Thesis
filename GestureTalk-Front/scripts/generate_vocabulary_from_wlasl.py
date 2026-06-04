"""
Generate comprehensive vocabulary JSON from WLASL class list.
This script reads the WLASL class list and creates a vocabulary configuration file.
"""

import json
import os

# Path to WLASL class list file (relative to project root)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
WLASL_CLASS_LIST = os.path.join(PROJECT_ROOT, 'GestureTalk-Backend/SignDetectionModel/wordset/wlasl_class_list.txt')
OUTPUT_JSON = os.path.join(PROJECT_ROOT, 'GestureTalk-Front/assets/config/vocabulary.json')

def generate_vocabulary():
    """Generate vocabulary JSON from WLASL class list."""
    print("="*60)
    print("Generating Vocabulary Configuration from WLASL")
    print("="*60)
    
    words = {}
    
    # Read WLASL class list
    if not os.path.exists(WLASL_CLASS_LIST):
        print(f"Error: WLASL class list not found at {WLASL_CLASS_LIST}")
        print("Please ensure the path is correct.")
        return None
    
    print(f"\nReading WLASL class list from: {WLASL_CLASS_LIST}")
    
    with open(WLASL_CLASS_LIST, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split('\t')
            if len(parts) >= 2:
                try:
                    word_idx = int(parts[0].strip())
                    word = parts[1].strip().lower()
                    
                    # Skip empty words
                    if word:
                        # Handle multi-word phrases (e.g., "thank you", "ice cream")
                        # Convert spaces to underscores for file naming
                        file_safe_word = word.replace(' ', '_')
                        
                        words[word] = {
                            'index': word_idx,
                            'hasVideo': False,  # User needs to add videos manually
                            'videoPath': f'assets/signs/words/{file_safe_word}.mp4',
                            'imagePath': f'assets/signs/words/{file_safe_word}.png',
                            'fileSafeName': file_safe_word,  # For file system
                        }
                except ValueError:
                    continue
    
    print(f"\nLoaded {len(words)} words from WLASL dataset")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(OUTPUT_JSON)
    os.makedirs(output_dir, exist_ok=True)
    
    # Create vocabulary structure
    vocabulary = {
        'version': '1.0.0',
        'totalWords': len(words),
        'wordsWithVideos': 0,  # User will update this when adding videos
        'words': words,
        'metadata': {
            'source': 'WLASL (Word-Level American Sign Language)',
            'generatedBy': 'generate_vocabulary_from_wlasl.py',
            'totalEntries': len(words),
        }
    }
    
    # Write to JSON file with proper formatting
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(vocabulary, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Vocabulary configuration saved to: {OUTPUT_JSON}")
    print(f"   Total words: {len(words)}")
    print(f"\n📝 Next steps:")
    print(f"   1. Copy sign videos to: assets/signs/words/")
    print(f"   2. Name videos as: <word>.mp4 (e.g., hello.mp4, thank_you.mp4)")
    print(f"   3. Run this script again after adding videos to update hasVideo flags")
    
    return OUTPUT_JSON

if __name__ == '__main__':
    generate_vocabulary()

