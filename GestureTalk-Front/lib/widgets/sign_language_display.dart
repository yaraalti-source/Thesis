import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:video_player/video_player.dart';
import 'dart:convert';
import 'dart:io';

/// Vocabulary manager for loading and accessing sign language words
class VocabularyManager {
  static VocabularyManager? _instance;
  Map<String, dynamic>? _vocabulary;
  bool _isLoading = false;
  bool _isLoaded = false;

  VocabularyManager._();

  static VocabularyManager get instance {
    _instance ??= VocabularyManager._();
    return _instance!;
  }

  /// Load vocabulary from JSON asset
  Future<void> loadVocabulary() async {
    if (_isLoaded || _isLoading) return;
    
    _isLoading = true;
    try {
      final String jsonString = await rootBundle.loadString('assets/config/vocabulary.json');
      final Map<String, dynamic> data = json.decode(jsonString);
      _vocabulary = data['words'] as Map<String, dynamic>?;
      _isLoaded = true;
      print('Vocabulary loaded: ${_vocabulary?.length ?? 0} words');
    } catch (e) {
      print('Error loading vocabulary: $e');
      // Fallback to empty vocabulary
      _vocabulary = {};
    } finally {
      _isLoading = false;
    }
  }

  /// Check if a word exists in vocabulary
  bool hasWord(String word) {
    if (_vocabulary == null) return false;
    return _vocabulary!.containsKey(word.toLowerCase());
  }

  /// Get word information from vocabulary
  Map<String, dynamic>? getWordInfo(String word) {
    if (_vocabulary == null) return null;
    return _vocabulary![word.toLowerCase()] as Map<String, dynamic>?;
  }

  /// Get all words in vocabulary
  Set<String> getAllWords() {
    if (_vocabulary == null) return {};
    return _vocabulary!.keys.toSet();
  }
}

/// Displays sign language images/videos for text-to-sign translation
class SignLanguageDisplay extends StatefulWidget {
  final String text;

  const SignLanguageDisplay({Key? key, required this.text}) : super(key: key);

  @override
  _SignLanguageDisplayState createState() => _SignLanguageDisplayState();
}

class _SignLanguageDisplayState extends State<SignLanguageDisplay> {
  List<SignItem> _signs = [];
  bool _vocabularyLoaded = false;

  @override
  void initState() {
    super.initState();
    _loadVocabularyAndParse();
  }

  Future<void> _loadVocabularyAndParse() async {
    await VocabularyManager.instance.loadVocabulary();
    if (mounted) {
      setState(() {
        _vocabularyLoaded = true;
      });
      _parseTextToSigns();
    }
  }

