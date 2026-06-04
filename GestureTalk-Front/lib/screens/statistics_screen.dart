import 'dart:async';
import 'package:flutter/material.dart';
import 'package:gesture_talk/services/statistics_service.dart';
import 'package:gesture_talk/theme/app_theme.dart';
import 'package:google_fonts/google_fonts.dart';

class StatisticsScreen extends StatefulWidget {
  const StatisticsScreen({super.key});

  @override
  State<StatisticsScreen> createState() => _StatisticsScreenState();
}

class _StatisticsScreenState extends State<StatisticsScreen>
    with SingleTickerProviderStateMixin {
  final StatisticsService _statsService = StatisticsService();
  bool _isLoading = true;
  Map<String, dynamic> _usageStats = {};
  List<Map<String, dynamic>> _dailyUsage = [];
  List<Map<String, dynamic>> _weeklyUsage = [];
  List<Map<String, dynamic>> _monthlyUsage = [];
  List<Map<String, dynamic>> _topWords = [];
  Duration _totalUsageTime = Duration.zero;
  String _selectedPeriod = 'day'; // 'day', 'week', 'month'
  
  late AnimationController _animationController;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _loadStatistics();
    
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
    _animationController.dispose();
    super.dispose();
  }

  Future<void> _loadStatistics() async {
    setState(() {
      _isLoading = true;
    });

    try {
      final translations = await _statsService.getAllTranslations();
      final stats = _statsService.calculateUsageStats(translations);
      final daily = _statsService.getDailyUsage(translations);
      final weekly = _statsService.getWeeklyUsage(translations);
      final monthly = _statsService.getMonthlyUsage(translations);
      final usageTime = await _statsService.getTotalUsageTime();

      setState(() {
        _usageStats = stats;
        _dailyUsage = daily;
        _weeklyUsage = weekly;
        _monthlyUsage = monthly;
        _topWords = List<Map<String, dynamic>>.from(stats['topWords'] ?? []);
        _totalUsageTime = usageTime;
        _isLoading = false;
      });
    } catch (e) {
      print('Error loading statistics: $e');
      setState(() {
        _isLoading = false;
      });
    }
  }

  String _formatDuration(Duration duration) {
    final hours = duration.inHours;
    final minutes = duration.inMinutes.remainder(60);
    
    if (hours > 0) {
      return '${hours}h ${minutes}m';
    } else {
      return '${minutes}m';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppTheme.backgroundGradient),
        child: SafeArea(
          child: _isLoading
              ? const Center(
                  child: CircularProgressIndicator(color: AppTheme.accentTeal),
                )
              : FadeTransition(
                  opacity: _fadeAnimation,
                  child: RefreshIndicator(
                    onRefresh: _loadStatistics,
                    color: AppTheme.accentTeal,
                    child: SingleChildScrollView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 24),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const SizedBox(height: 20),
                            
                            // Header
                            _buildHeader(),
                            
                            const SizedBox(height: 32),
                            
                            // Quick Stats Cards
                            _buildQuickStats(),
                            
                            const SizedBox(height: 24),
                            
                            // Usage Chart
                            _buildUsageChart(),
                            
                            const SizedBox(height: 24),
                            
                            // Type Distribution
                            _buildTypeDistribution(),
                            
                            const SizedBox(height: 24),
                            
                            // Top Words
                            if (_topWords.isNotEmpty) _buildTopWords(),
                            
                            const SizedBox(height: 24),
                            
                            // Usage Time
                            _buildUsageTime(),
                            
                            const SizedBox(height: 32),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Statistics',
              style: GoogleFonts.poppins(
                fontSize: 28,
                fontWeight: FontWeight.w700,
                color: AppTheme.textPrimary,
              ),
            ),
            Text(
              'Your usage insights',
              style: GoogleFonts.poppins(
                fontSize: 14,
                color: AppTheme.textSecondary,
              ),
            ),
          ],
        ),
        IconButton(
          onPressed: _loadStatistics,
          icon: const Icon(
            Icons.refresh_rounded,
            color: AppTheme.accentTeal,
          ),
        ),
      ],
    );
  }

  Widget _buildQuickStats() {
    return Row(
      children: [
        Expanded(
          child: _buildStatCard(
            label: 'Today',
            value: '${_usageStats['today'] ?? 0}',
            icon: Icons.today,
            color: AppTheme.accentTeal,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildStatCard(
            label: 'This Week',
            value: '${_usageStats['week'] ?? 0}',
            icon: Icons.calendar_view_week,
            color: AppTheme.accentCyan,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildStatCard(
            label: 'Total',
            value: '${_usageStats['total'] ?? 0}',
            icon: Icons.history,
            color: AppTheme.success,
          ),
        ),
      ],
    );
  }

  Widget _buildStatCard({
    required String label,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: AppTheme.glassCard,
      child: Column(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: color.withOpacity(0.15),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: color, size: 20),
          ),
          const SizedBox(height: 12),
          Text(
            value,
            style: GoogleFonts.poppins(
              fontSize: 24,
              fontWeight: FontWeight.w700,
              color: AppTheme.textPrimary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: GoogleFonts.poppins(
              fontSize: 12,
              color: AppTheme.textMuted,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildUsageChart() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: AppTheme.glassCard,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Usage Trend',
                style: GoogleFonts.poppins(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.textPrimary,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.inputBackground,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: DropdownButton<String>(
                  value: _selectedPeriod,
                  underline: const SizedBox(),
                  dropdownColor: AppTheme.cardBackground,
                  style: GoogleFonts.poppins(
                    color: AppTheme.textPrimary,
                    fontSize: 12,
                  ),
                  items: const [
                    DropdownMenuItem(value: 'day', child: Text('7 Days')),
                    DropdownMenuItem(value: 'week', child: Text('4 Weeks')),
                    DropdownMenuItem(value: 'month', child: Text('6 Months')),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _selectedPeriod = value ?? 'week';
                    });
                    _loadStatistics();
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          SizedBox(
            height: 200,
            child: _buildBarChart(),
          ),
        ],
      ),
    );
  }

  Widget _buildBarChart() {
    List<Map<String, dynamic>> chartData = [];
    String labelKey = 'date';
    String valueKey = 'count';

    if (_selectedPeriod == 'day') {
      chartData = _dailyUsage;
      labelKey = 'dayName';
    } else if (_selectedPeriod == 'week') {
      chartData = _weeklyUsage;
      labelKey = 'week';
    } else {
      chartData = _monthlyUsage;
      labelKey = 'month';
    }

    if (chartData.isEmpty) {
      return Center(
        child: Text(
          'No data available',
          style: GoogleFonts.poppins(
            color: AppTheme.textMuted,
            fontSize: 14,
          ),
        ),
      );
    }

    final values = chartData.map((e) => e[valueKey] as int).toList();
    if (values.isEmpty) {
      return Center(
        child: Text(
          'No data available',
          style: GoogleFonts.poppins(
            color: AppTheme.textMuted,
            fontSize: 14,
          ),
        ),
      );
    }
    final maxValue = values.reduce((a, b) => a > b ? a : b);

    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: chartData.map((data) {
        final value = data[valueKey] as int;
        final label = data[labelKey] as String;
        final height = maxValue > 0 ? (value / maxValue) : 0.0;

        return Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Text(
                  value.toString(),
                  style: GoogleFonts.poppins(
                    fontSize: 10,
                    color: AppTheme.textSecondary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Expanded(
                  child: Container(
                    margin: const EdgeInsets.symmetric(horizontal: 2),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.bottomCenter,
                        end: Alignment.topCenter,
                        colors: [
                          AppTheme.accentTeal,
                          AppTheme.accentCyan,
                        ],
                      ),
                      borderRadius: const BorderRadius.vertical(
                        top: Radius.circular(4),
                      ),
                    ),
                    height: double.infinity,
                    child: FractionallySizedBox(
                      heightFactor: height,
                      alignment: Alignment.bottomCenter,
                      child: Container(
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            begin: Alignment.bottomCenter,
                            end: Alignment.topCenter,
                            colors: [
                              AppTheme.accentTeal,
                              AppTheme.accentCyan,
                            ],
                          ),
                          borderRadius: const BorderRadius.vertical(
                            top: Radius.circular(4),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  label.length > 6 ? label.substring(0, 6) : label,
                  style: GoogleFonts.poppins(
                    fontSize: 9,
                    color: AppTheme.textMuted,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildTypeDistribution() {
    final typeCount = Map<String, int>.from(_usageStats['byType'] ?? {});
    
    if (typeCount.isEmpty) {
      return const SizedBox.shrink();
    }

    final total = typeCount.values.reduce((a, b) => a + b);
    final sortedTypes = typeCount.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: AppTheme.glassCard,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'By Type',
            style: GoogleFonts.poppins(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: AppTheme.textPrimary,
            ),
          ),
          const SizedBox(height: 20),
          ...sortedTypes.map((entry) {
            final percentage = total > 0 ? (entry.value / total) : 0.0;
            final type = entry.key;
            final count = entry.value;
            
            IconData icon;
            Color color;
            String label;
            
            switch (type) {
              case 'image':
                icon = Icons.image_outlined;
                color = AppTheme.accentTeal;
                label = 'Image';
                break;
              case 'video':
                icon = Icons.videocam_outlined;
                color = AppTheme.accentCyan;
                label = 'Video';
                break;
              case 'live':
                icon = Icons.live_tv_outlined;
                color = AppTheme.success;
                label = 'Live';
                break;
              case 'voice':
                icon = Icons.mic_outlined;
                color = AppTheme.warning;
                label = 'Voice';
                break;
              default:
                icon = Icons.translate;
                color = AppTheme.textMuted;
                label = type.toUpperCase();
            }

            return Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          Icon(icon, color: color, size: 18),
                          const SizedBox(width: 8),
                          Text(
                            label,
                            style: GoogleFonts.poppins(
                              fontSize: 14,
                              fontWeight: FontWeight.w500,
                              color: AppTheme.textPrimary,
                            ),
                          ),
                        ],
                      ),
                      Text(
                        '$count (${(percentage * 100).toStringAsFixed(0)}%)',
                        style: GoogleFonts.poppins(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.textSecondary,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: percentage,
                      minHeight: 6,
                      backgroundColor: AppTheme.inputBackground,
                      valueColor: AlwaysStoppedAnimation<Color>(color),
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildTopWords() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: AppTheme.glassCard,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.trending_up, color: AppTheme.accentTeal, size: 20),
              const SizedBox(width: 8),
              Text(
                'Most Used Words',
                style: GoogleFonts.poppins(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _topWords.asMap().entries.map((entry) {
              final index = entry.key;
              final word = entry.value['word'] as String;
              final count = entry.value['count'] as int;
              
              return Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  gradient: index < 3
                      ? LinearGradient(
                          colors: [
                            AppTheme.accentTeal.withOpacity(0.2),
                            AppTheme.accentCyan.withOpacity(0.2),
                          ],
                        )
                      : null,
                  color: index >= 3
                      ? AppTheme.inputBackground
                      : null,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: index < 3
                        ? AppTheme.accentTeal.withOpacity(0.5)
                        : AppTheme.divider.withOpacity(0.3),
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (index < 3)
                      Container(
                        width: 20,
                        height: 20,
                        decoration: BoxDecoration(
                          color: AppTheme.accentTeal,
                          shape: BoxShape.circle,
                        ),
                        child: Center(
                          child: Text(
                            '${index + 1}',
                            style: GoogleFonts.poppins(
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              color: AppTheme.primaryDark,
                            ),
                          ),
                        ),
                      ),
                    if (index < 3) const SizedBox(width: 6),
                    Text(
                      word,
                      style: GoogleFonts.poppins(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      '($count)',
                      style: GoogleFonts.poppins(
                        fontSize: 12,
                        color: AppTheme.textMuted,
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildUsageTime() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: AppTheme.glassCard,
      child: Row(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              gradient: AppTheme.primaryGradient,
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(
              Icons.access_time,
              color: AppTheme.textPrimary,
              size: 28,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Total Usage Time',
                  style: GoogleFonts.poppins(
                    fontSize: 14,
                    color: AppTheme.textMuted,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  _formatDuration(_totalUsageTime),
                  style: GoogleFonts.poppins(
                    fontSize: 24,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
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

