import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:video_player/video_player.dart';
import 'package:http/http.dart' as http;
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:gesture_talk/theme/app_theme.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:share_plus/share_plus.dart';

class HistoryPage extends StatefulWidget {
  const HistoryPage({super.key});

  @override
  _HistoryPageState createState() => _HistoryPageState();
}

class _HistoryPageState extends State<HistoryPage> with SingleTickerProviderStateMixin {
  late Future<List<Map<String, dynamic>>> _translationHistory;
  final storage = const FlutterSecureStorage();
  final baseUrl = dotenv.env['BASE_URL'];
  
  late AnimationController _animationController;
  
  // Search and Sort
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  String _sortBy = 'date'; // 'date', 'type', 'alphabetical'
  bool _sortAscending = false;
  
  // Notes
  final Map<String, TextEditingController> _noteControllers = {};

  @override
  void initState() {
    super.initState();
    _translationHistory = fetchTranslationHistory();
    
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    _animationController.forward();
  }

  @override
  void dispose() {
    _animationController.dispose();
    _searchController.dispose();
    for (var controller in _noteControllers.values) {
      controller.dispose();
    }
    _noteControllers.clear();
    super.dispose();
  }
  
  List<Map<String, dynamic>> _filterAndSort(List<Map<String, dynamic>> history) {
    List<Map<String, dynamic>> filtered = history;
    
    // Filter by search query
    if (_searchQuery.isNotEmpty) {
      filtered = filtered.where((entry) {
        final text = (entry['translated_text'] ?? '').toString().toLowerCase();
        final type = (entry['input_type'] ?? '').toString().toLowerCase();
        return text.contains(_searchQuery.toLowerCase()) || 
               type.contains(_searchQuery.toLowerCase());
      }).toList();
    }
    
    // Sort
    filtered.sort((a, b) {
      switch (_sortBy) {
        case 'date':
          final dateA = _parseDate(a['created_at']);
          final dateB = _parseDate(b['created_at']);
          return _sortAscending 
              ? dateA.compareTo(dateB)
              : dateB.compareTo(dateA);
        case 'type':
          final typeA = (a['input_type'] ?? '').toString();
          final typeB = (b['input_type'] ?? '').toString();
          return _sortAscending 
              ? typeA.compareTo(typeB)
              : typeB.compareTo(typeA);
        case 'alphabetical':
          final textA = (a['translated_text'] ?? '').toString().toLowerCase();
          final textB = (b['translated_text'] ?? '').toString().toLowerCase();
          return _sortAscending 
              ? textA.compareTo(textB)
              : textB.compareTo(textA);
        default:
          return 0;
      }
    });
    
    return filtered;
  }
  
  DateTime _parseDate(String? dateString) {
    if (dateString == null || dateString.isEmpty) {
      return DateTime(1970);
    }
    try {
      return DateTime.parse(dateString);
    } catch (e) {
      return DateTime(1970);
    }
  }
  