  @override
  void didUpdateWidget(SignLanguageDisplay oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.text != widget.text) {
      _parseTextToSigns();
    }
  }

  void _parseTextToSigns() {
    if (widget.text.isEmpty) {
      setState(() => _signs = []);
      return;
    }

    List<SignItem> signs = [];
    List<String> words = widget.text.toLowerCase().trim().split(' ');

    for (String word in words) {
      if (word.isEmpty) continue;

      // Remove punctuation
      word = word.replaceAll(RegExp(r'[^\w]'), '');

      // Check if it's a single letter or short acronym (2-3 letters all caps)
      if (word.length == 1) {
        // Single letter - show as letter card
        signs.add(SignItem(
          label: word.toUpperCase(),
          path: 'assets/signs/letters/${word.toUpperCase()}.png',
          type: SignType.letter,
        ));
      } else if (word.length <= 3 && word == word.toUpperCase()) {
        // Short acronym (like USA, FBI) - spell out each letter
        for (var char in word.split('')) {
          if (RegExp(r'[a-zA-Z]').hasMatch(char)) {
            signs.add(SignItem(
              label: char.toUpperCase(),
              path: 'assets/signs/letters/${char.toUpperCase()}.png',
              type: SignType.letter,
            ));
          }
        }
      } else if (_isCommonWord(word)) {
        // Known word - show as word card
        final wordInfo = VocabularyManager.instance.getWordInfo(word);
        final fileSafeName = wordInfo?['fileSafeName'] ?? word.replaceAll(' ', '_');
        final videoPath = wordInfo?['videoPath'] ?? 'assets/signs/words/$fileSafeName.mp4';
        
        signs.add(SignItem(
          label: word.toUpperCase(),
          path: videoPath,
          type: SignType.word,
        ));
      } else if (_shouldSpellOut(word)) {
        // Name or special word - spell out each letter
        for (var char in word.split('')) {
          if (RegExp(r'[a-zA-Z]').hasMatch(char)) {
            signs.add(SignItem(
              label: char.toUpperCase(),
              path: 'assets/signs/letters/${char.toUpperCase()}.png',
              type: SignType.letter,
            ));
          }
        }
      } else {
        // Unknown word - show as unknown word card
        signs.add(SignItem(
          label: word.toUpperCase(),
          path: '',
          type: SignType.unknown,
        ));
      }
    }

    setState(() => _signs = signs);
  }

  bool _shouldSpellOut(String word) {
    // Spell out if:
    // 1. First letter is uppercase (likely a name)
    // 2. Word contains numbers
    // 3. Word is very short (1-2 letters)
    return word.length <= 2 || 
           RegExp(r'[0-9]').hasMatch(word) ||
           (word.isNotEmpty && word[0] == word[0].toUpperCase());
  }

  bool _isCommonWord(String word) {
    // Check if word exists in WLASL vocabulary
    final vocab = VocabularyManager.instance;
    if (vocab.hasWord(word)) {
      return true;
    }
    
    // Also check common variations and aliases
    final wordLower = word.toLowerCase();
    
    // Handle common word variations
    final variations = {
      'hi': 'hello',
      'bye': 'goodbye',
      'thanks': 'thank you',
      'thank': 'thank you',
      'okay': 'ok',
      'mum': 'mom',
      'dad': 'father',
    };
    
    if (variations.containsKey(wordLower)) {
      return vocab.hasWord(variations[wordLower]!);
    }
    
    return false;
  }

  @override
  Widget build(BuildContext context) {
    if (!_vocabularyLoaded) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text(
              'Loading vocabulary...',
              style: TextStyle(color: Colors.grey, fontSize: 16),
            ),
          ],
        ),
      );
    }
    
    if (_signs.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.sign_language, size: 80, color: Colors.grey),
            SizedBox(height: 16),
            Text(
              'Speak to see sign language',
              style: TextStyle(color: Colors.grey, fontSize: 16),
            ),
          ],
        ),
      );
    }

    return GridView.builder(
      shrinkWrap: true,
      physics: NeverScrollableScrollPhysics(),
      padding: EdgeInsets.all(8),
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
        childAspectRatio: 0.9,
      ),
      itemCount: _signs.length,
      itemBuilder: (context, index) {
        return _buildSignCard(_signs[index]);
      },
    );
  }

  Widget _buildSignCard(SignItem sign) {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Sign media (image or video placeholder)
          Expanded(
            flex: 3,
            child: Padding(
              padding: EdgeInsets.all(8),
              child: _buildSignMedia(sign),
            ),
          ),
          
          // Label
          Container(
            padding: EdgeInsets.symmetric(vertical: 8, horizontal: 4),
            decoration: BoxDecoration(
              color: sign.type == SignType.word 
                  ? Colors.purple.withOpacity(0.1)
                  : sign.type == SignType.letter
                      ? Colors.blue.withOpacity(0.1)
                      : sign.type == SignType.unknown
                          ? Colors.grey.withOpacity(0.1)
                          : Colors.blue.withOpacity(0.1),
              borderRadius: BorderRadius.only(
                bottomLeft: Radius.circular(12),
                bottomRight: Radius.circular(12),
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              mainAxisSize: MainAxisSize.min,
              children: [
                if (sign.type == SignType.word)
                  Icon(Icons.waving_hand, size: 14, color: Colors.purple),
                if (sign.type == SignType.letter)
                  Icon(Icons.text_fields, size: 14, color: Colors.blue),
                if (sign.type == SignType.unknown)
                  Icon(Icons.help_outline, size: 14, color: Colors.grey),
                SizedBox(width: 4),
                Flexible(
                  child: Text(
                    sign.label,
                    style: TextStyle(
                      fontSize: sign.type == SignType.letter ? 18 : 14,
                      fontWeight: FontWeight.bold,
                      color: sign.type == SignType.word 
                          ? Colors.purple 
                          : sign.type == SignType.letter
                              ? Colors.blue
                              : sign.type == SignType.unknown
                                  ? Colors.grey
                                  : Colors.blue,
                    ),
                    textAlign: TextAlign.center,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSignMedia(SignItem sign) {
    switch (sign.type) {
      case SignType.letter:
        // Letter card - show image or placeholder
        return Image.asset(
          sign.path,
          fit: BoxFit.contain,
          errorBuilder: (context, error, stackTrace) {
            // Fallback: Show letter with blue background
            return Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [Colors.blue.shade300, Colors.blue.shade600],
                ),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Center(
                child: Text(
                  sign.label,
                  style: TextStyle(
                    fontSize: 60,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
              ),
            );
          },
        );

      case SignType.word:
        // Word sign - try video first, then image, then unique placeholder
        // Use the path from vocabulary (includes correct file-safe name)
        final wordPath = sign.path;
        
        // Try to show video if it's an MP4 file
        if (wordPath.endsWith('.mp4')) {
          return _buildVideoPlayer(wordPath, sign.label);
        }
        
        // Try PNG image first
        final imagePath = wordPath.replaceAll('.mp4', '.png');
        return Image.asset(
          imagePath,
          fit: BoxFit.contain,
          errorBuilder: (context, error, stackTrace) {
            // If image fails, try the original path as image
            if (imagePath != wordPath) {
              return Image.asset(
                wordPath,
                fit: BoxFit.contain,
                errorBuilder: (context, error2, stackTrace2) {
                  // Final fallback: Show unique word placeholder
                  return _buildWordPlaceholder(sign.label);
                },
              );
            }
            // Final fallback: Show unique word placeholder
            return _buildWordPlaceholder(sign.label);
          },
        );

      case SignType.unknown:
        // Unknown word - show with question mark
        return Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Colors.grey.shade600, Colors.grey.shade800],
            ),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.help_outline, size: 50, color: Colors.white),
              SizedBox(height: 12),
              Padding(
                padding: EdgeInsets.symmetric(horizontal: 8),
                child: Text(
                  sign.label,
                  style: TextStyle(
                    color: Colors.white, 
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              SizedBox(height: 8),
              Text(
                'Not in vocabulary',
                style: TextStyle(
                  color: Colors.white70, 
                  fontSize: 10,
                ),
              ),
            ],
          ),
        );

      default:
        return Icon(Icons.help_outline, size: 50);
    }
  }

  /// Build video player widget for sign videos
  Widget _buildVideoPlayer(String videoPath, String label) {
    return _SignVideoPlayer(
      videoPath: videoPath,
      label: label,
    );
  }

  /// Build unique word placeholder with word-specific styling
  Widget _buildWordPlaceholder(String label, {bool showPlayIcon = false}) {
    // Create a unique color based on word label (deterministic)
    final hash = label.hashCode;
    final hue = (hash.abs() % 360).toDouble();
    final color1 = HSLColor.fromAHSL(1.0, hue, 0.5, 0.6).toColor();
    final color2 = HSLColor.fromAHSL(1.0, (hue + 30) % 360, 0.5, 0.4).toColor();
    
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [color1, color2],
        ),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Show play icon if video should be there, otherwise sign language icon
          Icon(
            showPlayIcon ? Icons.play_circle_outline : Icons.sign_language,
            size: showPlayIcon ? 50 : 40,
            color: Colors.white,
          ),
          SizedBox(height: 8),
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 6),
            child: Text(
              label,
              style: TextStyle(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          SizedBox(height: 4),
          Text(
            showPlayIcon ? 'Video Available' : 'Sign Word',
            style: TextStyle(
              color: Colors.white70,
              fontSize: 10,
            ),
          ),
        ],
      ),
    );
  }
}

