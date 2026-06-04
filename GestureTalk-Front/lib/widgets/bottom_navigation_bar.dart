import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:gesture_talk/screens/history_screen.dart';
import 'package:gesture_talk/screens/live_translation_screen.dart';
import 'package:gesture_talk/screens/login_screen.dart';
import 'package:gesture_talk/screens/media_translation_screen.dart';
import 'package:gesture_talk/screens/profile_screen.dart';
import 'package:gesture_talk/screens/voice_to_sign_screen.dart';
import 'package:gesture_talk/screens/statistics_screen.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:gesture_talk/theme/app_theme.dart';
import 'package:google_fonts/google_fonts.dart';

class MyBottomNavigationBar extends StatefulWidget {
  const MyBottomNavigationBar({super.key});

  @override
  State<MyBottomNavigationBar> createState() => _MyBottomNavigationBarState();
}

class _MyBottomNavigationBarState extends State<MyBottomNavigationBar> {
  int _selectedIndex = 0;
  List<Widget>? _pages;
  List<_NavItem>? _navItems;
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  String? _userRole;

  @override
  void initState() {
    super.initState();
    _checkUserRole();
  }

  Future<void> _checkUserRole() async {
    _userRole = await _storage.read(key: 'role');

    if (_userRole == null) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (context) => const LoginPage()),
      );
    } else {
      _initializePages();
    }
  }

  void _initializePages() {
    setState(() {
      if (_userRole == 'regular') {
        _pages = [
          const LiveTranslationScreen(),
          const MediaTranslationPage(),
          const VoiceToSignScreen(),
          const HistoryPage(),
          const StatisticsScreen(),
          const ProfilePage(),
        ];
        _navItems = [
          _NavItem(icon: Icons.sign_language, activeIcon: Icons.sign_language, label: 'Live'),
          _NavItem(icon: Icons.perm_media_outlined, activeIcon: Icons.perm_media, label: 'Media'),
          _NavItem(icon: Icons.mic_outlined, activeIcon: Icons.mic, label: 'Voice'),
          _NavItem(icon: Icons.history_outlined, activeIcon: Icons.history, label: 'History'),
          _NavItem(icon: Icons.bar_chart_outlined, activeIcon: Icons.bar_chart, label: 'Stats'),
          _NavItem(icon: Icons.person_outline, activeIcon: Icons.person, label: 'Profile'),
        ];
      } else if (_userRole == 'mute') {
        _pages = [
          const MediaTranslationPage(),
          const HistoryPage(),
          const StatisticsScreen(),
          const ProfilePage(),
        ];
        _navItems = [
          _NavItem(icon: Icons.perm_media_outlined, activeIcon: Icons.perm_media, label: 'Media'),
          _NavItem(icon: Icons.history_outlined, activeIcon: Icons.history, label: 'History'),
          _NavItem(icon: Icons.bar_chart_outlined, activeIcon: Icons.bar_chart, label: 'Stats'),
          _NavItem(icon: Icons.person_outline, activeIcon: Icons.person, label: 'Profile'),
        ];
      }
    });
  }

  Future<bool> _checkToken(BuildContext context) async {
    final token = await _storage.read(key: 'jwt_token');
    final baseUrl = dotenv.env['BASE_URL'];

    if (token == null) {
      return false;
    }

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/verify-token'),
        headers: {
          'Authorization': 'Bearer $token',
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['valid']) {
          return true;
        } else {
          await _storage.delete(key: 'jwt_token');
          return false;
        }
      } else {
        await _storage.delete(key: 'jwt_token');
        return false;
      }
    } catch (e) {
      return false;
    }
  }

  void _onItemTapped(int index) async {
    bool isValid = await _checkToken(context);

    if (isValid) {
      setState(() {
        _selectedIndex = index;
      });
    } else {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (context) => const LoginPage()),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _pages == null
          ? Container(
              decoration: const BoxDecoration(gradient: AppTheme.backgroundGradient),
              child: const Center(
                child: CircularProgressIndicator(color: AppTheme.accentTeal),
              ),
            )
          : _pages![_selectedIndex],
      bottomNavigationBar: _pages == null || _navItems == null
          ? null
          : _buildCustomNavBar(),
    );
  }

  Widget _buildCustomNavBar() {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.primaryMid,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.3),
            blurRadius: 20,
            offset: const Offset(0, -5),
          ),
        ],
      ),
      child: SafeArea(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            mainAxisSize: MainAxisSize.max,
            children: List.generate(
              _navItems!.length,
              (index) => Expanded(
                child: _buildNavItem(index),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildNavItem(int index) {
    final item = _navItems![index];
    final isSelected = _selectedIndex == index;

    return GestureDetector(
      onTap: () => _onItemTapped(index),
      behavior: HitTestBehavior.opaque,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.accentTeal.withOpacity(0.15) : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              child: Icon(
                isSelected ? item.activeIcon : item.icon,
                color: isSelected ? AppTheme.accentTeal : AppTheme.textMuted,
                size: isSelected ? 22 : 20,
              ),
            ),
            const SizedBox(height: 2),
            Flexible(
              child: AnimatedDefaultTextStyle(
                duration: const Duration(milliseconds: 200),
                style: GoogleFonts.poppins(
                  fontSize: 10,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                  color: isSelected ? AppTheme.accentTeal : AppTheme.textMuted,
                ),
                child: Text(
                  item.label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.center,
                ),
              ),
            ),
            // Active indicator
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              margin: const EdgeInsets.only(top: 2),
              width: isSelected ? 16 : 0,
              height: 2,
              decoration: BoxDecoration(
                color: AppTheme.accentTeal,
                borderRadius: BorderRadius.circular(2),
                boxShadow: isSelected
                    ? [
                        BoxShadow(
                          color: AppTheme.accentTeal.withOpacity(0.5),
                          blurRadius: 6,
                          spreadRadius: 1,
                        ),
                      ]
                    : null,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _NavItem {
  final IconData icon;
  final IconData activeIcon;
  final String label;

  _NavItem({
    required this.icon,
    required this.activeIcon,
    required this.label,
  });
}
