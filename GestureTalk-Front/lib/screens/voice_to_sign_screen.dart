import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:http/http.dart' as http;
import 'package:audioplayers/audioplayers.dart';
import 'package:gesture_talk/theme/app_theme.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:gesture_talk/services/connectivity_service.dart';
import 'package:gesture_talk/widgets/sign_language_visual_display.dart';
import 'package:gesture_talk/widgets/sign_language_display.dart';

class VoiceToSignScreen extends StatefulWidget {
  const VoiceToSignScreen({super.key});

  @override
  State<VoiceToSignScreen> createState() => _VoiceToSignScreenState();
}

class _VoiceToSignScreenState extends State<VoiceToSignScreen>
    with SingleTickerProviderStateMixin {
  final stt.SpeechToText _speech = stt.SpeechToText();
  final AudioPlayer _audioPlayer = AudioPlayer();
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  final ConnectivityService _connectivity = ConnectivityService();
  final String? baseUrl = dotenv.env['BASE_URL'];

  bool _isListening = false;
  String _recognizedText = '';
  String _signLanguageText = '';
  bool _isProcessing = false;
  bool _isAvailable = false;
  double _confidence = 0.0;
  
  late AnimationController _animationController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _initializeSpeech();
    
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
    
    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.2).animate(
      CurvedAnimation(parent: _animationController, curve: Curves.easeInOut),
    );
  }

  Future<void> _initializeSpeech() async {
    final available = await _speech.initialize(
      onStatus: (status) {
        if (status == 'done' || status == 'notListening') {
          setState(() {
            _isListening = false;
          });
        }
      },
      onError: (error) {
        print('Speech recognition error: $error');
        _showSnackBar('Speech recognition error: ${error.errorMsg}', isError: true);
      },
    );

    setState(() {
      _isAvailable = available;
    });

    if (!available) {
      _showSnackBar('Speech recognition not available on this device', isError: true);
    }
  }

  void _startListening() async {
    if (!_isAvailable) {
      _showSnackBar('Speech recognition not available', isError: true);
      return;
    }

    setState(() {
      _isListening = true;
      _recognizedText = '';
      _signLanguageText = '';
    });

    await _speech.listen(
      onResult: (result) {
        setState(() {
          _recognizedText = result.recognizedWords;
          _confidence = result.confidence;
        });

        if (result.finalResult) {
          _processTextToSign(result.recognizedWords);
        }
      },
      listenFor: const Duration(seconds: 30),
      pauseFor: const Duration(seconds: 3),
      localeId: 'en_US',
      cancelOnError: true,
      partialResults: true,
    );
  }

  void _stopListening() {
    _speech.stop();
    setState(() {
      _isListening = false;
    });
  }

  Future<void> _processTextToSign(String text) async {
    if (text.trim().isEmpty) return;

    setState(() {
      _isProcessing = true;
    });

    try {
      // For now, we'll display the text as sign language representation
      // In a full implementation, you would:
      // 1. Convert text to sign language notation (e.g., ASL gloss)
      // 2. Show sign language animations/videos
      // 3. Display sign language symbols

      // Simple conversion: Show text with sign language formatting
      final signLanguageText = _convertToSignLanguageFormat(text);
      
      setState(() {
        _signLanguageText = signLanguageText;
      });

      // Generate audio for the recognized text
      await _generateAudio(text);

      // Save to server if online
      if (_connectivity.isOnline) {
        await _saveToServer(text, signLanguageText);
      }
    } catch (e) {
      print('Error processing text to sign: $e');
      _showSnackBar('Error processing text', isError: true);
    } finally {
      setState(() {
        _isProcessing = false;
      });
    }
  }

  String _convertToSignLanguageFormat(String text) {
    // Return the original text - the visual display widget will handle
    // splitting into words and displaying as signs
    return text.trim();
  }

  Future<void> _generateAudio(String text) async {
    if (text.trim().isEmpty) {
      _showSnackBar('No text to play', isError: true);
      return;
    }

    if (baseUrl == null || baseUrl!.isEmpty) {
      _showSnackBar('App configuration error: BASE_URL is missing.', isError: true);
      return;
    }

    final uri = Uri.parse('$baseUrl/api/speech');
    print('Requesting audio for text: "$text"');
    print('URL: $uri');

    try {
      _showSnackBar('Generating audio...', isError: false);
      
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'text': text}),
      ).timeout(const Duration(seconds: 30));

      print('Audio response status: ${response.statusCode}');
      print('Audio response body length: ${response.bodyBytes.length}');

      if (response.statusCode == 200) {
        final audioBytes = response.bodyBytes;
        if (audioBytes.isNotEmpty) {
          print('Audio bytes received: ${audioBytes.length} bytes');
          try {
            // Stop any currently playing audio first
            await _audioPlayer.stop();
            await _audioPlayer.play(BytesSource(audioBytes));
            _showSnackBar('Playing audio...', isError: false);
          } catch (e) {
            print('Error playing audio: $e');
            _showSnackBar('Error playing audio: ${e.toString()}', isError: true);
          }
        } else {
          print('No audio data in response');
          _showSnackBar('No audio data received', isError: true);
        }
      } else {
        final errorBody = response.body;
        print('Audio generation failed. Status: ${response.statusCode}');
        print('Error body: $errorBody');
        _showSnackBar('Failed to generate audio: ${response.statusCode}', isError: true);
      }
    } catch (e, stackTrace) {
      print('Error generating speech: $e');
      print('Stack trace: $stackTrace');
      String errorMsg = 'Error generating audio';
      if (e.toString().contains('SocketException') || e.toString().contains('Failed host lookup')) {
        errorMsg = 'Cannot connect to server. Check your internet connection.';
      } else if (e.toString().contains('TimeoutException')) {
        errorMsg = 'Request timed out. Server may be slow or unreachable.';
      } else {
        errorMsg = 'Error: ${e.toString()}';
      }
      _showSnackBar(errorMsg, isError: true);
    }
  }

  Future<void> _saveToServer(String originalText, String signText) async {
    try {
      final token = await _storage.read(key: 'jwt_token');
      if (token == null) return;

      final response = await http.post(
        Uri.parse('$baseUrl/api/translations'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'input_type': 'voice',
          'translated_text': signText,
        }),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        // Successfully saved
      }
    } catch (e) {
      print('Error saving to server: $e');
      // Will be synced later when online
    }
  }

  void _showSnackBar(String message, {required bool isError}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            Icon(
              isError ? Icons.error_outline : Icons.check_circle_outline,
              color: isError ? AppTheme.error : AppTheme.success,
            ),
            const SizedBox(width: 12),
            Expanded(child: Text(message)),
          ],
        ),
        backgroundColor: AppTheme.cardBackground,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        margin: const EdgeInsets.all(16),
      ),
    );
  }

  @override
  void dispose() {
    _speech.stop();
    _audioPlayer.dispose();
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppTheme.backgroundGradient),
        child: SafeArea(
          child: SingleChildScrollView(
            physics: const BouncingScrollPhysics(),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 20),
                  
                  // Header
                  _buildHeader(),
                  
                  const SizedBox(height: 32),
                  
                  // Voice Input Section
                  _buildVoiceInputSection(),
                  
                  const SizedBox(height: 24),
                  
                  // Recognized Text
                  if (_recognizedText.isNotEmpty) _buildRecognizedText(),
                  
                  const SizedBox(height: 24),
                  
                  // Sign Language Display
                  if (_signLanguageText.isNotEmpty) _buildSignLanguageDisplay(),
                  
                  const SizedBox(height: 32),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Voice to Sign',
          style: GoogleFonts.poppins(
            fontSize: 28,
            fontWeight: FontWeight.w700,
            color: AppTheme.textPrimary,
          ),
        ),
        Text(
          'Speak to convert to sign language',
          style: GoogleFonts.poppins(
            fontSize: 14,
            color: AppTheme.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _buildVoiceInputSection() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(32),
      decoration: AppTheme.glassCard,
      child: Column(
        children: [
          // Microphone Button
          GestureDetector(
            onTap: _isListening ? _stopListening : _startListening,
            child: AnimatedBuilder(
              animation: _pulseAnimation,
              builder: (context, child) {
                return Transform.scale(
                  scale: _isListening ? _pulseAnimation.value : 1.0,
                  child: Container(
                    width: 120,
                    height: 120,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: _isListening
                          ? AppTheme.primaryGradient
                          : LinearGradient(
                              colors: [
                                AppTheme.accentTeal.withOpacity(0.3),
                                AppTheme.accentCyan.withOpacity(0.3),
                              ],
                            ),
                      boxShadow: [
                        BoxShadow(
                          color: _isListening
                              ? AppTheme.accentTeal.withOpacity(0.5)
                              : AppTheme.accentTeal.withOpacity(0.2),
                          blurRadius: 30,
                          spreadRadius: 10,
                        ),
                      ],
                    ),
                    child: Icon(
                      _isListening ? Icons.mic : Icons.mic_none,
                      size: 50,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                );
              },
            ),
          ),
          
          const SizedBox(height: 24),
          
          Text(
            _isListening ? 'Listening...' : 'Tap to start speaking',
            style: GoogleFonts.poppins(
              fontSize: 16,
              fontWeight: FontWeight.w500,
              color: AppTheme.textPrimary,
            ),
          ),
          
          if (_isListening && _confidence > 0) ...[
            const SizedBox(height: 12),
            Text(
              'Confidence: ${(_confidence * 100).toStringAsFixed(0)}%',
              style: GoogleFonts.poppins(
                fontSize: 12,
                color: AppTheme.textMuted,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildRecognizedText() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: AppTheme.glassCard,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.text_fields, color: AppTheme.accentTeal, size: 20),
              const SizedBox(width: 8),
              Text(
                'Recognized Text',
                style: GoogleFonts.poppins(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.textMuted,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            _recognizedText,
            style: GoogleFonts.poppins(
              fontSize: 18,
              color: AppTheme.textPrimary,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 12),
          // Play Audio Button for recognized text
          _buildPlayAudioButton(_recognizedText),
        ],
      ),
    );
  }

  Widget _buildSignLanguageDisplay() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: AppTheme.glassCard,
      child: _isProcessing
          ? const SizedBox(
              height: 200,
              child: Center(
                child: CircularProgressIndicator(color: AppTheme.accentTeal),
              ),
            )
          : _signLanguageText.isNotEmpty
              ? Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
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
                    // Sign language display with proper constraints
                    SignLanguageDisplay(text: _signLanguageText),
                    const SizedBox(height: 16),
                    // Play Audio Button
                    _buildPlayAudioButton(_signLanguageText),
                  ],
                )
              : Column(
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
                    const SizedBox(height: 12),
                    Text(
                      'Signs will appear here',
                      style: GoogleFonts.poppins(
                        fontSize: 14,
                        color: AppTheme.textMuted,
                      ),
                    ),
                  ],
                ),
    );
  }

  Widget _buildPlayAudioButton(String text) {
    return GestureDetector(
      onTap: text.trim().isNotEmpty
          ? () async {
              await _generateAudio(text);
            }
          : null,
      child: Opacity(
        opacity: text.trim().isNotEmpty ? 1.0 : 0.5,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 20),
          decoration: BoxDecoration(
            gradient: text.trim().isNotEmpty
                ? AppTheme.primaryGradient
                : LinearGradient(
                    colors: [
                      AppTheme.textMuted.withOpacity(0.3),
                      AppTheme.textMuted.withOpacity(0.3),
                    ],
                  ),
            borderRadius: BorderRadius.circular(12),
            boxShadow: text.trim().isNotEmpty
                ? [
                    BoxShadow(
                      color: AppTheme.accentTeal.withOpacity(0.3),
                      blurRadius: 8,
                      spreadRadius: 1,
                    ),
                  ]
                : null,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.volume_up,
                color: text.trim().isNotEmpty
                    ? AppTheme.primaryDark
                    : AppTheme.textMuted,
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                'Play Audio',
                style: GoogleFonts.poppins(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: text.trim().isNotEmpty
                      ? AppTheme.primaryDark
                      : AppTheme.textMuted,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