class SignItem {
  final String label;
  final String path;
  final SignType type;

  SignItem({
    required this.label,
    required this.path,
    required this.type,
  });
}

enum SignType { letter, word, unknown }

/// Video player widget for sign language videos
class _SignVideoPlayer extends StatefulWidget {
  final String videoPath;
  final String label;

  const _SignVideoPlayer({
    required this.videoPath,
    required this.label,
  });

  @override
  _SignVideoPlayerState createState() => _SignVideoPlayerState();
}

class _SignVideoPlayerState extends State<_SignVideoPlayer> {
  VideoPlayerController? _controller;
  bool _isInitialized = false;
  bool _hasError = false;

  @override
  void initState() {
    super.initState();
    _initializeVideo();
  }

  Future<void> _initializeVideo() async {
    try {
      // Try to load as asset video
      _controller = VideoPlayerController.asset(widget.videoPath);
      await _controller!.initialize();
      
      if (mounted) {
        setState(() {
          _isInitialized = true;
        });
        // Auto-play the video once
        _controller!.play();
        // Loop the video
        _controller!.setLooping(true);
      }
    } catch (e) {
      // Video asset not found or can't be loaded
      if (mounted) {
        setState(() {
          _hasError = true;
        });
      }
      _controller?.dispose();
      _controller = null;
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_hasError || _controller == null || !_isInitialized) {
      // Show unique placeholder with play icon indicating video should be there
      return _buildUniquePlaceholder(widget.label, showPlayIcon: true);
    }

    // Show video player
    return GestureDetector(
      onTap: () {
        if (_controller!.value.isPlaying) {
          _controller!.pause();
        } else {
          _controller!.play();
        }
      },
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          color: Colors.black,
        ),
        child: AspectRatio(
          aspectRatio: _controller!.value.aspectRatio,
          child: VideoPlayer(_controller!),
        ),
      ),
    );
  }

  Widget _buildUniquePlaceholder(String label, {bool showPlayIcon = false}) {
    // Create a unique color based on word label (deterministic)
    final hash = label.hashCode;
    final hue = (hash.abs() % 360).toDouble();
    final color1 = HSLColor.fromAHSL(1.0, hue, 0.5, 0.6).toColor();
    final color2 = HSLColor.fromAHSL(1.0, (hue + 30) % 360, 0.5, 0.4).toColor();
    
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [color1, color2],
        ),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            showPlayIcon ? Icons.play_circle_outline : Icons.sign_language,
            size: showPlayIcon ? 50 : 40,
            color: Colors.white,
          ),
          SizedBox(height: 8),
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 6),
            child: Text(
              label,
              style: TextStyle(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          SizedBox(height: 4),
          Text(
            showPlayIcon ? 'Add Video' : 'Sign Word',
            style: TextStyle(
              color: Colors.white70,
              fontSize: 10,
            ),
          ),
        ],
      ),
    );
  }
}

