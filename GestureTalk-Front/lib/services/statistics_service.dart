import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

class StatisticsService {
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  final String? baseUrl = dotenv.env['BASE_URL'];

  // Get all translations for statistics
  Future<List<Map<String, dynamic>>> getAllTranslations() async {
    try {
      final token = await _storage.read(key: 'jwt_token');
      if (token == null) return [];

      final response = await http.get(
        Uri.parse('$baseUrl/api/get-translations'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body);
        if (decoded is List) {
          return List<Map<String, dynamic>>.from(decoded);
        }
      }
      return [];
    } catch (e) {
      print('Error fetching translations for stats: $e');
      return [];
    }
  }

  // Calculate usage statistics
  Map<String, dynamic> calculateUsageStats(List<Map<String, dynamic>> translations) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final weekAgo = today.subtract(const Duration(days: 7));
    final monthAgo = today.subtract(const Duration(days: 30));

    int todayCount = 0;
    int weekCount = 0;
    int monthCount = 0;
    int totalCount = translations.length;

    Map<String, int> typeCount = {};
    Map<String, int> wordFrequency = {};

    for (var translation in translations) {
      final createdAt = _parseDate(translation['created_at']);
      final type = translation['input_type']?.toString() ?? 'unknown';
      final text = translation['translated_text']?.toString() ?? '';

      // Count by date
      if (createdAt.isAfter(today)) {
        todayCount++;
      }
      if (createdAt.isAfter(weekAgo)) {
        weekCount++;
      }
      if (createdAt.isAfter(monthAgo)) {
        monthCount++;
      }

      // Count by type
      typeCount[type] = (typeCount[type] ?? 0) + 1;

      // Count word frequency
      final words = text
          .toLowerCase()
          .replaceAll(RegExp(r'[^\w\s]'), ' ')
          .split(' ')
          .where((w) => w.length > 2)
          .toList();
      
      for (var word in words) {
        wordFrequency[word] = (wordFrequency[word] ?? 0) + 1;
      }
    }

    // Get top words
    final sortedWords = wordFrequency.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    final topWords = sortedWords.take(10).map((e) => {
      'word': e.key,
      'count': e.value,
    }).toList();

    return {
      'total': totalCount,
      'today': todayCount,
      'week': weekCount,
      'month': monthCount,
      'byType': typeCount,
      'topWords': topWords,
    };
  }

  // Get daily usage for chart (last 7 days)
  List<Map<String, dynamic>> getDailyUsage(List<Map<String, dynamic>> translations) {
    final now = DateTime.now();
    final dailyCounts = <String, int>{};

    // Initialize last 7 days
    for (int i = 6; i >= 0; i--) {
      final date = now.subtract(Duration(days: i));
      final dateKey = '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
      dailyCounts[dateKey] = 0;
    }

    // Count translations per day
    for (var translation in translations) {
      final createdAt = _parseDate(translation['created_at']);
      final dateKey = '${createdAt.year}-${createdAt.month.toString().padLeft(2, '0')}-${createdAt.day.toString().padLeft(2, '0')}';
      
      if (dailyCounts.containsKey(dateKey)) {
        dailyCounts[dateKey] = (dailyCounts[dateKey] ?? 0) + 1;
      }
    }

    return dailyCounts.entries.map((e) => {
      'date': e.key,
      'count': e.value,
      'dayName': _getDayName(e.key),
    }).toList();
  }

  // Get weekly usage for chart (last 4 weeks)
  List<Map<String, dynamic>> getWeeklyUsage(List<Map<String, dynamic>> translations) {
    final now = DateTime.now();
    final weeklyCounts = <String, int>{};

    // Initialize last 4 weeks
    for (int i = 3; i >= 0; i--) {
      final weekStart = now.subtract(Duration(days: i * 7));
      final weekKey = 'Week ${4 - i}';
      weeklyCounts[weekKey] = 0;
    }

    // Count translations per week
    for (var translation in translations) {
      final createdAt = _parseDate(translation['created_at']);
      final daysDiff = now.difference(createdAt).inDays;
      final weekIndex = (daysDiff / 7).floor();
      
      if (weekIndex >= 0 && weekIndex < 4) {
        final weekKey = 'Week ${4 - weekIndex}';
        weeklyCounts[weekKey] = (weeklyCounts[weekKey] ?? 0) + 1;
      }
    }

    return weeklyCounts.entries.map((e) => {
      'week': e.key,
      'count': e.value,
    }).toList();
  }

  // Get monthly usage for chart (last 6 months)
  List<Map<String, dynamic>> getMonthlyUsage(List<Map<String, dynamic>> translations) {
    final now = DateTime.now();
    final monthlyCounts = <String, int>{};

    // Initialize last 6 months
    for (int i = 5; i >= 0; i--) {
      final month = now.subtract(Duration(days: i * 30));
      final monthKey = '${_getMonthName(month.month)} ${month.year}';
      monthlyCounts[monthKey] = 0;
    }

    // Count translations per month
    for (var translation in translations) {
      final createdAt = _parseDate(translation['created_at']);
      final monthKey = '${_getMonthName(createdAt.month)} ${createdAt.year}';
      
      if (monthlyCounts.containsKey(monthKey)) {
        monthlyCounts[monthKey] = (monthlyCounts[monthKey] ?? 0) + 1;
      }
    }

    return monthlyCounts.entries.map((e) => {
      'month': e.key,
      'count': e.value,
    }).toList();
  }

  // Track app usage time
  Future<void> trackSessionStart() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('session_start', DateTime.now().toIso8601String());
  }

  Future<Duration> getTotalUsageTime() async {
    final prefs = await SharedPreferences.getInstance();
    final totalSeconds = prefs.getInt('total_usage_seconds') ?? 0;
    return Duration(seconds: totalSeconds);
  }

  Future<void> trackSessionEnd() async {
    final prefs = await SharedPreferences.getInstance();
    final sessionStart = prefs.getString('session_start');
    if (sessionStart != null) {
      final start = DateTime.parse(sessionStart);
      final duration = DateTime.now().difference(start);
      final totalSeconds = (prefs.getInt('total_usage_seconds') ?? 0) + duration.inSeconds;
      await prefs.setInt('total_usage_seconds', totalSeconds);
      await prefs.remove('session_start');
    }
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

  String _getDayName(String dateKey) {
    try {
      final parts = dateKey.split('-');
      final date = DateTime(int.parse(parts[0]), int.parse(parts[1]), int.parse(parts[2]));
      final days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
      return days[date.weekday - 1];
    } catch (e) {
      return '';
    }
  }

  String _getMonthName(int month) {
    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];
    return months[month - 1];
  }
}










