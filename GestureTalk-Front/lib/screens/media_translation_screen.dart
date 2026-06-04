import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:image_picker/image_picker.dart';
import 'package:video_player/video_player.dart';
import 'package:http/http.dart' as http;
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:gesture_talk/theme/app_theme.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:gesture_talk/services/connectivity_service.dart';
import 'package:gesture_talk/widgets/offline_indicator.dart';
import 'package:provider/provider.dart';

class MediaTranslationPage extends StatefulWidget {
  const MediaTranslationPage({super.key});

  @override
  _MediaTranslationPageState createState() => _MediaTranslationPageState();
}

class _MediaTranslationPageState extends State<MediaTranslationPage>
    with SingleTickerProviderStateMixin {
  XFile? _mediaFile;
  VideoPlayerController? _videoController;
  String _translation = '';
  bool _isTranslating = false;
  bool _translationSaved = false;
  String? _translationId; // Store the translation ID from database
  final AudioPlayer _audioPlayer = AudioPlayer();
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  final baseUrl = dotenv.env['BASE_URL'];
  
  late AnimationController _animationController;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _animationController, curve: Curves.easeOut),
    );
    _animationController.forward();
  }

  @override
  void dispose() {
    _videoController?.dispose();
    _audioPlayer.dispose();
    _animationController.dispose();
    super.dispose();
  }

  Future<void> _pickMedia() async {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (BuildContext context) {
        return Container(
          decoration: const BoxDecoration(
            color: AppTheme.cardBackground,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 20),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: AppTheme.divider,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  const SizedBox(height: 24),
                  Text(
                    'Select Media Type',
                    style: GoogleFonts.poppins(
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      _buildMediaOption(
                        icon: Icons.image_outlined,
                        label: 'Image',
                        onTap: () async {
                          Navigator.pop(context);
                          final picker = ImagePicker();
                          final XFile? pickedFile =
                              await picker.pickImage(source: ImageSource.gallery);
                          if (pickedFile != null) {
                            setState(() {
                              _mediaFile = pickedFile;
                              _videoController?.dispose();
                              _videoController = null;
                              _translation = '';
                              _translationSaved = false;
                              _translationId = null;
                            });
                          }
                        },
                      ),
                      _buildMediaOption(
                        icon: Icons.videocam_outlined,
                        label: 'Video',
                        onTap: () async {
                          Navigator.pop(context);
                          final picker = ImagePicker();
                          final XFile? pickedFile =
                              await picker.pickVideo(source: ImageSource.gallery);
                          if (pickedFile != null) {
                            _videoController?.dispose();
                            _videoController =
                                VideoPlayerController.file(File(pickedFile.path))
                                  ..initialize().then((_) {
                                    setState(() {});
                                    _videoController!.play();
                                  });
                            setState(() {
                              _mediaFile = pickedFile;
                              _translation = '';
                              _translationSaved = false;
                              _translationId = null;
                            });
                          }
                        },
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildMediaOption({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 120,
        padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 20),
        decoration: BoxDecoration(
          color: AppTheme.inputBackground,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: AppTheme.divider.withOpacity(0.3),
          ),
        ),
        child: Column(
          children: [
            Icon(
              icon,
              size: 40,
              color: AppTheme.accentTeal,
            ),
            const SizedBox(height: 12),
            Text(
              label,
              style: GoogleFonts.poppins(
                fontSize: 14,
                fontWeight: FontWeight.w500,
                color: AppTheme.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _translateMedia() async {
    if (_mediaFile == null) {
      _showSnackBar('Please select a media file first', isError: true);
      return;
    }

    setState(() {
      _isTranslating = true;
    });

    // Use environment variable for classifier URL, fallback to localhost for development
    final classifierUrl = dotenv.env['CLASSIFIER_URL'] ?? 'http://10.0.2.2:8001';
    final uri = Uri.parse(_mediaFile!.path.endsWith('.mp4')
        ? '$classifierUrl/predict_video'
        : '$classifierUrl/predict_image');

    final request = http.MultipartRequest('POST', uri)
      ..files.add(await http.MultipartFile.fromPath('file', _mediaFile!.path));

    try {
      // Add timeout for video processing - longer timeout for videos (120 seconds)
      final timeoutDuration = _mediaFile!.path.endsWith('.mp4') 
          ? const Duration(seconds: 120) 
          : const Duration(seconds: 30);
      
      final response = await request.send().timeout(timeoutDuration);

      if (response.statusCode == 200) {
        final responseData = await response.stream.bytesToString();
        print('Raw response: $responseData');
        
        dynamic decodedResponse;
        try {
          decodedResponse = jsonDecode(responseData);
          print('Decoded response type: ${decodedResponse.runtimeType}');
          print('Decoded response: $decodedResponse');
        } catch (e) {
          print('Error decoding JSON: $e');
          _showSnackBar('Invalid response format', isError: true);
          return;
        }

        // Check for error messages from backend first
        if (decodedResponse is Map<String, dynamic> && decodedResponse.containsKey('message')) {
          final errorMessage = decodedResponse['message']?.toString();
          if (errorMessage != null && errorMessage.isNotEmpty) {
            _showSnackBar(errorMessage, isError: true);
            setState(() {
              _translation = '';
              _translationSaved = false;
              _translationId = null;
            });
            return;
          }
        }
        
        // Handle different response formats
        String? translationText;
        
        if (decodedResponse is Map<String, dynamic>) {
          // Try different possible keys for translation
          if (decodedResponse.containsKey('Translation')) {
            translationText = decodedResponse['Translation']?.toString();
          } else if (decodedResponse.containsKey('translation')) {
            translationText = decodedResponse['translation']?.toString();
          } else if (decodedResponse.containsKey('text')) {
            translationText = decodedResponse['text']?.toString();
          } else if (decodedResponse.containsKey('result')) {
            translationText = decodedResponse['result']?.toString();
          } else if (decodedResponse.containsKey('prediction')) {
            translationText = decodedResponse['prediction']?.toString();
          } else {
            // If no known key, try to find any string value
            for (var value in decodedResponse.values) {
              if (value is String && value.isNotEmpty && value != 'null') {
                translationText = value;
                break;
              }
            }
          }
        } else if (decodedResponse is String) {
          translationText = decodedResponse;
        } else if (decodedResponse is List && decodedResponse.isNotEmpty) {
          // If response is a list, take the first element
          final firstItem = decodedResponse[0];
          if (firstItem is Map) {
            translationText = firstItem['Translation']?.toString() ?? 
                            firstItem['translation']?.toString() ??
                            firstItem['text']?.toString();
          } else if (firstItem is String) {
            translationText = firstItem;
          }
        }

        // Check if translation is null or empty
        if (translationText == null || 
            translationText.isEmpty || 
            translationText.toLowerCase() == 'null' ||
            translationText.trim().isEmpty) {
          _showSnackBar('No translation found in response', isError: true);
          print('Available keys in response: ${decodedResponse is Map ? (decodedResponse as Map).keys.toList() : 'N/A'}');
          setState(() {
            _translation = '';
            _translationSaved = false;
            _translationId = null;
          });
        } else {
          // Clean the translation text
          final cleanedText = translationText!
              .replaceAll('[', '')
              .replaceAll(']', '')
              .replaceAll(',', '')
              .trim();
          
          setState(() {
            _translation = cleanedText;
            _translationSaved = false; // Reset flag for new translation
            _translationId = null; // Reset translation ID
          });
          print('Translation set to: $_translation');
          
          // Automatically generate audio and save translation with audio
          await _generateAndSaveAudio(cleanedText);
        }
      } else {
        final errorBody = await response.stream.bytesToString();
        print('Translation failed with status ${response.statusCode}: $errorBody');
        _showSnackBar('Translation failed. Status: ${response.statusCode}', isError: true);
      }
    } catch (e) {
      print('Translation error: $e');
      String errorMsg = 'Translation error';
      if (e.toString().contains('TimeoutException') || e.toString().contains('timeout')) {
        errorMsg = 'Video processing timed out. The video may be too long. Please try a shorter video.';
      } else if (e.toString().contains('SocketException') || e.toString().contains('Failed host lookup')) {
        errorMsg = 'Cannot connect to server. Check your internet connection.';
      } else {
        errorMsg = 'Error: ${e.toString()}';
      }
      _showSnackBar(errorMsg, isError: true);
      setState(() {
        _translation = '';
        _translationId = null;
      });
    } finally {
      setState(() {
        _isTranslating = false;
      });
    }
  }

  Future<void> _generateAndSaveAudio(String text) async {
    if (text.trim().isEmpty) {
      _showSnackBar('No text to generate audio for', isError: true);
      return;
    }

    if (baseUrl == null || baseUrl!.isEmpty) {
      _showSnackBar('App configuration error: BASE_URL is missing.', isError: true);
      return;
    }

    final uri = Uri.parse('$baseUrl/api/speech');
    print('Generating audio for text: "$text"');
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
          
          // Save audio to temporary file
          final tempDir = Directory.systemTemp;
          final audioFile = File('${tempDir.path}/audio_${DateTime.now().millisecondsSinceEpoch}.mp3');
          await audioFile.writeAsBytes(audioBytes);
          print('Audio saved to temp file: ${audioFile.path}');
          
          // Save translation with audio to database
          if (_mediaFile != null && !_translationSaved) {
            await _saveTranslation(text, audioPath: audioFile.path);
            setState(() {
              _translationSaved = true;
            });
          } else if (_translationId != null) {
            // Update existing translation with audio
            await _updateTranslationWithAudio(_translationId!, audioFile.path);
          }
          
          // Clean up temp file after saving
          try {
            await audioFile.delete();
          } catch (e) {
            print('Error deleting temp audio file: $e');
          }
          
          _showSnackBar('Translation and audio saved!', isError: false);
        } else {
          print('No audio data in response');
          _showSnackBar('No audio data received', isError: true);
          // Still save translation without audio
          if (_mediaFile != null && !_translationSaved) {
            await _saveTranslation(text);
            setState(() {
              _translationSaved = true;
            });
          }
        }
      } else {
        final errorBody = response.body;
        print('Audio generation failed. Status: ${response.statusCode}');
        print('Error body: $errorBody');
        _showSnackBar('Failed to generate audio, saving translation without audio', isError: false);
        
        // Save translation without audio
        if (_mediaFile != null && !_translationSaved) {
          await _saveTranslation(text);
          setState(() {
            _translationSaved = true;
          });
        }
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
      _showSnackBar('$errorMsg. Saving translation without audio.', isError: false);
      
      // Save translation without audio on error
      if (_mediaFile != null && !_translationSaved) {
        await _saveTranslation(text);
        setState(() {
          _translationSaved = true;
        });
      }
    }
  }

  Future<void> _sendTranslationForSpeech(String text) async {
    if (text.trim().isEmpty) {
      _showSnackBar('No text to play', isError: true);
      return;
    }

    if (baseUrl == null || baseUrl!.isEmpty) {
      _showSnackBar('App configuration error: BASE_URL is missing.', isError: true);
      return;
    }

    // If we have a translation ID, try to fetch audio from database first
    if (_translationId != null) {
      try {
        final jwtToken = await _storage.read(key: 'jwt_token');
        if (jwtToken != null && jwtToken.isNotEmpty) {
          final uri = Uri.parse('$baseUrl/api/translations/$_translationId');
          final response = await http.get(
            uri,
            headers: {
              'Authorization': 'Bearer $jwtToken',
              'Content-Type': 'application/json',
            },
          ).timeout(const Duration(seconds: 10));

          if (response.statusCode == 200) {
            final data = jsonDecode(response.body);
            final audioPath = data['translated_audio'];
            if (audioPath != null && audioPath.toString().isNotEmpty) {
              // Audio exists in database, play it
              final audioUrl = _buildAudioUrl(audioPath.toString());
              if (audioUrl.isNotEmpty) {
                print('Playing audio from database: $audioUrl');
                try {
                  // Stop any currently playing audio
                  if (_audioPlayer.state == PlayerState.playing) {
                    await _audioPlayer.stop();
                  }
                  
                  // Always set the source before playing (required when player is stopped)
                  await _audioPlayer.setSourceUrl(audioUrl);
                  
                  // Play the audio
                  await _audioPlayer.resume();
                  _showSnackBar('Playing audio...', isError: false);
                  return;
                } catch (e) {
                  print('Error playing audio: $e');
                  _showSnackBar('Error playing audio: ${e.toString()}', isError: true);
                }
              } else {
                print('Failed to construct audio URL from: $audioPath');
              }
            }
          }
        }
      } catch (e) {
        print('Error fetching audio from database: $e');
        // Fall through to generate new audio
      }
    }

    // If no audio in database or fetch failed, generate new audio
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
            if (_audioPlayer.state == PlayerState.playing) {
              await _audioPlayer.stop();
            }
            
            // Play audio directly from bytes
            // Always set source before playing (required when player is stopped)
            await _audioPlayer.setSource(BytesSource(audioBytes));
            await _audioPlayer.resume();
            _showSnackBar('Playing audio...', isError: false);
            
            // If we have a translation ID, update it with the audio
            if (_translationId != null) {
              // Save audio to temp file and update translation
              final tempDir = Directory.systemTemp;
              final audioFile = File('${tempDir.path}/audio_${DateTime.now().millisecondsSinceEpoch}.mp3');
              await audioFile.writeAsBytes(audioBytes);
              await _updateTranslationWithAudio(_translationId!, audioFile.path);
              try {
                await audioFile.delete();
              } catch (e) {
                print('Error deleting temp audio file: $e');
              }
            }
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

  Future<void> _updateTranslationWithAudio(String translationId, String audioPath) async {
    final jwtToken = await _storage.read(key: 'jwt_token');
    if (jwtToken == null || jwtToken.isEmpty) {
      print('Cannot update translation: No JWT token found');
      return;
    }
    
    final uri = Uri.parse('$baseUrl/api/translations/$translationId');
    
    try {
      final audioFile = File(audioPath);
      if (!await audioFile.exists()) {
        print('Audio file does not exist: $audioPath');
        return;
      }
      
      final request = http.MultipartRequest('PUT', uri)
        ..headers['Authorization'] = 'Bearer $jwtToken'
        ..files.add(await http.MultipartFile.fromPath('translated_audio', audioPath));
      
      final response = await request.send();
      if (response.statusCode == 200) {
        print('Translation updated with audio successfully');
      } else {
        print('Failed to update translation with audio: ${response.statusCode}');
      }
    } catch (e) {
      print('Error updating translation with audio: $e');
    }
  }

  Future<void> _saveTranslationWithoutFile(String text, {String? audioPath}) async {
    final jwtToken = await _storage.read(key: 'jwt_token');
    if (jwtToken == null || jwtToken.isEmpty) {
      print('Cannot save translation: No JWT token found');
      return;
    }
    
    final uri = Uri.parse('$baseUrl/api/translations');

    final request = http.MultipartRequest('POST', uri)
      ..headers['Authorization'] = 'Bearer $jwtToken'
      ..fields['input_type'] = _mediaFile!.path.endsWith('.mp4') ? 'video' : 'image'
      ..fields['translated_text'] = text;
    
    // Add audio file only if available
    if (audioPath != null && audioPath.isNotEmpty) {
      try {
        final audioFile = File(audioPath);
        if (await audioFile.exists()) {
          request.files.add(await http.MultipartFile.fromPath('translated_audio', audioPath));
        }
      } catch (e) {
        print('Error adding audio file: $e');
      }
    }
    
    // Intentionally NOT adding the video file

    try {
      print('Sending translation save request (without video file)...');
      print('  - input_type: ${_mediaFile!.path.endsWith('.mp4') ? 'video' : 'image'}');
      print('  - translated_text: $text');
      print('  - has audio file: ${audioPath != null && audioPath.isNotEmpty}');
      
      final saveTimeoutDuration = const Duration(seconds: 60);
      final response = await request.send().timeout(saveTimeoutDuration);
      final responseBody = await response.stream.bytesToString();
      
      print('Translation save response status: ${response.statusCode}');
      
      if (response.statusCode == 200 || response.statusCode == 201) {
        try {
          final responseData = jsonDecode(responseBody);
          if (responseData is Map<String, dynamic>) {
            if (responseData.containsKey('translation')) {
              final translation = responseData['translation'];
              if (translation is Map && translation.containsKey('id')) {
                setState(() {
                  _translationId = translation['id'].toString();
                });
                print('Translation saved with ID: $_translationId');
              }
            } else if (responseData.containsKey('id')) {
              setState(() {
                _translationId = responseData['id'].toString();
              });
              print('Translation saved with ID: $_translationId');
            }
          }
        } catch (e) {
          print('Error parsing translation response: $e');
        }
        _showSnackBar('Translation saved (video file was too large to upload)', isError: false);
      } else {
        _showSnackBar('Failed to save translation', isError: true);
        print('Failed to save translation. Response: $responseBody');
      }
    } catch (e) {
      print('Error saving translation: $e');
      _showSnackBar('Error saving translation: ${e.toString()}', isError: true);
    }
  }

  Future<void> _saveTranslation(String text, {String? audioPath}) async {
    final jwtToken = await _storage.read(key: 'jwt_token');
    if (jwtToken == null || jwtToken.isEmpty) {
      print('Cannot save translation: No JWT token found');
      return; // Silently fail if not logged in
    }
    
    final uri = Uri.parse('$baseUrl/api/translations');

    final request = http.MultipartRequest('POST', uri)
      ..headers['Authorization'] = 'Bearer $jwtToken'
      ..fields['input_type'] = _mediaFile!.path.endsWith('.mp4') ? 'video' : 'image'
      ..fields['translated_text'] = text;
    
    // Add audio file only if available
    if (audioPath != null && audioPath.isNotEmpty) {
      try {
        final audioFile = File(audioPath);
        if (await audioFile.exists()) {
          request.files.add(await http.MultipartFile.fromPath('translated_audio', audioPath));
        }
      } catch (e) {
        print('Error adding audio file: $e');
      }
    }
    
    // Add input media file
    bool fileAdded = false;
    try {
      final mediaFile = File(_mediaFile!.path);
      if (await mediaFile.exists()) {
        final fileSize = await mediaFile.length();
        print('Adding input file: ${_mediaFile!.path}, size: ${(fileSize / 1024 / 1024).toStringAsFixed(2)} MB');
        
        // Check file size - allow large files for testing (no hard limit)
        final fileSizeMB = fileSize / 1024 / 1024;
        print('File size: ${fileSizeMB.toStringAsFixed(2)} MB');
        
        // Warn if file is very large but still try to upload
        if (fileSize > 500 * 1024 * 1024) { // 500MB
          print('Warning: Very large file (${fileSizeMB.toStringAsFixed(2)} MB), upload may take a while or timeout');
          _showSnackBar('Large video file detected (${fileSizeMB.toStringAsFixed(1)} MB). Uploading...', isError: false);
        } else if (fileSize > 200 * 1024 * 1024) { // 200MB
          print('Info: Large file (${fileSizeMB.toStringAsFixed(2)} MB), may take some time to upload');
        }
        
        // Always try to upload regardless of size (for testing)
        request.files.add(await http.MultipartFile.fromPath('input_data', _mediaFile!.path));
        fileAdded = true;
        print('Input file added successfully (size: ${fileSizeMB.toStringAsFixed(2)} MB)');
      } else {
        print('Error: Input file does not exist at path: ${_mediaFile!.path}');
        _showSnackBar('Video file not found. Translation saved without video file.', isError: false);
      }
    } catch (e) {
      print('Error adding input file: $e');
      _showSnackBar('Error adding video file: ${e.toString()}. Translation saved without video file.', isError: false);
    }

    try {
      print('Sending translation save request...');
      print('  - input_type: ${_mediaFile!.path.endsWith('.mp4') ? 'video' : 'image'}');
      print('  - translated_text: $text');
      print('  - has input_data file: $fileAdded');
      print('  - has audio file: ${audioPath != null && audioPath.isNotEmpty}');
      
      // Add timeout for save request - longer for videos with files
      // For testing: allow very long timeouts for large files
      final saveTimeoutDuration = (fileAdded && _mediaFile!.path.endsWith('.mp4'))
          ? const Duration(seconds: 600)  // 10 minutes for video uploads (testing mode)
          : const Duration(seconds: 120);   // 2 minutes for images/audio only
      
      print('Upload timeout set to: ${saveTimeoutDuration.inMinutes} minutes');
      final response = await request.send().timeout(saveTimeoutDuration);
      final responseBody = await response.stream.bytesToString();
      
      print('Translation save response status: ${response.statusCode}');
      print('Translation save response body: $responseBody');
      
      if (response.statusCode == 200 || response.statusCode == 201) {
        try {
          final responseData = jsonDecode(responseBody);
          // Extract translation ID from response
          if (responseData is Map<String, dynamic>) {
            if (responseData.containsKey('translation')) {
              final translation = responseData['translation'];
              if (translation is Map && translation.containsKey('id')) {
                setState(() {
                  _translationId = translation['id'].toString();
                });
                print('Translation saved with ID: $_translationId');
              }
            } else if (responseData.containsKey('id')) {
              setState(() {
                _translationId = responseData['id'].toString();
              });
              print('Translation saved with ID: $_translationId');
            }
          }
        } catch (e) {
          print('Error parsing translation response: $e');
        }
        _showSnackBar('Translation saved!', isError: false);
      } else if (response.statusCode == 413) {
        // 413 Payload Too Large - try saving without the video file
        print('413 Error: Video file too large. Attempting to save without video file...');
        _showSnackBar('Video file is too large for upload. Saving translation without video file...', isError: false);
        
        // Retry saving without the video file
        await _saveTranslationWithoutFile(text, audioPath: audioPath);
        return; // Exit early since we've handled it
      } else {
        // Try to parse error message from response
        try {
          final errorData = jsonDecode(responseBody);
          if (errorData is Map && errorData.containsKey('errors')) {
            final errors = errorData['errors'];
            String errorMsg = 'Failed to save translation';
            if (errors is Map && errors.containsKey('input_data')) {
              errorMsg = 'Video file error: ${errors['input_data'][0]}';
            } else if (errors is Map) {
              errorMsg = 'Validation error: ${errors.values.first[0]}';
            }
            _showSnackBar(errorMsg, isError: true);
          } else if (errorData is Map && errorData.containsKey('error')) {
            _showSnackBar(errorData['error'].toString(), isError: true);
          } else {
            _showSnackBar('Failed to save translation (Status: ${response.statusCode})', isError: true);
          }
        } catch (e) {
          _showSnackBar('Failed to save translation (Status: ${response.statusCode})', isError: true);
        }
        print('Failed to save translation. Response: $responseBody');
      }
    } catch (e) {
      print('Error saving translation: $e');
      String errorMsg = 'Error saving translation';
      if (e.toString().contains('TimeoutException') || e.toString().contains('timeout')) {
        errorMsg = 'Save request timed out. The video file may be too large. Translation may have been saved without the video file.';
      } else if (e.toString().contains('FileSystemException') || e.toString().contains('No such file')) {
        errorMsg = 'Video file not accessible. Translation saved without video file.';
      } else if (e.toString().contains('SocketException') || e.toString().contains('Failed host lookup')) {
        errorMsg = 'Cannot connect to server. Check your internet connection.';
      } else {
        errorMsg = 'Error saving translation: ${e.toString()}';
      }
      _showSnackBar(errorMsg, isError: true);
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

  String _formatTranslatedText(String? text) {
    if (text == null || text.isEmpty || text == 'null' || text == 'Null') {
      return '';
    }
    // Clean up the text: remove brackets, commas, and "null" strings
    return text
        .replaceAll('[', '')
        .replaceAll(']', '')
        .replaceAll(',', '')
        .replaceAll('null', '')
        .replaceAll('Null', '')
        .trim();
  }

  String _buildAudioUrl(String? audioPath) {
    if (audioPath == null || audioPath.isEmpty) {
      return '';
    }
    
    if (baseUrl == null || baseUrl!.isEmpty) {
      print('Warning: BASE_URL is not set, cannot construct audio URL');
      return '';
    }
    
    final String baseUrlValue = baseUrl!;
    String path = audioPath.toString().trim();
    print('_buildAudioUrl input: $path');
    
    // Extract the path part from any URL format (handles malformed URLs with duplicates)
    String? extractedPath;
    
    // Find /storage/ in the string - this is the actual path we need
    final storageIndex = path.indexOf('/storage/');
    if (storageIndex != -1) {
      // Extract everything from /storage/ onwards
      String tempPath = path.substring(storageIndex);
      // Remove any http:// or https:// fragments that might be embedded
      extractedPath = tempPath.split(RegExp(r'https?://')).first.trim();
    } else {
      // If no /storage/ found, try to find /uploads/ and prepend /storage
      final uploadsIndex = path.indexOf('/uploads/');
      if (uploadsIndex != -1) {
        String tempPath = path.substring(uploadsIndex);
        // Remove any http:// or https:// fragments
        String cleanPath = tempPath.split(RegExp(r'https?://')).first.trim();
        extractedPath = '/storage/$cleanPath';
      }
    }
    
    // If we extracted a path, use it with the frontend's base URL
    if (extractedPath != null && extractedPath.isNotEmpty) {
      // Remove leading slash if baseUrl already ends with /
      String cleanPath = extractedPath.startsWith('/') ? extractedPath : '/$extractedPath';
      String finalUrl = baseUrlValue.endsWith('/') 
          ? '${baseUrlValue.substring(0, baseUrlValue.length - 1)}$cleanPath'
          : '$baseUrlValue$cleanPath';
      
      print('Using extracted path with frontend base URL: $finalUrl (from original: $path)');
      return finalUrl;
    }
    
    // If it's already a full URL (starts with http:// or https://), try to use it
    // But replace the host with frontend's base URL if different
    if (path.startsWith('http://') || path.startsWith('https://')) {
      try {
        Uri uri = Uri.parse(path);
        if (uri.hasScheme && uri.hasAuthority) {
          // Check if the host matches our base URL
          Uri? baseUri = Uri.tryParse(baseUrlValue);
          if (baseUri != null && uri.host != baseUri.host) {
            // Replace with frontend's base URL
            String newPath = uri.path;
            if (uri.query.isNotEmpty) {
              newPath += '?${uri.query}';
            }
            String finalUrl = baseUrlValue.endsWith('/') 
                ? '${baseUrlValue.substring(0, baseUrlValue.length - 1)}$newPath'
                : '$baseUrlValue$newPath';
            print('Replaced backend URL with frontend base URL: $finalUrl (from original: $path)');
            return finalUrl;
          }
          return uri.toString();
        }
      } catch (e) {
        print('Error parsing URL: $path, error: $e');
      }
    }
    
    // Otherwise, construct the URL from the relative path
    // Remove leading slash if present
    if (path.startsWith('/')) {
      path = path.substring(1);
    }
    
    // Check if path already includes 'storage/' to avoid duplication
    if (path.startsWith('storage/')) {
      return '$baseUrlValue/$path';
    }
    
    return '$baseUrlValue/storage/$path';
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
              Expanded(
                child: FadeTransition(
                  opacity: _fadeAnimation,
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
                    
                    // Media Preview Card
                    _buildMediaPreviewCard(),
                    
                    const SizedBox(height: 24),
                    
                    // Translation Result
                    if (_translation.isNotEmpty) _buildTranslationCard(),
                    
                    const SizedBox(height: 24),
                    
                    // Action Buttons
                    _buildActionButtons(),
                    
                          const SizedBox(height: 32),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ],
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
          'Media Translation',
          style: GoogleFonts.poppins(
            fontSize: 28,
            fontWeight: FontWeight.w700,
            color: AppTheme.textPrimary,
          ),
        ),
        Text(
          'Upload an image or video to translate',
          style: GoogleFonts.poppins(
            fontSize: 14,
            color: AppTheme.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _buildMediaPreviewCard() {
    return GestureDetector(
      onTap: _pickMedia,
      child: Container(
        width: double.infinity,
        height: 280,
        decoration: AppTheme.glassCard,
        child: _mediaFile == null
            ? _buildEmptyMediaState()
            : _buildMediaPreview(),
      ),
    );
  }

  Widget _buildEmptyMediaState() {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            color: AppTheme.accentTeal.withOpacity(0.15),
            shape: BoxShape.circle,
          ),
          child: const Icon(
            Icons.add_photo_alternate_outlined,
            size: 40,
            color: AppTheme.accentTeal,
          ),
        ),
        const SizedBox(height: 20),
        Text(
          'Tap to upload media',
          style: GoogleFonts.poppins(
            fontSize: 16,
            fontWeight: FontWeight.w500,
            color: AppTheme.textPrimary,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Supported formats: JPG, PNG, MP4',
          style: GoogleFonts.poppins(
            fontSize: 12,
            color: AppTheme.textMuted,
          ),
        ),
      ],
    );
  }

  Widget _buildMediaPreview() {
    if (_mediaFile!.path.endsWith('.mp4')) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(18),
        child: _videoController != null && _videoController!.value.isInitialized
            ? Stack(
                alignment: Alignment.center,
                children: [
                  AspectRatio(
                    aspectRatio: _videoController!.value.aspectRatio,
                    child: VideoPlayer(_videoController!),
                  ),
                  GestureDetector(
                    onTap: () {
                      setState(() {
                        if (_videoController!.value.isPlaying) {
                          _videoController!.pause();
                        } else {
                          _videoController!.play();
                        }
                      });
                    },
                    child: Container(
                      width: 64,
                      height: 64,
                      decoration: BoxDecoration(
                        color: AppTheme.primaryDark.withOpacity(0.7),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        _videoController!.value.isPlaying
                            ? Icons.pause
                            : Icons.play_arrow,
                        color: AppTheme.accentTeal,
                        size: 36,
                      ),
                    ),
                  ),
                  Positioned(
                    top: 12,
                    right: 12,
                    child: _buildChangeMediaButton(),
                  ),
                ],
              )
            : const Center(
                child: CircularProgressIndicator(color: AppTheme.accentTeal),
              ),
      );
    } else {
      return ClipRRect(
        borderRadius: BorderRadius.circular(18),
        child: Stack(
          fit: StackFit.expand,
          children: [
            Image.file(
              File(_mediaFile!.path),
              fit: BoxFit.cover,
            ),
            Positioned(
              top: 12,
              right: 12,
              child: _buildChangeMediaButton(),
            ),
          ],
        ),
      );
    }
  }

  Widget _buildChangeMediaButton() {
    return GestureDetector(
      onTap: _pickMedia,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: AppTheme.primaryDark.withOpacity(0.8),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.swap_horiz,
              color: AppTheme.accentTeal,
              size: 18,
            ),
            const SizedBox(width: 6),
            Text(
              'Change',
              style: GoogleFonts.poppins(
                color: AppTheme.textPrimary,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTranslationCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: AppTheme.glassCard,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: AppTheme.success.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(
                  Icons.check,
                  color: AppTheme.success,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Text(
                'Translation Result',
                style: GoogleFonts.poppins(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            _formatTranslatedText(_translation),
            style: GoogleFonts.poppins(
              fontSize: 20,
              fontWeight: FontWeight.w500,
              color: AppTheme.accentCyan,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 16),
          // Play Audio Button
          _buildPlayAudioButton(),
        ],
      ),
    );
  }

  Widget _buildPlayAudioButton() {
    final formattedText = _formatTranslatedText(_translation);
    final hasText = formattedText.isNotEmpty;
    
    return GestureDetector(
      onTap: hasText
          ? () async {
              await _sendTranslationForSpeech(formattedText);
            }
          : null,
      child: Opacity(
        opacity: hasText ? 1.0 : 0.5,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 20),
          decoration: BoxDecoration(
            gradient: hasText
                ? AppTheme.primaryGradient
                : LinearGradient(
                    colors: [
                      AppTheme.textMuted.withOpacity(0.3),
                      AppTheme.textMuted.withOpacity(0.3),
                    ],
                  ),
            borderRadius: BorderRadius.circular(12),
            boxShadow: hasText
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
                color: hasText ? AppTheme.primaryDark : AppTheme.textMuted,
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                'Play Audio',
                style: GoogleFonts.poppins(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: hasText ? AppTheme.primaryDark : AppTheme.textMuted,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildActionButtons() {
    return Column(
      children: [
        // Upload Button
        GestureDetector(
          onTap: _pickMedia,
          child: Container(
            width: double.infinity,
            height: 56,
            decoration: BoxDecoration(
              color: AppTheme.cardBackground,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: AppTheme.accentTeal.withOpacity(0.5),
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(
                  Icons.upload_file,
                  color: AppTheme.accentTeal,
                  size: 22,
                ),
                const SizedBox(width: 10),
                Text(
                  _mediaFile == null ? 'Upload Media' : 'Change Media',
                  style: GoogleFonts.poppins(
                    color: AppTheme.accentTeal,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ),
        
        const SizedBox(height: 16),
        
        // Translate Button
        GradientButton(
          text: 'Translate',
          isLoading: _isTranslating,
          onPressed: _translateMedia,
          icon: Icons.translate,
        ),
      ],
    );
  }
}
