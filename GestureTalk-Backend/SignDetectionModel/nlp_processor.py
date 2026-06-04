"""
NLP Processor for Sign Language Translation
Improves grammar, adds articles, and forms natural sentences
"""

import re
from typing import List

class SignLanguageNLP:
    """Simple but effective NLP for sign language translation"""
    
    def __init__(self):
        # Common articles and prepositions
        self.articles = {'a', 'an', 'the'}
        self.prepositions = {'to', 'in', 'on', 'at', 'for', 'with', 'by', 'from'}
        
        # Verbs that need "to" after them
        self.verbs_need_to = {
            'go', 'want', 'need', 'like', 'love', 'try', 'start', 'begin',
            'decide', 'plan', 'hope', 'expect', 'learn', 'teach'
        }
        
        # Verbs that need "a/an" after them
        self.verbs_need_article = {
            'want', 'need', 'have', 'get', 'buy', 'find', 'see', 'eat', 'drink',
            'read', 'write', 'make', 'create', 'build'
        }
        
        # Common sentence starters
        self.sentence_starters = {
            'i': 'I', 'my': 'My', 'me': 'Me', 'you': 'You', 'we': 'We',
            'he': 'He', 'she': 'She', 'they': 'They', 'it': 'It'
        }
        
    def process(self, text: str, is_sentence: bool = True) -> str:
        """
        Main processing function - improves the translated text
        
        Args:
            text: Input text to process
            is_sentence: If True, treats as full sentence. If False, treats as single word.
        """
        if not text or not text.strip():
            return text
        
        original_text = text  # Keep original for comparison
        
        # Step 1: Clean and normalize
        text = self._clean_text(text)
        
        # Step 1.5: Only separate letters from words (don't modify words themselves)
        # This separates trailing letters from words, but keeps words complete
        text = self._separate_letters_from_words(text)
        
        # Step 1.6: CRITICAL - Merge separated letters back into words if they form a known word
        # This handles cases where a word like "SUNDAY" was incorrectly split into "S U N D A Y"
        # We check if consecutive letters form a known word and merge them back
        text = self._merge_letters_into_words(text)
        
        # Step 2: Split into words
        words = text.strip().split()
        
        if not words:
            return text
        
        # For single words, just capitalize
        if len(words) == 1 and not is_sentence:
            return words[0].capitalize()
        
        # Step 3: Improve grammar (only for sentences)
        if is_sentence and len(words) > 1:
            words = self._add_articles(words)
            words = self._add_prepositions(words)
            words = self._fix_common_patterns(words)
        
        # Step 4: Capitalize and format
        result = ' '.join(words)
        if is_sentence:
            result = self._capitalize_sentence(result)
            result = self._add_punctuation(result)
        else:
            result = result.capitalize()
        
        return result
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text while preserving letter-word boundaries.
        Ensures spaces between letters and words are maintained.
        """
        # Normalize multiple spaces to single space
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text
    
    def _add_articles(self, words: List[str]) -> List[str]:
        """Add articles (a, an, the) where needed"""
        result = []
        i = 0
        
        while i < len(words):
            word = words[i].lower()
            result.append(words[i])  # Add current word
            
            # Check if next word needs an article
            if i < len(words) - 1:
                next_word = words[i + 1].lower()
                
                # Verb + noun pattern: "want water" → "want a water"
                if word in self.verbs_need_article and self._is_noun(next_word):
                    # Check if article already exists
                    if i + 1 < len(words) - 1:
                        after_next = words[i + 2].lower()
                        if after_next not in self.articles:
                            result.append('a')
                    elif next_word not in ['a', 'an', 'the']:
                        result.append('a')
            
            i += 1
        
        return result
    
    def _add_prepositions(self, words: List[str]) -> List[str]:
        """Add prepositions where needed"""
        result = []
        i = 0
        
        while i < len(words):
            word = words[i].lower()
            result.append(words[i])
            
            # "go store" → "go to store"
            if word in self.verbs_need_to and i < len(words) - 1:
                next_word = words[i + 1].lower()
                # Check if "to" is missing
                if next_word not in self.prepositions and self._is_noun(next_word):
                    # Don't add if already has preposition
                    if i + 1 < len(words) - 1:
                        after_next = words[i + 2].lower()
                        if after_next not in self.prepositions:
                            result.append('to')
                    else:
                        result.append('to')
            
            i += 1
        
        return result
    
    def _fix_common_patterns(self, words: List[str]) -> List[str]:
        """Fix common sign language patterns"""
        result = []
        i = 0
        
        while i < len(words):
            word = words[i].lower()
            
            # "I name yara" → "I name is yara" or "My name is yara"
            if word == 'name' and i > 0:
                prev = words[i - 1].lower()
                if prev in ['i', 'my']:
                    if prev == 'i':
                        result[-1] = 'My'  # Change "I" to "My"
                    result.append('name')
                    if i < len(words) - 1:
                        # Check if "is" is missing
                        next_word = words[i + 1].lower()
                        if next_word != 'is':
                            result.append('is')
                    else:
                        result.append('is')
                else:
                    result.append(words[i])
            # "I am" → keep as is
            elif word == 'am' and i > 0 and words[i - 1].lower() == 'i':
                result.append(words[i])
            # "you are" → keep as is
            elif word == 'are' and i > 0 and words[i - 1].lower() == 'you':
                result.append(words[i])
            else:
                result.append(words[i])
            
            i += 1
        
        return result
    
    def _separate_letters_from_words(self, text: str) -> str:
        """
        Separate letters from words while keeping words complete.
        
        CRITICAL RULES:
        1. Words with 4+ characters are ALWAYS kept COMPLETE - NEVER split (these are words from 2-hand detection)
        2. Words with 3+ characters that match common words are kept COMPLETE
        3. Only separate letters from each other (e.g., "ABC" -> "A B C")
        4. Separate letters from words (e.g., "ABCHELLO" -> "A B C HELLO")
        5. When 1 hand is detected (letter), separate that letter from any word it's attached to
        6. Add spaces between each word and letter detected
        
        PROFESSIONAL APPROACH: Preserve word integrity - complete words are NEVER modified.
        
        Example: "SUNDAY" -> "SUNDAY" (kept complete - 6 characters, known word)
                 "ABCHELLO" -> "A B C HELLO" (separates letters, keeps word complete)
                 "HELLOA" -> "HELLO A" (separates letter from word)
                 "AB" -> "A B" (separates consecutive letters)
                 "HELLO" -> "HELLO" (keeps word complete - NEVER splits words)
                 "MONDAY" -> "MONDAY" (kept complete - never split)
        """
        if not text or len(text.strip()) <= 1:
            return text
        
        # Common words that should be kept complete
        # CRITICAL: Words detected with 2 hands are ALWAYS kept complete - never split
        common_words = {
            # Greetings
            'hello', 'hi', 'hey', 'good', 'morning', 'afternoon', 'evening', 'night', 'day',
            # Politeness
            'thank', 'thanks', 'you', 'please', 'sorry', 'excuse', 'welcome',
            # Basic responses
            'yes', 'no', 'ok', 'okay', 'sure', 'maybe',
            # Pronouns
            'i', 'me', 'my', 'you', 'your', 'we', 'us', 'they', 'them', 'he', 'she', 'it', 'his', 'her',
            # Common verbs
            'go', 'come', 'want', 'need', 'like', 'love', 'see', 'know', 'think', 'say', 'tell',
            'do', 'make', 'get', 'take', 'give', 'help', 'work', 'play', 'eat', 'drink', 'sleep',
            'walk', 'run', 'sit', 'stand', 'look', 'watch', 'listen', 'read', 'write', 'learn', 'teach',
            # Common nouns
            'water', 'food', 'home', 'house', 'school', 'work', 'book', 'car', 'friend', 'family',
            'mother', 'father', 'mom', 'dad', 'sister', 'brother', 'teacher', 'student', 'doctor',
            'hospital', 'restaurant', 'park', 'beach', 'city', 'country', 'world',
            'time', 'day', 'night', 'morning', 'afternoon', 'evening',
            'apple', 'banana', 'bread', 'milk', 'coffee', 'tea',
            'store', 'shop', 'market', 'place', 'room', 'door', 'window', 'table', 'chair',
            'phone', 'computer', 'tv', 'radio', 'music', 'song', 'movie', 'game',
            'money', 'dollar', 'penny', 'bag', 'box', 'cup', 'plate', 'knife', 'fork', 'spoon',
            # Days of the week (CRITICAL: These are complete words, never split)
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
            # Months
            'january', 'february', 'march', 'april', 'may', 'june', 'july', 
            'august', 'september', 'october', 'november', 'december',
            # Common multi-character words that should never be split
            'today', 'tomorrow', 'yesterday', 'week', 'month', 'year', 'hour', 'minute', 'second',
            'people', 'person', 'child', 'children', 'man', 'woman', 'boy', 'girl', 'baby',
            'color', 'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink', 'black', 'white',
            'number', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
            'big', 'small', 'good', 'bad', 'happy', 'sad', 'angry', 'tired', 'hungry', 'thirsty',
            'hot', 'cold', 'warm', 'cool', 'new', 'old', 'young', 'fast', 'slow', 'easy', 'hard',
            # Grammar words
            'name', 'is', 'am', 'are', 'was', 'were', 'have', 'has', 'had', 'will', 'can', 'should',
            'a', 'an', 'the', 'to', 'in', 'on', 'at', 'for', 'with', 'by', 'from', 'of', 'and', 'or', 'but'
        }
        
        # First, split by existing spaces
        words = text.strip().split()
        result_words = []
        
        # If no spaces in original text, check if it's letters+word or just letters
        if ' ' not in text.strip():
            text_no_spaces = text.strip()
            if len(text_no_spaces) > 1:
                # First try to separate letters from words
                separated_no_spaces = self._separate_letters_from_word_boundary(text_no_spaces, common_words)
                if len(separated_no_spaces) > 1:
                    # Found letters+word pattern - return separated
                    return ' '.join(separated_no_spaces)
                # If no word found, check if it's a letter sequence
                elif self._is_letter_sequence(text_no_spaces, common_words):
                    # It's a sequence of letters - separate them
                    separated_letters = ' '.join(list(text_no_spaces.upper()))
                    return separated_letters
        
        # Process each word/token that was split by spaces
        for word in words:
            word_lower = word.lower()
            
            # PRIORITY 1: If word is already a known word, keep it completely as-is (DON'T MODIFY)
            if word_lower in common_words:
                result_words.append(word)
                continue
            
            # PRIORITY 1.5: CRITICAL - Words with 4+ characters are ALWAYS kept complete
            # Words detected with 2 hands are typically 4+ characters and should NEVER be split
            # This prevents words like "SUNDAY", "MONDAY", "HELLO", etc. from being split
            if len(word) >= 4:
                # Check if it's a known word first
                if word_lower in common_words:
                    result_words.append(word)
                    continue
                # Even if not in common_words, keep 4+ character words complete
                # Only check for trailing letters if the base word is known
                letter_separated = self._separate_trailing_letters(word, common_words)
                if len(letter_separated) == 1:
                    # No separation - keep word COMPLETE (this is a word, not letters)
                    result_words.append(word)
                else:
                    # Trailing letters were separated (e.g., "SUNDAYA" -> "SUNDAY" + "A")
                    result_words.extend(letter_separated)
                continue
            
            # PRIORITY 2: Check if this contains letters followed by a word (e.g., "ABCHELLO")
            # This happens when letters are detected first, then a word is added without space
            separated = self._separate_letters_from_word_boundary(word, common_words)
            if len(separated) > 1:
                # Letters and word were separated
                result_words.extend(separated)
                continue
            
            # PRIORITY 3: For words 3 characters long, be conservative
            # Check for trailing letters only if base is a known word
            if len(word) == 3:
                letter_separated = self._separate_trailing_letters(word, common_words)
                if len(letter_separated) > 1:
                    # Trailing letters were separated
                    result_words.extend(letter_separated)
                else:
                    # No separation - keep word COMPLETE
                    result_words.append(word)
                continue
            
            # PRIORITY 4: Check if this is a short sequence of single letters (e.g., "AB", "ABC")
            # Only for very short sequences (2-3 chars) that are clearly not words
            if self._is_letter_sequence(word, common_words):
                # Separate each letter with spaces (e.g., "AB" -> "A B")
                separated_letters = ' '.join(list(word.upper()))
                result_words.extend(separated_letters.split())
                continue
            
            # PRIORITY 5: For short words (1-3 chars), be conservative
            # First check if it's a known word - if so, keep it complete
            if word_lower in common_words:
                result_words.append(word)
                continue
            
            # Check if it's a short letter sequence (2-3 chars, not a word)
            if self._is_letter_sequence(word, common_words):
                # Separate consecutive letters (e.g., "AB" -> "A B")
                separated_letters = ' '.join(list(word.upper()))
                result_words.extend(separated_letters.split())
            else:
                # Might have trailing letter, but for short words, be conservative
                # Only separate if it's clearly a trailing letter on a known base
                letter_separated = self._separate_trailing_letters(word, common_words)
                if len(letter_separated) == 1:
                    # No separation - keep as is (treat as word)
                    result_words.append(word)
                else:
                    # Trailing letter was separated
                    result_words.extend(letter_separated)
        
        # Ensure all words are separated by spaces
        return ' '.join(result_words)
    
    def _separate_letters_from_word_boundary(self, text: str, common_words: set) -> list:
        """
        Separate letters from words when letters come before a word.
        This handles cases where letters are detected first (without spaces), then a word is added.
        
        Example: "ABCHELLO" -> ["A", "B", "C", "HELLO"]
                 "XYZWORLD" -> ["X", "Y", "Z", "WORLD"]
                 "ABHELLO" -> ["A", "B", "HELLO"]
                 "AHELLO" -> ["A", "HELLO"]
        
        Returns list of separated parts, or [text] if no separation needed.
        """
        if not text or len(text) < 2:
            return [text]
        
        text_lower = text.lower()
        text_upper = text.upper()
        
        # Try to find a known word at the end of the text
        # Check from longest to shortest words for better matching
        sorted_words = sorted(common_words, key=len, reverse=True)
        
        for known_word in sorted_words:
            if len(known_word) < 2:  # Skip very short words (but allow 2-letter words like "go", "no")
                continue
            
            # Check if text ends with this known word (case-insensitive)
            if text_lower.endswith(known_word):
                # Found a word at the end - check if there are letters before it
                prefix = text[:-len(known_word)]
                
                if len(prefix) > 0:
                    # Check if prefix consists of single uppercase letters
                    # This indicates letters were concatenated together
                    prefix_clean = prefix.replace(' ', '')  # Remove any spaces
                    if prefix_clean and all(c.isalpha() and c.isupper() for c in prefix_clean):
                        # Prefix is all uppercase letters - separate each letter
                        letters = list(prefix_clean.upper())
                        # Return separated letters and the word (keep original word case)
                        word_part = text[-len(known_word):]
                        result = letters + [word_part]
                        return result
        
        # Also check for pattern: letters + word where word starts at any position
        # This handles cases where word might be in the middle
        for known_word in sorted_words:
            if len(known_word) < 3:
                continue
            
            # Find word in the text (not just at the end) - case insensitive
            word_start_idx = text_lower.find(known_word)
            if word_start_idx > 0:
                # Found word somewhere in the text
                prefix = text[:word_start_idx]
                suffix = text[word_start_idx + len(known_word):]
                
                # Check if prefix is letters (after removing spaces)
                prefix_clean = prefix.replace(' ', '')
                if prefix_clean and all(c.isalpha() and c.isupper() for c in prefix_clean):
                    # Separate prefix letters
                    letters = list(prefix_clean.upper())
                    # Get the word part (preserve original case)
                    word_part = text[word_start_idx:word_start_idx + len(known_word)]
                    result = letters + [word_part]
                    
                    # Handle suffix if it exists
                    if suffix:
                        suffix_clean = suffix.replace(' ', '')
                        if suffix_clean and all(c.isalpha() and c.isupper() for c in suffix_clean):
                            # Suffix is also letters - separate them
                            result.extend(list(suffix_clean.upper()))
                        else:
                            # Suffix might be another word or mixed - add as is
                            result.append(suffix)
                    return result
        
        # No word found, or no letter prefix found
        return [text]
    
    def _is_letter_sequence(self, text: str, common_words: set = None) -> bool:
        """
        Check if text is a sequence of single letters (e.g., "AB", "ABC", "XYZ").
        Returns True ONLY if:
        - It's 2-3 characters long (typical letter sequences)
        - All characters are single uppercase letters
        - It's NOT a known word
        - It doesn't contain any known word substring
        
        CRITICAL: We are VERY conservative - only treat as letters if it's clearly
        a short sequence (2-3 chars) and definitely not a word.
        Words detected with 2 hands (4+ characters) should NEVER be split - they are always kept complete.
        """
        if not text or len(text) < 2:
            return False
        
        # Must be all uppercase letters
        if not all(c.isalpha() and c.isupper() for c in text):
            return False
        
        # NEVER treat known words as letter sequences
        if common_words and text.lower() in common_words:
            return False
        
        # CRITICAL: Words 4+ characters are NEVER letter sequences
        # Words detected with 2 hands are typically 4+ characters (e.g., "SUNDAY", "MONDAY", "HELLO")
        # These are complete words and must be kept intact
        if len(text) >= 4:
            # Longer sequences are words, not letters - keep them complete
            return False
        
        # Only for 2-3 character sequences, check if they're letter sequences
        if 2 <= len(text) <= 3:
            # Check if it matches any known word (even short ones like "go", "to", "me")
            if common_words:
                text_lower = text.lower()
                # Check exact match - if it's a known word, it's NOT a letter sequence
                if text_lower in common_words:
                    return False
                # Check if any substring is a known word - if so, probably not just letters
                for word in common_words:
                    if len(word) >= 2 and word in text_lower:
                        return False
            
            # Only 2-3 character sequences that are clearly not words can be letter sequences
            # This allows "AB", "ABC", "XYZ" to be separated, but keeps longer words intact
            return True
        
        # Default: not a letter sequence
        return False
    
    def _merge_letters_into_words(self, text: str) -> str:
        """
        Merge separated letters back into complete words if they form a known word.
        
        This handles cases where a word like "SUNDAY" was incorrectly split into "S U N D A Y".
        We check if consecutive single-letter tokens form a known word and merge them.
        
        Example:
            "S U N D A Y" -> "SUNDAY" (if "sunday" is in common_words)
            "H E L L O" -> "HELLO" (if "hello" is in common_words)
            "A B C" -> "A B C" (if "abc" is not a known word, keep separated)
        
        CRITICAL: This ensures complete words are preserved even if they were split earlier.
        """
        if not text or len(text.strip()) <= 1:
            return text
        
        # Get common words for checking
        common_words = {
            # Days of the week
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
            # Common words
            'hello', 'hi', 'hey', 'good', 'morning', 'afternoon', 'evening', 'night', 'day',
            'thank', 'thanks', 'you', 'please', 'sorry', 'excuse', 'welcome',
            'yes', 'no', 'ok', 'okay', 'sure', 'maybe',
            'i', 'me', 'my', 'you', 'your', 'we', 'us', 'they', 'them', 'he', 'she', 'it',
            'go', 'come', 'want', 'need', 'like', 'love', 'see', 'know', 'think', 'say', 'tell',
            'do', 'make', 'get', 'take', 'give', 'help', 'work', 'play', 'eat', 'drink', 'sleep',
            'water', 'food', 'home', 'house', 'school', 'work', 'book', 'car', 'friend', 'family',
            'mother', 'father', 'mom', 'dad', 'sister', 'brother', 'teacher', 'student', 'doctor',
            'hospital', 'restaurant', 'park', 'beach', 'city', 'country', 'world',
            'time', 'day', 'night', 'morning', 'afternoon', 'evening',
            'apple', 'banana', 'bread', 'milk', 'coffee', 'tea',
            'store', 'shop', 'market', 'place', 'room', 'door', 'window', 'table', 'chair',
            'phone', 'computer', 'tv', 'radio', 'music', 'song', 'movie', 'game',
            'money', 'dollar', 'penny', 'bag', 'box', 'cup', 'plate', 'knife', 'fork', 'spoon',
            'today', 'tomorrow', 'yesterday', 'week', 'month', 'year', 'hour', 'minute', 'second',
            'people', 'person', 'child', 'children', 'man', 'woman', 'boy', 'girl', 'baby',
            'color', 'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink', 'black', 'white',
            'number', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
            'big', 'small', 'good', 'bad', 'happy', 'sad', 'angry', 'tired', 'hungry', 'thirsty',
            'hot', 'cold', 'warm', 'cool', 'new', 'old', 'young', 'fast', 'slow', 'easy', 'hard',
            'name', 'is', 'am', 'are', 'was', 'were', 'have', 'has', 'had', 'will', 'can', 'should',
            'a', 'an', 'the', 'to', 'in', 'on', 'at', 'for', 'with', 'by', 'from', 'of', 'and', 'or', 'but'
        }
        
        # Split text into tokens
        tokens = text.strip().split()
        if len(tokens) < 2:
            return text
        
        result_tokens = []
        i = 0
        
        while i < len(tokens):
            token = tokens[i]
            
            # Check if current token is a single letter (uppercase, length 1)
            if len(token) == 1 and token.isalpha() and token.isupper():
                # Try to find a sequence of consecutive letters that form a known word
                # Check sequences from longest possible (all remaining tokens) down to 2 letters
                max_length = min(len(tokens) - i, 10)  # Check up to 10 consecutive letters
                merged = False
                
                # Try merging from longest to shortest sequence
                for length in range(max_length, 1, -1):
                    if i + length > len(tokens):
                        continue
                    
                    # Get sequence of tokens
                    sequence = tokens[i:i+length]
                    
                    # Check if all are single uppercase letters
                    if all(len(t) == 1 and t.isalpha() and t.isupper() for t in sequence):
                        # Form word from sequence
                        potential_word = ''.join(sequence).lower()
                        
                        # Check if it's a known word
                        if potential_word in common_words:
                            # Found a known word! Merge the letters
                            result_tokens.append(''.join(sequence).upper())
                            i += length
                            merged = True
                            break
                
                if not merged:
                    # No word found - keep the letter separate
                    result_tokens.append(token)
                    i += 1
            else:
                # Not a single letter - keep as is
                result_tokens.append(token)
                i += 1
        
        return ' '.join(result_tokens)
    
    def _separate_concatenated_words(self, word: str, common_words: set) -> list:
        """
        Separate concatenated words (words stuck together without spaces).
        Example: "HELLOWORLD" -> ["HELLO", "WORLD"]
                 "GOODMORNING" -> ["GOOD", "MORNING"]
                 "HELLO" -> ["HELLO"] (single word, no separation needed)
        """
        word_lower = word.lower()
        
        # If it's already a known word, return as-is
        if word_lower in common_words:
            return [word]
        
        # Try to find word boundaries by checking for known words
        # Check from longest to shortest words for better matching
        sorted_words = sorted(common_words, key=len, reverse=True)
        
        result = []
        remaining = word_lower
        original_remaining = word
        
        while remaining:
            found_match = False
            
            # Try to match longest possible word at the start
            for common_word in sorted_words:
                if len(common_word) < 3:  # Skip very short words (a, an, etc.) to avoid false matches
                    continue
                    
                if remaining.startswith(common_word):
                    # Found a match - extract it
                    result.append(original_remaining[:len(common_word)])
                    remaining = remaining[len(common_word):]
                    original_remaining = original_remaining[len(common_word):]
                    found_match = True
                    break
            
            if not found_match:
                # No word match found - check if we have partial result
                if result:
                    # Add remaining as-is (might be a letter or unknown word)
                    if remaining:
                        result.append(original_remaining)
                    break
                else:
                    # No words found at all - return original word
                    return [word]
        
        return result if result else [word]
    
    def _separate_trailing_letters(self, word: str, common_words: set) -> list:
        """
        Separate trailing letters from a word recursively.
        Returns a list of words/letters.
        
        CRITICAL: For words 4+ characters, be VERY conservative - only separate if base is a known word.
        Words like "SUNDAY", "MONDAY" should NEVER be split.
        
        Example: "HELLOAB" -> ["HELLO", "A", "B"]
                 "HELLOA" -> ["HELLO", "A"]
                 "HELLO" -> ["HELLO"]
                 "SUNDAY" -> ["SUNDAY"] (never split - complete word)
                 "SUNDAYA" -> ["SUNDAY", "A"] (only if "SUNDAY" is known word)
        """
        word_lower = word.lower()
        
        # Base case: if it's a known word, return as-is (keep complete)
        if word_lower in common_words:
            return [word]
        
        # Base case: single character, return as-is
        if len(word) <= 1:
            return [word]
        
        # CRITICAL: For words 4+ characters, be VERY conservative
        # Only separate trailing letters if the base word (without last char) is a known word
        # This prevents splitting complete words like "SUNDAY", "MONDAY", etc.
        if len(word) >= 4:
            base_word = word[:-1].lower()
            last_char = word[-1].upper()
            
            # Only separate if base is a known word
            if base_word in common_words:
                # Base is a known word - separate the trailing letter
                base_result = self._separate_trailing_letters(word[:-1], common_words)
                base_result.append(last_char)
                return base_result
            else:
                # Base is not a known word - keep the entire word complete
                # This prevents splitting words like "SUNDAY" into "SUNDA" + "Y"
                return [word]
        
        # For shorter words (2-3 chars), try to separate trailing letters
        # Only if word ends with a letter and has at least 2 characters before it
        if len(word) > 2 and word[-1].isalpha() and word[-2].isalpha():
            base_word = word[:-1].lower()
            last_char = word[-1].upper()
            
            # If base is a known word, separate the last letter
            if base_word in common_words:
                base_result = self._separate_trailing_letters(word[:-1], common_words)
                base_result.append(last_char)
                return base_result
            else:
                # Base is not a known word, try to separate from the base
                base_result = self._separate_trailing_letters(word[:-1], common_words)
                if len(base_result) > 1 or (len(base_result) == 1 and base_result[0] != word[:-1]):
                    base_result.append(last_char)
                    return base_result
        
        # Can't separate further, return as-is
        return [word]
    
    
    def _is_noun(self, word: str) -> bool:
        """Simple check if word is likely a noun"""
        # Common nouns (you can expand this)
        common_nouns = {
            'water', 'food', 'store', 'home', 'school', 'work', 'book',
            'car', 'house', 'friend', 'family', 'mother', 'father',
            'sister', 'brother', 'teacher', 'student', 'doctor', 'hospital',
            'restaurant', 'park', 'beach', 'city', 'country', 'world',
            'time', 'day', 'night', 'morning', 'afternoon', 'evening',
            'apple', 'banana', 'bread', 'milk', 'coffee', 'tea'
        }
        
        # If it's a common noun, article, or preposition, it's not a verb
        if word.lower() in common_nouns:
            return True
        
        # If it's not a verb indicator, assume it might be a noun
        if word.lower() not in self.verbs_need_to and word.lower() not in self.verbs_need_article:
            # Simple heuristic: if word is longer than 3 chars and not a pronoun, might be noun
            if len(word) > 3 and word.lower() not in ['i', 'you', 'he', 'she', 'we', 'they', 'it']:
                return True
        
        return False
    
    def _capitalize_sentence(self, text: str) -> str:
        """Capitalize first letter and proper nouns"""
        if not text:
            return text
        
        # Capitalize first letter
        text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
        
        # Capitalize "I" when standalone
        text = re.sub(r'\bi\b', 'I', text)
        
        # Capitalize common proper nouns (you can expand this)
        proper_nouns = {
            'yara', 'john', 'mary', 'mike', 'sarah', 'david', 'lisa',
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
            'saturday', 'sunday', 'january', 'february', 'march',
            'april', 'may', 'june', 'july', 'august', 'september',
            'october', 'november', 'december'
        }
        
        words = text.split()
        result = []
        for word in words:
            if word.lower() in proper_nouns:
                result.append(word.capitalize())
            else:
                result.append(word)
        
        return ' '.join(result)
    
    def _add_punctuation(self, text: str) -> str:
        """Add punctuation if missing"""
        if not text:
            return text
        
        # Remove trailing punctuation first
        text = text.rstrip('.,!?')
        
        # Add period if it's a statement (doesn't end with ? or !)
        if not text.endswith(('?', '!')):
            # Check if it's a question word
            question_words = {'what', 'where', 'when', 'who', 'why', 'how', 'which'}
            first_word = text.split()[0].lower() if text.split() else ''
            
            if first_word in question_words:
                text += '?'
            else:
                text += '.'
        
        return text
    
    def process_word_sequence(self, words: List[str]) -> str:
        """Process a sequence of words (for real-time translation)"""
        text = ' '.join(words)
        return self.process(text)


# Global instance
nlp_processor = SignLanguageNLP()

def improve_translation(text: str, is_sentence: bool = True) -> str:
    """
    Main function to improve translated text
    
    Args:
        text: Input text to improve
        is_sentence: If True, treats as full sentence. If False, single word.
    
    Usage: 
        improved_text = improve_translation("I go store")  # Full sentence
        improved_text = improve_translation("hello", is_sentence=False)  # Single word
    
    Returns: 
        "I go to the store." (for sentences)
        "Hello" (for single words)
    """
    return nlp_processor.process(text, is_sentence=is_sentence)

