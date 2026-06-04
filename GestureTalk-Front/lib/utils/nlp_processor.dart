/// NLP Processor for Sign Language Translation
/// Improves grammar and sentence structure in Flutter

class NLPProcessor {
  /// Improve translation text with grammar correction
  static String improveTranslation(String text) {
    if (text.isEmpty) return text;

    // Clean text
    text = text.trim().replaceAll(RegExp(r'\s+'), ' ');
    
    List<String> words = text.split(' ');
    if (words.isEmpty) return text;

    // Add articles and prepositions
    words = _addArticles(words);
    words = _addPrepositions(words);
    words = _fixCommonPatterns(words);

    // Join and format
    String result = words.join(' ');
    result = _capitalizeSentence(result);
    result = _addPunctuation(result);

    return result;
  }

  static List<String> _addArticles(List<String> words) {
    List<String> result = [];
    final verbsNeedArticle = {
      'want', 'need', 'have', 'get', 'buy', 'find', 'see', 'eat', 'drink'
    };
    final articles = {'a', 'an', 'the'};

    for (int i = 0; i < words.length; i++) {
      result.add(words[i]);
      
      if (i < words.length - 1) {
        String word = words[i].toLowerCase();
        String nextWord = words[i + 1].toLowerCase();
        
        // Add article after verbs
        if (verbsNeedArticle.contains(word) && 
            !articles.contains(nextWord) &&
            _isLikelyNoun(nextWord)) {
          result.add('a');
        }
      }
    }
    
    return result;
  }

  static List<String> _addPrepositions(List<String> words) {
    List<String> result = [];
    final verbsNeedTo = {'go', 'want', 'need', 'like', 'try'};
    final prepositions = {'to', 'in', 'on', 'at', 'for'};

    for (int i = 0; i < words.length; i++) {
      result.add(words[i]);
      
      if (i < words.length - 1) {
        String word = words[i].toLowerCase();
        String nextWord = words[i + 1].toLowerCase();
        
        // Add "to" after certain verbs
        if (verbsNeedTo.contains(word) && 
            !prepositions.contains(nextWord) &&
            _isLikelyNoun(nextWord)) {
          result.add('to');
        }
      }
    }
    
    return result;
  }

  static List<String> _fixCommonPatterns(List<String> words) {
    List<String> result = [];
    
    for (int i = 0; i < words.length; i++) {
      String word = words[i].toLowerCase();
      
      // "I name yara" → "My name is yara"
      if (word == 'name' && i > 0) {
        String prev = words[i - 1].toLowerCase();
        if (prev == 'i') {
          result[result.length - 1] = 'My';
          result.add('name');
          if (i < words.length - 1 && words[i + 1].toLowerCase() != 'is') {
            result.add('is');
          }
          continue;
        }
      }
      
      result.add(words[i]);
    }
    
    return result;
  }

  static bool _isLikelyNoun(String word) {
    final commonNouns = {
      'water', 'food', 'store', 'home', 'school', 'work', 'book',
      'car', 'house', 'friend', 'family', 'apple', 'banana'
    };
    
    if (commonNouns.contains(word)) return true;
    if (word.length > 3) return true; // Simple heuristic
    return false;
  }

  static String _capitalizeSentence(String text) {
    if (text.isEmpty) return text;
    
    // Capitalize first letter
    text = text[0].toUpperCase() + text.substring(1);
    
    // Capitalize "I"
    text = text.replaceAll(RegExp(r'\bi\b'), 'I');
    
    return text;
  }

  static String _addPunctuation(String text) {
    if (text.isEmpty) return text;
    
    // Remove trailing punctuation
    text = text.replaceAll(RegExp(r'[.,!?]+$'), '');
    
    // Check if question
    final questionWords = {'what', 'where', 'when', 'who', 'why', 'how'};
    final firstWord = text.split(' ').isNotEmpty 
        ? text.split(' ')[0].toLowerCase() 
        : '';
    
    if (questionWords.contains(firstWord)) {
      text += '?';
    } else {
      text += '.';
    }
    
    return text;
  }
}

