import 'dart:async';
import 'dart:typed_data';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_image_compress/flutter_image_compress.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http_parser/http_parser.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:http/http.dart' as http;
import 'package:gesture_talk/theme/app_theme.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:gesture_talk/services/connectivity_service.dart';
import 'package:gesture_talk/widgets/offline_indicator.dart';
import 'package:provider/provider.dart';

class LiveTranslationScreen extends StatefulWidget {
  const LiveTranslationScreen({super.key});

  @override
  _LiveTranslationScreenState createState() => _LiveTranslationScreenState();
}

class _LiveTranslationScreenState extends State<LiveTranslationScreen>
    with SingleTickerProviderStateMixin {
  CameraController? _controller;
  WebSocketChannel? _webSocketChannel;
  bool _isTranslating = false;
  String _translation = '';
  bool _isCameraInitialized = false;
  final int _maxLines = 3;
  bool _isRecording = false;
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  final baseUrl = dotenv.env['BASE_URL'];
  final GlobalKey _translationDisplayKey = GlobalKey();
  
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;
  
  // Save tracking variables
  bool _isSaving = false;
  
  @override
  void initState() {
    super.initState();
    _initCamera();
    
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );
    
    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.2).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
    
    print('LiveTranslationScreen initialized');
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    final camera = cameras.first;
    _controller = CameraController(camera, ResolutionPreset.high);
    await _controller!.initialize();
    setState(() {
      _isCameraInitialized = true;
    });
  }

  void _connectToWebSocket() async {
    // Use environment variable for WebSocket URL, fallback to localhost for development
    final wsUrl = dotenv.env['WEBSOCKET_URL'] ?? 'ws://10.0.2.2:8002';
    final webSocketChannel = WebSocketChannel.connect(Uri.parse(wsUrl));
    setState(() {
      _webSocketChannel = webSocketChannel;
    });

    webSocketChannel.stream.listen(
      (event) {
        print('Received from WebSocket: $event');
        
        // Parse JSON response
        try {
          final data = jsonDecode(event.toString());
          final prediction = data['prediction']?.toString() ?? '';
          final type = data['type']?.toString() ?? '';
          final confidence = data['confidence']?.toDouble() ?? 0.0;
          
          // Debug logging for two-hand detection
          if (type == 'word' || type == 'letter') {
            print('WebSocket: type=$type, prediction=$prediction, confidence=$confidence');
          } else if (type == 'none') {
            // Only log occasionally to avoid spam
            if (DateTime.now().millisecond % 10 == 0) {
              print('WebSocket: No detection (type=none)');
            }
          }
          
          if (prediction.isNotEmpty && type != 'none' && type != 'error') {
            // Update translation based on type (word vs letter)
            print('WebSocket: Received prediction: "$prediction", type: $type');
            setState(() {
              if (type == 'word') {
                // For words: replace current word or add as new word
                _updateTranslationWord(prediction);
              } else if (type == 'letter') {
                // For letters: accumulate letters to form a word
                _updateTranslationLetter(prediction);
              } else {
                // Fallback: treat as word
                _updateTranslationWord(prediction);
              }
            });
            print('WebSocket: Translation updated to: "${_translation}"');
          }
        } catch (e) {
          print('Error parsing WebSocket response: $e');
          // Fallback: treat as plain text
          final text = event.toString();
          if (text.isNotEmpty) {
            setState(() {
              _updateTranslation(text);
            });
          }
        }
      },
      onError: (error) {
        print('WebSocket error: $error');
      },
      onDone: () {
        print('WebSocket connection closed');
      },
    );
  }

  void _captureAndSendFrame() async {
    if (_controller != null && _controller!.value.isInitialized) {
      while (_isTranslating) {
        final XFile image = await _controller!.takePicture();
        final Uint8List bytes = await image.readAsBytes();
        final compressedBytes = await FlutterImageCompress.compressWithList(
          bytes,
          minHeight: 480,
          minWidth: 640,
          quality: 90,
        );
        if (_webSocketChannel != null) {
          _webSocketChannel!.sink.add(compressedBytes);
        }
        await Future.delayed(const Duration(seconds: 1));
      }
    }
  }

  void _updateTranslationWord(String word) {
    print('_updateTranslationWord called with: "$word", current: "$_translation"');
    setState(() {
      String previousTranslation = _translation.trim();
      
      if (_translation.isEmpty) {
        // First word - just add it
        _translation = word;
      } else {
        // Check if this word is the same as the last word
        List<String> translationWords = _translation.trim().split(' ');
        String lastWord = translationWords.isEmpty ? '' : translationWords.last;
        
        if (word == lastWord) {
          // Same word - don't add again, just schedule save
          print('Word "$word" is same as last word "$lastWord" - keeping current translation');
        } else {
          // Different word - add as new word with space
          _translation = '$_translation $word';
        }
      }
      
      // Check text size and handle overflow
      final textStyle = GoogleFonts.poppins(
        fontSize: 18,
        fontWeight: FontWeight.w500,
        height: 1.5,
      );
      
      final containerWidth = MediaQuery.of(context).size.width - 80;
      final maxHeight = _maxLines * (textStyle.fontSize! * textStyle.height!);
      
      final textPainter = TextPainter(
        text: TextSpan(
          text: _translation.trim(),
          style: textStyle,
        ),
        textDirection: TextDirection.ltr,
        maxLines: _maxLines,
      );
      
      textPainter.layout(maxWidth: containerWidth);
      
      if (textPainter.didExceedMaxLines || textPainter.height > maxHeight) {
        // Just clear and start fresh with the new word
        // Don't save - only save when recording stops
        _translation = word;
      }
    });
  }
  
  void _updateTranslationLetter(String letter) {
    print('_updateTranslationLetter called with: "$letter", current: "$_translation"');
    setState(() {
      String previousTranslation = _translation.trim();
      
      if (_translation.isEmpty) {
        // First letter - start building word
        _translation = letter;
      } else {
        // Get the last character to check for duplicates
        String lastChar = _translation.trim().isEmpty ? '' : _translation.trim()[_translation.trim().length - 1];
        
        // Check if same letter repeated (user holding sign)
        if (lastChar == letter) {
          // Same letter - don't add duplicate
          print('Letter "$letter" is same as last letter - not adding duplicate');
        } else {
          // Different letter - append with space
          _translation = '$_translation $letter';
          print('Appended letter "$letter" with space - now: "$_translation"');
        }
      }
      
      // Check text size and handle overflow
      final textStyle = GoogleFonts.poppins(
        fontSize: 18,
        fontWeight: FontWeight.w500,
        height: 1.5,
      );
      
      final containerWidth = MediaQuery.of(context).size.width - 80;
      final maxHeight = _maxLines * (textStyle.fontSize! * textStyle.height!);
      
      final textPainter = TextPainter(
        text: TextSpan(
          text: _translation.trim(),
          style: textStyle,
        ),
        textDirection: TextDirection.ltr,
        maxLines: _maxLines,
      );
      
      textPainter.layout(maxWidth: containerWidth);
      
      if (textPainter.didExceedMaxLines || textPainter.height > maxHeight) {
        // Just clear and start fresh with the new letter
        // Don't save - only save when recording stops
        _translation = letter;
      }
    });
  }
  
  // Keep old method for backward compatibility (but it will treat as word)
  void _updateTranslation(String newText) {
    _updateTranslationWord(newText);
  }

  void _sendVideoToApi(XFile videoFile) async {
    final jwtToken = await _storage.read(key: 'jwt_token');
    
    if (jwtToken == null || jwtToken.isEmpty) {
      _showSnackBar('Please login to save recordings', isError: true);
      return;
    }
    
    if (_isSaving) {
      print('Already saving, skipping duplicate save');
      return;
    }
    
    setState(() {
      _isSaving = true;
    });
    
    try {
      final url = baseUrl;
      if (url == null || url.isEmpty) {
        _showSnackBar('App configuration error: BASE_URL is missing.', isError: true);
        return;
      }
      
      // Get the current translation before saving
      final translationToSave = _translation.trim();
      
      print('Saving recording with video and translation...');
      print('Translation: "$translationToSave"');
      print('Video file: ${videoFile.path}');
      
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$url/api/translations'),
      );
      request.headers['Authorization'] = 'Bearer $jwtToken';
      request.headers['Accept'] = 'application/json';
      
      // Add video file
      request.files.add(await http.MultipartFile.fromPath(
        'input_data',
        videoFile.path,
        contentType: MediaType('video', 'mp4'),
      ));
      
      // Add translation text (even if empty, backend should handle it)
      request.fields['translated_text'] = translationToSave;
      request.fields['input_type'] = 'live';
      
      print('Request prepared with:');
      print('  - input_data: video file (${videoFile.path})');
      print('  - translated_text: "$translationToSave"');
      print('  - input_type: live');
      
      var response = await request.send();
      final responseBody = await response.stream.bytesToString();
      
      print('Response status: ${response.statusCode}');
      print('Response body: $responseBody');
      
      if (response.statusCode == 201 || response.statusCode == 200) {
        _showSnackBar('Recording saved successfully!', isError: false);
        // Clear translation after successful save
        setState(() {
          _translation = '';
        });
      } else {
        try {
          final errorData = jsonDecode(responseBody);
          _showSnackBar('Error: ${errorData['error'] ?? 'Failed to save recording'}', isError: true);
        } catch (e) {
          _showSnackBar('Error saving recording (${response.statusCode})', isError: true);
        }
      }
    } catch (e, stackTrace) {
      print('Error saving recording: $e');
      print('Stack trace: $stackTrace');
      _showSnackBar('Error saving recording: ${e.toString()}', isError: true);
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
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

  void _toggleTranslation() {
    setState(() {
      _isTranslating = !_isTranslating;
    });
    
    if (_isTranslating) {
      _pulseController.repeat(reverse: true);
      _connectToWebSocket();
      _captureAndSendFrame();
    } else {
      _pulseController.stop();
      _pulseController.reset();
      _webSocketChannel?.sink.close();
      // Don't save here - only save when recording stops
    }
  }

  void _toggleRecording() async {
    if (_controller != null && _controller!.value.isInitialized) {
      if (!_controller!.value.isRecordingVideo) {
        await _controller!.startVideoRecording();
        setState(() {
          _isRecording = true;
        });
      } else {
        final XFile videoFile = await _controller!.stopVideoRecording();
        setState(() {
          _isRecording = false;
        });
        _sendVideoToApi(videoFile);
      }
    }
  }

  @override
  void dispose() {
    // Don't save on dispose - only save when recording stops
    _webSocketChannel?.sink.close();
    _pulseController.dispose();
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppTheme.backgroundGradient),
        child: SafeArea(
          child: Column(
            children: [
              // Offline Indicator
              const OfflineIndicator(),
              // Custom App Bar
              _buildAppBar(),
              
              // Camera Preview
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Column(
                    children: [
                      const SizedBox(height: 16),
                      
                      // Camera Container
                      Expanded(
                        flex: 3,
                        child: _buildCameraPreview(),
                      ),
                      
                      const SizedBox(height: 20),
                      
                      // Translation Display
                      _buildTranslationDisplay(),
                      
                      const SizedBox(height: 20),
                      
                      // Control Buttons
                      _buildControlButtons(),
                      
                      const SizedBox(height: 24),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAppBar() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Live Translation',
                style: GoogleFonts.poppins(
                  fontSize: 24,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textPrimary,
                ),
              ),
              Text(
                _isTranslating ? 'Translating...' : 'Ready to translate',
                style: GoogleFonts.poppins(
                  fontSize: 14,
                  color: _isTranslating ? AppTheme.accentTeal : AppTheme.textSecondary,
                ),
              ),
            ],
          ),
          // Status indicator
          AnimatedBuilder(
            animation: _pulseController,
            builder: (context, child) {
              return Container(
                width: 12,
                height: 12,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: _isTranslating ? AppTheme.accentTeal : AppTheme.textMuted,
                  boxShadow: _isTranslating
                      ? [
                          BoxShadow(
                            color: AppTheme.accentTeal.withOpacity(0.5 * _pulseAnimation.value),
                            blurRadius: 10 * _pulseAnimation.value,
                            spreadRadius: 2 * _pulseAnimation.value,
                          ),
                        ]
                      : null,
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildCameraPreview() {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: _isTranslating
              ? AppTheme.accentTeal.withOpacity(0.5)
              : AppTheme.divider.withOpacity(0.3),
          width: 2,
        ),
        boxShadow: _isTranslating
            ? [
                BoxShadow(
                  color: AppTheme.accentTeal.withOpacity(0.2),
                  blurRadius: 20,
                  spreadRadius: 2,
                ),
              ]
            : [
                BoxShadow(
                  color: Colors.black.withOpacity(0.3),
                  blurRadius: 20,
                  offset: const Offset(0, 10),
                ),
              ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(22),
        child: _isCameraInitialized
            ? Stack(
                fit: StackFit.expand,
                children: [
                  CameraPreview(_controller!),
                  
                  // Overlay gradient
                  Positioned(
                    bottom: 0,
                    left: 0,
                    right: 0,
                    height: 100,
                    child: Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [
                            Colors.transparent,
                            Colors.black.withOpacity(0.5),
                          ],
                        ),
                      ),
                    ),
                  ),
                  
                  // Recording indicator
                  if (_isRecording)
                    Positioned(
                      top: 16,
                      right: 16,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: AppTheme.error.withOpacity(0.9),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 8,
                              height: 8,
                              decoration: const BoxDecoration(
                                shape: BoxShape.circle,
                                color: Colors.white,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Text(
                              'REC',
                              style: GoogleFonts.poppins(
                                color: Colors.white,
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  
                  // Translation status
                  if (_isTranslating)
                    Positioned(
                      top: 16,
                      left: 16,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: AppTheme.accentTeal.withOpacity(0.9),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const SizedBox(
                              width: 12,
                              height: 12,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor: AlwaysStoppedAnimation<Color>(AppTheme.primaryDark),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              'LIVE',
                              style: GoogleFonts.poppins(
                                color: AppTheme.primaryDark,
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              )
            : Container(
                color: AppTheme.cardBackground,
                child: const Center(
                  child: CircularProgressIndicator(
                    color: AppTheme.accentTeal,
                  ),
                ),
              ),
      ),
    );
  }

  Widget _buildTranslationDisplay() {
    return Container(
      key: _translationDisplayKey,
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: AppTheme.glassCard,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.translate,
                color: AppTheme.accentTeal,
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                'Translation',
                style: GoogleFonts.poppins(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.textSecondary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            _translation.isEmpty ? 'Start translating to see text here...' : _translation.trim(),
            style: GoogleFonts.poppins(
              fontSize: 18,
              fontWeight: FontWeight.w500,
              color: _translation.isEmpty ? AppTheme.textMuted : AppTheme.textPrimary,
              height: 1.5,
            ),
            maxLines: _maxLines,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _buildControlButtons() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // Record button
        _buildControlButton(
          icon: _isRecording ? Icons.stop : Icons.fiber_manual_record,
          label: _isRecording ? 'Stop' : 'Record',
          color: _isRecording ? AppTheme.error : AppTheme.textSecondary,
          onTap: _toggleRecording,
          isSecondary: true,
        ),
        
        const SizedBox(width: 24),
        
        // Main translate button
        GestureDetector(
          onTap: _toggleTranslation,
          child: AnimatedBuilder(
            animation: _pulseController,
            builder: (context, child) {
              return Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: _isTranslating
                      ? null
                      : AppTheme.primaryGradient,
                  color: _isTranslating ? AppTheme.error : null,
                  boxShadow: [
                    BoxShadow(
                      color: (_isTranslating ? AppTheme.error : AppTheme.accentTeal)
                          .withOpacity(0.4 * (_isTranslating ? _pulseAnimation.value : 1)),
                      blurRadius: 20 * (_isTranslating ? _pulseAnimation.value : 1),
                      spreadRadius: 2,
                    ),
                  ],
                ),
                child: Icon(
                  _isTranslating ? Icons.stop : Icons.sign_language,
                  color: _isTranslating ? Colors.white : AppTheme.primaryDark,
                  size: 36,
                ),
              );
            },
          ),
        ),
        
        const SizedBox(width: 24),
        
        // Clear button
        _buildControlButton(
          icon: Icons.refresh,
          label: 'Clear',
          color: AppTheme.textSecondary,
          onTap: () {
            setState(() {
              _translation = '';
            });
          },
          isSecondary: true,
        ),
      ],
    );
  }

  Widget _buildControlButton({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onTap,
    bool isSecondary = false,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppTheme.cardBackground,
              border: Border.all(
                color: AppTheme.divider.withOpacity(0.3),
                width: 1,
              ),
            ),
            child: Icon(
              icon,
              color: color,
              size: 24,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            label,
            style: GoogleFonts.poppins(
              fontSize: 12,
              color: AppTheme.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}
