import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import 'dart:io';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:gesture_talk/screens/sign_up_screen.dart';
import 'package:gesture_talk/widgets/bottom_navigation_bar.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:gesture_talk/theme/app_theme.dart';
import 'package:google_fonts/google_fonts.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  _LoginPageState createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> with SingleTickerProviderStateMixin {
  final _formKey = GlobalKey<FormState>();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final _storage = const FlutterSecureStorage();
  bool _isLoading = false;
  bool _obscurePassword = true;
  final baseUrl = dotenv.env['BASE_URL'];
  
  late AnimationController _animationController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    
    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _animationController,
        curve: const Interval(0.0, 0.6, curve: Curves.easeOut),
      ),
    );
    
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.3),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _animationController,
        curve: const Interval(0.2, 1.0, curve: Curves.easeOutCubic),
      ),
    );
    
    _animationController.forward();
  }

  @override
  void dispose() {
    _animationController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    if (_formKey.currentState!.validate()) {
      setState(() {
        _isLoading = true;
      });

      final url = baseUrl;
      if (url == null || url.isEmpty) {
        _showErrorSnackBar('App configuration error. Please contact support.');
        setState(() {
          _isLoading = false;
        });
        return;
      }

      try {
        final response = await http.post(
          Uri.parse('$url/api/login'),
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          body: json.encode({
            'email': _emailController.text,
            'password': _passwordController.text,
          }),
        ).timeout(const Duration(seconds: 30));

        // Check if response is JSON before parsing
        final contentType = response.headers['content-type'] ?? '';
        if (!contentType.contains('application/json')) {
          _showErrorSnackBar('Server returned unexpected format. Status: ${response.statusCode}\n\nResponse: ${response.body.substring(0, response.body.length > 200 ? 200 : response.body.length)}');
          print('Non-JSON response. Status: ${response.statusCode}, Content-Type: $contentType');
          print('Response body: ${response.body.substring(0, response.body.length > 500 ? 500 : response.body.length)}');
          return;
        }

        if (response.statusCode == 200) {
          final data = json.decode(response.body);
          final token = data['authorisation']['token'];
          final role = data['user']['user_type'];
          
          await _storage.write(key: 'jwt_token', value: token);
          await _storage.write(key: 'role', value: role);
          
          if (mounted) {
            Navigator.of(context).pushReplacement(
              PageRouteBuilder(
                pageBuilder: (context, animation, secondaryAnimation) =>
                    const MyBottomNavigationBar(),
                transitionsBuilder: (context, animation, secondaryAnimation, child) {
                  return FadeTransition(opacity: animation, child: child);
                },
                transitionDuration: const Duration(milliseconds: 500),
              ),
            );
          }
        } else {
          // Try to parse error response, but handle if it's not JSON
          try {
            final errorData = json.decode(response.body);
            final errorMessage = errorData['message'] ?? 'Invalid email or password';
            _showErrorSnackBar(errorMessage);
          } catch (e) {
            _showErrorSnackBar('Server error (${response.statusCode}): ${response.body.substring(0, response.body.length > 200 ? 200 : response.body.length)}');
            print('Error parsing response: $e');
            print('Response body: ${response.body}');
          }
        }
      } on SocketException catch (e) {
        final errorMsg = 'Cannot connect to server.\n\n'
            'URL: $url/api/login\n\n'
            'Please check:\n'
            '1. Backend server is running (php artisan serve)\n'
            '2. .env file has correct BASE_URL\n'
            '3. Phone and computer are on same WiFi';
        _showErrorSnackBar(errorMsg);
        print('Socket error: $e');
        print('Attempted URL: $url/api/login');
      } on http.ClientException catch (e) {
        final errorMsg = 'Connection error.\n\n'
            'URL: $url/api/login\n\n'
            'Please check your internet connection and backend server.';
        _showErrorSnackBar(errorMsg);
        print('Network error: $e');
        print('Attempted URL: $url/api/login');
      } on TimeoutException catch (e) {
        final errorMsg = 'Request timed out.\n\n'
            'URL: $url/api/login\n\n'
            'Server may be down or unreachable.';
        _showErrorSnackBar(errorMsg);
        print('Timeout error: $e');
        print('Attempted URL: $url/api/login');
      } on FormatException catch (e) {
        final errorMsg = 'Server returned invalid response format.\n\n'
            'Expected JSON but received HTML or other format.\n\n'
            'This usually means:\n'
            '1. Route not found (404)\n'
            '2. Server error page\n'
            '3. Middleware redirect';
        _showErrorSnackBar(errorMsg);
        print('Format error: $e');
        print('Attempted URL: $url/api/login');
      } catch (e) {
        // Check if it's a network-related error
        final errorString = e.toString().toLowerCase();
        String errorMsg;
        if (errorString.contains('socket') || 
            errorString.contains('network') || 
            errorString.contains('connection') ||
            errorString.contains('failed host lookup')) {
          errorMsg = 'Cannot connect to server.\n\n'
              'URL: $url/api/login\n\n'
              'Check: Backend running? Correct BASE_URL in .env?';
        } else {
          errorMsg = 'Error: ${e.toString()}';
        }
        _showErrorSnackBar(errorMsg);
        print('Login error: $e');
        print('Attempted URL: $url/api/login');
      } finally {
        if (mounted) {
          setState(() {
            _isLoading = false;
          });
        }
      }
    }
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.error_outline, color: AppTheme.error),
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
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppTheme.backgroundGradient),
        child: SafeArea(
          child: SingleChildScrollView(
            physics: const BouncingScrollPhysics(),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24.0),
              child: FadeTransition(
                opacity: _fadeAnimation,
                child: SlideTransition(
                  position: _slideAnimation,
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        const SizedBox(height: 60),
                        
                        // Animated Logo with glow effect
                        _buildAnimatedLogo(),
                        
                        const SizedBox(height: 24),
                        
                        // App name and tagline
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
                          'Sign in to continue',
                          style: GoogleFonts.poppins(
                            fontSize: 16,
                            color: AppTheme.textSecondary,
                          ),
                        ),
                        
                        const SizedBox(height: 48),
                        
                        // Glass card container for form
                        Container(
                          padding: const EdgeInsets.all(24),
                          decoration: AppTheme.glassCard,
                          child: Column(
                            children: [
                              // Email field
                              _buildTextField(
                                controller: _emailController,
                                label: 'Email',
                                hint: 'Enter your email',
                                prefixIcon: Icons.email_outlined,
                                keyboardType: TextInputType.emailAddress,
                                validator: (value) {
                                  if (value == null || value.isEmpty) {
                                    return 'Please enter your email';
                                  } else if (!RegExp(r'^[^@]+@[^@]+\.[^@]+').hasMatch(value)) {
                                    return 'Please enter a valid email';
                                  }
                                  return null;
                                },
                              ),
                              
                              const SizedBox(height: 20),
                              
                              // Password field
                              _buildTextField(
                                controller: _passwordController,
                                label: 'Password',
                                hint: 'Enter your password',
                                prefixIcon: Icons.lock_outline,
                                obscureText: _obscurePassword,
                                suffixIcon: IconButton(
                                  icon: Icon(
                                    _obscurePassword
                                        ? Icons.visibility_outlined
                                        : Icons.visibility_off_outlined,
                                    color: AppTheme.textMuted,
                                  ),
                                  onPressed: () {
                                    setState(() {
                                      _obscurePassword = !_obscurePassword;
                                    });
                                  },
                                ),
                                validator: (value) {
                                  if (value == null || value.isEmpty) {
                                    return 'Please enter your password';
                                  } else if (value.length < 6) {
                                    return 'Password must be at least 6 characters';
                                  }
                                  return null;
                                },
                              ),
                              
                              const SizedBox(height: 32),
                              
                              // Login button
                              GradientButton(
                                text: 'Sign In',
                                isLoading: _isLoading,
                                onPressed: _login,
                                icon: Icons.arrow_forward,
                              ),
                            ],
                          ),
                        ),
                        
                        const SizedBox(height: 32),
                        
                        // Sign up link
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              "Don't have an account? ",
                              style: GoogleFonts.poppins(
                                color: AppTheme.textSecondary,
                                fontSize: 14,
                              ),
                            ),
                            GestureDetector(
                              onTap: () {
                                Navigator.of(context).pushReplacement(
                                  PageRouteBuilder(
                                    pageBuilder: (context, animation, secondaryAnimation) =>
                                        const SignUpPage(),
                                    transitionsBuilder:
                                        (context, animation, secondaryAnimation, child) {
                                      return FadeTransition(opacity: animation, child: child);
                                    },
                                  ),
                                );
                              },
                              child: Text(
                                'Sign Up',
                                style: GoogleFonts.poppins(
                                  color: AppTheme.accentTeal,
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                        
                        const SizedBox(height: 40),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildAnimatedLogo() {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0.8, end: 1.0),
      duration: const Duration(seconds: 2),
      curve: Curves.easeInOut,
      builder: (context, scale, child) {
        return Transform.scale(
          scale: scale,
          child: Container(
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
        );
      },
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    String? hint,
    required IconData prefixIcon,
    bool obscureText = false,
    Widget? suffixIcon,
    TextInputType? keyboardType,
    String? Function(String?)? validator,
  }) {
    return TextFormField(
      controller: controller,
      obscureText: obscureText,
      keyboardType: keyboardType,
      validator: validator,
      style: GoogleFonts.poppins(
        color: AppTheme.textPrimary,
        fontSize: 16,
      ),
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        prefixIcon: Icon(prefixIcon, color: AppTheme.textMuted, size: 22),
        suffixIcon: suffixIcon,
        labelStyle: GoogleFonts.poppins(color: AppTheme.textMuted),
        hintStyle: GoogleFonts.poppins(color: AppTheme.textMuted.withOpacity(0.5)),
      ),
    );
  }
}
