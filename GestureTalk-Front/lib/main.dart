import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:gesture_talk/screens/login_screen.dart';
import 'package:gesture_talk/widgets/bottom_navigation_bar.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:gesture_talk/theme/app_theme.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:gesture_talk/services/connectivity_service.dart';
import 'package:gesture_talk/services/statistics_service.dart';
import 'package:gesture_talk/widgets/app_lifecycle_wrapper.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Disable debug overflow banner (yellow/black stripes)
  ErrorWidget.builder = (FlutterErrorDetails details) {
    return Container(
      color: AppTheme.primaryDark,
      child: Center(
        child: Text(
          'An error occurred',
          style: GoogleFonts.poppins(color: AppTheme.textPrimary),
        ),
      ),
    );
  };
  
  // Set system UI overlay style for immersive dark theme
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
      systemNavigationBarColor: AppTheme.primaryDark,
      systemNavigationBarIconBrightness: Brightness.light,
    ),
  );
  
  await dotenv.load();
  print('BASE_URL: ${dotenv.env['BASE_URL']}');
  
  // Track app session start for statistics
  final statsService = StatisticsService();
  await statsService.trackSessionStart();
  
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => ConnectivityService(),
      child: AppLifecycleWrapper(
        child: MaterialApp(
          title: 'GestureTalk',
          debugShowCheckedModeBanner: false,
          theme: AppTheme.darkTheme.copyWith(
            textTheme: GoogleFonts.poppinsTextTheme(
              AppTheme.darkTheme.textTheme,
            ),
          ),
          home: FutureBuilder<bool>(
            future: _checkToken(context),
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const _SplashScreen();
              }
              if (snapshot.hasError) {
                return const Center(child: Text('An error occurred'));
              }
              return snapshot.data == true
                  ? const MyBottomNavigationBar()
                  : const LoginPage();
            },
          ),
        ),
      ),
    );
  }
}

class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppTheme.backgroundGradient),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Animated logo with glow
              Container(
                width: 120,
                height: 120,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.accentTeal.withOpacity(0.4),
                      blurRadius: 40,
                      spreadRadius: 10,
                    ),
                  ],
                ),
                child: ClipOval(
                  child: Image.asset(
                    'assets/images/sign.jfif',
                    fit: BoxFit.cover,
                  ),
                ),
              ),
              const SizedBox(height: 32),
              Text(
                'GestureTalk',
                style: GoogleFonts.poppins(
                  fontSize: 32,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textPrimary,
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Breaking barriers through signs',
                style: GoogleFonts.poppins(
                  fontSize: 14,
                  color: AppTheme.textSecondary,
                ),
              ),
              const SizedBox(height: 48),
              const SizedBox(
                width: 32,
                height: 32,
                child: CircularProgressIndicator(
                  strokeWidth: 3,
                  valueColor: AlwaysStoppedAnimation<Color>(AppTheme.accentTeal),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

Future<bool> _checkToken(BuildContext context) async {
  const storage = FlutterSecureStorage();
  final token = await storage.read(key: 'jwt_token');
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
        await storage.delete(key: 'jwt_token');
        return false;
      }
    } else {
      await storage.delete(key: 'jwt_token');
      return false;
    }
  } catch (e) {
    return false;
  }
}