  void _copyToClipboard(String text) {
    Clipboard.setData(ClipboardData(text: text));
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle, color: AppTheme.success, size: 20),
            const SizedBox(width: 12),
            Text(
              'Copied to clipboard',
              style: GoogleFonts.poppins(color: AppTheme.textPrimary),
            ),
          ],
        ),
        backgroundColor: AppTheme.cardBackground,
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 2),
      ),
    );
  }
  
  void _shareTranslation(Map<String, dynamic> entry) {
    final text = _formatTranslatedText(entry['translated_text']);
    final type = entry['input_type'] ?? 'translation';
    final date = _formatDate(entry['created_at']);
    
    Share.share(
      'GestureTalk Translation\n\n'
      'Type: ${type.toUpperCase()}\n'
      'Date: $date\n\n'
      'Translation:\n$text',
      subject: 'GestureTalk Translation',
    );
  }
  
  void _showNoteDialog(Map<String, dynamic> entry) {
    final entryId = entry['id'].toString();
    if (!_noteControllers.containsKey(entryId)) {
      _noteControllers[entryId] = TextEditingController(
        text: entry['note'] ?? '',
      );
    }
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppTheme.cardBackground,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text(
          'Add Note',
          style: GoogleFonts.poppins(
            color: AppTheme.textPrimary,
            fontWeight: FontWeight.w600,
          ),
        ),
        content: TextField(
          controller: _noteControllers[entryId],
          maxLines: 4,
          style: GoogleFonts.poppins(color: AppTheme.textPrimary),
          decoration: InputDecoration(
            hintText: 'Add a note to this translation...',
            hintStyle: GoogleFonts.poppins(color: AppTheme.textMuted),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(color: AppTheme.divider),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(color: AppTheme.accentTeal),
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(
              'Cancel',
              style: GoogleFonts.poppins(color: AppTheme.textMuted),
            ),
          ),
          TextButton(
            onPressed: () {
              _saveNote(entryId, _noteControllers[entryId]!.text);
              Navigator.pop(context);
            },
            child: Text(
              'Save',
              style: GoogleFonts.poppins(
                color: AppTheme.accentTeal,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
  
  Future<void> _saveNote(String entryId, String note) async {
    // In a real implementation, you would save this to the backend
    // For now, we'll just store it locally
    setState(() {
      // Update the entry with note
    });
  }

  Future<List<Map<String, dynamic>>> fetchTranslationHistory() async {
    try {
      final token = await storage.read(key: 'jwt_token');
      
      if (token == null || token.isEmpty) {
        print('History: No JWT token found');
        throw Exception('No authentication token found. Please login again.');
      }
      
      final url = Uri.parse('$baseUrl/api/get-translations');
      print('History: Fetching from $url');

      final response = await http.get(
        url,
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      );

      print('History: Response status: ${response.statusCode}');
      print('History: Response body: ${response.body}');

      if (response.statusCode == 200) {
        try {
          final decoded = jsonDecode(response.body);
          if (decoded is List) {
            print('History: Received ${decoded.length} translations');
            return List<Map<String, dynamic>>.from(decoded);
          } else {
            print('History: Response is not a list: $decoded');
            return [];
          }
        } catch (e) {
          print('History: Error decoding response: $e');
          return [];
        }
      } else if (response.statusCode == 401) {
        print('History: Unauthorized - token may be invalid');
        throw Exception('Authentication failed. Please login again.');
      } else {
        print('History: Error status ${response.statusCode}: ${response.body}');
        throw Exception('Failed to load translation history: ${response.statusCode}');
      }
    } catch (e) {
      print('History: Exception: $e');
      throw Exception('Error loading history: ${e.toString()}');
    }
  }

  void _refreshHistory() {
    setState(() {
      _translationHistory = fetchTranslationHistory();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppTheme.backgroundGradient),
        child: SafeArea(
          child: Column(
            children: [
              // Header
              _buildHeader(),
              
              // Search and Sort Bar
              _buildSearchAndSortBar(),
              
              // History List
              Expanded(
                child: FutureBuilder<List<Map<String, dynamic>>>(
                  future: _translationHistory,
                  builder: (context, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting) {
                      return const Center(
                        child: CircularProgressIndicator(color: AppTheme.accentTeal),
                      );
                    } else if (snapshot.hasError) {
                      return _buildErrorState();
                    } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
                      return _buildEmptyState();
                    } else {
                      final filteredAndSorted = _filterAndSort(snapshot.data!);
                      if (filteredAndSorted.isEmpty && _searchQuery.isNotEmpty) {
                        return _buildNoResultsState();
                      }
                      return _buildHistoryList(filteredAndSorted);
                    }
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'History',
                style: GoogleFonts.poppins(
                  fontSize: 28,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textPrimary,
                ),
              ),
              Text(
                'Your translation history',
                style: GoogleFonts.poppins(
                  fontSize: 14,
                  color: AppTheme.textSecondary,
                ),
              ),
            ],
          ),
          IconButton(
            onPressed: _refreshHistory,
            icon: const Icon(
              Icons.refresh_rounded,
              color: AppTheme.accentTeal,
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildSearchAndSortBar() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        children: [
          // Search Bar
          Container(
            decoration: BoxDecoration(
              color: AppTheme.cardBackground,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: AppTheme.divider.withOpacity(0.3),
              ),
            ),
            child: TextField(
              controller: _searchController,
              onChanged: (value) {
                setState(() {
                  _searchQuery = value;
                });
              },
              style: GoogleFonts.poppins(color: AppTheme.textPrimary),
              decoration: InputDecoration(
                hintText: 'Search translations...',
                hintStyle: GoogleFonts.poppins(color: AppTheme.textMuted),
                prefixIcon: Icon(Icons.search, color: AppTheme.textMuted),
                suffixIcon: _searchQuery.isNotEmpty
                    ? IconButton(
                        icon: Icon(Icons.clear, color: AppTheme.textMuted),
                        onPressed: () {
                          _searchController.clear();
                          setState(() {
                            _searchQuery = '';
                          });
                        },
                      )
                    : null,
                border: InputBorder.none,
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              ),
            ),
          ),
          const SizedBox(height: 12),
          // Sort Options
          Row(
            children: [
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: AppTheme.cardBackground,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.sort, color: AppTheme.textMuted, size: 18),
                      const SizedBox(width: 8),
                      Expanded(
                        child: DropdownButton<String>(
                          value: _sortBy,
                          isExpanded: true,
                          underline: const SizedBox(),
                          dropdownColor: AppTheme.cardBackground,
                          style: GoogleFonts.poppins(
                            color: AppTheme.textPrimary,
                            fontSize: 14,
                          ),
                          items: [
                            DropdownMenuItem(
                              value: 'date',
                              child: Text('Date', style: GoogleFonts.poppins()),
                            ),
                            DropdownMenuItem(
                              value: 'type',
                              child: Text('Type', style: GoogleFonts.poppins()),
                            ),
                            DropdownMenuItem(
                              value: 'alphabetical',
                              child: Text('Alphabetical', style: GoogleFonts.poppins()),
                            ),
                          ],
                          onChanged: (value) {
                            setState(() {
                              _sortBy = value ?? 'date';
                            });
                          },
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 8),
              GestureDetector(
                onTap: () {
                  setState(() {
                    _sortAscending = !_sortAscending;
                  });
                },
                child: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AppTheme.cardBackground,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    _sortAscending ? Icons.arrow_upward : Icons.arrow_downward,
                    color: AppTheme.accentTeal,
                    size: 20,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
  
  Widget _buildNoResultsState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.search_off, size: 64, color: AppTheme.textMuted),
          const SizedBox(height: 16),
          Text(
            'No results found',
            style: GoogleFonts.poppins(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: AppTheme.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Try a different search term',
            style: GoogleFonts.poppins(
              fontSize: 14,
              color: AppTheme.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 100,
            height: 100,
            decoration: BoxDecoration(
              color: AppTheme.cardBackground,
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.history,
              size: 48,
              color: AppTheme.textMuted,
            ),
          ),
          const SizedBox(height: 24),
          Text(
            'No translations yet',
            style: GoogleFonts.poppins(
              fontSize: 20,
              fontWeight: FontWeight.w600,
              color: AppTheme.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Your translation history will appear here',
            style: GoogleFonts.poppins(
              fontSize: 14,
              color: AppTheme.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState() {
    return FutureBuilder<List<Map<String, dynamic>>>(
      future: _translationHistory,
      builder: (context, snapshot) {
        String errorMessage = 'Failed to load history';
        if (snapshot.hasError) {
          errorMessage = snapshot.error.toString().replaceAll('Exception: ', '');
        }
        
        return Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(
                Icons.error_outline,
                size: 64,
                color: AppTheme.error,
              ),
              const SizedBox(height: 16),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: Text(
                  errorMessage,
                  style: GoogleFonts.poppins(
                    fontSize: 16,
                    color: AppTheme.textPrimary,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
              const SizedBox(height: 16),
              GradientButton(
                text: 'Retry',
                onPressed: _refreshHistory,
                width: 120,
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildHistoryList(List<Map<String, dynamic>> history) {
    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      physics: const BouncingScrollPhysics(),
      itemCount: history.length,
      itemBuilder: (context, index) {
        final entry = history[index];
        return AnimatedBuilder(
          animation: _animationController,
          builder: (context, child) {
            final delay = index * 0.1;
            final animation = Tween<double>(begin: 0.0, end: 1.0).animate(
              CurvedAnimation(
                parent: _animationController,
                curve: Interval(delay.clamp(0.0, 0.9), 1.0, curve: Curves.easeOut),
              ),
            );
            return FadeTransition(
              opacity: animation,
              child: SlideTransition(
                position: Tween<Offset>(
                  begin: const Offset(0, 0.3),
                  end: Offset.zero,
                ).animate(animation),
                child: _buildHistoryCard(entry),
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildHistoryCard(Map<String, dynamic> entry) {
    final inputType = entry['input_type'] ?? 'unknown';
    final IconData typeIcon;
    final String typeLabel;

    switch (inputType) {
      case 'image':
        typeIcon = Icons.image_outlined;
        typeLabel = 'Image';
        break;
      case 'video':
        typeIcon = Icons.videocam_outlined;
        typeLabel = 'Video';
        break;
      case 'live':
        typeIcon = Icons.live_tv_outlined;
        typeLabel = 'Live';
        break;
      default:
        typeIcon = Icons.translate;
        typeLabel = 'Translation';
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: AppTheme.glassCard,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: AppTheme.accentTeal.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    typeIcon,
                    color: AppTheme.accentTeal,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        typeLabel,
                        style: GoogleFonts.poppins(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.textPrimary,
                        ),
                      ),
                      Text(
                        _formatDate(entry['created_at']),
                        style: GoogleFonts.poppins(
                          fontSize: 12,
                          color: AppTheme.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          
          // Media Preview
          if (inputType == 'image')
            _buildImagePreview(entry)
          else if (inputType == 'video' || inputType == 'live')
            _buildVideoPreview(entry),
          
          // Translation
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(
                      Icons.translate,
                      size: 16,
                      color: AppTheme.textMuted,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Translation',
                      style: GoogleFonts.poppins(
                        fontSize: 12,
                        color: AppTheme.textMuted,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  _formatTranslatedText(entry['translated_text']),
                  style: GoogleFonts.poppins(
                    fontSize: 16,
                    color: AppTheme.textPrimary,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 12),
                // Action Buttons
                Row(
                  children: [
                    _buildActionButton(
                      icon: Icons.copy,
                      label: 'Copy',
                      onTap: () => _copyToClipboard(_formatTranslatedText(entry['translated_text'])),
                    ),
                    const SizedBox(width: 8),
                    _buildActionButton(
                      icon: Icons.share,
                      label: 'Share',
                      onTap: () => _shareTranslation(entry),
                    ),
                    const SizedBox(width: 8),
                    _buildActionButton(
                      icon: Icons.note_add,
                      label: 'Note',
                      onTap: () => _showNoteDialog(entry),
                    ),
                  ],
                ),
                // Note Display
                if (entry['note'] != null && entry['note'].toString().isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppTheme.accentTeal.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: AppTheme.accentTeal.withOpacity(0.3),
                      ),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(Icons.note, color: AppTheme.accentTeal, size: 16),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            entry['note'].toString(),
                            style: GoogleFonts.poppins(
                              fontSize: 12,
                              color: AppTheme.textPrimary,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
          
          // Audio Player
          if (entry['translated_audio'] != null) ...[
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: AudioWidget(
                audioUrl: _buildMediaUrl(entry['translated_audio']),
                translationId: entry['id'].toString(),
              ),
            ),
          ],
        ],
      ),
    );
  }

  String _buildMediaUrl(String? inputData) {
    if (inputData == null || inputData.isEmpty) {
      return '';
    }
    
    if (baseUrl == null || baseUrl!.isEmpty) {
      print('Warning: BASE_URL is not set, cannot construct media URL');
      return '';
    }
    
    final String baseUrlValue = baseUrl!;
    String path = inputData.toString().trim();
    print('_buildMediaUrl input: $path');
    
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

  Widget _buildImagePreview(Map<String, dynamic> entry) {
    final inputData = entry['input_data'];
    if (inputData == null || inputData.toString().isEmpty) {
      return Container(
        width: double.infinity,
        height: 200,
        margin: const EdgeInsets.symmetric(horizontal: 16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          color: AppTheme.inputBackground,
        ),
        child: const Center(
          child: Icon(Icons.image_not_supported, color: AppTheme.textMuted, size: 48),
        ),
      );
    }
    
    // Construct the image URL properly
    final imageUrl = _buildMediaUrl(inputData.toString());
    
    return Container(
      width: double.infinity,
      height: 200,
      margin: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: AppTheme.inputBackground,
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: Image.network(
          imageUrl,
          fit: BoxFit.cover,
          loadingBuilder: (context, child, loadingProgress) {
            if (loadingProgress == null) return child;
            return Center(
              child: CircularProgressIndicator(
                value: loadingProgress.expectedTotalBytes != null
                    ? loadingProgress.cumulativeBytesLoaded /
                        loadingProgress.expectedTotalBytes!
                    : null,
                color: AppTheme.accentTeal,
              ),
            );
          },
          errorBuilder: (context, error, stackTrace) {
            print('Image load error: $error for URL: $imageUrl');
            return const Center(
              child: Icon(Icons.broken_image, color: AppTheme.textMuted, size: 48),
            );
          },
        ),
      ),
    );
  }

  Widget _buildVideoPreview(Map<String, dynamic> entry) {
    final inputData = entry['input_data'];
    if (inputData == null || inputData.toString().isEmpty) {
      return Container(
        width: double.infinity,
        height: 200,
        margin: const EdgeInsets.symmetric(horizontal: 16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          color: AppTheme.inputBackground,
        ),
        child: const Center(
          child: Icon(Icons.videocam_off, color: AppTheme.textMuted, size: 48),
        ),
      );
    }
    
    // Construct the video URL properly
    final videoUrl = _buildMediaUrl(inputData.toString());
    
    return Container(
      width: double.infinity,
      height: 200,
      margin: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: AppTheme.inputBackground,
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: VideoWidget(videoUrl: videoUrl),
      ),
    );
  }

  String _formatTranslatedText(String? text) {
    if (text == null || text.isEmpty) {
      return 'No translation';
    }
    return text
        .replaceAll('[', '')
        .replaceAll(']', '')
        .replaceAll(',', '')
        .trim();
  }

  String _formatDate(String? dateString) {
    if (dateString == null || dateString.isEmpty) {
      return 'Unknown Date';
    }

    try {
      final DateTime dateTime = DateTime.parse(dateString);
      final now = DateTime.now();
      final difference = now.difference(dateTime);

      if (difference.inDays == 0) {
        if (difference.inHours == 0) {
          return '${difference.inMinutes} min ago';
        }
        return '${difference.inHours}h ago';
      } else if (difference.inDays == 1) {
        return 'Yesterday';
      } else if (difference.inDays < 7) {
        return '${difference.inDays} days ago';
      } else {
        return '${dateTime.day}/${dateTime.month}/${dateTime.year}';
      }
    } catch (e) {
      return 'Invalid Date';
    }
  }
  
  Widget _buildActionButton({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
  }) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
          decoration: BoxDecoration(
            color: AppTheme.inputBackground,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: AppTheme.divider.withOpacity(0.3),
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 16, color: AppTheme.accentTeal),
              const SizedBox(width: 6),
              Text(
                label,
                style: GoogleFonts.poppins(
                  fontSize: 12,
                  color: AppTheme.accentTeal,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class VideoWidget extends StatefulWidget {
  final String videoUrl;

  const VideoWidget({required this.videoUrl, super.key});

  @override
  _VideoWidgetState createState() => _VideoWidgetState();
}

class _VideoWidgetState extends State<VideoWidget> {
  late VideoPlayerController _controller;
  bool _isError = false;
  bool _isInitialized = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _initializeVideo();
  }

  void _initializeVideo() {
    try {
      print('VideoWidget: Initializing video from URL: ${widget.videoUrl}');
      
      // Parse the URL and ensure proper encoding
      Uri videoUri;
      try {
        videoUri = Uri.parse(widget.videoUrl);
        // If parsing fails, try encoding the path
        if (videoUri.hasScheme && videoUri.hasAuthority) {
          // URL is valid, use as is
        } else {
          // Try to fix the URL
          final parts = widget.videoUrl.split('/');
          final scheme = parts[0].replaceAll(':', '');
          final authority = parts.length > 2 ? parts[2] : '';
          final path = parts.length > 3 ? '/' + parts.sublist(3).join('/') : '/';
          videoUri = Uri(scheme: scheme, host: authority, path: path);
        }
      } catch (e) {
        print('VideoWidget: Error parsing URL, trying alternative: $e');
        // Fallback: try to construct URL manually
        final urlString = widget.videoUrl.replaceAll(' ', '%20');
        videoUri = Uri.parse(urlString);
      }
      
      print('VideoWidget: Using URI: $videoUri');
      
      _controller = VideoPlayerController.networkUrl(videoUri)
        ..initialize().then((_) {
          if (mounted) {
            print('VideoWidget: Video initialized successfully');
            setState(() {
              _isInitialized = true;
              _isError = false;
            });
          }
        }).catchError((error) {
          print('VideoWidget: Error initializing video: $error');
          if (mounted) {
            setState(() {
              _isError = true;
              _errorMessage = error.toString();
            });
          }
        });
    } catch (e) {
      print('VideoWidget: Exception creating controller: $e');
      if (mounted) {
        setState(() {
          _isError = true;
          _errorMessage = e.toString();
        });
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_isError) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, color: AppTheme.textMuted, size: 48),
            const SizedBox(height: 8),
            Text(
              'Failed to load video',
              style: GoogleFonts.poppins(
                color: AppTheme.textMuted,
                fontSize: 12,
              ),
            ),
            if (_errorMessage != null) ...[
              const SizedBox(height: 4),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Text(
                  _errorMessage!.length > 50 
                    ? '${_errorMessage!.substring(0, 50)}...' 
                    : _errorMessage!,
                  style: GoogleFonts.poppins(
                    color: AppTheme.textMuted,
                    fontSize: 10,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ],
            const SizedBox(height: 8),
            TextButton.icon(
              onPressed: _initializeVideo,
              icon: const Icon(Icons.refresh, size: 16, color: AppTheme.accentTeal),
              label: Text(
                'Retry',
                style: GoogleFonts.poppins(
                  color: AppTheme.accentTeal,
                  fontSize: 12,
                ),
              ),
            ),
          ],
        ),
      );
    }

    return _isInitialized
        ? Stack(
            alignment: Alignment.center,
            children: [
              AspectRatio(
                aspectRatio: _controller.value.aspectRatio,
                child: VideoPlayer(_controller),
              ),
              GestureDetector(
                onTap: () {
                  setState(() {
                    if (_controller.value.isPlaying) {
                      _controller.pause();
                    } else {
                      _controller.play();
                    }
                  });
                },
                child: Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    color: AppTheme.primaryDark.withOpacity(0.7),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    _controller.value.isPlaying ? Icons.pause : Icons.play_arrow,
                    color: AppTheme.accentTeal,
                    size: 32,
                  ),
                ),
              ),
            ],
          )
        : const Center(
            child: CircularProgressIndicator(color: AppTheme.accentTeal),
          );
  }
}

class AudioWidget extends StatefulWidget {
  final String audioUrl;
  final String? translationId;

  const AudioWidget({required this.audioUrl, this.translationId, super.key});

  @override
  _AudioWidgetState createState() => _AudioWidgetState();
}

class _AudioWidgetState extends State<AudioWidget> {
  late AudioPlayer _audioPlayer;
  bool isPlaying = false;
  bool _isError = false;
  double _playbackSpeed = 1.0;

  @override
  void initState() {
    super.initState();
    _audioPlayer = AudioPlayer();
    _audioPlayer.onPlayerStateChanged.listen((state) {
      if (mounted) {
        setState(() {
          isPlaying = state == PlayerState.playing;
        });
      }
    });
    // Listen for when audio completes to reset state
    _audioPlayer.onPlayerComplete.listen((_) {
      if (mounted) {
        setState(() {
          isPlaying = false;
        });
      }
    });
  }

  void _togglePlayPause() async {
    try {
      if (isPlaying) {
        await _audioPlayer.pause();
      } else {
        // Handle different player states
        if (_audioPlayer.state == PlayerState.completed) {
          // If audio completed, stop and reset before playing again
          await _audioPlayer.stop();
          await _audioPlayer.setSourceUrl(widget.audioUrl);
        } else if (_audioPlayer.state == PlayerState.stopped) {
          // If stopped, set source before playing
          await _audioPlayer.setSourceUrl(widget.audioUrl);
        }
        // Set playback speed and resume
        await _audioPlayer.setPlaybackRate(_playbackSpeed);
        await _audioPlayer.resume();
      }
    } catch (e) {
      setState(() {
        _isError = true;
      });
    }
  }
  
  void _showSpeedDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppTheme.cardBackground,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text(
          'Playback Speed',
          style: GoogleFonts.poppins(
            color: AppTheme.textPrimary,
            fontWeight: FontWeight.w600,
          ),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '${_playbackSpeed}x',
              style: GoogleFonts.poppins(
                fontSize: 24,
                fontWeight: FontWeight.w700,
                color: AppTheme.accentTeal,
              ),
            ),
            const SizedBox(height: 16),
            Slider(
              value: _playbackSpeed,
              min: 0.5,
              max: 2.0,
              divisions: 6,
              label: '${_playbackSpeed}x',
              activeColor: AppTheme.accentTeal,
              onChanged: (value) {
                setState(() {
                  _playbackSpeed = value;
                });
                _audioPlayer.setPlaybackRate(value);
              },
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('0.5x', style: GoogleFonts.poppins(color: AppTheme.textMuted, fontSize: 12)),
                Text('1.0x', style: GoogleFonts.poppins(color: AppTheme.textMuted, fontSize: 12)),
                Text('2.0x', style: GoogleFonts.poppins(color: AppTheme.textMuted, fontSize: 12)),
              ],
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(
              'Done',
              style: GoogleFonts.poppins(
                color: AppTheme.accentTeal,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _audioPlayer.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_isError) {
      return Text(
        'Failed to load audio',
        style: GoogleFonts.poppins(color: AppTheme.textMuted, fontSize: 12),
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppTheme.accentTeal.withOpacity(0.15),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          GestureDetector(
            onTap: _togglePlayPause,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  isPlaying ? Icons.pause_circle : Icons.play_circle,
                  color: AppTheme.accentTeal,
                  size: 24,
                ),
                const SizedBox(width: 10),
                Text(
                  isPlaying ? 'Pause' : 'Play',
                  style: GoogleFonts.poppins(
                    color: AppTheme.accentTeal,
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          const Spacer(),
          GestureDetector(
            onTap: _showSpeedDialog,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.speed, color: AppTheme.textMuted, size: 18),
                const SizedBox(width: 4),
                Text(
                  '${_playbackSpeed}x',
                  style: GoogleFonts.poppins(
                    color: AppTheme.textMuted,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
