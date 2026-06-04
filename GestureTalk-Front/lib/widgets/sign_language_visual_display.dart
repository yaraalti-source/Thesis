import 'package:flutter/material.dart';
import 'package:gesture_talk/theme/app_theme.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter_dotenv/flutter_dotenv.dart';

class SignLanguageVisualDisplay extends StatefulWidget {
  final String text;
  final String? baseUrl;

  const SignLanguageVisualDisplay({
    super.key,
    required this.text,
    this.baseUrl,
  });

  @override
  State<SignLanguageVisualDisplay> createState() => _SignLanguageVisualDisplayState();
}

class _SignLanguageVisualDisplayState extends State<SignLanguageVisualDisplay> {
  List<String> _words = [];
  Map<String, String?> _signImages = {};
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _processText();
  }

  @override
  void didUpdateWidget(SignLanguageVisualDisplay oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.text != widget.text) {
      _processText();
    }
  }

  void _processText() {
    // Split text into words
    final words = widget.text
        .toLowerCase()
        .replaceAll(RegExp(r'[^\w\s]'), ' ')
        .split(' ')
        .where((w) => w.trim().isNotEmpty)
        .toList();
    
    setState(() {
      _words = words;
      _signImages = {};
    });

    // Try to fetch sign images for each word
    _loadSignImages(words);
  }

  Future<void> _loadSignImages(List<String> words) async {
    setState(() {
      _isLoading = true;
    });

    // For each word, try to get sign language image/video
    for (var word in words) {
      try {
        // Try to get sign image from backend
        final imageUrl = await _getSignImageUrl(word);
        if (imageUrl != null && mounted) {
          setState(() {
            _signImages[word] = imageUrl;
          });
        }
      } catch (e) {
        print('Error loading sign image for $word: $e');
      }
    }

    setState(() {
      _isLoading = false;
    });
  }

  Future<String?> _getSignImageUrl(String word) async {
    // Check if backend has sign images endpoint
    // For now, we'll use a placeholder approach
    // In a full implementation, you would:
    // 1. Call backend API to get sign image/video URL
    // 2. Or use a sign language image library
    
    // Placeholder: Return null (will show icon instead)
    return null;
  }

  Widget _buildSignCard(String word, String? imageUrl) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.cardBackground,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AppTheme.accentTeal.withOpacity(0.3),
          width: 1.5,
        ),
      ),
      child: Row(
        children: [
          // Sign Image/Icon
          Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              color: AppTheme.accentTeal.withOpacity(0.15),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: AppTheme.accentTeal.withOpacity(0.3),
              ),
            ),
            child: imageUrl != null
                ? ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.network(
                      imageUrl,
                      fit: BoxFit.cover,
                      errorBuilder: (context, error, stackTrace) {
                        return _buildSignIcon(word);
                      },
                    ),
                  )
                : _buildSignIcon(word),
          ),
          
          const SizedBox(width: 16),
          
          // Word Label
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  word.toUpperCase(),
                  style: GoogleFonts.poppins(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                    letterSpacing: 1.2,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Sign Language',
                  style: GoogleFonts.poppins(
                    fontSize: 12,
                    color: AppTheme.textMuted,
                  ),
                ),
              ],
            ),
          ),
          
          // Sign Language Icon
          Icon(
            Icons.sign_language,
            color: AppTheme.accentTeal,
            size: 24,
          ),
        ],
      ),
    );
  }

  Widget _buildSignIcon(String word) {
    // Create a visual representation of the sign
    // Using the first letter as a placeholder
    final firstLetter = word.isNotEmpty ? word[0].toUpperCase() : '?';
    
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Hand gesture icon
          Icon(
            Icons.back_hand,
            color: AppTheme.accentTeal,
            size: 32,
          ),
          const SizedBox(height: 4),
          // Letter indicator
          Text(
            firstLetter,
            style: GoogleFonts.poppins(
              fontSize: 16,
              fontWeight: FontWeight.w700,
              color: AppTheme.accentTeal,
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_words.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.sign_language, color: AppTheme.accentCyan, size: 20),
            const SizedBox(width: 8),
            Text(
              'Sign Language',
              style: GoogleFonts.poppins(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: AppTheme.textMuted,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        if (_isLoading)
          const Center(
            child: CircularProgressIndicator(color: AppTheme.accentTeal),
          )
        else
          ..._words.map((word) => _buildSignCard(word, _signImages[word])).toList(),
      ],
    );
  }
}










